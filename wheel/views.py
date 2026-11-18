from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from . import screenshot
from .health import summarise
from .forms import ScreenshotUploadForm, StatementUploadForm, SubscriptionForm
from reminders.models import Reminder

from .models import CommonApp, Subscription, link_common_apps
from .statement import StatementError, find_regular_payments, read_statement

# Where the payments we found are kept between the upload and review pages
SESSION_KEY = 'statement_found'


@login_required
def subscription_list(request):
    """Show the apps that belong to the signed-in user, and nobody else's."""
    link_common_apps(request.user)
    everything = list(
        request.user.subscriptions.select_related('common_app').prefetch_related('common_app__plans')
    )
    subscriptions = [sub for sub in everything if sub.status == Subscription.Status.ACTIVE]
    cancelled = [sub for sub in everything if sub.status == Subscription.Status.CANCELLED]
    check_dates = {
        reminder.subscription_id: reminder.due_date
        for reminder in request.user.reminders.filter(kind=Reminder.Kind.CHARGE_CHECK, is_done=False)
    }
    for sub in cancelled:
        sub.check_date = check_dates.get(sub.pk)
    return render(request, 'wheel/subscription_list.html', {
        'subscriptions': subscriptions,
        'cancelled': cancelled,
        'summary': summarise(subscriptions),
        'screenshots_ready': screenshot.is_set_up(),
    })


@login_required
def subscription_add(request):
    """
    Add a new app. First pick a common app (or choose to type your own),
    then fill in the form. Picking a common app and plan fills it in for you.
    """
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f'{subscription.name} has been added.')
            return redirect('subscription_list')
        return render(request, 'wheel/subscription_form.html', {'form': form})

    slug = request.GET.get('app')
    if not slug and not request.GET.get('own'):
        return _pick_an_app(request)

    common_app, chosen_plan, initial = None, None, {}
    if slug:
        common_app = get_object_or_404(CommonApp, slug=slug)
        initial = {
            'common_app': common_app.pk,
            'name': common_app.name,
            'category': common_app.category,
        }
        if common_app.category == 'social':
            initial.update({'price': 0, 'usage': 'daily'})  # social apps are usually free
        chosen_plan = common_app.plans.filter(pk=request.GET.get('plan') or 0).first()
        if chosen_plan:
            initial.update({
                'plan_name': chosen_plan.name,
                'price': chosen_plan.price,
                'billing_period': chosen_plan.billing_period,
            })
    return render(request, 'wheel/subscription_form.html', {
        'form': SubscriptionForm(initial=initial),
        'common_app': common_app,
        'chosen_plan': chosen_plan,
    })


def _pick_an_app(request):
    """Step 1 of adding an app: search the list of common apps."""
    query = request.GET.get('q', '').strip()
    common_apps = CommonApp.objects.all()
    if query:
        common_apps = common_apps.filter(name__icontains=query)
    return render(request, 'wheel/subscription_pick.html', {
        'common_apps': common_apps,
        'query': query,
    })


@login_required
def subscription_edit(request, pk):
    """Change one of my apps. Other people's apps give a 'not found' page."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, f'{subscription.name} has been updated.')
            return redirect('subscription_list')
    else:
        form = SubscriptionForm(instance=subscription)
    return render(request, 'wheel/subscription_form.html', {
        'form': form,
        'subscription': subscription,
    })


@login_required
def subscription_delete(request, pk):
    """Remove one of my apps, after asking 'are you sure?'."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        name = subscription.name
        subscription.delete()
        messages.success(request, f'{name} has been removed.')
        return redirect('subscription_list')
    return render(request, 'wheel/subscription_confirm_delete.html', {
        'subscription': subscription,
    })


@login_required
def statement_upload(request):
    """Upload bank statements. They are read straight away and never saved."""
    if request.method == 'POST':
        form = StatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            transactions = []
            try:
                for statement in form.cleaned_data['statements']:
                    transactions.extend(read_statement(statement))
            except StatementError as error:
                form.add_error('statements', f'{statement.name}: {error}')
            else:
                found = find_regular_payments(transactions)
                if found:
                    request.session[SESSION_KEY] = found
                    return redirect('statement_review')
                form.add_error(
                    'statements',
                    "We read your statement but didn't find any regular payments. "
                    'Try a statement that covers 2 or 3 months.',
                )
    else:
        form = StatementUploadForm()
    return render(request, 'wheel/statement_upload.html', {'form': form})


@login_required
def statement_review(request):
    """Show the regular payments we found, and add the ones the user ticks."""
    found = request.session.get(SESSION_KEY)
    if not found:
        return redirect('subscription_list')

    my_app_names = {
        name.lower() for name in request.user.subscriptions.values_list('name', flat=True)
    }
    for item in found:
        item['already_added'] = item['name'].lower() in my_app_names

    if request.method == 'POST':
        ticked = set(request.POST.getlist('add'))
        added = 0
        for index, item in enumerate(found):
            if str(index) in ticked and not item['already_added']:
                Subscription.objects.create(
                    user=request.user,
                    common_app=CommonApp.objects.filter(name__iexact=item['name']).first(),
                    name=item['name'],
                    plan_name=item.get('plan_name', ''),
                    category=item['category'],
                    price=Decimal(item['price']),
                    billing_period=item['billing_period'],
                    next_payment_date=_to_date(item.get('next_payment_date')),
                    trial_end_date=_to_date(item.get('trial_end_date')),
                )
                added += 1
        del request.session[SESSION_KEY]
        if added:
            messages.success(request, f'{added} app{"s" if added != 1 else ""} added to AppWheel.')
        else:
            messages.info(request, 'No apps were added.')
        return redirect('subscription_list')

    return render(request, 'wheel/statement_review.html', {'found': found})


def _to_date(value):
    """Dates are kept as text between pages; turn them back into dates."""
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


@login_required
def screenshot_upload(request):
    """Upload screenshots of subscriptions. AI reads them; they are never saved."""
    form = ScreenshotUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and screenshot.is_set_up() and form.is_valid():
        found = []
        try:
            for picture in form.cleaned_data['screenshots']:
                found.extend(screenshot.read_screenshot(picture))
        except screenshot.ScreenshotError as error:
            form.add_error('screenshots', f'{picture.name}: {error}')
        else:
            if found:
                request.session[SESSION_KEY] = found
                return redirect('statement_review')
            form.add_error(
                'screenshots',
                "We couldn't see any active subscriptions in that picture. "
                'Try a screenshot of your Subscriptions page.',
            )
    return render(request, 'wheel/screenshot_upload.html', {
        'form': form,
        'is_set_up': screenshot.is_set_up(),
    })


@login_required
def cancel_help(request, pk):
    """Help to cancel an app: the company's cancel page and simple steps."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    return render(request, 'wheel/cancel_help.html', {'subscription': subscription})


def charge_check_date(subscription, today):
    """The day after the next payment would have been taken."""
    if subscription.next_payment_date and subscription.next_payment_date >= today:
        return subscription.next_payment_date + timedelta(days=1)
    days = {'weekly': 7, 'yearly': 30}.get(subscription.billing_period, 30)
    return today + timedelta(days=days)


@login_required
def mark_cancelled(request, pk):
    """'I've cancelled': take it off the totals and set a reminder to check for charges."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method != 'POST':
        return redirect('cancel_help', pk=pk)
    today = date.today()
    subscription.status = Subscription.Status.CANCELLED
    subscription.cancelled_on = today
    subscription.save()

    check_on = charge_check_date(subscription, today)
    if subscription.price:
        Reminder.objects.update_or_create(
            user=request.user,
            subscription=subscription,
            kind=Reminder.Kind.CHARGE_CHECK,
            is_done=False,
            defaults={
                'title': f'Check you weren\'t charged by {subscription.name}',
                'details': (
                    f'You cancelled {subscription.name} on {today:%d %B %Y}. '
                    'Look at your bank statement or app store receipts. '
                    'If you were charged, AppWheel has a refund request ready for you.'
                ),
                'due_date': check_on,
            },
        )
        messages.success(
            request,
            f'{subscription.name} is cancelled and off your totals. '
            f'We\'ll remind you on {check_on.day} {check_on:%B} to check you weren\'t charged.',
        )
    else:
        messages.success(request, f'{subscription.name} is cancelled and off your wheel.')
    return redirect('subscription_list')


@login_required
def mark_active(request, pk):
    """Undo 'I've cancelled', for example if it was pressed by mistake."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        subscription.status = Subscription.Status.ACTIVE
        subscription.cancelled_on = None
        subscription.save()
        subscription.reminders.filter(kind=Reminder.Kind.CHARGE_CHECK, is_done=False).delete()
        messages.success(request, f'{subscription.name} is back on your wheel.')
    return redirect('subscription_list')


@login_required
def refund_request(request, pk):
    """A ready-written refund request for a payment taken after cancelling."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    return render(request, 'wheel/refund_request.html', {'subscription': subscription})


@login_required
def safety_guides(request, pk):
    """Safety and privacy guides for one social or messaging app."""
    subscription = get_object_or_404(
        Subscription.objects.select_related('common_app'), pk=pk, user=request.user,
    )
    return render(request, 'wheel/safety.html', {'subscription': subscription})
