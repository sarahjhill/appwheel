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
        OTHER = 'other', 'Other'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders')
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    title = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    due_date = models.DateField()
    subscription = models.ForeignKey(
        'wheel.Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='reminders',
    )
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f'{self.title} ({self.due_date})'
