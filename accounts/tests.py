from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SignUpTests(TestCase):
    def test_someone_can_sign_up_with_email(self):
        response = self.client.post(reverse('account_signup'), {
            'email': 'new@example.com',
            'password1': 'a-long-test-password-123',
            'password2': 'a-long-test-password-123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)

    def test_typing_delete_removes_the_account(self):
        response = self.client.post(reverse('delete_account'), {'confirm': 'DELETE'})
        self.assertRedirects(response, reverse('account_login'))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_without_typing_delete_nothing_happens(self):
        self.client.post(reverse('delete_account'), {'confirm': 'yes'})
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
