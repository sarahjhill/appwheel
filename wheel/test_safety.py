from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reminders.automatic import keep_privacy_checkup
from reminders.models import Reminder

from .health import AMBER, GREEN, score_subscription
from .models import CommonApp, Subscription

TODAY = date.today()


class SafetyGuideTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)
        self.instagram = CommonApp.objects.get(name='Instagram')

    def add_instagram(self):
        return Subscription.objects.create(
            user=self.user, name='Instagram', price=Decimal('0'), category='social',
            common_app=self.instagram, usage='daily',
        )

    def test_six_social_apps_each_have_six_guides_with_official_links(self):
        for name in ['Facebook', 'Instagram', 'TikTok', 'WhatsApp', 'X', 'Snapchat']:
            app = CommonApp.objects.get(name=name)
            self.assertEqual(app.category, 'social')
            self.assertEqual(app.safety_guides.count(), 6)
            self.assertTrue(all(guide.help_url.startswith('https://') for guide in app.safety_guides.all()))

    def test_choosing_a_social_app_fills_in_a_price_of_zero(self):
        response = self.client.get(reverse('subscription_add'), {'app': 'instagram'})
        self.assertContains(response, 'value="0"')

    def test_guides_without_steps_send_people_to_the_official_help_page(self):
        self.add_instagram()
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Safety &amp; privacy')
        self.assertContains(response, 'Block someone')
        self.assertContains(response, 'href="https://help.instagram.com"')
        self.assertContains(response, 'Always check the official help page.')

    def test_guides_with_steps_show_them_and_the_last_checked_date(self):
        guide = self.instagram.safety_guides.get(title='Block someone')
        guide.steps = 'Go to their profile\nTap the three dots\nTap Block'
        guide.last_checked = date(2026, 11, 18)
        guide.save()
        sub = self.add_instagram()
        response = self.client.get(reverse('safety_guides', args=[sub.pk]))
        self.assertContains(response, '<li>Tap Block</li>')
        self.assertContains(response, 'Last checked: 18 November 2026')

    def test_someone_elses_guides_page_is_not_found(self):
        other = get_user_model().objects.create_user(
            username='alex', email='alex@example.com', password='a-long-test-password-123'
        )
        theirs = Subscription.objects.create(user=other, name='Instagram', price=Decimal('0'))
        self.assertEqual(self.client.get(reverse('safety_guides', args=[theirs.pk])).status_code, 404)


class PrivacyCheckupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )

    def add_social(self):
        return Subscription.objects.create(
            user=self.user, name='TikTok', price=Decimal('0'), category='social', usage='daily',
        )

    def test_no_social_apps_means_no_privacy_checkup(self):
        Subscription.objects.create(user=self.user, name='Netflix', price=Decimal('12.99'), category='video')
        keep_privacy_checkup(self.user, TODAY)
        self.assertFalse(Reminder.objects.filter(kind='privacy').exists())

    def test_a_social_app_starts_a_monthly_privacy_checkup(self):
        self.add_social()
        keep_privacy_checkup(self.user, TODAY)
        reminder = Reminder.objects.get(kind='privacy')
        self.assertEqual(reminder.due_date, TODAY)
        self.assertEqual(reminder.repeat_every_days, 30)

    def test_social_app_is_amber_when_the_checkup_is_due_and_green_once_done(self):
        sub = self.add_social()
        keep_privacy_checkup(self.user, TODAY)
        health = score_subscription(sub, [sub], today=TODAY)
        self.assertEqual(health.light, AMBER)
        self.assertIn('Privacy check-up due', health.reason)

        self.client.force_login(self.user)
        reminder = Reminder.objects.get(kind='privacy')
        self.client.post(reverse('reminder_done', args=[reminder.pk]))
        next_one = Reminder.objects.get(kind='privacy', is_done=False)
        self.assertEqual(next_one.due_date, TODAY + timedelta(days=30))

        health = score_subscription(sub, [sub], today=TODAY)
        self.assertEqual(health.light, GREEN)
        self.assertEqual(health.reason, 'Your privacy check-up is up to date.')

    def test_removing_the_last_social_app_stops_the_checkup(self):
        sub = self.add_social()
        keep_privacy_checkup(self.user, TODAY)
        sub.delete()
        keep_privacy_checkup(self.user, TODAY)
        self.assertFalse(Reminder.objects.filter(kind='privacy', is_done=False).exists())

    def test_two_social_apps_are_not_flagged_as_doing_the_same_job(self):
        first = self.add_social()
        second = Subscription.objects.create(
            user=self.user, name='WhatsApp', price=Decimal('0'), category='social', usage='daily',
        )
        health = score_subscription(first, [first, second], today=TODAY)
        self.assertNotIn('similar job', health.reason)
