from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Create or update the Google SocialApp using environment variables.'

    def handle(self, *args, **options):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
        secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
        site_id = getattr(settings, 'SITE_ID', None)

        if not client_id or 'your-google-client-id' in client_id:
            self.stderr.write(self.style.ERROR('GOOGLE_CLIENT_ID is not configured correctly in settings or .env.'))
            return

        if not secret or 'your-google-client-secret' in secret:
            self.stderr.write(self.style.ERROR('GOOGLE_CLIENT_SECRET is not configured correctly in settings or .env.'))
            return

        if site_id is None:
            self.stderr.write(self.style.ERROR('SITE_ID is not configured in settings.'))
            return

        try:
            site = Site.objects.get(id=site_id)
        except Site.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Site with ID {site_id} does not exist. Please create it in django admin.'))
            return

        social_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google OAuth',
                'client_id': client_id,
                'secret': secret,
                'key': '',
            }
        )

        if not created:
            social_app.client_id = client_id
            social_app.secret = secret
            social_app.key = ''
            social_app.name = 'Google OAuth'
            social_app.save()
            self.stdout.write(self.style.SUCCESS('Updated existing Google SocialApp.'))
        else:
            self.stdout.write(self.style.SUCCESS('Created new Google SocialApp.'))

        if site not in social_app.sites.all():
            social_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f'Added site {site.domain} (ID {site.id}) to the Google SocialApp.'))

        self.stdout.write(self.style.SUCCESS('Google SocialApp sync complete.'))
