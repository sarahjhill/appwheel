from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PersonalContact


def make_user(name='sam'):
    return get_user_model().objects.create_user(
        username=name, email=f'{name}@example.com', password='a-long-test-password-123'
    )


class HelpPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_logged_out_visitors_are_sent_to_log_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('help_page')).status_code, 302)

    def test_emergency_numbers_are_tap_to_call(self):
        response = self.client.get(reverse('help_page'))
        for link in ['href="tel:999"', 'href="tel:111"', 'href="tel:101"', 'href="tel:116123"']:
            self.assertContains(response, link)
        self.assertContains(response, 'Samaritans')
        self.assertContains(response, 'press 55')

    def test_adding_a_contact_makes_a_tap_to_call_button(self):
        self.client.post(reverse('contact_add'), {
            'label': 'gp', 'name': 'Splott Surgery', 'phone': '029 2000 0000', 'email': '',
        })
        contact = PersonalContact.objects.get()
        self.assertEqual(contact.user, self.user)
        response = self.client.get(reverse('help_page'))
        self.assertContains(response, 'href="tel:02920000000"')
        self.assertContains(response, 'GP surgery')

    def test_international_numbers_keep_the_plus(self):
        contact = PersonalContact(phone='+44 (0)29 2000 0000')
        self.assertEqual(contact.phone_link, 'tel:+4402920000000')

    def test_a_contact_needs_a_phone_or_email(self):
        response = self.client.post(reverse('contact_add'), {'label': 'other', 'name': 'Nobody', 'phone': '', 'email': ''})
        self.assertContains(response, 'Please add a phone number or an email address.')
        self.assertEqual(PersonalContact.objects.count(), 0)

    def test_phone_numbers_must_be_numbers(self):
        response = self.client.post(reverse('contact_add'), {
            'label': 'other', 'name': 'Mum', 'phone': 'call me maybe', 'email': '',
        })
        self.assertContains(response, 'using numbers only')

    def test_editing_and_removing_a_contact(self):
        contact = PersonalContact.objects.create(user=self.user, name='Mum', phone='07700 900000')
        self.client.post(reverse('contact_edit', args=[contact.pk]), {
            'label': 'next_of_kin', 'name': 'Mum', 'phone': '07700 900001', 'email': '',
        })
        contact.refresh_from_db()
        self.assertEqual(contact.label, 'next_of_kin')
        self.client.post(reverse('contact_delete', args=[contact.pk]))
        self.assertEqual(PersonalContact.objects.count(), 0)

    def test_i_never_see_or_change_someone_elses_contacts(self):
        theirs = PersonalContact.objects.create(user=make_user('alex'), name='Alex Private GP', phone='0123')
        self.assertNotContains(self.client.get(reverse('help_page')), 'Alex Private GP')
        self.assertEqual(self.client.get(reverse('contact_edit', args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('contact_delete', args=[theirs.pk])).status_code, 404)
        self.assertTrue(PersonalContact.objects.filter(pk=theirs.pk).exists())
