import io
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Subscription
from .screenshot import ScreenshotError, read_screenshot

# What Claude might send back after reading an iPhone Subscriptions page
CLAUDE_ANSWER = {
    'content': [{
        'type': 'tool_use',
        'name': 'record_subscriptions',
        'input': {'subscriptions': [
            {'name': 'Netflix', 'plan_name': 'Standard', 'price': 12.99, 'billing_period': 'monthly',
             'next_payment_date': '2026-12-03', 'category': 'video'},
            {'name': 'Headway: Book Summaries', 'price': 9.99, 'billing_period': 'monthly',
             'next_payment_date': '2026-11-25', 'trial_end_date': '2026-11-24', 'category': 'books'},
            {'name': 'iCloud+', 'plan_name': '200 GB', 'price': 2.99, 'billing_period': 'monthly',
             'next_payment_date': 'not a date', 'category': 'storage'},
        ]},
    }],
}


def fake_screenshot(name='IMG_0001.PNG'):
    buffer = io.BytesIO()
    Image.new('RGB', (390, 844), 'white').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


def fake_response(status=200, body=CLAUDE_ANSWER):
    response = mock.Mock(status_code=status)
    response.json.return_value = body
    return response


@override_settings(ANTHROPIC_API_KEY='test-key')
class ReadScreenshotTests(TestCase):
    @mock.patch('wheel.screenshot.requests.post', return_value=fake_response())
    def test_reads_subscriptions_from_a_screenshot(self, post):
        found = {item['name']: item for item in read_screenshot(fake_screenshot())}
        self.assertEqual(found['Netflix']['price'], '12.99')
        self.assertEqual(found['Netflix']['plan_name'], 'Standard')
        self.assertEqual(found['Netflix']['next_payment_date'], '2026-12-03')
        self.assertEqual(found['Headway: Book Summaries']['trial_end_date'], '2026-11-24')
        # A date Claude got wrong is left blank, not saved as rubbish
        self.assertEqual(found['iCloud+']['next_payment_date'], '')
        # The picture is sent, and the key goes in the header (never the web address)
        sent = post.call_args.kwargs
        self.assertEqual(sent['headers']['x-api-key'], 'test-key')
        self.assertEqual(sent['json']['messages'][0]['content'][0]['type'], 'image')

    def test_a_file_that_is_not_a_picture_gives_a_clear_error(self):
        with self.assertRaises(ScreenshotError):
            read_screenshot(SimpleUploadedFile('notes.png', b'not a picture'))

    @mock.patch('wheel.screenshot.requests.post', return_value=fake_response(status=500, body={}))
    def test_a_problem_with_the_ai_gives_a_friendly_error(self, post):
        with self.assertRaises(ScreenshotError):
            read_screenshot(fake_screenshot())


class ScreenshotPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)

    def test_logged_out_visitors_are_sent_to_log_in(self):
        self.client.logout()
        response = self.client.get(reverse('screenshot_upload'))
        self.assertEqual(response.status_code, 302)

    @override_settings(ANTHROPIC_API_KEY='')
    def test_screenshot_button_is_hidden_until_switched_on(self):
        response = self.client.get(reverse('subscription_list'))
        self.assertNotContains(response, 'Upload a screenshot')

    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_screenshot_button_shows_when_switched_on(self):
        response = self.client.get(reverse('subscription_list'))
        self.assertContains(response, 'Upload a screenshot')

    @override_settings(ANTHROPIC_API_KEY='')
    def test_page_explains_when_screenshots_are_not_switched_on(self):
        response = self.client.get(reverse('screenshot_upload'))
        self.assertContains(response, "isn't switched on yet")

    @override_settings(ANTHROPIC_API_KEY='test-key')
    @mock.patch('wheel.screenshot.requests.post', return_value=fake_response())
    def test_upload_screenshot_then_add_ticked_apps(self, post):
        response = self.client.post(reverse('screenshot_upload'), {'screenshots': fake_screenshot()})
        self.assertRedirects(response, reverse('statement_review'))
        response = self.client.get(reverse('statement_review'))
        self.assertContains(response, 'Renews 2026-12-03')
        self.assertContains(response, 'Free trial ends 2026-11-24')
        self.assertEqual(Subscription.objects.count(), 0)  # nothing saved until ticked

        found = self.client.session['statement_found']
        everything = [str(i) for i in range(len(found))]
        self.client.post(reverse('statement_review'), {'add': everything})
        netflix = Subscription.objects.get(name='Netflix')
        self.assertEqual(netflix.user, self.user)
        self.assertEqual(netflix.price, Decimal('12.99'))
        self.assertEqual(netflix.plan_name, 'Standard')
        self.assertEqual(Subscription.objects.count(), 3)
        self.assertIsNotNone(Subscription.objects.get(name='Headway: Book Summaries').trial_end_date)
