from django.contrib import admin

from .models import CareDiary, DiaryEntry


@admin.register(DiaryEntry)
class DiaryEntryAdmin(admin.ModelAdmin):
    # Care notes are private: the admin list shows only dates and ratings
    list_display = ('user', 'date', 'rating')
    list_filter = ('rating',)
    search_fields = ('user__email',)


admin.site.register(CareDiary)
