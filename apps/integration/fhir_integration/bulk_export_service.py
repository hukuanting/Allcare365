"""Persisted-data-only FHIR Bulk Data projection.

Bulk export is intentionally a thin consumer of the same projector registry used
by the synchronous FHIR REST API.  It never manufactures resources to satisfy a
test fixture: every exported row must originate from an active persisted patient
and an explicitly approved ORM-backed projector.
"""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass

from apps.clinical.patients.models import Patient

from .fhir_context import FHIRContext
from .models import FHIRResource
from .projectors.registry import ProjectorRegistry
from .resource_identity import identity

# Trigger decorator-based projector registration before the allow-list is checked.
import apps.integration.fhir_integration.projectors  # noqa: F401,E402


logger = logging.getLogger("medical_system")


class BulkProjectionError(RuntimeError):
    """Raised when a requested export cannot be projected without fabrication."""


class BulkGroupNotFoundError(BulkProjectionError):
    """Raised when a Group export does not have a persisted Group resource."""


@dataclass(frozen=True)
class BulkExportScope:
    """The persisted patient cohort associated with one export job."""

    export_type: str
    group_id: str | None
    patients: tuple[Patient, ...]


class PersistentBulkExportService:
    """Project persisted ORM rows to NDJSON through ``ProjectorRegistry`` only."""

    GROUP_ID = "example-group"

    # These projectors query persisted patient/clinical ORM models.  Registered
    # singleton/template projectors (Location, Organization, Practitioner,
    # PractitionerRole, Media) and derived/non-query projectors (Provenance) are
    # deliberately excluded until they have a persisted repository boundary.
    ORM_BACKED_RESOURCE_TYPES = (
        "Patient",
        "AllergyIntolerance",
        "CarePlan",
        "CareTeam",
        "Condition",
        "Coverage",
        "Device",
        "DiagnosticReport",
        "DocumentReference",
        "Encounter",
        "Goal",
        "Immunization",
        "Medication",
        "MedicationDispense",
        "MedicationRequest",
        "Observation",
        "Procedure",
        "RelatedPerson",
        "ServiceRequest",
        "Specimen",
    )

    @classmethod
    def supported_resource_types(cls) -> tuple[str, ...]:
        """Return only approved types that really have a registered projector."""

        missing = [
            resource_type
            for resource_type in cls.ORM_BACKED_RESOURCE_TYPES
            if not ProjectorRegistry.has(resource_type)
        ]
        if missing:
            raise BulkProjectionError(
                "Bulk projector registration is incomplete: " + ", ".join(missing)
            )
        return cls.ORM_BACKED_RESOURCE_TYPES

    @classmethod
    def build_scope(cls, *, export_type: str, group_id: str | None = None) -> BulkExportScope:
        """Resolve a deterministic cohort without fallback patients."""

        from apps.clinical.patients.clinical_scope import clinical_patients

        active_patients = clinical_patients().order_by("id")
        if export_type == "system":
            patients = tuple(active_patients)
        elif export_type == "group":
            if not group_id:
                raise BulkProjectionError("Group export requires a Group logical id")
            _, patients = cls._resolve_persisted_group(group_id)
        else:
            raise BulkProjectionError(f"Unsupported Bulk Data export type: {export_type!r}")

        return BulkExportScope(
            export_type=export_type,
            group_id=group_id,
            patients=patients,
        )

    @classmethod
    def restore_scope(
        cls,
        *,
        export_type: str,
        group_id: str | None,
        patient_ids: list[str] | tuple[str, ...],
    ) -> BulkExportScope:
        """Restore the kickoff cohort recorded on an in-memory export job."""

        requested_ids = tuple(str(patient_id) for patient_id in patient_ids)
        if export_type not in {"system", "group"}:
            raise BulkProjectionError(f"Unsupported Bulk Data export type: {export_type!r}")
        if export_type == "group":
            if not group_id:
                raise BulkProjectionError("Group export requires a Group logical id")
            _, current_group_patients = cls._resolve_persisted_group(group_id)
            current_ids = tuple(str(patient.id) for patient in current_group_patients)
            if current_ids != requested_ids:
                raise BulkProjectionError(
                    "Persisted Group membership changed after Bulk export kickoff"
                )

        patient_queryset = Patient.objects.filter(id__in=requested_ids, is_active=True)
        if export_type == "system":
            from apps.clinical.patients.clinical_scope import clinical_patients

            patient_queryset = clinical_patients(patient_queryset)
        patients_by_id = {
            str(patient.id): patient
            for patient in patient_queryset
        }
        patients = tuple(
            patients_by_id[patient_id]
            for patient_id in requested_ids
            if patient_id in patients_by_id
        )
        if tuple(str(patient.id) for patient in patients) != requested_ids:
            raise BulkProjectionError(
                "Bulk export cohort changed after kickoff; refusing a partial file"
            )
        return BulkExportScope(
            export_type=export_type,
            group_id=group_id,
            patients=patients,
        )

    @classmethod
    def persisted_group_resource(cls, group_id: str) -> dict:
        """Return a validated persisted Group with resolvable member references."""

        resource, patients = cls._resolve_persisted_group(group_id)
        payload = deepcopy(resource.resource_data)
        payload["resourceType"] = "Group"
        payload["id"] = group_id
        payload["quantity"] = len(patients)
        return payload

    @classmethod
    def _resolve_persisted_group(cls, group_id: str) -> tuple[FHIRResource, tuple[Patient, ...]]:
        matches = list(
            FHIRResource.objects.filter(
                resource_type="Group",
                resource_id=group_id,
                is_active=True,
            )[:2]
        )
        if len(matches) != 1:
            raise BulkGroupNotFoundError(f"Persisted Group/{group_id} was not found")

        resource = matches[0]
        payload = resource.resource_data if isinstance(resource.resource_data, dict) else {}
        if payload.get("resourceType") != "Group" or str(payload.get("id") or "") != group_id:
            raise BulkProjectionError(f"Persisted Group/{group_id} has inconsistent resource identity")
        members = payload.get("member") or []
        if not isinstance(members, list):
            raise BulkProjectionError(f"Persisted Group/{group_id}.member must be an array")

        patients = []
        seen_patient_ids = set()
        for index, member in enumerate(members):
            reference = (
                member.get("entity", {}).get("reference")
                if isinstance(member, dict) and isinstance(member.get("entity"), dict)
                else None
            )
            parts = str(reference or "").split("/", 1)
            if len(parts) != 2 or parts[0] != "Patient" or not parts[1]:
                raise BulkProjectionError(
                    f"Persisted Group/{group_id} member {index} is not a Patient reference"
                )
            patient_db_id = identity.resolve_patient_db_id(parts[1])
            if patient_db_id is None or patient_db_id in seen_patient_ids:
                raise BulkProjectionError(
                    f"Persisted Group/{group_id} member {index} is missing, ambiguous, or duplicated"
                )
            patient = Patient.objects.filter(id=patient_db_id, is_active=True).first()
            if patient is None:
                raise BulkProjectionError(
                    f"Persisted Group/{group_id} member {index} is not an active patient"
                )
            seen_patient_ids.add(patient_db_id)
            patients.append(patient)

        declared_quantity = payload.get("quantity")
        if declared_quantity is not None and declared_quantity != len(patients):
            raise BulkProjectionError(
                f"Persisted Group/{group_id} quantity does not match its member array"
            )
        return resource, tuple(patients)

    def project_resources(
        self,
        *,
        resource_type: str,
        scope: BulkExportScope,
        request=None,
    ) -> list[dict]:
        """Project one requested type for every patient in ``scope``.

        The method is fail-closed: query/projection errors, type mismatches, missing
        logical IDs, and duplicate logical IDs abort the file rather than returning
        a partially fabricated or silently truncated export.
        """

        if resource_type not in self.supported_resource_types():
            raise BulkProjectionError(
                f"Resource type {resource_type!r} has no approved persisted Bulk projector."
            )

        try:
            projector = ProjectorRegistry.get(resource_type)
        except KeyError as exc:
            raise BulkProjectionError(str(exc)) from exc

        resources: list[dict] = []
        seen_ids: set[tuple[str, str]] = set()
        for patient in scope.patients:
            patient_fhir_id = identity.patient_id(patient)
            patient_db_id = str(patient.id)
            context = (
                FHIRContext.from_request(request, patient_id=patient_db_id)
                if request is not None
                else FHIRContext(patient_id=patient_db_id)
            )
            try:
                # Projector queries use the persisted database key for relational
                # filtering.  Their output uses ResourceIdentityService for FHIR IDs.
                rows = projector.query(patient_db_id, {}, context)
                projected = projector.project_batch(rows, context)
            except Exception as exc:
                logger.exception(
                    "Bulk projection failed for %s Patient/%s",
                    resource_type,
                    patient_fhir_id,
                )
                raise BulkProjectionError(
                    f"Failed to project {resource_type} for Patient/{patient_fhir_id}."
                ) from exc

            for resource in projected:
                if not isinstance(resource, dict):
                    raise BulkProjectionError(
                        f"{resource_type} projector returned a non-resource value."
                    )
                actual_type = resource.get("resourceType")
                resource_id = resource.get("id")
                if actual_type != resource_type or not resource_id:
                    raise BulkProjectionError(
                        f"{resource_type} projector returned an invalid resource identity."
                    )
                key = (actual_type, str(resource_id))
                if key in seen_ids:
                    raise BulkProjectionError(
                        f"{actual_type}/{resource_id} was projected more than once."
                    )
                seen_ids.add(key)
                resources.append(resource)

        return resources

    def render_ndjson(
        self,
        *,
        resource_type: str,
        scope: BulkExportScope,
        request=None,
    ) -> str:
        resources = self.project_resources(
            resource_type=resource_type,
            scope=scope,
            request=request,
        )
        if not resources:
            return ""
        return "\n".join(
            json.dumps(resource, ensure_ascii=False, separators=(",", ":"))
            for resource in resources
        ) + "\n"


__all__ = [
    "BulkExportScope",
    "BulkProjectionError",
    "PersistentBulkExportService",
]
