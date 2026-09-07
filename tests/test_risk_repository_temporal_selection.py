from datetime import date, datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

import pytest

from apps.clinical.health_screening.models import Observation
from apps.clinical.patients.models import Patient
from services.disease_risk_engine.repository import DiseaseRiskInputRepository


def _patient(mrn: str) -> Patient:
    return Patient.objects.create(
        first_name="Temporal",
        last_name="Selection",
        medical_record_number=mrn,
        date_of_birth=date(1970, 1, 1),
        sex="F",
    )


def _observation(
    patient: Patient,
    *,
    observation_type: str,
    code: str,
    value: float,
    unit: str,
    effective_at: datetime,
) -> Observation:
    return Observation.objects.create(
        patient=patient,
        observation_type=observation_type,
        category="vital-signs",
        code_system="http://loinc.org",
        code=code,
        value_quantity=value,
        value_unit=unit,
        effective_at=effective_at,
    )


@pytest.mark.django_db
def test_snapshot_selects_latest_valid_value_for_each_field_at_the_evaluation_time():
    patient = _patient("TEMPORAL-LATEST-001")
    evaluation_at = datetime(2026, 8, 29, 12, tzinfo=datetime_timezone.utc)

    # a: annual values -> current value wins; a future value must not leak into
    # a point-in-time assessment.
    _observation(
        patient,
        observation_type="heart_rate",
        code="8867-4",
        value=70,
        unit="{beats}/min",
        effective_at=evaluation_at - timedelta(days=365),
    )
    latest_a = _observation(
        patient,
        observation_type="heart_rate",
        code="8867-4",
        value=76,
        unit="{beats}/min",
        effective_at=evaluation_at - timedelta(hours=2),
    )
    _observation(
        patient,
        observation_type="heart_rate",
        code="8867-4",
        value=180,
        unit="{beats}/min",
        effective_at=evaluation_at + timedelta(minutes=1),
    )

    # b: only ten-year-old data -> it remains the latest available value and
    # its age is made explicit for the model's freshness policy.
    latest_b = _observation(
        patient,
        observation_type="fasting_glucose",
        code="1558-6",
        value=95,
        unit="mg/dL",
        effective_at=evaluation_at - timedelta(days=3650),
    )

    # c: ten-, five-, and three-year values -> the three-year value wins.
    for years, value in ((10, 60), (5, 64), (3, 67)):
        latest_c = _observation(
            patient,
            observation_type="body_weight",
            code="29463-7",
            value=value,
            unit="kg",
            effective_at=evaluation_at - timedelta(days=365 * years),
        )
    _observation(
        patient,
        observation_type="body_height",
        code="8302-2",
        value=170,
        unit="cm",
        effective_at=evaluation_at - timedelta(days=1),
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(
        patient,
        evaluation_as_of=evaluation_at,
    )

    assert snapshot.data["heart_rate"] == 76
    assert snapshot.data["resting_heart_rate"] == 76
    assert snapshot.data["fasting_glucose"] == 95
    assert snapshot.data["body_weight"] == 67
    assert snapshot.sources["heart_rate"]["id"] == str(latest_a.id)
    assert snapshot.sources["fasting_glucose"]["id"] == str(latest_b.id)
    assert snapshot.sources["body_weight"]["id"] == str(latest_c.id)
    assert snapshot.sources["fasting_glucose"]["age_at_evaluation_days"] == 3650
    assert snapshot.sources["body_weight"]["age_at_evaluation_days"] == 1095
    assert snapshot.sources["bmi"]["oldest_input_age_days"] == 1095
    assert snapshot.sources["bmi"]["newest_input_age_days"] == 1
    assert snapshot.sources["bmi"]["input_temporal_span_days"] == 1094
    assert snapshot.sources["_snapshot"]["selection_policy"] == (
        "latest_valid_at_or_before_evaluation_per_field"
    )


@pytest.mark.django_db
def test_continuous_stream_snapshot_inspects_a_bounded_recent_candidate_set():
    patient = _patient("TEMPORAL-STREAM-001")
    evaluation_at = datetime(2026, 8, 29, 12, tzinfo=datetime_timezone.utc)
    Observation.objects.bulk_create(
        [
            Observation(
                patient=patient,
                observation_type="heart_rate",
                category="vital-signs",
                code_system="http://loinc.org",
                code="8867-4",
                value_quantity=60 + (offset % 40),
                value_unit="{beats}/min",
                effective_at=evaluation_at - timedelta(seconds=offset),
            )
            for offset in range(2000)
        ]
    )

    repository = DiseaseRiskInputRepository()
    with patch.object(
        repository,
        "_observation_quantity",
        wraps=repository._observation_quantity,
    ) as quantity_reader:
        snapshot = repository.build_snapshot(
            patient,
            evaluation_as_of=evaluation_at,
        )

    assert snapshot.data["heart_rate"] == 60
    assert quantity_reader.call_count <= repository.RECENT_CANDIDATES_PER_ALIAS


@pytest.mark.django_db
def test_latest_valid_selection_recovers_beyond_the_bounded_fast_path():
    patient = _patient("TEMPORAL-INVALID-FALLBACK-001")
    evaluation_at = datetime(2026, 8, 29, 12, tzinfo=datetime_timezone.utc)
    repository = DiseaseRiskInputRepository()
    repository.RECENT_CANDIDATES_PER_ALIAS = 4

    valid = _observation(
        patient,
        observation_type="heart_rate",
        code="8867-4",
        value=72,
        unit="{beats}/min",
        effective_at=evaluation_at - timedelta(minutes=10),
    )
    for offset in range(5):
        _observation(
            patient,
            observation_type="heart_rate",
            code="8867-4",
            value=100 + offset,
            unit="unsupported-unit",
            effective_at=evaluation_at - timedelta(minutes=offset),
        )

    snapshot = repository.build_snapshot(
        patient,
        evaluation_as_of=evaluation_at,
    )

    assert snapshot.data["heart_rate"] == 72
    assert snapshot.sources["heart_rate"]["id"] == str(valid.id)
