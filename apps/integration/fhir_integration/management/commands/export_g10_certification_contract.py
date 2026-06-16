import json

from django.core.management.base import BaseCommand

from apps.integration.fhir_integration.g10_testkit import (
    build_g10_single_patient_contract,
    default_output_path,
)


class Command(BaseCommand):
    help = "Export the local ONC g10 single-patient certification contract artifact."

    def handle(self, *args, **options):
        payload = build_g10_single_patient_contract()
        output_path = default_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Exported g10 certification contract to {output_path}"))
