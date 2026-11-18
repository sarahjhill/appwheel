from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from wheel.models import Subscription

from .automatic import sync_app_reminders
from .models import Reminder


@receiver(post_save, sender=Subscription)
def keep_reminders_in_step(sender, instance, **kwargs):
    sync_app_reminders(instance)


@receiver(pre_delete, sender=Subscription)
def remove_automatic_reminders(sender, instance, **kwargs):
    instance.reminders.filter(kind__in=Reminder.AUTOMATIC_KINDS).delete()
