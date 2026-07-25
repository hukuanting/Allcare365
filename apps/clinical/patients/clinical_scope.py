"""Shared boundaries between clinical records and conformance fixtures."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from .models import Patient


GOLDEN_DEMO_FIXTURE_KEY = "allcare365-risk-golden-patient"
GOLDEN_DEMO_MRN = "GOLDEN-RISK-001"
GOLDEN_DEMO_SOURCE_SYSTEM = "allcare365-golden-conformance"


def _clinical_patient_filter() -> Q:
    return (
        Q(metadata_json__clinical_use_prohibited__isnull=True)
        | Q(metadata_json__clinical_use_prohibited=False)
    )


def _golden_demo_filter() -> Q:
    """Return the exact persisted marker contract for the synthetic demo patient."""

    return Q(
        medical_record_number=GOLDEN_DEMO_MRN,
        source_system=GOLDEN_DEMO_SOURCE_SYSTEM,
        metadata_json__conformance_fixture=GOLDEN_DEMO_FIXTURE_KEY,
        metadata_json__synthetic=True,
        metadata_json__clinical_use_prohibited=True,
    )


def clinical_patients(queryset: QuerySet | None = None) -> QuerySet:
    """Return active patients that are permitted to participate in care.

    Synthetic certification/golden records remain persisted and addressable by
    dedicated conformance workflows, but must never enter ordinary clinical
    lists merely because they use the same schema.
    """

    source = queryset if queryset is not None else Patient.objects.all()
    return source.filter(is_active=True).filter(_clinical_patient_filter())


def risk_selectable_patients(
    queryset: QuerySet | None = None,
    *,
    include_golden_demo: bool = False,
) -> QuerySet:
    """Return the patient-picker scope for risk analysis.

    The opt-in adds only the one reserved, fully marked Golden Patient. Other
    conformance fixtures remain excluded even when ``include_golden_demo`` is
    true.
    """

    source = queryset if queryset is not None else Patient.objects.all()
    permitted = _clinical_patient_filter()
    if include_golden_demo:
        permitted |= _golden_demo_filter()
    return source.filter(is_active=True).filter(permitted)


def is_golden_demo_patient(patient: Patient | None) -> bool:
    """Recognize the demo patient without trusting a display name or MRN alone."""

    if patient is None or not patient.is_active:
        return False
    metadata = patient.metadata_json if isinstance(patient.metadata_json, dict) else {}
    return (
        patient.medical_record_number == GOLDEN_DEMO_MRN
        and patient.source_system == GOLDEN_DEMO_SOURCE_SYSTEM
        and metadata.get("conformance_fixture") == GOLDEN_DEMO_FIXTURE_KEY
        and metadata.get("synthetic") is True
        and metadata.get("clinical_use_prohibited") is True
    )


__all__ = [
    "GOLDEN_DEMO_FIXTURE_KEY",
    "GOLDEN_DEMO_MRN",
    "GOLDEN_DEMO_SOURCE_SYSTEM",
    "clinical_patients",
    "is_golden_demo_patient",
    "risk_selectable_patients",
]
