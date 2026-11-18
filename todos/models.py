from django.conf import settings
from django.db import models
from django.utils import timezone


class Todo(models.Model):
    """One thing on the user's to-do list."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='todos')
    text = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    # The day it's planned for. Unfinished to-dos from earlier days go to the backlog.
    day = models.DateField(default=timezone.localdate)
    in_backlog = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['done', '-created_at']

    def __str__(self):
        return self.text

    def is_backlog(self, today=None):
        """Not done, and either sent to the backlog or left over from an earlier day."""
        today = today or timezone.localdate()
        return not self.done and (self.in_backlog or self.day < today)
