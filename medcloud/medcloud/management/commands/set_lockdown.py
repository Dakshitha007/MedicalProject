import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Enable or disable emergency lockdown mode by creating or removing the lockdown file.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['enable', 'disable'])
        parser.add_argument('--lockdown-file', default=os.getenv('EMERGENCY_LOCKDOWN_FILE', '/tmp/lockdown.flag'))

    def handle(self, *args, **options):
        path = options['lockdown_file']
        if options['action'] == 'enable':
            open(path, 'a').close()
            self.stdout.write(self.style.SUCCESS(f'Lockdown enabled at {path}'))
        else:
            if os.path.exists(path):
                os.remove(path)
                self.stdout.write(self.style.SUCCESS(f'Lockdown disabled at {path}'))
            else:
                self.stdout.write(self.style.WARNING(f'Lockdown file does not exist: {path}'))
