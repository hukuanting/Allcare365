"""Create a persisted certification Group from explicitly selected fixtures."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource
from apps.integration.fhir_integration.resource_identity import identity

CERTIFICATION_GROUP_ORIGIN_NAMESPACE = "allcare365:onc-certification:v1"


class Command(BaseCommand):
    help = (
        "Create or update a persisted FHIR Group for Bulk Data certification. "
        "This command never creates patients."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--patient-id",
            action="append",
            dest="patient_ids",
            required=True,
            help="Existing synthetic/certification Patient UUID; repeat for each member.",
        )
        parser.add_argument(
            "--group-id",
            default="example-group",
            help="FHIR Group logical id (default: example-group).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        group_id = str(options["group_id"] or "").strip()
        requested_ids = [str(value).strip() for value in options["patient_ids"]]
        if not group_id:
            raise CommandError("--group-id cannot be blank")
        if len(requested_ids) != len(set(requested_ids)):
            raise CommandError("Duplicate --patient-id values are not allowed")

        patients_by_id = {
            str(patient.id): patient
            for patient in Patient.objects.filter(id__in=requested_ids, is_active=True)
        }
        if set(patients_by_id) != set(requested_ids):
            missing = sorted(set(requested_ids).difference(patients_by_id))
            raise CommandError("Active Patient fixture not found: " + ", ".join(missing))

        patients = [patients_by_id[patient_id] for patient_id in requested_ids]
        for patient in patients:
            metadata = patient.metadata_json if isinstance(patient.metadata_json, dict) else {}
            is_certification_fixture = bool(
                metadata.get("certification_fixture")
                or metadata.get("conformance_fixture")
            )
            if not (
                metadata.get("synthetic") is True
                and metadata.get("clinical_use_prohibited") is True
                and is_certification_fixture
            ):
                raise CommandError(
                    f"Patient {patient.id} is not an explicitly marked, clinical-use-prohibited fixture"
                )

        members = [
            {"entity": {"reference": f"Patient/{identity.patient_id(patient)}"}}
            for patient in patients
        ]
        resource_json = {
            "resourceType": "Group",
            "id": group_id,
            "type": "person",
            "actual": True,
            "quantity": len(members),
            "member": members,
        }
        persisted, created = FHIRResource.objects.select_for_update().get_or_create(
            resource_type="Group",
            resource_id=group_id,
            defaults={
                "origin_namespace": CERTIFICATION_GROUP_ORIGIN_NAMESPACE,
                "resource_data": resource_json,
                "is_active": True,
            },
        )
        if not created:
            if persisted.origin_namespace != CERTIFICATION_GROUP_ORIGIN_NAMESPACE:
                raise CommandError(
                    f"FHIR Group/{group_id} is owned by {persisted.origin_namespace}; "
                    "refusing certification fixture takeover"
                )
            persisted.resource_data = resource_json
            persisted.is_active = True
            persisted.save(update_fields=["resource_data", "is_active", "last_updated"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Persisted Group/{group_id} with {len(patients)} explicit certification members."
            )
        )
