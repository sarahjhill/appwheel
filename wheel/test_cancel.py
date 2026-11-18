from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reminders.models import Reminder

from .health import summarise
from .models import CommonApp, Subscription
from .views import charge_check_date


class CancelWithHelpTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)
        self.next_payment = date.today() + timedelta(days=10)
        self.netflix = Subscription.objects.create(
            user=self.user, name='Netflix', price=Decimal('12.99'), next_payment_date=self.next_payment,
        )

    def test_cancel_page_shows_steps_for_each_way_of_paying(self):
        response = self.client.get(reverse('cancel_help', args=[self.netflix.pk]))
        self.assertContains(response, 'Cancel Netflix')
        self.assertContains(response, 'Through my iPhone or iPad (Apple)')
        self.assertContains(response, 'Through Google Play (Android)')
        self.assertContains(response, "I've cancelled Netflix")

    def test_cancel_page_uses_the_companys_own_link_and_steps(self):
        common = CommonApp.objects.get(name='Netflix')
        common.cancel_url = 'https://www.example.com/cancel'
        common.cancel_steps = 'Sign in\nGo to Account\nChoose Cancel membership'
        common.save()
        self.netflix.common_app = common
        self.netflix.save()
        response = self.client.get(reverse('cancel_help', args=[self.netflix.pk]))
        self.assertContains(response, 'href="https://www.example.com/cancel"')
        self.assertContains(response, '<li>Choose Cancel membership</li>')
        self.assertNotContains(response, 'Through Google Play')

    def test_ive_cancelled_takes_it_off_the_totals_and_sets_a_reminder(self):
        response = self.client.post(reverse('mark_cancelled', args=[self.netflix.pk]))
        self.assertRedirects(response, reverse('subscription_list'))
        self.netflix.refresh_from_db()
        self.assertEqual(self.netflix.status, 'cancelled')
        self.assertEqual(self.netflix.cancelled_on, date.today())

        summary = summarise(list(self.user.subscriptions.all()))
        self.assertEqual(summary['monthly_total'], Decimal('0'))

        reminder = Reminder.objects.get(kind='charge_check')
        self.assertEqual(reminder.user, self.user)
        self.assertEqual(reminder.title, "Check you weren't charged by Netflix")
        self.assertEqual(reminder.due_date, self.next_payment + timedelta(days=1))

    def test_cancelling_twice_does_not_make_two_reminders(self):
        self.client.post(reverse('mark_cancelled', args=[self.netflix.pk]))
        self.client.post(reverse('mark_cancelled', args=[self.netflix.pk]))
        self.assertEqual(Reminder.objects.filter(kind='charge_check').count(), 1)

    def test_cancelled_apps_leave_the_wheel_and_show_in_the_cancelled_list(self):
        self.client.post(reverse('mark_cancelled', args=[self.netflix.pk]))
        home = self.client.get(reverse('home'))
        self.assertEqual(home.context['apps'], [])
        listing = self.client.get(reverse('subscription_list'))
        self.assertContains(listing, 'Cancelled')
        self.assertContains(listing, 'Charged after cancelling?')

    def test_put_back_on_my_wheel_undoes_it(self):
        self.client.post(reverse('mark_cancelled', args=[self.netflix.pk]))
        self.client.post(reverse('mark_active', args=[self.netflix.pk]))
        self.netflix.refresh_from_db()
        self.assertEqual(self.netflix.status, 'active')
        # The "check you weren't charged" reminder goes; the usual renewal reminder comes back
        self.assertEqual(list(Reminder.objects.values_list('kind', flat=True)), ['renewal'])

    def test_refund_request_is_ready_written(self):
        self.client.post(reverse('mark_cancelled', args=[self.netflix.pk]))
        response = self.client.get(reverse('refund_request', args=[self.netflix.pk]))
        self.assertContains(response, 'I cancelled my Netflix subscription on')
        self.assertContains(response, 'I was charged £12.99')
        self.assertContains(response, 'sam@example.com')
        self.assertContains(response, 'Direct Debit Guarantee')

    def test_i_cannot_cancel_someone_elses_app(self):
        someone_else = get_user_model().objects.create_user(
            username='alex', email='alex@example.com', password='a-long-test-password-123'
        )
        theirs = Subscription.objects.create(user=someone_else, name='Disney+', price=Decimal('4.99'))
        for name in ['cancel_help', 'refund_request']:
            self.assertEqual(self.client.get(reverse(name, args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('mark_cancelled', args=[theirs.pk])).status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, 'active')

    def test_check_date_when_no_next_payment_date_is_known(self):
        today = date(2026, 11, 17)
        sub = Subscription(name='Gym', price=Decimal('20'), billing_period='monthly')
        self.assertEqual(charge_check_date(sub, today), date(2026, 12, 17))
