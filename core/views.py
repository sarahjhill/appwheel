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


@login_required
def home(request):
    """The home page: the App Wheel."""
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
        'description': 'Spins all your apps into control.',
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
