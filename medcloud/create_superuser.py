import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcloud.settings')
django.setup()

def ensure_superuser(email='admin@local', username='admin', password='AdminPass123'):
    from authentication.models import User
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(email=email, username=username, password=password)
        print(f'Superuser created: {email} / {password}')
    else:
        print(f'Superuser already exists: {email}')

if __name__ == '__main__':
    ensure_superuser()
