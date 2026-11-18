from django.contrib import admin

from .models import CommonApp, CommonAppPlan, SafetyGuide, Subscription


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


@admin.register(SafetyGuide)
class SafetyGuideAdmin(admin.ModelAdmin):
    list_display = ('title', 'common_app', 'has_steps', 'last_checked')
    list_filter = ('common_app', 'last_checked')
    search_fields = ('title', 'common_app__name')

    @admin.display(boolean=True, description='steps added')
    def has_steps(self, guide):
        return bool(guide.steps.strip())
