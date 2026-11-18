"""
Fetches each common app's official icon from the company's own website and
saves it in static/app-icons/, so AppWheel can show real app logos.

Run it with:   python manage.py fetch_app_icons
Fetch again:   python manage.py fetch_app_icons --refresh
One app only:  python manage.py fetch_app_icons --app Netflix

The icons are saved inside AppWheel, so people's browsers never contact these
companies just by opening the wheel. Check each company's brand rules before
launching with their logo.
"""
import io
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, UnidentifiedImageError

from wheel.models import CommonApp

ICON_SIZE = 128
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/130.0 Safari/537.36'
    ),
    'Accept-Language': 'en-GB,en;q=0.9',
}


class IconLinks(HTMLParser):
    """Collects the <link rel="...icon..."> tags from a web page."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        attrs = dict(attrs)
        rel = (attrs.get('rel') or '').lower()
        if 'icon' in rel and attrs.get('href'):
            self.links.append((rel, attrs.get('sizes') or '', attrs['href']))


def best_icon_urls(page_url, html):
    """Best first: the phone home-screen icon, then the biggest browser icon."""
    parser = IconLinks()
    parser.feed(html)

    def score(link):
        rel, sizes, href = link
        size = max((int(number) for number in re.findall(r'\d+', sizes)), default=32)
        if href.lower().endswith('.svg'):
            size = 0  # SVGs can't be turned into PNGs here
        return (('apple-touch-icon' in rel) * 1000) + min(size, 512)

    links = sorted(parser.links, key=score, reverse=True)
    urls = [urljoin(page_url, href) for _, _, href in links if not href.lower().endswith('.svg')]
    # Most sites also have these at standard addresses
    urls += [urljoin(page_url, '/apple-touch-icon.png'), urljoin(page_url, '/favicon.ico')]
    seen = []
    for url in urls:
        if url not in seen:
            seen.append(url)
    return seen


def to_square_png(data):
    """Turn any icon (PNG, ICO, JPG) into a square 128 x 128 PNG."""
    image = Image.open(io.BytesIO(data))  # for .ico files this picks the biggest size
    image = image.convert('RGBA')
    if min(image.size) < 32:
        raise ValueError('too small')
    side = max(image.size)
    square = Image.new('RGBA', (side, side), (255, 255, 255, 0))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2), image)
    square = square.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    buffer = io.BytesIO()
    square.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def fetch_icon(website, get=requests.get):
    """Return a PNG of the website's icon, or raise an error saying why not."""
    last_problem = 'no icon found'
    for page_url in (f'https://www.{website}/', f'https://{website}/'):
        try:
            page = get(page_url, headers=HEADERS, timeout=10)
        except requests.RequestException as error:
            last_problem = f'could not reach {page_url} ({error.__class__.__name__})'
            continue
        html = page.text if page.ok else ''
        for icon_url in best_icon_urls(page.url or page_url, html):
            try:
                response = get(icon_url, headers=HEADERS, timeout=10)
                if response.ok and response.content:
                    return to_square_png(response.content)
            except (requests.RequestException, UnidentifiedImageError, ValueError, OSError):
                continue
        last_problem = 'the website did not share a usable icon'
    raise ValueError(last_problem)


class Command(BaseCommand):
    help = 'Fetch each common app\'s official icon from its own website.'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true', help='Fetch again even if an icon is already set.')
        parser.add_argument('--app', help='Only fetch the icon for this app, e.g. "Netflix".')

    def handle(self, *args, refresh=False, app=None, **options):
        folder = Path(settings.BASE_DIR) / 'static' / 'app-icons'
        folder.mkdir(parents=True, exist_ok=True)
        apps = CommonApp.objects.exclude(website='')
        if app:
            apps = apps.filter(name__iexact=app)
        if not refresh:
            apps = apps.filter(icon='')

        done, missing = [], []
        for common_app in apps:
            try:
                png = fetch_icon(common_app.website)
            except ValueError as problem:
                missing.append(f'{common_app.name} ({common_app.website}): {problem}')
                self.stdout.write(self.style.WARNING(f'  ✗ {common_app.name}'))
                continue
            file_name = f'{common_app.slug}.png'
            (folder / file_name).write_bytes(png)
            common_app.icon = file_name
            common_app.save(update_fields=['icon'])
            done.append(common_app.name)
            self.stdout.write(self.style.SUCCESS(f'  ✓ {common_app.name}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Saved {len(done)} icon(s) in static/app-icons/.'))
        if missing:
            self.stdout.write(self.style.WARNING(
                f'{len(missing)} app(s) still show letter tiles. Add these by hand in the admin if you want:'
            ))
            for line in missing:
                self.stdout.write(f'  - {line}')
