from django.core.management.base import BaseCommand
from frontend.services.integrity_service import verify_all_reports


class Command(BaseCommand):
    help = 'Verify off-chain report integrity against blockchain anchor hashes.'

    def handle(self, *args, **options):
        summary = verify_all_reports()
        self.stdout.write(self.style.SUCCESS(f"Integrity check complete: {summary}"))
