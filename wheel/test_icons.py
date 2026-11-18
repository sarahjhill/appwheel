from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CommonApp, Subscription


class AppIconTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sam', email='sam@example.com', password='a-long-test-password-123'
        )
        self.client.force_login(self.user)

    def add(self, name, **details):
        return Subscription.objects.create(user=self.user, name=name, price=Decimal('5'), **details)

    def test_initials(self):
        self.assertEqual(Subscription(name='Netflix').initials, 'Ne')
        self.assertEqual(Subscription(name='Sky TV').initials, 'ST')
        self.assertEqual(Subscription(name='iCloud+').initials, 'iC')
        self.assertEqual(Subscription(name='Instagram').initials, 'In')
        self.assertEqual(Subscription(name='EE').initials, 'EE')
        self.assertEqual(Subscription(name='O2').initials, 'O2')
        self.assertEqual(Subscription(name='X').initials, 'X')
        self.assertEqual(Subscription(name='Amazon Prime Video').initials, 'AP')

    def test_apps_without_an_official_icon_show_a_coloured_initials_tile(self):
        self.add('Sky TV', category='video')
        response = self.client.get(reverse('home'))
        self.assertContains(response, '<span class="app-initials tile-video" aria-hidden="true">ST</span>', html=True)

    def test_an_official_icon_is_shown_once_added(self):
        netflix = CommonApp.objects.get(name='Netflix')
        netflix.icon = 'netflix.png'
        netflix.save()
        self.add('Netflix', common_app=netflix, category='video')
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'src="/static/app-icons/netflix.png"')
        self.assertNotContains(response, 'class="app-initials')

    def test_apps_added_from_a_statement_are_linked_to_the_common_list(self):
        sky = self.add('Sky')
        self.assertIsNone(sky.common_app)
        self.client.get(reverse('home'))
        sky.refresh_from_db()
        self.assertEqual(sky.common_app, CommonApp.objects.get(name='Sky'))

    def test_my_apps_list_shows_icons_too(self):
        self.add('Spotify', category='music')
        response = self.client.get(reverse('subscription_list'))
        self.assertContains(response, 'tile-music')
