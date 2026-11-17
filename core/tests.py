from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_logged_out_visitors_are_sent_to_log_in(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)

    def test_logged_in_users_see_the_home_page(self):
        user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spins all your apps into control')


class WheelPageTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from wheel.models import Subscription
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)
        self.Subscription = Subscription
        self.Decimal = Decimal

    def add(self, name, price, **details):
        return self.Subscription.objects.create(user=self.user, name=name, price=self.Decimal(price), **details)

    def test_with_no_apps_the_home_page_helps_me_add_some(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Upload bank statements')
        self.assertNotContains(response, 'Spin the wheel')

    def test_my_apps_are_on_the_wheel_with_labels_lights_and_cards(self):
        self.add('Netflix', '12.99', usage='daily')
        self.add('Gym', '20.00', usage='never')
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Spin the wheel')
        self.assertContains(response, 'aria-label="Netflix, £12.99 a month, good value"')
        self.assertContains(response, 'aria-label="Gym, £20.00 a month, needs action"')
        self.assertContains(response, '<dialog class="app-card"', count=2)
        self.assertContains(response, 'Cancel Gym to save £240.00 a year')
        self.assertContains(response, '£32.99')

    def test_the_biggest_cost_starts_at_the_top(self):
        self.add('Cheap', '1.00')
        self.add('Dear', '50.00')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['apps'][0].name, 'Dear')

    def test_only_12_apps_go_on_the_wheel(self):
        for number in range(14):
            self.add(f'App {number}', f'{number + 1}.00')
        response = self.client.get(reverse('home'))
        self.assertEqual(len(response.context['apps']), 12)
        self.assertContains(response, '2 more in')

    def test_cancelled_apps_and_other_peoples_apps_are_not_on_my_wheel(self):
        self.add('Old', '5.00', status='cancelled')
        someone_else = get_user_model().objects.create_user(
            username='alex', email='alex@example.com', password='a-long-test-password-123'
        )
        self.Subscription.objects.create(user=someone_else, name='Theirs', price=self.Decimal('9.99'))
        self.add('Mine', '3.00')
        response = self.client.get(reverse('home'))
        names = [app.name for app in response.context['apps']]
        self.assertEqual(names, ['Mine'])
