import io
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from .management.commands.fetch_app_icons import best_icon_urls, fetch_icon, to_square_png
from .models import CommonApp


def picture(size=(180, 180), kind='PNG'):
    buffer = io.BytesIO()
    Image.new('RGBA', size, (229, 9, 20, 255)).save(buffer, format=kind)
    return buffer.getvalue()


def fake_response(url, text='', content=b'', ok=True):
    response = mock.Mock(ok=ok, text=text, content=content, url=url)
    return response


PAGE = '''<html><head>
<link rel="icon" href="/favicon-16.png" sizes="16x16">
<link rel="apple-touch-icon" href="/icons/apple-180.png" sizes="180x180">
<link rel="icon" href="/logo.svg" type="image/svg+xml">
</head></html>'''


class IconFetchingTests(TestCase):
    def test_the_phone_home_screen_icon_is_tried_first_and_svgs_are_skipped(self):
        urls = best_icon_urls('https://www.example.com/', PAGE)
        self.assertEqual(urls[0], 'https://www.example.com/icons/apple-180.png')
        self.assertNotIn('https://www.example.com/logo.svg', urls)
        self.assertIn('https://www.example.com/favicon.ico', urls)

    def test_icons_become_square_128_pixel_pngs(self):
        for data in [picture((180, 180)), picture((64, 48)), picture((48, 48), 'ICO')]:
            image = Image.open(io.BytesIO(to_square_png(data)))
            self.assertEqual(image.size, (128, 128))
            self.assertEqual(image.format, 'PNG')

    def test_tiny_icons_are_not_used(self):
        with self.assertRaises(ValueError):
            to_square_png(picture((16, 16)))

    def test_fetch_uses_the_websites_own_icon(self):
        def get(url, **kwargs):
            if url.endswith('apple-180.png'):
                return fake_response(url, content=picture())
            return fake_response(url, text=PAGE)
        png = fetch_icon('example.com', get=get)
        self.assertEqual(Image.open(io.BytesIO(png)).size, (128, 128))

    def test_a_website_without_an_icon_gives_a_clear_reason(self):
        def get(url, **kwargs):
            return fake_response(url, text='<html></html>', ok=False)
        with self.assertRaisesMessage(ValueError, 'did not share a usable icon'):
            fetch_icon('example.com', get=get)


class FetchCommandTests(TestCase):
    def test_the_command_saves_icons_and_lists_the_ones_it_could_not_get(self):
        folder = Path(self.id().replace('.', '_'))
        with mock.patch('wheel.management.commands.fetch_app_icons.fetch_icon') as fetch, \
                override_settings(BASE_DIR=Path('/tmp') / folder):
            fetch.side_effect = lambda website: picture() if website == 'netflix.com' else (_ for _ in ()).throw(ValueError('blocked'))
            output = io.StringIO()
            call_command('fetch_app_icons', stdout=output)
        self.assertEqual(CommonApp.objects.get(name='Netflix').icon, 'netflix.png')
        self.assertEqual(CommonApp.objects.get(name='Spotify').icon, '')
        self.assertIn('Saved 1 icon(s)', output.getvalue())
        self.assertIn('Spotify (spotify.com): blocked', output.getvalue())
        self.assertTrue((Path('/tmp') / folder / 'static' / 'app-icons' / 'netflix.png').exists())

    def test_every_common_app_has_a_website(self):
        self.assertFalse(CommonApp.objects.filter(website='').exists())
