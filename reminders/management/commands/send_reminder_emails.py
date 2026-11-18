"""
Sends each person one email listing the reminders that are due today (or overdue
and not yet emailed). Heroku Scheduler runs this once a day:

    python manage.py send_reminder_emails

Each reminder is only emailed once. People can turn the emails off on their Account page.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from reminders.automatic import roll_forward_payment_dates
from reminders.models import EmailSettings, Reminder


class Command(BaseCommand):
    help = 'Email people the reminders that are due today.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        sent = 0
        for user in get_user_model().objects.filter(is_active=True).exclude(email=''):
            # Keep trial and renewal reminders up to date, even if they haven't opened AppWheel lately
            roll_forward_payment_dates(user, today)
            due = list(Reminder.objects.filter(
                user=user, is_done=False, emailed_on__isnull=True, due_date__lte=today,
            ).order_by('due_date', 'time'))
            if not due or not EmailSettings.wants_emails(user):
                continue
            context = {
                'reminders': due,
                'today': today,
                'reminders_url': f'{settings.SITE_URL}/reminders/',
                'account_url': f'{settings.SITE_URL}/account/',
            }
            count = len(due)
            send_mail(
                subject=f'AppWheel: {count} reminder{"s" if count != 1 else ""} for today',
                message=render_to_string('reminders/email/due_today.txt', context),
                html_message=render_to_string('reminders/email/due_today.html', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            Reminder.objects.filter(pk__in=[reminder.pk for reminder in due]).update(emailed_on=today)
            sent += 1
        self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder email(s).'))
