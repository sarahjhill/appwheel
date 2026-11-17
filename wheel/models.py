from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Subscription(models.Model):
    """One app or subscription that a user pays for (or uses for free)."""

    class Category(models.TextChoices):
        MUSIC = 'music', 'Music'
        VIDEO = 'video', 'TV and video'
        AI = 'ai', 'AI tools'
        STORAGE = 'storage', 'Cloud storage'
        BOOKS = 'books', 'Books and audiobooks'
        DESIGN = 'design', 'Design'
        FITNESS = 'fitness', 'Health and fitness'
        OTHER = 'other', 'Other'

    class BillingPeriod(models.TextChoices):
        WEEKLY = 'weekly', 'Every week'
        MONTHLY = 'monthly', 'Every month'
        YEARLY = 'yearly', 'Every year'

    class Usage(models.TextChoices):
        DAILY = 'daily', 'Every day'
        WEEKLY = 'weekly', 'Every week'
        MONTHLY = 'monthly', 'Every month'
        RARELY = 'rarely', 'Rarely'
        NEVER = 'never', 'Never'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    name = models.CharField('app name', max_length=100)
    plan_name = models.CharField(
        'plan', max_length=100, blank=True,
        help_text='For example "Premium Family". Leave blank if you\'re not sure.',
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER,
    )
    price = models.DecimalField(
        'price (£)', max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Type 0 for a free app.',
    )
    billing_period = models.CharField(
        'how often you pay', max_length=10,
        choices=BillingPeriod.choices, default=BillingPeriod.MONTHLY,
    )
    next_payment_date = models.DateField(
        'next payment date', null=True, blank=True,
    )
    trial_end_date = models.DateField(
        'free trial ends', null=True, blank=True,
        help_text='Only if you\'re on a free trial.',
    )
    usage = models.CharField(
        'how often you use it', max_length=10,
        choices=Usage.choices, default=Usage.WEEKLY,
    )
    benefits = models.CharField(
        'what you get from it', max_length=200, blank=True,
        help_text='Optional. For example "no adverts" or "shared with my family".',
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.user})'
