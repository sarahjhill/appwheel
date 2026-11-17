"""
Adds a starter list of well-known apps. Plans and prices are added in the
admin, because prices change and need checking on each company's website.
"""
from django.db import migrations
from django.utils.text import slugify

STARTER_APPS = [
    ('Adobe', 'design'), ('Amazon Prime', 'video'), ('Amazon Prime Video', 'video'),
    ('Apple Music', 'music'), ('Apple TV+', 'video'), ('Audible', 'books'),
    ('BritBox', 'video'), ('BT', 'other'), ('Calm', 'fitness'), ('Canva', 'design'),
    ('ChatGPT', 'ai'), ('Claude', 'ai'), ('David Lloyd', 'fitness'), ('Deezer', 'music'),
    ('Deliveroo Plus', 'other'), ('discovery+', 'video'), ('Disney+', 'video'),
    ('Dropbox', 'storage'), ('Duolingo', 'other'), ('EE', 'other'), ('Everand', 'books'),
    ('Figma', 'design'), ('giffgaff', 'other'), ('Google One', 'storage'),
    ('Headspace', 'fitness'), ('iCloud+', 'storage'), ('Kindle Unlimited', 'books'),
    ('LinkedIn Premium', 'other'), ('Microsoft 365', 'storage'), ('Midjourney', 'ai'),
    ('Netflix', 'video'), ('Nintendo Switch Online', 'other'), ('NOW', 'video'),
    ('O2', 'other'), ('Paramount+', 'video'), ('Patreon', 'other'), ('Peloton', 'fitness'),
    ('PlayStation Plus', 'other'), ('Plusnet', 'other'), ('PureGym', 'fitness'),
    ('Sky', 'video'), ('Spotify', 'music'), ('Strava', 'fitness'), ('TalkTalk', 'other'),
    ('The Gym Group', 'fitness'), ('Tidal', 'music'), ('TV Licence', 'video'),
    ('Uber One', 'other'), ('Virgin Media', 'other'), ('Vodafone', 'other'),
    ('Xbox Game Pass', 'other'), ('YouTube Premium', 'video'),
]


def add_starter_apps(apps, schema_editor):
    CommonApp = apps.get_model('wheel', 'CommonApp')
    for name, category in STARTER_APPS:
        CommonApp.objects.get_or_create(
            name=name, defaults={'slug': slugify(name) or name.lower(), 'category': category},
        )


def remove_starter_apps(apps, schema_editor):
    CommonApp = apps.get_model('wheel', 'CommonApp')
    CommonApp.objects.filter(name__in=[name for name, _ in STARTER_APPS], plans__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('wheel', '0002_common_apps'),
    ]

    operations = [
        migrations.RunPython(add_starter_apps, remove_starter_apps),
    ]
