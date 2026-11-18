from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from wheel.models import Subscription

from .automatic import _add_period, roll_forward_payment_dates
from .models import ChecklistItem, Reminder

TODAY = date.today()


def make_user(name='sam'):
    return get_user_model().objects.create_user(
        username=name, email=f'{name}@example.com', password='a-long-test-password-123'
    )


class AutomaticReminderTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def add(self, **details):
        details.setdefault('name', 'Netflix')
        details.setdefault('price', Decimal('12.99'))
        return Subscription.objects.create(user=self.user, **details)

    def test_a_trial_ending_in_2_days_creates_a_reminder_due_today(self):
        self.add(name='Headway', trial_end_date=TODAY + timedelta(days=2))
        reminder = Reminder.objects.get(kind='trial')
        self.assertEqual(reminder.due_date, TODAY)
        self.assertIn('Headway free trial ends', reminder.title)
        self.assertIn('£12.99', reminder.details)

    def test_a_payment_creates_a_renewal_reminder_3_days_before(self):
        self.add(next_payment_date=TODAY + timedelta(days=10))
        reminder = Reminder.objects.get(kind='renewal')
        self.assertEqual(reminder.due_date, TODAY + timedelta(days=7))
        self.assertIn('£12.99', reminder.title)

    def test_free_apps_get_no_renewal_reminder(self):
        self.add(price=Decimal('0'), next_payment_date=TODAY + timedelta(days=10))
        self.assertFalse(Reminder.objects.filter(kind='renewal').exists())

    def test_changing_the_date_moves_the_reminder(self):
        sub = self.add(next_payment_date=TODAY + timedelta(days=10))
        sub.next_payment_date = TODAY + timedelta(days=20)
        sub.save()
        self.assertEqual(Reminder.objects.get(kind='renewal').due_date, TODAY + timedelta(days=17))

    def test_removing_the_trial_date_removes_the_reminder(self):
        sub = self.add(trial_end_date=TODAY + timedelta(days=5))
        sub.trial_end_date = None
        sub.save()
        self.assertFalse(Reminder.objects.filter(kind='trial').exists())

    def test_cancelling_removes_trial_and_renewal_reminders(self):
        sub = self.add(trial_end_date=TODAY + timedelta(days=5), next_payment_date=TODAY + timedelta(days=9))
        self.client.force_login(self.user)
        self.client.post(reverse('mark_cancelled', args=[sub.pk]))
        kinds = set(Reminder.objects.values_list('kind', flat=True))
        self.assertEqual(kinds, {'charge_check'})

    def test_deleting_an_app_removes_its_automatic_reminders(self):
        sub = self.add(next_payment_date=TODAY + timedelta(days=9))
        sub.delete()
        self.assertEqual(Reminder.objects.count(), 0)

    def test_payment_dates_that_have_passed_move_to_the_next_one(self):
        sub = self.add(next_payment_date=TODAY - timedelta(days=3))
        roll_forward_payment_dates(self.user)
        sub.refresh_from_db()
        self.assertGreaterEqual(sub.next_payment_date, TODAY)
        self.assertTrue(Reminder.objects.filter(kind='renewal').exists())

    def test_apps_added_before_reminders_existed_get_them_when_the_page_opens(self):
        sub = self.add(next_payment_date=TODAY + timedelta(days=10))
        Reminder.objects.all().delete()  # as if added before Stage 6
        self.client.force_login(self.user)
        self.client.get(reverse('reminder_list'))
        self.assertTrue(sub.reminders.filter(kind='renewal').exists())

    def test_adding_a_month_handles_short_months(self):
        self.assertEqual(_add_period(date(2027, 1, 31), 'monthly'), date(2027, 2, 28))
        self.assertEqual(_add_period(date(2026, 12, 5), 'monthly'), date(2027, 1, 5))
        self.assertEqual(_add_period(date(2026, 12, 5), 'yearly'), date(2027, 12, 5))
        self.assertEqual(_add_period(date(2026, 12, 5), 'weekly'), date(2026, 12, 12))


class RemindersPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_logged_out_visitors_are_sent_to_log_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('reminder_list')).status_code, 302)

    def test_reminders_are_grouped_into_this_week_later_and_done(self):
        Reminder.objects.create(user=self.user, title='Soon thing', due_date=TODAY + timedelta(days=2))
        Reminder.objects.create(user=self.user, title='Far thing', due_date=TODAY + timedelta(days=30))
        Reminder.objects.create(user=self.user, title='Old thing', due_date=TODAY, is_done=True)
        response = self.client.get(reverse('reminder_list'))
        self.assertEqual([r.title for r in response.context['this_week']], ['Soon thing'])
        self.assertEqual([r.title for r in response.context['later']], ['Far thing'])
        self.assertEqual([r.title for r in response.context['done']], ['Old thing'])

    def test_appointments_start_with_a_what_to_bring_checklist(self):
        response = self.client.get(reverse('reminder_add'), {'kind': 'appointment'})
        self.assertContains(response, 'Add an appointment')
        self.assertContains(response, 'Appointment letter')
        self.assertContains(response, 'Someone to come with you?')

        self.client.post(reverse('reminder_add'), {
            'kind': 'appointment', 'title': 'GP appointment', 'due_date': (TODAY + timedelta(days=8)).isoformat(),
            'time': '10:30', 'details': '', 'repeat_every_days': '',
            'checklist_text': 'Appointment letter\nList of your medication',
        })
        reminder = Reminder.objects.get()
        self.assertEqual(reminder.user, self.user)
        self.assertEqual([item.text for item in reminder.checklist.all()], ['Appointment letter', 'List of your medication'])

    def test_ticking_a_checklist_item(self):
        reminder = Reminder.objects.create(user=self.user, title='GP', due_date=TODAY, kind='appointment')
        item = ChecklistItem.objects.create(reminder=reminder, text='Appointment letter')
        self.client.post(reverse('checklist_tick', args=[item.pk]), {'ticked': 'on'})
        item.refresh_from_db()
        self.assertTrue(item.ticked)
        self.client.post(reverse('checklist_tick', args=[item.pk]), {})
        item.refresh_from_db()
        self.assertFalse(item.ticked)

    def test_a_repeat_prescription_makes_the_next_reminder_when_done(self):
        reminder = Reminder.objects.create(
            user=self.user, title='Order my repeat prescription', kind='prescription',
            due_date=TODAY, repeat_every_days=28,
        )
        self.client.post(reverse('reminder_done', args=[reminder.pk]))
        reminder.refresh_from_db()
        self.assertTrue(reminder.is_done)
        next_one = Reminder.objects.get(is_done=False)
        self.assertEqual(next_one.due_date, TODAY + timedelta(days=28))

    def test_prescription_reminders_link_to_the_nhs_app(self):
        Reminder.objects.create(user=self.user, title='Order', kind='prescription', due_date=TODAY)
        self.assertContains(self.client.get(reverse('reminder_list')), 'Open the NHS App')

    def test_automatic_reminders_cannot_be_edited(self):
        sub = Subscription.objects.create(
            user=self.user, name='Netflix', price=Decimal('12.99'), next_payment_date=TODAY + timedelta(days=5),
        )
        reminder = sub.reminders.get()
        response = self.client.get(reverse('reminder_edit', args=[reminder.pk]))
        self.assertRedirects(response, reverse('reminder_list'))

    def test_i_cannot_see_or_change_someone_elses_reminders(self):
        theirs = Reminder.objects.create(user=make_user('alex'), title='Their secret', due_date=TODAY)
        item = ChecklistItem.objects.create(reminder=theirs, text='Private')
        self.assertNotContains(self.client.get(reverse('reminder_list')), 'Their secret')
        for name in ['reminder_edit', 'reminder_delete']:
            self.assertEqual(self.client.get(reverse(name, args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('reminder_done', args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('checklist_tick', args=[item.pk]), {'ticked': 'on'}).status_code, 404)
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_done)

    def test_the_wheel_shows_whats_coming_up(self):
        Subscription.objects.create(
            user=self.user, name='Netflix', price=Decimal('12.99'), next_payment_date=TODAY + timedelta(days=5),
        )
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Coming up')
        self.assertContains(response, 'Netflix renews')
