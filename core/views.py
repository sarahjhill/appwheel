from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

from reminders.automatic import roll_forward_payment_dates
from wheel.health import summarise
from wheel.models import link_common_apps

# The wheel fits up to 12 apps comfortably on a phone
WHEEL_MAX_APPS = 12

# Example apps for the demo wheel on the public homepage (letter tiles, not real logos)
DEMO_APPS = [
    {'name': 'Netflix', 'initials': 'Ne', 'tile': 'video', 'price': '12.99', 'light': 'amber', 'label': 'Could cost less',
     'tip': 'Switch to Standard with adverts to save £60 a year'},
    {'name': 'Spotify', 'initials': 'Sp', 'tile': 'music', 'price': '11.99', 'light': 'green', 'label': 'Good value',
     'tip': 'You use it every day. Nothing to change.'},
    {'name': 'PureGym', 'initials': 'Pu', 'tile': 'fitness', 'price': '24.99', 'light': 'red', 'label': 'Needs action',
     'tip': 'You haven\'t been since August. Cancel to save £299.88 a year'},
    {'name': 'iCloud+', 'initials': 'iC', 'tile': 'storage', 'price': '2.99', 'light': 'green', 'label': 'Good value',
     'tip': 'Your photos are backed up. Nothing to change.'},
    {'name': 'Headway', 'initials': 'He', 'tile': 'books', 'price': '9.99', 'light': 'red', 'label': 'Needs action',
     'tip': 'Free trial ends in 2 days. Cancel before then to avoid paying'},
    {'name': 'Disney+', 'initials': 'Di', 'tile': 'video', 'price': '4.99', 'light': 'amber', 'label': 'Could cost less',
     'tip': 'You also pay for Netflix. Keep one to save £59.88 a year'},
    {'name': 'Instagram', 'initials': 'In', 'tile': 'social', 'price': '0', 'light': 'amber', 'label': 'Could cost less',
     'tip': 'Free, but your monthly privacy check-up is due'},
    {'name': 'Canva', 'initials': 'Ca', 'tile': 'design', 'price': '10.99', 'light': 'green', 'label': 'Good value',
     'tip': 'Used every week for work. Nothing to change.'},
]
for _index, _app in enumerate(DEMO_APPS):
    _app['angle'] = round(_index * 360 / len(DEMO_APPS), 3)


def home(request):
    """Visitors see the AppWheel homepage; signed-in people see their App Wheel."""
    if not request.user.is_authenticated:
        return render(request, 'core/landing.html', {'demo_apps': _demo_apps_with_logos()})
    roll_forward_payment_dates(request.user)
    link_common_apps(request.user)
    subscriptions = list(
        request.user.subscriptions.filter(status='active')
        .select_related('common_app')
        .prefetch_related('common_app__plans', 'common_app__safety_guides')
    )
    summary = summarise(subscriptions)
    # Biggest costs first, so the most important apps are on the wheel
    on_wheel = sorted(subscriptions, key=lambda sub: sub.monthly_cost, reverse=True)[:WHEEL_MAX_APPS]
    step = 360 / len(on_wheel) if on_wheel else 0
    for index, sub in enumerate(on_wheel):
        sub.angle = round(index * step, 3)
        sub.short_name = _short_name(sub.name)
    return render(request, 'core/home.html', {
        'apps': on_wheel,
        'hidden_count': len(subscriptions) - len(on_wheel),
        'paid_count': sum(1 for sub in subscriptions if sub.price),
        'summary': summary,
        'coming_up': request.user.reminders.filter(is_done=False)[:3],
    })


def _demo_apps_with_logos():
    """Use each example app's official logo where one has been added in the admin."""
    from wheel.models import CommonApp
    icons = dict(
        CommonApp.objects.filter(name__in=[app['name'] for app in DEMO_APPS]).exclude(icon='')
        .values_list('name', 'icon')
    )
    return [app | {'icon_path': f'app-icons/{icons[app["name"]]}' if app['name'] in icons else ''} for app in DEMO_APPS]


def _short_name(name):
    """A short label that fits inside a wheel button, e.g. 'Amazon Prime' -> 'Amazon'."""
    if len(name) <= 8:
        return name
    first_word = name.split()[0] if name.split() else name
    return (first_word if len(first_word) >= 3 else name)[:8]


@login_required
def account(request):
    """Account settings: password, email, installing the app, deleting the account."""
    from reminders.models import EmailSettings
    return render(request, 'core/account.html', {
        'reminder_emails': EmailSettings.wants_emails(request.user),
    })


# ----- Installable app (PWA) -----

@cache_control(max_age=86400)
def manifest(request):
    """Tells phones the app's name, icon and colours, so it can be added to the home screen."""
    data = {
        'name': 'AppWheel',
        'short_name': 'AppWheel',
        'description': 'Spin your apps and life into control.',
        'start_url': '/?source=home-screen',
        'scope': '/',
        'display': 'standalone',
        'background_color': '#15112b',
        'theme_color': '#15112b',
        'lang': 'en-GB',
        'icons': [
            {'src': static('icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': static('icons/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return JsonResponse(data, content_type='application/manifest+json')


@cache_control(no_cache=True)
def service_worker(request):
    """The service worker must be served from the top of the site so it covers every page."""
    response = render(request, 'core/sw.js', {
        'offline_url': '/offline/',
        'files': [
            '/offline/',
            static('css/style.css'),
            static('js/wheel.js'),
            static('js/pwa.js'),
            static('js/todo.js'),
            static('icons/icon-192.png'),
        ],
    }, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


def offline(request):
    """Shown when the phone has no signal."""
    return render(request, 'core/offline.html')


def install(request):
    """How to put AppWheel on your phone's home screen."""
    return render(request, 'core/install.html')
