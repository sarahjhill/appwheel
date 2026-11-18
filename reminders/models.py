from django.conf import settings
from django.db import models


class Reminder(models.Model):
    """Something the user needs to do on a date, like checking they weren't charged."""

    class Kind(models.TextChoices):
        CHARGE_CHECK = 'charge_check', 'Check you weren\'t charged'
        TRIAL = 'trial', 'Free trial ending'
        RENEWAL = 'renewal', 'Renewal coming up'
        APPOINTMENT = 'appointment', 'Appointment'
        PRESCRIPTION = 'prescription', 'Repeat prescription'
        PRIVACY = 'privacy', 'Privacy check-up'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders')
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    title = models.CharField(max_length=200)
    details = models.TextField('notes', blank=True)
    due_date = models.DateField('date')
    time = models.TimeField(null=True, blank=True)
    repeat_every_days = models.PositiveSmallIntegerField(
        'repeat every (days)', null=True, blank=True,
        help_text='For example 28 for a monthly repeat prescription. Leave blank for a one-off.',
    )
    subscription = models.ForeignKey(
        'wheel.Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='reminders',
    )
    is_done = models.BooleanField(default=False)
    emailed_on = models.DateField(null=True, blank=True)  # so each reminder is only emailed once
    created_at = models.DateTimeField(auto_now_add=True)

    # Made automatically from an app's dates, so they're kept in step with the app
    AUTOMATIC_KINDS = (Kind.TRIAL, Kind.RENEWAL)

    class Meta:
        ordering = ['due_date', 'time']

    def __str__(self):
        return f'{self.title} ({self.due_date})'

    @property
    def is_automatic(self):
        return self.kind in self.AUTOMATIC_KINDS


class ChecklistItem(models.Model):
    """One thing to remember, like 'Appointment letter'."""

    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='checklist')
    text = models.CharField(max_length=200)
    ticked = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'pk']

    def __str__(self):
        return self.text



class EmailSettings(models.Model):
    """Whether the user wants a reminder email on days when something is due."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_settings')
    reminder_emails = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'email settings'

    def __str__(self):
        return f'{self.user}: reminder emails {"on" if self.reminder_emails else "off"}'

    @classmethod
    def wants_emails(cls, user):
        settings_row = cls.objects.filter(user=user).first()
        return settings_row.reminder_emails if settings_row else True
