"""
Adds the main social and messaging apps, each with six safety guide topics
linked to the app's official help centre. The step-by-step instructions are
added in the admin after checking them on the official help pages, because
these apps change their menus often.
"""
from django.db import migrations

SOCIAL_APPS = [
    ('Facebook', 'facebook', 'https://www.facebook.com/help'),
    ('Instagram', 'instagram', 'https://help.instagram.com'),
    ('TikTok', 'tiktok', 'https://support.tiktok.com'),
    ('WhatsApp', 'whatsapp', 'https://faq.whatsapp.com'),
    ('X', 'x', 'https://help.x.com'),
    ('Snapchat', 'snapchat', 'https://help.snapchat.com'),
]

GUIDE_TOPICS = [
    'Block someone',
    'Make your posts private',
    'See where you\'re logged in',
    'Report a fake account or scam',
    'Delete or deactivate your account',
    'Reach a real person',
]


def add_social_apps(apps, schema_editor):
    CommonApp = apps.get_model('wheel', 'CommonApp')
    SafetyGuide = apps.get_model('wheel', 'SafetyGuide')
    for name, slug, help_url in SOCIAL_APPS:
        common_app, _ = CommonApp.objects.get_or_create(
            name=name, defaults={'slug': slug, 'category': 'social', 'help_url': help_url},
        )
        for position, title in enumerate(GUIDE_TOPICS):
            SafetyGuide.objects.get_or_create(
                common_app=common_app, title=title,
                defaults={'help_url': help_url, 'position': position},
            )


def remove_social_apps(apps, schema_editor):
    CommonApp = apps.get_model('wheel', 'CommonApp')
    CommonApp.objects.filter(name__in=[name for name, _, _ in SOCIAL_APPS], subscriptions__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('wheel', '0005_safety_guides'),
    ]

    operations = [
        migrations.RunPython(add_social_apps, remove_social_apps),
    ]
