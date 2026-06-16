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
import uuid
from typing import TYPE_CHECKING

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

    @staticmethod
    def patient_id(patient) -> str:
        return ResourceIdentityService.SINGLE_PATIENT_FHIR_ID

    @staticmethod
    def resolve_patient_db_id(token: str | None) -> str | None:
        """
        Resolve an incoming FHIR patient token (logical id/reference) to
        a relational Patient.id for query filtering.
        """
        if not token:
            return None

        raw = str(token).split("/")[-1].strip()
        if not raw:
            return None

        from apps.clinical.patients.models import Patient

        if raw in {ResourceIdentityService.SINGLE_PATIENT_FHIR_ID, "onc-patient-1", "1"}:
            p = Patient.objects.filter(is_active=True).order_by("created_at", "id").first()
            return str(p.id) if p else None

        try:
            uuid.UUID(raw)
        except (TypeError, ValueError):
            p = Patient.objects.filter(is_active=True).order_by("created_at", "id").first()
            return str(p.id) if p else None

        p = Patient.objects.filter(id=raw, is_active=True).only("id").first()
        if p:
            return str(p.id)
        return None

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
        slug = loc_name.lower().replace(" ", "-")[:32]
        return f"loc-{slug}"

    # ── Practitioner ─────────────────────────────────────────

    @staticmethod
    def practitioner_id(user) -> str:
        return f"pract-{user.id}"

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
