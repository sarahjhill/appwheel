from datetime import date, timedelta


def reminder_panel(request):
    """How many reminders are due this week (or overdue), for the tab on the left."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    week_end = date.today() + timedelta(days=7)
    return {
        'reminders_this_week': request.user.reminders.filter(is_done=False, due_date__lte=week_end).count(),
    }
