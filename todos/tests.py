from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from django.urls import reverse

from .models import Todo

AJAX = {'HTTP_X_REQUESTED_WITH': 'fetch'}


def make_user(name='sam'):
    return get_user_model().objects.create_user(
        username=name, email=f'{name}@example.com', password='a-long-test-password-123'
    )


class TodoPanelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_the_panel_is_on_every_page_when_logged_in(self):
        for name in ['home', 'subscription_list', 'reminder_list', 'help_page']:
            response = self.client.get(reverse(name))
            self.assertContains(response, 'data-todo-panel')
            self.assertContains(response, 'To do')

    def test_the_panel_is_not_shown_when_logged_out(self):
        self.client.logout()
        self.assertNotContains(self.client.get(reverse('account_login')), 'data-todo-panel')

    def test_adding_in_the_background_returns_the_new_list(self):
        response = self.client.post(reverse('todo_add'), {'text': 'Phone the GP', 'next': '/apps/'}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Phone the GP')
        self.assertContains(response, 'data-todo-count="1"')
        self.assertContains(response, 'data-todo-announce="Added: Phone the GP"')
        self.assertEqual(Todo.objects.get().user, self.user)

    def test_adding_without_javascript_goes_back_to_the_same_page(self):
        response = self.client.post(reverse('todo_add'), {'text': 'Phone the GP', 'next': '/reminders/'})
        self.assertRedirects(response, '/reminders/')

    def test_it_never_redirects_to_another_website(self):
        response = self.client.post(reverse('todo_add'), {'text': 'x', 'next': 'https://evil.example.com/'})
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_empty_to_dos_are_not_added(self):
        self.client.post(reverse('todo_add'), {'text': '   '}, **AJAX)
        self.assertEqual(Todo.objects.count(), 0)

    def test_ticking_moves_it_to_done_and_back(self):
        todo = Todo.objects.create(user=self.user, text='Check my Sky bill')
        response = self.client.post(reverse('todo_toggle', args=[todo.pk]), **AJAX)
        todo.refresh_from_db()
        self.assertTrue(todo.done)
        self.assertIsNotNone(todo.done_at)
        self.assertContains(response, 'Done (1)')
        self.assertContains(response, 'data-todo-count="0"')
        self.client.post(reverse('todo_toggle', args=[todo.pk]), **AJAX)
        todo.refresh_from_db()
        self.assertFalse(todo.done)

    def test_editing(self):
        todo = Todo.objects.create(user=self.user, text='Phone GP')
        self.client.post(reverse('todo_edit', args=[todo.pk]), {'text': 'Phone the GP about my letter'}, **AJAX)
        todo.refresh_from_db()
        self.assertEqual(todo.text, 'Phone the GP about my letter')

    def test_editing_without_javascript_has_its_own_page(self):
        todo = Todo.objects.create(user=self.user, text='Phone GP')
        response = self.client.get(reverse('todo_edit', args=[todo.pk]), {'next': '/apps/'})
        self.assertContains(response, 'Edit to-do')
        self.assertContains(response, 'value="Phone GP"')

    def test_deleting_and_clearing_done(self):
        keep = Todo.objects.create(user=self.user, text='Keep me')
        gone = Todo.objects.create(user=self.user, text='Delete me')
        Todo.objects.create(user=self.user, text='Old', done=True)
        self.client.post(reverse('todo_delete', args=[gone.pk]), **AJAX)
        self.client.post(reverse('todo_clear_done'), **AJAX)
        self.assertEqual(list(Todo.objects.values_list('text', flat=True)), [keep.text])

    def test_actions_must_be_posts(self):
        todo = Todo.objects.create(user=self.user, text='x')
        self.assertEqual(self.client.get(reverse('todo_delete', args=[todo.pk])).status_code, 405)

    def test_i_never_see_or_change_someone_elses_to_dos(self):
        theirs = Todo.objects.create(user=make_user('alex'), text='Alex private to-do')
        self.assertNotContains(self.client.get(reverse('home')), 'Alex private to-do')
        for name in ['todo_toggle', 'todo_edit', 'todo_delete']:
            self.assertEqual(self.client.post(reverse(name, args=[theirs.pk]), {'text': 'hacked'}).status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.text, 'Alex private to-do')
        self.assertFalse(theirs.done)



class BacklogTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    def panel(self):
        return self.client.get(reverse('home')).context

    def test_new_to_dos_go_on_todays_list(self):
        self.client.post(reverse('todo_add'), {'text': 'Phone the GP'}, **AJAX)
        context = self.panel()
        self.assertEqual([t.text for t in context['todo_items']], ['Phone the GP'])
        self.assertEqual(context['todo_backlog'], [])

    def test_unfinished_to_dos_from_earlier_days_go_to_the_backlog(self):
        Todo.objects.create(user=self.user, text='From yesterday', day=self.today - timedelta(days=1))
        Todo.objects.create(user=self.user, text='Done yesterday', day=self.today - timedelta(days=1), done=True)
        Todo.objects.create(user=self.user, text='Today', day=self.today)
        context = self.panel()
        self.assertEqual([t.text for t in context['todo_items']], ['Today'])
        self.assertEqual([t.text for t in context['todo_backlog']], ['From yesterday'])
        self.assertEqual([t.text for t in context['todo_done']], ['Done yesterday'])

    def test_the_tab_counts_todays_to_dos_only(self):
        Todo.objects.create(user=self.user, text='Old', day=self.today - timedelta(days=3))
        Todo.objects.create(user=self.user, text='Today', day=self.today)
        response = self.client.get(reverse('home'))
        self.assertContains(response, '1<span class="visually-hidden"> left today</span>')

    def test_moving_a_backlog_to_do_back_to_today(self):
        old = Todo.objects.create(user=self.user, text='Old', day=self.today - timedelta(days=3))
        response = self.client.post(reverse('todo_move', args=[old.pk]), {'to': 'today'}, **AJAX)
        old.refresh_from_db()
        self.assertEqual(old.day, self.today)
        self.assertFalse(old.is_backlog())
        self.assertContains(response, 'Moved to today: Old')

    def test_sending_a_to_do_to_the_backlog_myself(self):
        todo = Todo.objects.create(user=self.user, text='Later', day=self.today)
        self.client.post(reverse('todo_move', args=[todo.pk]), {'to': 'backlog'}, **AJAX)
        todo.refresh_from_db()
        self.assertTrue(todo.is_backlog())
        self.assertEqual([t.text for t in self.panel()['todo_backlog']], ['Later'])

    def test_ticking_a_backlog_to_do_moves_it_to_done(self):
        old = Todo.objects.create(user=self.user, text='Old', day=self.today - timedelta(days=3))
        self.client.post(reverse('todo_toggle', args=[old.pk]), **AJAX)
        context = self.panel()
        self.assertEqual(context['todo_backlog'], [])
        self.assertEqual([t.text for t in context['todo_done']], ['Old'])

    def test_i_cannot_move_someone_elses_to_do(self):
        theirs = Todo.objects.create(user=make_user('alex'), text='Theirs')
        self.assertEqual(self.client.post(reverse('todo_move', args=[theirs.pk]), {'to': 'backlog'}).status_code, 404)
