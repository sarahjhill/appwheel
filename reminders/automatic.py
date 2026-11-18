"""
Automatic reminders made from each app's dates:
  - a free trial ending  -> remind 2 days before
  - a payment coming up  -> remind 3 days before
They are updated whenever the app changes, and removed if it's cancelled.
"""
from datetime import date, timedelta
from decimal import Decimal

from .models import Reminder

TRIAL_NOTICE_DAYS = 2
RENEWAL_NOTICE_DAYS = 3


def _nice_date(day):
    return f'{day:%a} {day.day} {day:%b}'


def sync_app_reminders(subscription, today=None):
    """Create, update or remove the automatic reminders for one app."""
    today = today or date.today()
    price = Decimal(subscription.price or 0)
    active = subscription.status == 'active'

    trial = subscription.trial_end_date
    if active and trial and trial >= today:
        _keep(
            subscription, Reminder.Kind.TRIAL,
            title=f'{subscription.name} free trial ends {_nice_date(trial)}',
            details=(
                f'Cancel before then if you don\'t want to pay'
                + (f' £{price:,.2f}.' if price else '.')
            ),
            due_date=max(today, trial - timedelta(days=TRIAL_NOTICE_DAYS)),
        )
    else:
        _remove(subscription, Reminder.Kind.TRIAL)

    payment = subscription.next_payment_date
    if active and payment and payment >= today and price:
        _keep(
            subscription, Reminder.Kind.RENEWAL,
            title=f'{subscription.name} renews {_nice_date(payment)} · £{price:,.2f}',
            details='Still using it? If not, cancel before it renews.',
            due_date=max(today, payment - timedelta(days=RENEWAL_NOTICE_DAYS)),
        )
    else:
        _remove(subscription, Reminder.Kind.RENEWAL)


def _keep(subscription, kind, **fields):
    reminder = subscription.reminders.filter(kind=kind).order_by('-due_date').first()
    if reminder and reminder.is_done and reminder.title == fields['title']:
        return  # already dealt with this one
    if reminder:
        for name, value in fields.items():
            setattr(reminder, name, value)
        reminder.is_done = False
        reminder.save()
    else:
        Reminder.objects.create(user=subscription.user, subscription=subscription, kind=kind, **fields)


def _remove(subscription, kind):
    subscription.reminders.filter(kind=kind, is_done=False).delete()


def roll_forward_payment_dates(user, today=None):
    """
    Move payment dates that have passed on to the next one (e.g. 5 Nov -> 5 Dec),
    and make sure every app's automatic reminders are up to date.
    """
    today = today or date.today()
    keep_privacy_checkup(user, today)
    for subscription in user.subscriptions.filter(status='active'):
        payment = subscription.next_payment_date
        if payment and payment < today:
            while payment < today:
                payment = _add_period(payment, subscription.billing_period)
            subscription.next_payment_date = payment
            subscription.save()  # this also updates the reminders
        else:
            sync_app_reminders(subscription, today)


def _add_period(day, billing_period):
    if billing_period == 'weekly':
        return day + timedelta(days=7)
    months = 12 if billing_period == 'yearly' else 1
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    # 31 Jan + 1 month -> 28/29 Feb
    for day_number in (day.day, 30, 29, 28):
        try:
            return date(year, month, day_number)
        except ValueError:
            continue


def keep_privacy_checkup(user, today=None):
    """Anyone with a social or messaging app on their wheel gets a monthly privacy check-up."""
    today = today or date.today()
    has_social = user.subscriptions.filter(status='active', category='social').exists()
    waiting = user.reminders.filter(kind=Reminder.Kind.PRIVACY, is_done=False)
    if has_social and not waiting.exists():
        Reminder.objects.create(
            user=user,
            kind=Reminder.Kind.PRIVACY,
            title='Monthly privacy check-up',
            details=(
                'Take 5 minutes to check who can see your posts and where you\'re logged in. '
                'Open each social app on your wheel and use its Safety & privacy guides.'
            ),
            due_date=today,
            repeat_every_days=30,
        )
    elif not has_social:
        waiting.delete()
