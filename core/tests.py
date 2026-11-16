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
