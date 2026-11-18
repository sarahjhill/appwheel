from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.TextChoices):
    MUSIC = 'music', 'Music'
    VIDEO = 'video', 'TV and video'
    AI = 'ai', 'AI tools'
    STORAGE = 'storage', 'Cloud storage'
    BOOKS = 'books', 'Books and audiobooks'
    DESIGN = 'design', 'Design'
    FITNESS = 'fitness', 'Health and fitness'
    SOCIAL = 'social', 'Social and messaging'
    OTHER = 'other', 'Other'


class BillingPeriod(models.TextChoices):
    WEEKLY = 'weekly', 'Every week'
    MONTHLY = 'monthly', 'Every month'
    YEARLY = 'yearly', 'Every year'


def to_monthly(price, billing_period):
    """Turn a weekly, monthly or yearly price into a price per month."""
    price = Decimal(price)
    if billing_period == BillingPeriod.WEEKLY:
        price = price * 52 / 12
    elif billing_period == BillingPeriod.YEARLY:
        price = price / 12
    return price.quantize(Decimal('0.01'))


class CommonApp(models.Model):
    """A well-known app, like Netflix. Managed in the admin, shared by everyone."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    cancel_url = models.URLField('cancel page', blank=True, help_text='The page where people cancel.')
    help_url = models.URLField('help page', blank=True)
    website = models.CharField(
        max_length=100, blank=True,
        help_text='The company\'s own website, for example netflix.com. Used to fetch its official icon.',
    )
    icon = models.CharField(
        max_length=100, blank=True,
        help_text=(
            'File name of the official icon in static/app-icons/, for example netflix.png. '
            'Only add it if the company\'s brand rules allow. Leave blank to show initials.'
        ),
    )
    cancel_steps = models.TextField(
        blank=True,
        help_text='Simple steps to cancel, one per line. Check them on the company\'s own help page.',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SafetyGuide(models.Model):
    """A short, plain-English guide, like 'Block someone on Instagram'."""

    common_app = models.ForeignKey(CommonApp, on_delete=models.CASCADE, related_name='safety_guides')
    title = models.CharField(max_length=120)
    steps = models.TextField(
        blank=True,
        help_text='One step per line. Copy them from the official help page, in plain English.',
    )
    help_url = models.URLField('official help page')
    last_checked = models.DateField(
        null=True, blank=True, help_text='The date you last checked these steps against the official help page.',
    )
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['common_app', 'position']

    def __str__(self):
        return f'{self.common_app.name}: {self.title}'

    @property
    def step_list(self):
        return [step.strip() for step in self.steps.splitlines() if step.strip()]


class CommonAppPlan(models.Model):
    """One plan for a common app, like Netflix Standard at £12.99 a month."""

    common_app = models.ForeignKey(CommonApp, on_delete=models.CASCADE, related_name='plans')
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        'price (£)', max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    billing_period = models.CharField(
        max_length=10, choices=BillingPeriod.choices, default=BillingPeriod.MONTHLY,
    )

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f'{self.common_app.name} {self.name}'

    @property
    def monthly_cost(self):
        return to_monthly(self.price, self.billing_period)


class Subscription(models.Model):
    """One app or subscription that a user pays for (or uses for free)."""

    Category = Category
    BillingPeriod = BillingPeriod

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
    common_app = models.ForeignKey(
        CommonApp, on_delete=models.SET_NULL, null=True, blank=True,
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
    cancelled_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.user})'

    @property
    def monthly_cost(self):
        """What this costs in an average month, whether paid weekly, monthly or yearly."""
        return to_monthly(self.price, self.billing_period)

    @property
    def yearly_cost(self):
        return (self.monthly_cost * 12).quantize(Decimal('0.01'))

    @property
    def initials(self):
        """Letters for the app's tile, e.g. 'Netflix' -> 'Ne', 'iCloud+' -> 'iC', 'Sky TV' -> 'ST'."""
        words = [word for word in self.name.replace('+', ' ').split() if word]
        if not words:
            return '?'
        if len(words) > 1:
            return (words[0][0] + words[1][0]).upper()
        word = words[0]
        if word.isupper():
            return word[:3]  # names that are already short capitals: EE, BT, NOW
        letters = word[:2]
        # Keep names like "iCloud" as they're written; otherwise "Ne" not "NE"
        return letters if letters[0].islower() and letters[1:].isupper() else letters[0].upper() + letters[1:].lower()

    @property
    def icon_path(self):
        """The official icon's file in static/, if one has been added for this app."""
        if self.common_app and self.common_app.icon:
            return f'app-icons/{self.common_app.icon}'
        return ''

    @property
    def cancel_step_list(self):
        if self.common_app and self.common_app.cancel_steps:
            return [step.strip() for step in self.common_app.cancel_steps.splitlines() if step.strip()]
        return []


def link_common_apps(user):
    """Link the user's apps to the common list by name, so they get icons, plans and guides."""
    for subscription in user.subscriptions.filter(common_app__isnull=True):
        common_app = CommonApp.objects.filter(name__iexact=subscription.name).first()
        if common_app:
            subscription.common_app = common_app
            subscription.save(update_fields=['common_app'])
