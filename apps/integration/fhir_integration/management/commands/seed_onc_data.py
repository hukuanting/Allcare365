"""
Backward-compatible wrapper for the canonical ONC seed command.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Compatibility wrapper which delegates to `seed_onc_patient`, the "
        "canonical ONC/g10 relational golden-patient seed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--patient-id",
            type=str,
            default="00000000-0000-4000-a000-000000000001",
            help="UUID for the seeded Patient primary key.",
        )

    def handle(self, *args, **options):
        call_command("seed_onc_patient", patient_id=options["patient_id"])
        self.stdout.write(
            self.style.SUCCESS(
                "Delegated to seed_onc_patient; canonical ONC golden patient seeded."
            )
        )
