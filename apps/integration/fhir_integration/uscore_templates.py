"""
US Core STU7 reusable projection templates.

This module centralizes:
1) Referential backbone singleton IDs.
2) Common Must Support fallback builders.
3) Canonical LOINC/category mappings used by multiple projectors.
"""
from __future__ import annotations

from typing import Tuple


PRACTITIONER_ID = "example-practitioner"
PRACTITIONER_ROLE_ID = "example-practitioner-role"
ORGANIZATION_ID = "bulk-organization-1"
LOCATION_ID = "bulk-location-1"
MEDIA_ID = "media-example-1"


def backbone_practitioner_ref(ref_builder) -> dict:
    return ref_builder.practitioner(PRACTITIONER_ID)


def backbone_organization_ref(ref_builder) -> dict:
    return ref_builder.organization(ORGANIZATION_ID)


def backbone_location_ref(ref_builder) -> dict:
    return ref_builder.location(LOCATION_ID)


def backbone_media_ref(ref_builder) -> dict:
    return ref_builder.media(MEDIA_ID)


def encounter_ref_for_patient(patient_id: str, ref_builder, identity_service) -> dict:
    """
    Resolve a stable encounter reference for a patient. Falls back to the
    canonical placeholder only when no screening exists.
    """
    try:
        from apps.clinical.health_screening.models import HealthScreening

        screening = (
            HealthScreening.objects.filter(patient_id=patient_id, is_active=True)
            .order_by("encounter_time", "screening_date")
            .first()
        )
        if screening is not None:
            return ref_builder.encounter(identity_service.encounter_id(screening))
    except Exception:
        pass
    return ref_builder.encounter("enc-placeholder")


def lab_test_name_to_loinc_key(test_name: str) -> str:
    name = (test_name or "").lower()
    if "a1c" in name or "hemoglobin a1c" in name:
        return "hba1c"
    if "glucose" in name:
        return "lab_glucose"
    if "cholesterol" in name:
        return "lab_total_cholesterol"
    return "hemoglobin"


def note_type_to_loinc(note_type: str) -> Tuple[str, str]:
    mapping = {
        "consultation": ("11488-4", "Consult note"),
        "discharge_summary": ("18842-5", "Discharge summary"),
        "emergency": ("34878-9", "Emergency medicine Note"),
        "history_physical": ("34117-2", "History and physical note"),
        "operative": ("11504-8", "Surgical operation note"),
        "procedure": ("28570-0", "Procedure note"),
        "progress": ("11506-3", "Progress note"),
    }
    return mapping.get(note_type, ("11506-3", "Progress note"))

