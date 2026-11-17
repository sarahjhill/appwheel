"""
Health scores: a green, amber or red light for each app, the reason in
plain English, and ways to save with £ amounts.

The rules (from the plan):
  Red    - free trial ends within 7 days
  Red    - used "rarely" or "never"
  Amber  - another app in the same category (e.g. two music apps)
  Amber  - a cheaper plan exists
  Amber  - paying monthly when paying yearly is cheaper
  Green  - none of the above
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .models import BillingPeriod, CommonApp

GREEN, AMBER, RED = 'green', 'amber', 'red'
SYMBOLS = {GREEN: '✓', AMBER: '!', RED: '✕'}
LABELS = {GREEN: 'Good value', AMBER: 'Could cost less', RED: 'Needs action'}
# Categories where having two apps is normal, so we don't flag them
CATEGORIES_NOT_COMPARED = {'other'}


@dataclass
class Tip:
    text: str
    yearly_saving: Decimal

    @property
    def monthly_saving(self):
        return (self.yearly_saving / 12).quantize(Decimal('0.01'))


@dataclass
class Health:
    light: str
    score: int
    reason: str
    tips: list = field(default_factory=list)

    @property
    def symbol(self):
        return SYMBOLS[self.light]

    @property
    def label(self):
        return LABELS[self.light]

    @property
    def best_yearly_saving(self):
        """The most you could save on this app (tips aren't added together)."""
        return max((tip.yearly_saving for tip in self.tips), default=Decimal('0'))


def money(amount):
    return f'£{Decimal(amount).quantize(Decimal("0.01")):,}'


def score_subscription(sub, all_subs, today=None):
    """Work out the light, score, reason and money-saving tips for one app."""
    today = today or date.today()
    problems = []  # (light, points to take off, reason)
    tips = []
    yearly = sub.yearly_cost
    common_app = _common_app_for(sub)

    # Red: free trial ending soon
    if sub.trial_end_date and 0 <= (sub.trial_end_date - today).days <= 7:
        days = (sub.trial_end_date - today).days
        when = 'today' if days == 0 else 'tomorrow' if days == 1 else f'in {days} days'
        problems.append((RED, 50, f'Your free trial ends {when}. Cancel before then if you don\'t want to pay.'))
        if sub.price:
            tips.append(Tip(
                f'Cancel before {sub.trial_end_date.day} {sub.trial_end_date:%B} to avoid paying {money(sub.price)}',
                yearly,
            ))

    # Red: hardly used
    if sub.usage in ('rarely', 'never') and sub.price:
        used = 'never use' if sub.usage == 'never' else 'rarely use'
        problems.append((RED, 50, f'You {used} it but pay {money(yearly)} a year.'))
        tips.append(Tip(f'Cancel {sub.name} to save {money(yearly)} a year', yearly))

    # Amber: another app doing the same job
    if sub.price and sub.category not in CATEGORIES_NOT_COMPARED:
        others = [
            other for other in all_subs
            if other.pk != sub.pk and other.status == 'active' and other.category == sub.category
        ]
        if others:
            names = _join_names([other.name for other in others[:3]])
            does = 'does' if len(others) == 1 else 'do'
            problems.append((AMBER, 20, f'You also pay for {names}, which {does} a similar job.'))
            keeper = _app_to_keep([sub] + others)
            if keeper.pk != sub.pk:
                tips.append(Tip(f'Cancel {sub.name} and keep {keeper.name} to save {money(yearly)} a year', yearly))

    # Amber: a cheaper plan, or a cheaper way to pay
    if common_app and sub.price:
        plans = list(common_app.plans.all())
        cheaper = [
            plan for plan in plans
            if plan.billing_period != BillingPeriod.YEARLY
            and plan.monthly_cost < sub.monthly_cost
            and plan.name.lower() != (sub.plan_name or '').lower()
        ]
        if cheaper:
            plan = max(cheaper, key=lambda plan: plan.monthly_cost)  # the next one down
            saving = (sub.monthly_cost - plan.monthly_cost) * 12
            problems.append((AMBER, 20, f'{common_app.name} has a cheaper plan: {plan.name} at {money(plan.price)} a month.'))
            tips.append(Tip(f'Switch to {plan.name} to save {money(saving)} a year', saving))

        if sub.billing_period != BillingPeriod.YEARLY:
            yearly_plans = [
                plan for plan in plans
                if plan.billing_period == BillingPeriod.YEARLY and plan.price < yearly
                and (not sub.plan_name or sub.plan_name.lower() in plan.name.lower())
            ]
            if yearly_plans:
                plan = min(yearly_plans, key=lambda plan: plan.price)
                saving = yearly - plan.price
                problems.append((AMBER, 15, f'Paying yearly would cost {money(plan.price)} instead of {money(yearly)}.'))
                tips.append(Tip(f'Pay yearly to save {money(saving)} a year', saving))

    if not problems:
        reason = 'Good value. You use it and there\'s nothing cheaper we know of.'
        if not sub.price:
            reason = 'It\'s free, so there\'s nothing to save.'
        score = 100 if sub.usage in ('daily', 'weekly') or not sub.price else 85
        return Health(GREEN, score, reason, tips)

    order = {RED: 0, AMBER: 1}
    problems.sort(key=lambda problem: order[problem[0]])
    score = max(5, 100 - sum(points for _, points, _ in problems))
    tips.sort(key=lambda tip: tip.yearly_saving, reverse=True)
    return Health(problems[0][0], score, problems[0][2], tips)


USAGE_RANK = {'daily': 0, 'weekly': 1, 'monthly': 2, 'rarely': 3, 'never': 4}


def _app_to_keep(similar_apps):
    """Of several apps doing the same job, keep the one used most (then the cheapest)."""
    return min(similar_apps, key=lambda app: (USAGE_RANK.get(app.usage, 2), app.monthly_cost, app.pk))


def _join_names(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def _common_app_for(sub):
    if sub.common_app_id:
        return sub.common_app
    return CommonApp.objects.filter(name__iexact=sub.name).prefetch_related('plans').first()


def summarise(subscriptions, today=None):
    """Score every active app and add up the totals for the page."""
    active = [sub for sub in subscriptions if sub.status == 'active']
    for sub in subscriptions:
        sub.health = score_subscription(sub, active, today) if sub.status == 'active' else None
    monthly = sum((sub.monthly_cost for sub in active), Decimal('0'))
    savings = sum((sub.health.best_yearly_saving for sub in active), Decimal('0'))
    return {
        'monthly_total': monthly.quantize(Decimal('0.01')),
        'yearly_total': (monthly * 12).quantize(Decimal('0.01')),
        'possible_yearly_saving': savings.quantize(Decimal('0.01')),
        'counts': {
            light: sum(1 for sub in active if sub.health.light == light)
            for light in (GREEN, AMBER, RED)
        },
    }
