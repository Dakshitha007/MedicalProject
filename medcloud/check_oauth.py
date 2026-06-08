import os, sys
from pathlib import Path
sys.path.insert(0, os.path.join(os.getcwd(), 'medcloud'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcloud.settings')
import django
django.setup()
from django.conf import settings
print('GOOGLE_CLIENT_ID from settings:', repr(getattr(settings, 'GOOGLE_CLIENT_ID', None)))
print('SOCIALACCOUNT_PROVIDERS.google.APP:', settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APP'))
# Check database SocialApp entries
try:
    from allauth.socialaccount.models import SocialApp
    apps = list(SocialApp.objects.filter(provider='google'))
    print('SocialApp google count:', len(apps))
    for app in apps:
        print('  SocialApp id:', app.id, 'name:', app.name, 'client_id:', app.client_id, 'sites:', [s.id for s in app.sites.all()])
except Exception as e:
    print('Error reading SocialApp from DB:', e)
# Print SITE_ID
print('SITE_ID:', getattr(settings, 'SITE_ID', None))
print('INSTALLED_APPS contains allauth:', 'allauth' in settings.INSTALLED_APPS)
