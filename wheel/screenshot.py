"""
Reads a screenshot of someone's subscriptions (for example the iPhone
Subscriptions page) using Anthropic's Claude, and turns it into the same
list of found payments that the bank statement reader makes.

The picture is sent to Anthropic to be read, then thrown away.
AppWheel never saves it.
"""
import base64
import io
from datetime import date

import requests
from django.conf import settings

from .statement import known_app

API_URL = 'https://api.anthropic.com/v1/messages'
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_SIDE = 1568  # bigger pictures cost more and aren't read any better


class ScreenshotError(Exception):
    """Something went wrong reading the screenshot."""


# We ask Claude to fill in this form, so the answer is always in the same shape
RECORD_TOOL = {
    'name': 'record_subscriptions',
    'description': 'Record every active subscription shown in the screenshot.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'subscriptions': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string', 'description': 'The app or service, e.g. "Netflix"'},
                        'plan_name': {'type': 'string', 'description': 'The plan, e.g. "Premium". Empty if not shown.'},
                        'price': {'type': 'number', 'description': 'Price in pounds, e.g. 4.99. 0 if free.'},
                        'billing_period': {'type': 'string', 'enum': ['weekly', 'monthly', 'yearly']},
                        'next_payment_date': {
                            'type': 'string',
                            'description': 'Next renewal date as YYYY-MM-DD, or empty if not shown.',
                        },
                        'trial_end_date': {
                            'type': 'string',
                            'description': 'If it is a free trial, the date it ends as YYYY-MM-DD, otherwise empty.',
                        },
                        'category': {
                            'type': 'string',
                            'enum': ['music', 'video', 'ai', 'storage', 'books', 'design', 'fitness', 'other'],
                        },
                    },
                    'required': ['name', 'price', 'billing_period', 'category'],
                },
            },
        },
        'required': ['subscriptions'],
    },
}


def is_set_up():
    return bool(settings.ANTHROPIC_API_KEY)


def read_screenshot(uploaded_file):
    """Return a list of found subscriptions from one screenshot."""
    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise ScreenshotError('That picture is too big. Please choose one under 5 MB.')
    image_data, media_type = _prepare_image(uploaded_file)
    items = ask_claude(image_data, media_type)
    return [_tidy(item) for item in items if item.get('name')]


def _prepare_image(uploaded_file):
    """Check it's a picture and shrink it if it's very large."""
    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(uploaded_file)
        image.load()
    except (UnidentifiedImageError, OSError):
        raise ScreenshotError(
            "We couldn't open that picture. Please choose a screenshot (PNG or JPG)."
        )
    image = image.convert('RGB')
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii'), 'image/png'


def ask_claude(image_data, media_type):
    """Send the picture to Claude and get back the subscriptions it can see."""
    if not is_set_up():
        raise ScreenshotError('Screenshot reading is not set up yet.')

    instructions = (
        f"Today's date is {date.today().isoformat()}. "
        'This is a screenshot of someone\'s subscriptions, for example the iPhone or Android '
        'Subscriptions page, or a bill. Record every ACTIVE subscription you can see. '
        'Leave out anything marked Expired, Cancelled or Inactive. '
        'If a renewal date has no year, use the next time that date comes round. '
        'Prices are in pounds. Only use information shown in the picture; never guess a price.'
    )
    try:
        response = requests.post(
            API_URL,
            headers={
                'x-api-key': settings.ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': settings.ANTHROPIC_MODEL,
                'max_tokens': 2000,
                'tools': [RECORD_TOOL],
                'tool_choice': {'type': 'tool', 'name': 'record_subscriptions'},
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': image_data}},
                        {'type': 'text', 'text': instructions},
                    ],
                }],
            },
            timeout=60,
        )
    except requests.RequestException:
        raise ScreenshotError("We couldn't reach our picture reader. Please try again in a minute.")

    if response.status_code != 200:
        raise ScreenshotError(
            "Our picture reader isn't working right now. Please try again later, or add the app yourself."
        )
    for block in response.json().get('content', []):
        if block.get('type') == 'tool_use':
            return block.get('input', {}).get('subscriptions', [])
    return []


def _valid_date(value):
    try:
        return date.fromisoformat(value).isoformat() if value else ''
    except (TypeError, ValueError):
        return ''


def _tidy(item):
    """Put Claude's answer into the same shape as the bank statement reader's."""
    known = known_app(item['name'])
    name, category = known if known else (item['name'].strip()[:100], item.get('category', 'other'))
    try:
        price = f"{max(float(item.get('price') or 0), 0):.2f}"
    except (TypeError, ValueError):
        price = '0.00'
    period = item.get('billing_period')
    return {
        'name': name,
        'plan_name': (item.get('plan_name') or '')[:100],
        'category': category,
        'price': price,
        'billing_period': period if period in ('weekly', 'monthly', 'yearly') else 'monthly',
        'next_payment_date': _valid_date(item.get('next_payment_date')),
        'trial_end_date': _valid_date(item.get('trial_end_date')),
        'known': True,
        'source': 'screenshot',
    }
