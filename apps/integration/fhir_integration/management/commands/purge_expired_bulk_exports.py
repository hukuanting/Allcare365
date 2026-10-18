from django.core.management.base import BaseCommand

from apps.integration.fhir_integration.bulk_export_jobs import BulkExportJobStore


class Command(BaseCommand):
    help = "Delete expired FHIR Bulk Data jobs and their private NDJSON output files."

    def handle(self, *args, **options):
        purged = BulkExportJobStore.purge_expired()
        self.stdout.write(self.style.SUCCESS(f"Purged {purged} expired Bulk Data export job(s)."))
