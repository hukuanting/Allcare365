import json
from datetime import datetime, timezone
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from oauth2_provider.models import AccessToken, Grant, RefreshToken

from apps.clinical.health_screening.models import (
    DataImportBatch,
    Questionnaire,
    RiskAssessmentRun,
)
from apps.clinical.patients.models import Patient, Practitioner
from apps.core.authentication.models import ProductUser
from apps.integration.fhir_integration.models import AuditLog, FHIRResource, FHIRResourceMapping


PROTECTED_PATIENT_IDS = {
    "00000000-0000-4000-a000-000000000001",  # ONC Single Patient API golden patient
    "10000000-0000-4000-a000-000000000001",  # Bulk Data group patient
    "10000000-0000-4000-a000-000000000002",
    "10000000-0000-4000-a000-000000000003",
}

PROTECTED_CLIENT_IDS = {
    "inferno_ehr_client",
    "inferno_client_id",
    "inferno_public_client",
    "inferno_asymmetric_client",
    "inferno_bulk_client",
}


class Command(BaseCommand):
    help = (
        "Clean product/development database data while preserving ONC g10 "
        "certification fixtures and Inferno client registrations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Apply deletion. Without this flag the command only prints a dry-run report.",
        )
        parser.add_argument(
            "--keep-risk-assessments",
            action="store_true",
            help="Keep product-derived risk runs and FHIRResource RiskAssessment rows.",
        )
        parser.add_argument(
            "--archive-dir",
            default="logs/database_cleanup",
            help="Directory for cleanup manifest JSON.",
        )

    def handle(self, *args, **options):
        execute = options["execute"]
        archive_dir = Path(settings.BASE_DIR) / options["archive_dir"]

        report = self._build_report(options)
        archive_path = self._write_report(report, archive_dir, execute)

        self.stdout.write(self.style.WARNING("Product database cleanup report"))
        self.stdout.write(f"Mode: {'EXECUTE' if execute else 'DRY-RUN'}")
        self.stdout.write(f"Archive: {archive_path}")
        self.stdout.write("")

        for label, count in report["delete_counts"].items():
            self.stdout.write(f"{label}: {count}")

        self.stdout.write("")
        self.stdout.write("Protected patients:")
        for patient in report["protected_patients"]:
            self.stdout.write(f"- {patient['id']} {patient['mrn']} {patient['name']}")

        self.stdout.write("")
        self.stdout.write("Protected OAuth clients:")
        for client_id in report["protected_clients"]:
            self.stdout.write(f"- {client_id}")

        if not execute:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Dry-run complete. Re-run with --execute to apply."))
            return

        with transaction.atomic():
            self._delete_candidates(options)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Cleanup complete. ONC fixtures were preserved."))

    def _build_report(self, options):
        patient_candidates = Patient.objects.exclude(id__in=PROTECTED_PATIENT_IDS).order_by("id")
        protected_patients = Patient.objects.filter(id__in=PROTECTED_PATIENT_IDS).order_by("id")
        risk_candidates = FHIRResource.objects.filter(resource_type="RiskAssessment")

        delete_counts = {
            "non_protected_patients": patient_candidates.count(),
            "oauth_access_tokens": AccessToken.objects.count(),
            "oauth_refresh_tokens": RefreshToken.objects.count(),
            "oauth_authorization_grants": Grant.objects.count(),
        }
        if not options["keep_risk_assessments"]:
            delete_counts["product_risk_assessment_runs"] = RiskAssessmentRun.objects.count()
            delete_counts["product_fhir_risk_assessments"] = risk_candidates.count()
        delete_counts.update({
            "product_fhir_resource_mappings": FHIRResourceMapping.objects.count(),
            "product_import_batches": DataImportBatch.objects.count(),
            "product_questionnaires": Questionnaire.objects.count(),
            "product_practitioners": Practitioner.objects.count(),
            "product_users": ProductUser.objects.count(),
            "audit_logs": AuditLog.objects.count(),
        })

        model_counts = {}
        for model in apps.get_models():
            label = model._meta.label
            if label.startswith(("patients.", "health_screening.", "fhir_integration.", "authentication.")):
                try:
                    model_counts[label] = model.objects.count()
                except Exception as exc:
                    model_counts[label] = f"error: {exc}"

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "execute" if options["execute"] else "dry_run",
            "protected_patient_ids": sorted(PROTECTED_PATIENT_IDS),
            "protected_client_ids": sorted(PROTECTED_CLIENT_IDS),
            "protected_patients": [
                {
                    "id": str(patient.id),
                    "mrn": patient.medical_record_number,
                    "name": f"{patient.first_name} {patient.last_name}",
                }
                for patient in protected_patients
            ],
            "patient_delete_candidates": [
                {
                    "id": str(patient.id),
                    "mrn": patient.medical_record_number,
                    "name": f"{patient.first_name} {patient.last_name}",
                }
                for patient in patient_candidates
            ],
            "protected_clients": sorted(PROTECTED_CLIENT_IDS),
            "delete_counts": delete_counts,
            "model_counts_before": model_counts,
        }

    def _write_report(self, report, archive_dir, execute):
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "execute" if execute else "dry_run"
        filename = f"{stamp}_{slugify(mode)}.json"
        path = archive_dir / filename
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _delete_candidates(self, options):
        Patient.objects.exclude(id__in=PROTECTED_PATIENT_IDS).delete()
        AccessToken.objects.all().delete()
        RefreshToken.objects.all().delete()
        Grant.objects.all().delete()

        if not options["keep_risk_assessments"]:
            RiskAssessmentRun.objects.all().delete()
            FHIRResource.objects.filter(resource_type="RiskAssessment").delete()

        FHIRResourceMapping.objects.all().delete()
        DataImportBatch.objects.all().delete()
        Questionnaire.objects.all().delete()
        Practitioner.objects.all().delete()
        ProductUser.objects.all().delete()
        AuditLog.objects.all().delete()
