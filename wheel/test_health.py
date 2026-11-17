from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .health import AMBER, GREEN, RED, score_subscription, summarise
from .models import CommonApp, Subscription

TODAY = date(2026, 11, 17)


class HealthTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )

    def add(self, name, price='9.99', **details):
        details.setdefault('category', 'other')
        details.setdefault('usage', 'weekly')
        return Subscription.objects.create(user=self.user, name=name, price=Decimal(price), **details)

    def score(self, sub):
        return score_subscription(sub, list(self.user.subscriptions.all()), today=TODAY)


class MonthlyCostTests(HealthTestCase):
    def test_monthly_cost_for_each_way_of_paying(self):
        self.assertEqual(self.add('A', '10.00', billing_period='monthly').monthly_cost, Decimal('10.00'))
        self.assertEqual(self.add('B', '120.00', billing_period='yearly').monthly_cost, Decimal('10.00'))
        self.assertEqual(self.add('C', '3.00', billing_period='weekly').monthly_cost, Decimal('13.00'))
        self.assertEqual(self.add('D', '10.00').yearly_cost, Decimal('120.00'))


class HealthRuleTests(HealthTestCase):
    def test_used_often_and_nothing_cheaper_is_green(self):
        health = self.score(self.add('Spotify', category='music', usage='daily'))
        self.assertEqual(health.light, GREEN)
        self.assertEqual(health.score, 100)
        self.assertEqual(health.tips, [])

    def test_free_apps_are_green(self):
        health = self.score(self.add('Duolingo', '0', usage='never'))
        self.assertEqual(health.light, GREEN)

    def test_a_trial_ending_in_3_days_is_red(self):
        health = self.score(self.add('Headway', trial_end_date=TODAY + timedelta(days=3)))
        self.assertEqual(health.light, RED)
        self.assertIn('in 3 days', health.reason)
        self.assertIn('Cancel before 20 November', health.tips[0].text)

    def test_a_trial_ending_in_10_days_is_not_red(self):
        health = self.score(self.add('Headway', trial_end_date=TODAY + timedelta(days=10)))
        self.assertEqual(health.light, GREEN)

    def test_rarely_used_is_red_with_the_yearly_saving(self):
        health = self.score(self.add('Gym', '20.00', usage='rarely'))
        self.assertEqual(health.light, RED)
        self.assertIn('£240.00 a year', health.reason)
        self.assertEqual(health.tips[0].yearly_saving, Decimal('240.00'))

    def test_two_apps_doing_the_same_job_are_amber(self):
        spotify = self.add('Spotify', '11.99', category='music', usage='daily')
        apple = self.add('Apple Music', '10.99', category='music', usage='monthly')
        health = self.score(spotify)
        self.assertEqual(health.light, AMBER)
        self.assertIn('also pay for Apple Music, which does a similar job', health.reason)
        # Spotify is used most, so it's the one to keep: no "cancel" tip for it
        self.assertEqual(health.tips, [])
        apple_health = self.score(apple)
        self.assertEqual(apple_health.tips[0].text, 'Cancel Apple Music and keep Spotify to save £131.88 a year')

    def test_savings_never_add_up_to_cancelling_everything(self):
        self.add('Netflix', '12.99', category='video')
        self.add('Sky', '85.31', category='video')
        self.add('Sky TV', '118.90', category='video')
        summary = summarise(list(self.user.subscriptions.all()), today=TODAY)
        # Netflix is the cheapest of three used equally, so keep it and save on the other two
        self.assertEqual(summary['possible_yearly_saving'], Decimal('2450.52'))

    def test_two_other_category_apps_are_not_compared(self):
        health = self.score(self.add('EE', category='other'))
        self.add('Patreon', category='other')
        self.assertEqual(health.light, GREEN)

    def test_a_cheaper_plan_is_amber_with_the_saving(self):
        netflix = CommonApp.objects.get(name='Netflix')
        netflix.plans.create(name='Standard with adverts', price=Decimal('7.99'))
        netflix.plans.create(name='Standard', price=Decimal('12.99'))
        netflix.plans.create(name='Premium', price=Decimal('20.99'))
        health = self.score(self.add('Netflix', '20.99', plan_name='Premium', common_app=netflix, category='video'))
        self.assertEqual(health.light, AMBER)
        self.assertIn('Standard at £12.99', health.reason)
        self.assertEqual(health.tips[0].yearly_saving, Decimal('96.00'))

    def test_cheapest_plan_has_no_cheaper_plan_tip(self):
        netflix = CommonApp.objects.get(name='Netflix')
        netflix.plans.create(name='Standard with adverts', price=Decimal('7.99'))
        health = self.score(self.add('Netflix', '7.99', plan_name='Standard with adverts', category='video'))
        self.assertEqual(health.light, GREEN)

    def test_paying_monthly_when_yearly_is_cheaper_is_amber(self):
        spotify = CommonApp.objects.get(name='Spotify')
        spotify.plans.create(name='Individual', price=Decimal('11.99'))
        spotify.plans.create(name='Individual yearly', price=Decimal('120.00'), billing_period='yearly')
        health = self.score(self.add('Spotify', '11.99', plan_name='Individual', category='music', common_app=spotify))
        self.assertEqual(health.light, AMBER)
        self.assertEqual(health.tips[0].yearly_saving, Decimal('23.88'))

    def test_red_beats_amber_and_lowers_the_score(self):
        self.add('Apple Music', category='music')
        health = self.score(self.add('Spotify', category='music', usage='never'))
        self.assertEqual(health.light, RED)
        self.assertEqual(health.score, 30)


class TotalsTests(HealthTestCase):
    def test_totals_add_up_active_apps_only(self):
        self.add('Netflix', '12.99', usage='daily')
        self.add('Gym', '20.00', usage='never')
        self.add('Old app', '50.00', status='cancelled')
        summary = summarise(list(self.user.subscriptions.all()), today=TODAY)
        self.assertEqual(summary['monthly_total'], Decimal('32.99'))
        self.assertEqual(summary['yearly_total'], Decimal('395.88'))
        self.assertEqual(summary['possible_yearly_saving'], Decimal('240.00'))
        self.assertEqual(summary['counts'], {GREEN: 1, AMBER: 0, RED: 1})

    def test_my_apps_page_shows_totals_lights_and_tips(self):
        self.add('Gym', '20.00', usage='never')
        self.client.force_login(self.user)
        response = self.client.get(reverse('subscription_list'))
        self.assertContains(response, '£20.00')
        self.assertContains(response, 'You could save up to')
        self.assertContains(response, 'Needs action')
        self.assertContains(response, 'Ways to save')
        self.assertContains(response, 'Cancel Gym to save £240.00 a year')
