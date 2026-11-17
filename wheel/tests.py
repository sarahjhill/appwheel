from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Subscription


def make_user(name):
    return get_user_model().objects.create_user(
        username=name, email=f'{name}@example.com', password='a-long-test-password-123'
    )


def valid_form_data(**changes):
    data = {
        'name': 'Netflix',
        'plan_name': 'Standard',
        'category': 'video',
        'price': '12.99',
        'billing_period': 'monthly',
        'next_payment_date': '2026-12-01',
        'trial_end_date': '',
        'usage': 'weekly',
        'benefits': 'no adverts',
    }
    data.update(changes)
    return data


class LoggedOutTests(TestCase):
    def test_logged_out_visitors_are_sent_to_log_in(self):
        for name in ['subscription_list', 'subscription_add']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('account_login'), response.url)


class AddAppTests(TestCase):
    def setUp(self):
        self.user = make_user('sam')
        self.client.force_login(self.user)

    def test_add_page_shows_the_form(self):
        response = self.client.get(reverse('subscription_add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add an app')

    def test_adding_an_app_saves_it_for_me(self):
        response = self.client.post(reverse('subscription_add'), valid_form_data())
        self.assertRedirects(response, reverse('subscription_list'))
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.name, 'Netflix')
        self.assertEqual(subscription.price, Decimal('12.99'))
        self.assertEqual(subscription.next_payment_date, date(2026, 12, 1))
        self.assertIsNone(subscription.trial_end_date)

    def test_free_apps_can_be_added_with_a_price_of_zero(self):
        self.client.post(reverse('subscription_add'), valid_form_data(name='Duolingo', price='0'))
        self.assertEqual(Subscription.objects.get().price, Decimal('0'))

    def test_a_trial_end_date_can_be_added(self):
        self.client.post(reverse('subscription_add'), valid_form_data(trial_end_date='2026-11-30'))
        self.assertEqual(Subscription.objects.get().trial_end_date, date(2026, 11, 30))

    def test_price_cannot_be_negative(self):
        response = self.client.post(reverse('subscription_add'), valid_form_data(price='-5'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_name_is_required(self):
        response = self.client.post(reverse('subscription_add'), valid_form_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)


class OnlyMyAppsTests(TestCase):
    def test_i_only_see_my_own_apps(self):
        me = make_user('sam')
        someone_else = make_user('alex')
        Subscription.objects.create(user=me, name='Spotify', price=Decimal('11.99'))
        Subscription.objects.create(user=someone_else, name='Disney+', price=Decimal('4.99'))

        self.client.force_login(me)
        response = self.client.get(reverse('subscription_list'))
        self.assertContains(response, 'Spotify')
        self.assertNotContains(response, 'Disney+')

    def test_the_form_cannot_add_an_app_to_someone_elses_account(self):
        me = make_user('sam')
        someone_else = make_user('alex')
        self.client.force_login(me)
        self.client.post(reverse('subscription_add'), valid_form_data(user=someone_else.pk))
        self.assertEqual(Subscription.objects.get().user, me)
