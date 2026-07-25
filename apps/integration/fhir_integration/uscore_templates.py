"""Small, source-backed terminology and relationship helpers for US Core.

This module deliberately contains no resource identifiers or fixture data.
Projectors may only emit references returned from explicit persisted
relationships.
"""
from __future__ import annotations

from typing import Optional, Tuple

def direct_encounter_for_source(source):
    """Return one persisted encounter directly related to ``source``.

    A direct Encounter FK is preferred.  Legacy clinical rows tied to a
    HealthScreening may resolve through Encounter.source_screening, but only
    when that relationship identifies exactly one active row.  Ambiguity is
    fail-closed and never becomes a first/most-recent encounter guess.
    """
    from apps.clinical.health_screening.models import Encounter, HealthScreening

    if isinstance(source, Encounter):
        return source if source.is_active else None

    encounter_id = getattr(source, "encounter_id", None)
    if encounter_id:
        matches = list(
            Encounter.objects.filter(id=encounter_id, is_active=True)
            .select_related("practitioner", "practitioner__organization")[:2]
        )
        return matches[0] if len(matches) == 1 else None

    screening = source if isinstance(source, HealthScreening) else getattr(source, "health_screening", None)
    if screening is None:
        screening = getattr(source, "source_screening", None)
    if screening is None:
        return None

    matches = list(
        Encounter.objects.filter(source_screening_id=screening.id, is_active=True)
        .select_related("practitioner", "practitioner__organization")[:2]
    )
    return matches[0] if len(matches) == 1 else None


def encounter_ref_for_source(source, ref_builder, identity_service) -> Optional[dict]:
    encounter = direct_encounter_for_source(source)
    if encounter is None or getattr(encounter, "source_screening", None) is None:
        return None
    return ref_builder.encounter(identity_service.encounter_id(encounter.source_screening))


def lab_test_name_to_loinc_key(test_name: str) -> Optional[str]:
    name = (test_name or "").strip().casefold()
    if not name or name == "unknown test":
        return None
    if "a1c" in name or "hemoglobin a1c" in name:
        return "hba1c"
    if "glucose" in name:
        return "lab_glucose"
    if "total cholesterol" in name or name == "cholesterol":
        return "lab_total_cholesterol"
    if "hemoglobin" in name or "haemoglobin" in name:
        return "hemoglobin"
    return None


def note_type_to_loinc(note_type: str) -> Optional[Tuple[str, str]]:
    mapping = {
        "consultation": ("11488-4", "Consult note"),
        "discharge_summary": ("18842-5", "Discharge summary"),
        "emergency": ("34878-9", "Emergency medicine Note"),
        "history_physical": ("34117-2", "History and physical note"),
        "operative": ("11504-8", "Surgical operation note"),
        "procedure": ("28570-0", "Procedure note"),
        "progress": ("11506-3", "Progress note"),
        "diagnostic_imaging": ("18748-4", "Diagnostic imaging study"),
        "laboratory_report": ("11502-2", "Laboratory report"),
        "pathology_report": ("11526-1", "Pathology study"),
    }
    return mapping.get((note_type or "").strip().casefold())
