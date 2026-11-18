from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .screenshot import ScreenshotError, read_pasted_text

# What Claude might send back after reading a pasted Sky bill
CLAUDE_ANSWER = {
    'content': [{
        'type': 'tool_use',
        'name': 'record_subscriptions',
        'input': {'subscriptions': [
            {'name': 'Sky Broadband', 'plan_name': 'Superfast', 'price': 35, 'billing_period': 'monthly',
             'next_payment_date': '2026-12-01', 'category': 'other'},
        ]},
    }],
}


def fake_response(status=200, body=CLAUDE_ANSWER):
    response = mock.Mock(status_code=status)
    response.json.return_value = body
    return response


@override_settings(ANTHROPIC_API_KEY='test-key')
class ReadPastedTextTests(TestCase):
    @mock.patch('wheel.screenshot.requests.post', return_value=fake_response())
    def test_reads_a_bill_from_pasted_text(self, post):
        found = read_pasted_text('Your Sky bill: Superfast broadband £35.00 a month')
        # AppWheel already knows Sky, so it uses its own name for it
        self.assertEqual(found[0]['name'], 'Sky')
        self.assertEqual(found[0]['price'], '35.00')
        self.assertEqual(found[0]['next_payment_date'], '2026-12-01')
        # The text is sent to Claude
        sent = post.call_args.kwargs['json']['messages'][0]['content']
        self.assertIn('Superfast broadband', sent)

    def test_empty_text_gives_a_clear_error(self):
        with self.assertRaises(ScreenshotError):
            read_pasted_text('   ')

    @mock.patch('wheel.screenshot.requests.post', return_value=fake_response(status=500))
    def test_a_broken_ai_reader_gives_a_clear_error(self, post):
        with self.assertRaises(ScreenshotError):
            read_pasted_text('Netflix £12.99')


@override_settings(ANTHROPIC_API_KEY='test-key')
class PasteTextPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('sam', password='a-good-password-123')
        self.client.force_login(self.user)

    def test_page_loads(self):
        response = self.client.get(reverse('paste_text'))
        self.assertContains(response, 'Paste a bill or email')

    @mock.patch('wheel.screenshot.requests.post', return_value=fake_response())
    def test_pasting_a_bill_goes_to_the_review_page(self, post):
        response = self.client.post(reverse('paste_text'), {'text': 'Sky bill £35 a month'})
        self.assertRedirects(response, reverse('statement_review'))
        # Nothing is saved until the user ticks it on the review page
        self.assertEqual(self.user.subscriptions.count(), 0)

    def test_you_must_be_signed_in(self):
        self.client.logout()
        response = self.client.get(reverse('paste_text'))
        self.assertEqual(response.status_code, 302)
