import re

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    r'^\+?[\d\s()-]{3,20}$',
    'Please enter a phone number using numbers only, for example 029 2000 0000.',
)


class PersonalContact(models.Model):
    """Someone important to the user: their GP, pharmacy, next of kin or care company."""

    class Label(models.TextChoices):
        GP = 'gp', 'GP surgery'
        PHARMACY = 'pharmacy', 'Pharmacy'
        NEXT_OF_KIN = 'next_of_kin', 'Next of kin'
        CARE_COMPANY = 'care_company', 'Care company'
        SOCIAL_WORKER = 'social_worker', 'Social worker'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contacts')
    label = models.CharField('who is this?', max_length=20, choices=Label.choices, default=Label.OTHER)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['label', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_label_display()})'

    @property
    def phone_link(self):
        """The number as a tap-to-call link, e.g. 'tel:+442920000000'."""
        return 'tel:' + re.sub(r'[^\d+]', '', self.phone)
