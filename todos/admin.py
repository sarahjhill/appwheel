from django.contrib import admin

from .models import Todo


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ('text', 'user', 'done', 'created_at')
    list_filter = ('done',)
    search_fields = ('user__email',)
