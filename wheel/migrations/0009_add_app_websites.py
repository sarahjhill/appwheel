"""Adds each common app's official website, used to fetch its official icon."""
from django.db import migrations

WEBSITES = {
    'Adobe': 'adobe.com', 'Amazon Prime': 'amazon.co.uk', 'Amazon Prime Video': 'primevideo.com',
    'Apple Music': 'apple.com', 'Apple TV+': 'apple.com', 'Audible': 'audible.co.uk',
    'BritBox': 'britbox.co.uk', 'BT': 'bt.com', 'Calm': 'calm.com', 'Canva': 'canva.com',
    'ChatGPT': 'chatgpt.com', 'Claude': 'claude.ai', 'David Lloyd': 'davidlloyd.co.uk',
    'Deezer': 'deezer.com', 'Deliveroo Plus': 'deliveroo.co.uk', 'discovery+': 'discoveryplus.com',
    'Disney+': 'disneyplus.com', 'Dropbox': 'dropbox.com', 'Duolingo': 'duolingo.com',
    'EE': 'ee.co.uk', 'Everand': 'everand.com', 'Figma': 'figma.com', 'giffgaff': 'giffgaff.com',
    'Google One': 'one.google.com', 'Headspace': 'headspace.com', 'iCloud+': 'icloud.com',
    'Kindle Unlimited': 'amazon.co.uk', 'LinkedIn Premium': 'linkedin.com',
    'Microsoft 365': 'microsoft.com', 'Midjourney': 'midjourney.com', 'Netflix': 'netflix.com',
    'Nintendo Switch Online': 'nintendo.com', 'NOW': 'nowtv.com', 'O2': 'o2.co.uk',
    'Paramount+': 'paramountplus.com', 'Patreon': 'patreon.com', 'Peloton': 'onepeloton.co.uk',
    'PlayStation Plus': 'playstation.com', 'Plusnet': 'plus.net', 'PureGym': 'puregym.com',
    'Sky': 'sky.com', 'Spotify': 'spotify.com', 'Strava': 'strava.com', 'TalkTalk': 'talktalk.co.uk',
    'The Gym Group': 'thegymgroup.com', 'Tidal': 'tidal.com', 'TV Licence': 'tvlicensing.co.uk',
    'Uber One': 'uber.com', 'Virgin Media': 'virginmedia.com', 'Vodafone': 'vodafone.co.uk',
    'Xbox Game Pass': 'xbox.com', 'YouTube Premium': 'youtube.com',
    'Facebook': 'facebook.com', 'Instagram': 'instagram.com', 'TikTok': 'tiktok.com',
    'WhatsApp': 'whatsapp.com', 'X': 'x.com', 'Snapchat': 'snapchat.com',
}


def add_websites(apps, schema_editor):
    CommonApp = apps.get_model('wheel', 'CommonApp')
    for name, website in WEBSITES.items():
        CommonApp.objects.filter(name=name, website='').update(website=website)


class Migration(migrations.Migration):

    dependencies = [
        ('wheel', '0008_app_websites'),
    ]

    operations = [
        migrations.RunPython(add_websites, migrations.RunPython.noop),
    ]
