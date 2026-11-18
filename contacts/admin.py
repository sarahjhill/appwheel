from django.contrib import admin

from .models import PersonalContact


@admin.register(PersonalContact)
class PersonalContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'user')
    list_filter = ('label',)
    search_fields = ('name', 'user__email')
