import os
import sys
from datetime import date

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from apps.clinical.patients.models import Patient
from services.disease_risk_engine.repository import DiseaseRiskInputRepository


def test_patient_age_is_unknown_when_date_of_birth_is_absent():
    patient = Patient(date_of_birth=None)

    assert patient.age is None


@pytest.mark.django_db
def test_repository_age_can_be_frozen_for_conformance_vectors():
    patient = Patient.objects.create(
        first_name="Frozen",
        last_name="Age",
        date_of_birth=date(1968, 2, 14),
        sex="F",
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(
        patient,
        evaluation_as_of=date(2026, 7, 15),
    )

    assert snapshot.data["age"] == 58
    assert snapshot.sources["age"]["evaluation_as_of"] == "2026-07-15"


def test_repository_canonicalizes_known_sex_variants_and_preserves_unknown():
    assert DiseaseRiskInputRepository._canonical_sex("M") == "M"
    assert DiseaseRiskInputRepository._canonical_sex("male") == "M"
    assert DiseaseRiskInputRepository._canonical_sex("F") == "F"
    assert DiseaseRiskInputRepository._canonical_sex("female") == "F"
    assert DiseaseRiskInputRepository._canonical_sex("U") is None
    assert DiseaseRiskInputRepository._canonical_sex("other") is None
    assert DiseaseRiskInputRepository._canonical_sex("") is None


@pytest.mark.django_db
def test_repository_resolves_a_unique_mrn_without_treating_it_as_a_uuid():
    patient = Patient.objects.create(
        first_name="Unique",
        last_name="Patient",
        medical_record_number="RISK-MRN-UNIQUE",
    )

    assert DiseaseRiskInputRepository().get_patient("RISK-MRN-UNIQUE") == patient


@pytest.mark.django_db
def test_repository_fails_closed_for_a_duplicate_mrn():
    for first_name in ("First", "Second"):
        Patient.objects.create(
            first_name=first_name,
            last_name="Duplicate",
            medical_record_number="RISK-MRN-DUPLICATE",
        )

    assert DiseaseRiskInputRepository().get_patient("RISK-MRN-DUPLICATE") is None

