from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_logged_out_visitors_see_the_appwheel_homepage(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/landing.html')
        self.assertContains(response, 'Create your free account')
        self.assertContains(response, reverse('account_signup'))
        self.assertContains(response, 'data-demo-wheel')

    def test_logged_in_users_see_the_home_page(self):
        user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spin your apps and life into control')


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


class InstallableAppTests(TestCase):
    def test_manifest_has_name_icons_and_full_screen(self):
        response = self.client.get(reverse('manifest'))
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        data = response.json()
        self.assertEqual(data['name'], 'AppWheel')
        self.assertEqual(data['display'], 'standalone')
        sizes = {icon['sizes'] for icon in data['icons']}
        self.assertEqual(sizes, {'192x192', '512x512'})
        self.assertTrue(any(icon.get('purpose') == 'maskable' for icon in data['icons']))

    def test_service_worker_is_served_from_the_top_of_the_site(self):
        response = self.client.get('/sw.js')
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertContains(response, "const OFFLINE_URL = '/offline/'")

    def test_service_worker_never_saves_private_pages(self):
        script = self.client.get('/sw.js').content.decode()
        for private in ['/apps/', '/reminders/', '/care/', '/help/', '/accounts/']:
            self.assertNotIn(f"'{private}'", script)

    def test_offline_and_install_pages_work_without_logging_in(self):
        self.assertContains(self.client.get(reverse('offline')), "You're offline")
        self.assertContains(self.client.get(reverse('install')), 'Add to Home Screen')

    def test_every_page_links_the_manifest_and_icon(self):
        response = self.client.get(reverse('account_login'))
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'apple-touch-icon')


class ServiceWorkerFreshnessTests(TestCase):
    def test_design_files_are_fetched_fresh_before_using_the_saved_copy(self):
        script = self.client.get('/sw.js').content.decode()
        self.assertIn("fetch(request, { cache: 'no-cache' })", script)
        self.assertNotIn("return saved || fetch(request)", script)


class AccountMenuTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)

    def test_account_link_is_in_the_menu_next_to_log_out(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, f'class="account-link" href="{reverse("account")}"')
        self.assertContains(response, 'Log out')

    def test_account_page_has_the_account_options(self):
        response = self.client.get(reverse('account'))
        self.assertContains(response, 'sam@example.com')
        for link in ['account_change_password', 'account_email', 'install', 'delete_account']:
            self.assertContains(response, reverse(link))

    def test_account_page_needs_logging_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)


class FreshStylesTests(TestCase):
    def test_design_files_are_never_reused_from_the_browser_while_building(self):
        from django.test import override_settings
        with override_settings(DEBUG=True):
            response = self.client.get('/static/css/style.css')
        self.assertEqual(response['Cache-Control'], 'no-cache')


class LandingLogoTests(TestCase):
    def test_example_wheel_uses_official_logos_where_added_and_tiles_otherwise(self):
        from wheel.models import CommonApp
        CommonApp.objects.filter(name='Netflix').update(icon='netflix.png')
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'src="/static/app-icons/netflix.png"')
        self.assertContains(response, 'tile-books')  # Headway has no logo, so it keeps its tile
