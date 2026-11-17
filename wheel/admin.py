from django.contrib import admin

from .models import CommonApp, CommonAppPlan, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'price', 'billing_period', 'status')
    list_filter = ('category', 'billing_period', 'status')
    search_fields = ('name', 'user__email')


class CommonAppPlanInline(admin.TabularInline):
    model = CommonAppPlan
    extra = 2


@admin.register(CommonApp)
class CommonAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'plan_count')
    list_filter = ('category',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CommonAppPlanInline]

    @admin.display(description='plans')
    def plan_count(self, common_app):
        return common_app.plans.count()
