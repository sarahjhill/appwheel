import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .automatic import roll_forward_payment_dates
from .forms import DEFAULT_CHECKLIST, ReminderForm
from .models import ChecklistItem, EmailSettings, Reminder

NHS_APP_URL = 'https://www.nhs.uk/nhs-app/'
STARTING_TITLES = {
    Reminder.Kind.APPOINTMENT: '',
    Reminder.Kind.PRESCRIPTION: 'Order my repeat prescription',
    Reminder.Kind.OTHER: '',
}


@login_required
def reminder_list(request):
    """All my reminders: this week, later, and done."""
    roll_forward_payment_dates(request.user)
    today = date.today()
    week_end = today + timedelta(days=7)
    reminders = request.user.reminders.select_related('subscription').prefetch_related('checklist')
    to_do = [reminder for reminder in reminders if not reminder.is_done]
    return render(request, 'reminders/reminder_list.html', {
        'this_week': [reminder for reminder in to_do if reminder.due_date <= week_end],
        'later': [reminder for reminder in to_do if reminder.due_date > week_end],
        'done': [reminder for reminder in reminders if reminder.is_done][-20:][::-1],
        'today': today,
        'nhs_app_url': NHS_APP_URL,
    })


@login_required
def reminder_add(request):
    kind = request.GET.get('kind', Reminder.Kind.OTHER)
    if kind not in STARTING_TITLES:
        kind = Reminder.Kind.OTHER
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            _save_checklist(reminder, form.checklist_lines())
            messages.success(request, 'Your reminder has been added.')
            return redirect('reminder_list')
    else:
        try:
            chosen_day = date.fromisoformat(request.GET.get('date', ''))
        except ValueError:
            chosen_day = None
        form = ReminderForm(initial={
            'due_date': chosen_day,
            'kind': kind,
            'title': STARTING_TITLES[kind],
            'checklist_text': '\n'.join(DEFAULT_CHECKLIST.get(kind, [])),
            'repeat_every_days': 28 if kind == Reminder.Kind.PRESCRIPTION else None,
        })
    return render(request, 'reminders/reminder_form.html', {'form': form, 'kind': kind})


@login_required
def reminder_edit(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    if reminder.kind not in STARTING_TITLES:
        messages.info(request, 'AppWheel keeps this reminder up to date from your app, so it can\'t be edited.')
        return redirect('reminder_list')
    if request.method == 'POST':
        form = ReminderForm(request.POST, instance=reminder)
        if form.is_valid():
            form.save()
            _save_checklist(reminder, form.checklist_lines())
            messages.success(request, 'Your reminder has been updated.')
            return redirect('reminder_list')
    else:
        form = ReminderForm(instance=reminder)
    return render(request, 'reminders/reminder_form.html', {'form': form, 'reminder': reminder})


def _save_checklist(reminder, lines):
    """Keep ticks on items that are still there; add new ones; remove old ones."""
    ticked = {item.text: item.ticked for item in reminder.checklist.all()}
    reminder.checklist.all().delete()
    ChecklistItem.objects.bulk_create([
        ChecklistItem(reminder=reminder, text=text, ticked=ticked.get(text, False), position=index)
        for index, text in enumerate(lines)
    ])


@login_required
def reminder_done(request, pk):
    """Mark as done (or not done). A repeating reminder makes the next one."""
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    if request.method == 'POST':
        reminder.is_done = not reminder.is_done
        reminder.save()
        if reminder.is_done and reminder.repeat_every_days:
            next_reminder = Reminder.objects.create(
                user=reminder.user, kind=reminder.kind, title=reminder.title, details=reminder.details,
                due_date=reminder.due_date + timedelta(days=reminder.repeat_every_days),
                time=reminder.time, repeat_every_days=reminder.repeat_every_days,
            )
            ChecklistItem.objects.bulk_create([
                ChecklistItem(reminder=next_reminder, text=item.text, position=item.position)
                for item in reminder.checklist.all()
            ])
            messages.success(
                request,
                f'Done. We\'ll remind you again on {next_reminder.due_date.day} {next_reminder.due_date:%B}.',
            )
        elif reminder.is_done:
            messages.success(request, 'Done. Well done!')
    return redirect('reminder_list')


@login_required
def checklist_tick(request, pk):
    """Tick or untick one checklist item."""
    item = get_object_or_404(ChecklistItem, pk=pk, reminder__user=request.user)
    if request.method == 'POST':
        item.ticked = request.POST.get('ticked') == 'on'
        item.save()
    return redirect(f"{reverse('reminder_list')}#reminder-{item.reminder_id}")


@login_required
def reminder_delete(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    if request.method == 'POST':
        reminder.delete()
        messages.success(request, 'Your reminder has been deleted.')
        return redirect('reminder_list')
    return render(request, 'reminders/reminder_confirm_delete.html', {'reminder': reminder})


@login_required
def reminder_calendar(request):
    """
    The reminders for one month (plus the days either side that show on the
    calendar), for the calendar panel on the left of every page.
    """
    roll_forward_payment_dates(request.user)
    today = date.today()
    try:
        year, month = (int(part) for part in request.GET.get('month', '').split('-'))
        first = date(year, month, 1)
    except ValueError:
        first = today.replace(day=1)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    start, end = first - timedelta(days=6), last + timedelta(days=6)

    days = {}
    reminders = request.user.reminders.filter(due_date__range=(start, end))
    for reminder in reminders:
        days.setdefault(reminder.due_date.isoformat(), []).append({
            'id': reminder.pk,
            'title': reminder.title,
            'kind': reminder.kind,
            'kind_label': reminder.get_kind_display(),
            'time': reminder.time.strftime('%H:%M') if reminder.time else '',
            'done': reminder.is_done,
            'url': f"{reverse('reminder_list')}#reminder-{reminder.pk}",
        })
    return JsonResponse({
        'month': f'{first:%Y-%m}',
        'title': f'{first:%B %Y}',
        'today': today.isoformat(),
        'days': days,
        'add_url': reverse('reminder_add'),
    })


@login_required
def email_settings(request):
    """Switch reminder emails on or off."""
    if request.method == 'POST':
        wanted = request.POST.get('reminder_emails') == 'on'
        EmailSettings.objects.update_or_create(user=request.user, defaults={'reminder_emails': wanted})
        messages.success(request, f'Reminder emails are now {"on" if wanted else "off"}.')
    return redirect('account')
