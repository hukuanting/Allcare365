"""
Resource Identity Service.

Maps internal DB primary keys to stable FHIR resource IDs.
FHIR ID ≠ DB PK — this indirection is critical for:
  - Multi-tenant isolation
  - Patient merging
  - External imports
  - Logical deletes
"""
from __future__ import annotations
import hashlib
import re
import uuid
from typing import TYPE_CHECKING

from django.db import DatabaseError

if TYPE_CHECKING:
    from django.db import models as django_models


class ResourceIdentityService:
    """
    Central authority for converting DB objects to FHIR resource IDs.

    All projectors MUST use this instead of accessing `.id` / `.pk` directly.
    Future changes (e.g. prefixing, hashing, tenant scoping) happen here only.
    """

    # ── Patient ──────────────────────────────────────────────

    SINGLE_PATIENT_FHIR_ID = "00000000-0000-4000-a000-000000000001"
    PATIENT_FHIR_ID_METADATA_KEY = "fhir_patient_id"
    _FHIR_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")

    @classmethod
    def patient_id(cls, patient) -> str:
        """Return the patient's stable, collision-free FHIR logical id.

        A source FHIR id is used only when it was explicitly persisted on the
        patient and can be proven unique.  The relational UUID is the safe
        fallback and preserves the ONC fixture because that fixture's primary
        key is already the canonical certification UUID.
        """
        database_id = str(patient.id)
        metadata = getattr(patient, "metadata_json", None)
        explicit_id = (
            metadata.get(cls.PATIENT_FHIR_ID_METADATA_KEY)
            if isinstance(metadata, dict)
            else None
        )
        explicit_id = str(explicit_id).strip() if explicit_id else ""
        if not cls._is_valid_fhir_id(explicit_id):
            return database_id

        try:
            if cls._explicit_patient_id_is_unique(patient, explicit_id):
                return explicit_id
        except DatabaseError:
            # If uniqueness cannot be established, the database UUID is the
            # only identity that is safe to expose.
            return database_id
        return database_id

    @classmethod
    def resolve_patient_db_id(cls, token: str | None) -> str | None:
        """
        Resolve an incoming FHIR patient token (logical id/reference) to
        a relational Patient.id for query filtering.
        """
        if not token:
            return None

        raw = str(token).rstrip("/").split("/")[-1].strip()
        if not cls._is_valid_fhir_id(raw):
            return None

        from apps.clinical.patients.models import Patient

        try:
            uuid.UUID(raw)
        except (TypeError, ValueError):
            pass
        else:
            patient = Patient.objects.filter(id=raw, is_active=True).only("id").first()
            if patient is not None:
                return str(patient.id)

        matches = list(
            Patient.objects.filter(
                is_active=True,
                metadata_json__fhir_patient_id=raw,
            ).only("id", "metadata_json")[:2]
        )
        if len(matches) == 1 and cls._explicit_patient_id_is_unique(matches[0], raw):
            return str(matches[0].id)
        return None

    @classmethod
    def _explicit_patient_id_is_unique(cls, patient, explicit_id: str) -> bool:
        from apps.clinical.patients.models import Patient

        patient_id = str(patient.id)
        persisted_matches = {
            str(value)
            for value in Patient.objects.filter(
                metadata_json__fhir_patient_id=explicit_id,
            ).values_list("id", flat=True)[:2]
        }
        if persisted_matches != {patient_id}:
            return False

        try:
            explicit_uuid = uuid.UUID(explicit_id)
        except (TypeError, ValueError):
            return True
        return not Patient.objects.filter(id=explicit_uuid).exclude(id=patient.id).exists()

    @classmethod
    def _is_valid_fhir_id(cls, value: str) -> bool:
        return bool(value and cls._FHIR_ID_PATTERN.fullmatch(value))

    @staticmethod
    def canonical_patient_id() -> str:
        return ResourceIdentityService.SINGLE_PATIENT_FHIR_ID

    # ── Encounter (HealthScreening) ──────────────────────────

    @staticmethod
    def encounter_id(screening) -> str:
        return f"enc-{screening.id}"

    # ── Observation (VitalSigns / Lab / Clinical Test) ───────

    @staticmethod
    def observation_id(source_obj, suffix: str = "") -> str:
        base = str(source_obj.id)
        return f"obs-{base}{'-' + suffix if suffix else ''}"

    # ── Condition (Problem) ──────────────────────────────────

    @staticmethod
    def condition_id(problem, index: int = 0) -> str:
        return f"con-{problem.id}"

    # ── AllergyIntolerance ───────────────────────────────────

    @staticmethod
    def allergy_id(allergy) -> str:
        return f"alg-{allergy.id}"

    # ── MedicationRequest ────────────────────────────────────

    @staticmethod
    def medication_request_id(med) -> str:
        return f"mreq-{med.id}"

    # ── MedicationDispense ───────────────────────────────────

    @staticmethod
    def medication_dispense_id(med) -> str:
        return f"mdisp-{med.id}"

    # ── Medication ───────────────────────────────────────────

    @staticmethod
    def medication_id(med) -> str:
        return f"med-{med.id}"

    # ── CarePlan ─────────────────────────────────────────────

    @staticmethod
    def care_plan_id(plan) -> str:
        return f"cp-{plan.id}"

    # ── CareTeam ─────────────────────────────────────────────

    @staticmethod
    def care_team_id(member) -> str:
        return f"ct-{member.id}"

    # ── Coverage ─────────────────────────────────────────────

    @staticmethod
    def coverage_id(ins) -> str:
        return f"cov-{ins.id}"

    # ── Device ───────────────────────────────────────────────

    @staticmethod
    def device_id(dev) -> str:
        return f"dev-{dev.id}"

    # ── DiagnosticReport ─────────────────────────────────────

    @staticmethod
    def diagnostic_report_id(report) -> str:
        return f"dr-{report.id}"

    # ── DocumentReference ────────────────────────────────────

    @staticmethod
    def document_reference_id(doc) -> str:
        return f"docref-{doc.id}"

    # ── Goal ─────────────────────────────────────────────────

    @staticmethod
    def goal_id(directive) -> str:
        return f"goal-{directive.id}"

    # ── Immunization ─────────────────────────────────────────

    @staticmethod
    def immunization_id(imm) -> str:
        return f"imm-{imm.id}"

    # ── Procedure ────────────────────────────────────────────

    @staticmethod
    def procedure_id(proc) -> str:
        return f"proc-{proc.id}"

    # ── ServiceRequest (MedicalOrder) ────────────────────────

    @staticmethod
    def service_request_id(order) -> str:
        return f"sreq-{order.id}"

    # ── Specimen ─────────────────────────────────────────────

    @staticmethod
    def specimen_id(lab) -> str:
        return f"spm-{lab.id}"

    # ── Organization ─────────────────────────────────────────

    @staticmethod
    def organization_id(org) -> str:
        return f"org-{org.id}"

    # ── Location ─────────────────────────────────────────────

    @staticmethod
    def location_id(loc_name: str) -> str:
        normalized = str(loc_name).strip().casefold()
        slug = re.sub(r"[^a-z0-9.-]+", "-", normalized).strip(".-")[:32]
        slug = slug or "location"
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
        return f"loc-{slug}-{digest}"

    # ── Practitioner ─────────────────────────────────────────

    @staticmethod
    def practitioner_id(user) -> str:
        return f"pract-{user.id}"

    @staticmethod
    def practitioner_role_id(link) -> str:
        return f"prrole-{link.id}"

    # ── RelatedPerson ────────────────────────────────────────

    @staticmethod
    def related_person_id(patient) -> str:
        return f"rp-{patient.id}"

    # ── Provenance ───────────────────────────────────────────

    @staticmethod
    def provenance_id(target_resource_id: str) -> str:
        return f"prov-{target_resource_id}"


# Module‑level singleton for convenience
identity = ResourceIdentityService()
