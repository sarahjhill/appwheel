from django.contrib import admin

from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'due_date', 'kind', 'is_done')
    list_filter = ('kind', 'is_done')
    search_fields = ('title', 'user__email')
