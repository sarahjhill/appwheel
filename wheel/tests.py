from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Subscription


def make_user(name):
    return get_user_model().objects.create_user(
        username=name, email=f'{name}@example.com', password='a-long-test-password-123'
    )


def valid_form_data(**changes):
    data = {
        'name': 'Netflix',
        'plan_name': 'Standard',
        'category': 'video',
        'price': '12.99',
        'billing_period': 'monthly',
        'next_payment_date': '2026-12-01',
        'trial_end_date': '',
        'usage': 'weekly',
        'benefits': 'no adverts',
    }
    data.update(changes)
    return data


class LoggedOutTests(TestCase):
    def test_logged_out_visitors_are_sent_to_log_in(self):
        for name in ['subscription_list', 'subscription_add']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('account_login'), response.url)


class AddAppTests(TestCase):
    def setUp(self):
        self.user = make_user('sam')
        self.client.force_login(self.user)

    def test_add_page_shows_the_form(self):
        response = self.client.get(reverse('subscription_add'), {'own': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add an app')

    def test_adding_an_app_saves_it_for_me(self):
        response = self.client.post(reverse('subscription_add'), valid_form_data())
        self.assertRedirects(response, reverse('subscription_list'))
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.name, 'Netflix')
        self.assertEqual(subscription.price, Decimal('12.99'))
        self.assertEqual(subscription.next_payment_date, date(2026, 12, 1))
        self.assertIsNone(subscription.trial_end_date)

    def test_free_apps_can_be_added_with_a_price_of_zero(self):
        self.client.post(reverse('subscription_add'), valid_form_data(name='Duolingo', price='0'))
        self.assertEqual(Subscription.objects.get().price, Decimal('0'))

    def test_a_trial_end_date_can_be_added(self):
        self.client.post(reverse('subscription_add'), valid_form_data(trial_end_date='2026-11-30'))
        self.assertEqual(Subscription.objects.get().trial_end_date, date(2026, 11, 30))

    def test_price_cannot_be_negative(self):
        response = self.client.post(reverse('subscription_add'), valid_form_data(price='-5'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_name_is_required(self):
        response = self.client.post(reverse('subscription_add'), valid_form_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)


class OnlyMyAppsTests(TestCase):
    def test_i_only_see_my_own_apps(self):
        me = make_user('sam')
        someone_else = make_user('alex')
        Subscription.objects.create(user=me, name='Spotify', price=Decimal('11.99'))
        Subscription.objects.create(user=someone_else, name='Disney+', price=Decimal('4.99'))

        self.client.force_login(me)
        response = self.client.get(reverse('subscription_list'))
        self.assertContains(response, 'Spotify')
        self.assertNotContains(response, 'Disney+')

    def test_the_form_cannot_add_an_app_to_someone_elses_account(self):
        me = make_user('sam')
        someone_else = make_user('alex')
        self.client.force_login(me)
        self.client.post(reverse('subscription_add'), valid_form_data(user=someone_else.pk))
        self.assertEqual(Subscription.objects.get().user, me)


class EditAndRemoveTests(TestCase):
    def setUp(self):
        self.me = make_user('sam')
        self.someone_else = make_user('alex')
        self.mine = Subscription.objects.create(user=self.me, name='Netflix', price=Decimal('12.99'))
        self.theirs = Subscription.objects.create(user=self.someone_else, name='Disney+', price=Decimal('4.99'))
        self.client.force_login(self.me)

    def test_my_apps_list_has_edit_and_remove_links(self):
        response = self.client.get(reverse('subscription_list'))
        self.assertContains(response, reverse('subscription_edit', args=[self.mine.pk]))
        self.assertContains(response, reverse('subscription_delete', args=[self.mine.pk]))

    def test_i_can_edit_any_detail_of_my_app(self):
        response = self.client.get(reverse('subscription_edit', args=[self.mine.pk]))
        self.assertContains(response, 'Edit Netflix')
        self.assertContains(response, 'value="12.99"')

        response = self.client.post(
            reverse('subscription_edit', args=[self.mine.pk]),
            valid_form_data(price='15.99', plan_name='Premium'),
        )
        self.assertRedirects(response, reverse('subscription_list'))
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.price, Decimal('15.99'))
        self.assertEqual(self.mine.plan_name, 'Premium')

    def test_i_cannot_edit_someone_elses_app(self):
        response = self.client.get(reverse('subscription_edit', args=[self.theirs.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse('subscription_edit', args=[self.theirs.pk]), valid_form_data(name='Hacked')
        )
        self.assertEqual(response.status_code, 404)
        self.theirs.refresh_from_db()
        self.assertEqual(self.theirs.name, 'Disney+')

    def test_remove_asks_me_to_confirm_first(self):
        response = self.client.get(reverse('subscription_delete', args=[self.mine.pk]))
        self.assertContains(response, 'Remove Netflix?')
        self.assertTrue(Subscription.objects.filter(pk=self.mine.pk).exists())

    def test_i_can_remove_my_app_after_confirming(self):
        response = self.client.post(reverse('subscription_delete', args=[self.mine.pk]))
        self.assertRedirects(response, reverse('subscription_list'))
        self.assertFalse(Subscription.objects.filter(pk=self.mine.pk).exists())

    def test_i_cannot_remove_someone_elses_app(self):
        response = self.client.post(reverse('subscription_delete', args=[self.theirs.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Subscription.objects.filter(pk=self.theirs.pk).exists())


class CommonAppTests(TestCase):
    def setUp(self):
        from .models import CommonApp
        self.user = make_user('sam')
        self.client.force_login(self.user)
        self.netflix = CommonApp.objects.get(name='Netflix')  # from the starter list
        self.standard = self.netflix.plans.create(name='Standard', price=Decimal('12.99'), billing_period='monthly')

    def test_add_starts_with_a_list_of_common_apps(self):
        response = self.client.get(reverse('subscription_add'))
        self.assertContains(response, 'Popular apps')
        self.assertContains(response, 'Netflix')
        self.assertContains(response, 'Spotify')

    def test_searching_shows_matching_apps(self):
        response = self.client.get(reverse('subscription_add'), {'q': 'spot'})
        self.assertContains(response, '?app=spotify')
        self.assertNotContains(response, '?app=netflix')

    def test_choosing_an_app_fills_in_name_and_category_and_shows_plans(self):
        response = self.client.get(reverse('subscription_add'), {'app': 'netflix'})
        self.assertContains(response, 'Add Netflix')
        self.assertContains(response, 'value="Netflix"')
        self.assertContains(response, '<option value="video" selected>')
        self.assertContains(response, 'Which plan are you on?')
        self.assertContains(response, 'Standard')

    def test_choosing_a_plan_fills_in_the_price(self):
        response = self.client.get(reverse('subscription_add'), {'app': 'netflix', 'plan': self.standard.pk})
        self.assertContains(response, 'value="12.99"')
        self.assertContains(response, 'value="Standard"')

    def test_saving_links_the_app_to_the_common_app(self):
        data = valid_form_data(common_app=self.netflix.pk)
        self.client.post(reverse('subscription_add'), data)
        self.assertEqual(Subscription.objects.get().common_app, self.netflix)

    def test_i_can_still_type_my_own_app(self):
        response = self.client.get(reverse('subscription_add'), {'own': '1'})
        self.assertContains(response, '<h1>Add an app</h1>', html=False)
        self.client.post(reverse('subscription_add'), valid_form_data(name='My Local Gym'))
        self.assertIsNone(Subscription.objects.get().common_app)

    def test_an_unknown_app_gives_not_found(self):
        response = self.client.get(reverse('subscription_add'), {'app': 'not-an-app'})
        self.assertEqual(response.status_code, 404)
