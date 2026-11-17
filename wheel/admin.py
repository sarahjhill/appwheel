from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'price', 'billing_period', 'status')
    list_filter = ('category', 'billing_period', 'status')
    search_fields = ('name', 'user__email')
