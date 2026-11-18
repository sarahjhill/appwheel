from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from contacts.models import PersonalContact
from wheel.models import Subscription

from . import ai

# What Claude might send back: an answer with one web page it used
CLAUDE_ANSWER = {
    'content': [
        {'type': 'server_tool_use', 'name': 'web_search', 'input': {'query': 'Cardiff social services'}},
        {'type': 'web_search_tool_result', 'content': []},
        {'type': 'text', 'text': 'You can contact Cardiff Council adult social services ', 'citations': [
            {'type': 'web_search_result_location', 'url': 'https://www.cardiff.gov.uk/social-care',
             'title': 'Social care - Cardiff Council'},
        ]},
        {'type': 'text', 'text': 'online or by phone.'},
    ],
}


def fake_response(status=200, body=CLAUDE_ANSWER):
    response = mock.Mock(status_code=status)
    response.json.return_value = body
    return response


class SetUpUser(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('sam', password='a-good-password-123')
        Subscription.objects.create(
            user=self.user, name='Sky', price=Decimal('35.00'), next_payment_date=date(2026, 12, 1),
        )
        PersonalContact.objects.create(
            user=self.user, label='gp', name='Heath Surgery', email='heath.surgery@example.nhs.uk',
        )


@override_settings(ANTHROPIC_API_KEY='test-key')
class AskTests(SetUpUser):
    @mock.patch('assistant.ai.requests.post', return_value=fake_response())
    def test_answer_and_sources_are_read(self, post):
        answer, sources = ai.ask(self.user, 'How do I contact social services?', [])
        self.assertEqual(answer, 'You can contact Cardiff Council adult social services online or by phone.')
        self.assertEqual(sources, [{'url': 'https://www.cardiff.gov.uk/social-care',
                                    'title': 'Social care - Cardiff Council'}])

    @mock.patch('assistant.ai.requests.post', return_value=fake_response())
    def test_claude_is_given_the_users_own_apps_and_contacts(self, post):
        ai.ask(self.user, "What's my doctor's email?", [])
        system = post.call_args.kwargs['json']['system']
        self.assertIn('Sky: £35.00', system)
        self.assertIn('heath.surgery@example.nhs.uk', system)
        # The key goes in the header, never the web address
        self.assertEqual(post.call_args.kwargs['headers']['x-api-key'], 'test-key')

    @mock.patch('assistant.ai.requests.post', return_value=fake_response())
    def test_other_peoples_details_are_never_sent(self, post):
        other = get_user_model().objects.create_user('alex', password='a-good-password-123')
        PersonalContact.objects.create(user=other, label='gp', name='Secret Surgery', email='secret@example.com')
        ai.ask(self.user, 'Who is my GP?', [])
        self.assertNotIn('secret@example.com', post.call_args.kwargs['json']['system'])

    def test_empty_question_gives_a_clear_error(self):
        with self.assertRaises(ai.AskError):
            ai.ask(self.user, '   ', [])

    @mock.patch('assistant.ai.requests.post', return_value=fake_response(status=500))
    def test_a_broken_ai_gives_a_clear_error(self, post):
        with self.assertRaises(ai.AskError):
            ai.ask(self.user, 'Hello', [])

    def test_links_that_are_not_https_are_left_out(self):
        body = {'content': [{'type': 'text', 'text': 'Hi', 'citations': [{'url': 'javascript:alert(1)'}]}]}
        self.assertEqual(ai.read_answer(body), ('Hi', []))


@override_settings(ANTHROPIC_API_KEY='test-key')
class AskPageTests(SetUpUser):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_page_shows_suggestions(self):
        response = self.client.get(reverse('ask_page'))
        self.assertContains(response, "What&#x27;s my doctor&#x27;s email?")
        self.assertContains(response, 'How do I contact social services?')

    @mock.patch('assistant.ai.requests.post', return_value=fake_response())
    def test_asking_shows_the_answer_and_where_it_came_from(self, post):
        response = self.client.post(reverse('ask_page'), {'question': 'How do I contact social services?'}, follow=True)
        self.assertContains(response, 'You asked:')
        self.assertContains(response, 'Cardiff Council adult social services')
        self.assertContains(response, 'https://www.cardiff.gov.uk/social-care')

    @mock.patch('assistant.ai.requests.post', return_value=fake_response())
    def test_follow_up_questions_include_the_conversation_so_far(self, post):
        self.client.post(reverse('ask_page'), {'question': 'How do I contact social services?'})
        self.client.post(reverse('ask_page'), {'question': 'What about out of hours?'})
        messages = post.call_args.kwargs['json']['messages']
        self.assertEqual([m['role'] for m in messages], ['user', 'assistant', 'user'])
        self.assertNotIn('sources', messages[1])

    @mock.patch('assistant.ai.requests.post', return_value=fake_response())
    def test_start_a_new_conversation_clears_it(self, post):
        self.client.post(reverse('ask_page'), {'question': 'Hello'})
        self.client.post(reverse('ask_clear'))
        response = self.client.get(reverse('ask_page'))
        self.assertNotContains(response, 'You asked:')

    def test_you_must_be_signed_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('ask_page')).status_code, 302)

    @override_settings(ANTHROPIC_API_KEY='')
    def test_page_explains_when_it_is_not_switched_on(self):
        response = self.client.get(reverse('ask_page'))
        self.assertContains(response, 'switched on yet')
