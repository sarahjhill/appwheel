from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from reminders.automatic import roll_forward_payment_dates
from wheel.health import summarise

# The wheel fits up to 12 apps comfortably on a phone
WHEEL_MAX_APPS = 12


@login_required
def home(request):
    """The home page: the App Wheel."""
    roll_forward_payment_dates(request.user)
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
