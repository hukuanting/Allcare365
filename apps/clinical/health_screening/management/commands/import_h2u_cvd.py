from pathlib import Path
from typing import Any, Dict

from django.core.management.base import BaseCommand, CommandError

from apps.clinical.health_screening.ingestion_service import HealthScreeningIngestionService


class Command(BaseCommand):
    help = "Import the H2U CVD input CSV into Patient, Encounter, Observation, and QuestionnaireResponse source models."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="H2U_cvd_input_update.csv",
            help="Path to H2U_cvd_input_update.csv. Defaults to the repository root file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and normalize rows without creating clinical source records.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Only process the first N rows. Useful for smoke tests.",
        )
        parser.add_argument(
            "--allow-duplicates",
            action="store_true",
            help="Create rows even if the derived encounter identifier already exists.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"]).resolve()
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        service = HealthScreeningIngestionService()
        with csv_path.open("rb") as file_obj:
            result = service.bulk_import_file(
                file_obj,
                source_type="h2u_cvd_csv",
                original_filename=csv_path.name,
                limit=options["limit"],
                dry_run=options["dry_run"],
                skip_existing=not options["allow_duplicates"],
                row_transform=self._normalize_h2u_row,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "H2U CVD import finished: "
                f"batch={result['batch_id']} "
                f"created={result['success_count']} "
                f"validated={result['validated_count']} "
                f"skipped={result['skipped_count']} "
                f"errors={result['error_count']} "
                f"total={result['total_count']}"
            )
        )
        if result["errors"]:
            for error in result["errors"][:20]:
                self.stdout.write(self.style.WARNING(f"row {error['row']}: {error['error']}"))
            if len(result["errors"]) > 20:
                self.stdout.write(self.style.WARNING(f"... {len(result['errors']) - 20} more errors omitted"))

    def _normalize_h2u_row(self, row: Dict[str, Any], row_number: int) -> Dict[str, Any]:
        cleaned = {
            str(key).strip(): value
            for key, value in row.items()
            if str(key).strip()
        }
        source = str(cleaned.get("Source") or "H2U").strip()
        source_patient_id = str(cleaned.get("ID") or row_number).strip()
        check_date = self._date_token(cleaned.get("CheckDate")) or f"row-{row_number}"
        mrn = f"H2U-{source}-{source_patient_id}"

        cleaned.update(
            {
                "patient": mrn,
                "medical_record_number": mrn,
                "first_name": source_patient_id,
                "last_name": "H2U",
                "source_system": "H2U",
                "source_record_id": f"{source}:{source_patient_id}",
                "source_type": "h2u_cvd_csv",
                "encounter_type": "h2u_cvd_screening",
                "encounter_identifier": f"H2U-CVD-{source}-{source_patient_id}-{check_date}",
                "encounter_location": source,
            }
        )
        return cleaned

    def _date_token(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        return "".join(char for char in str(value) if char.isdigit())
