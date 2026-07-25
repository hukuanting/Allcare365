"""
Observation Projector — Maps multiple source models → FHIR Observation.

Handles all US Core Observation profiles from a SINGLE projector:
  - VitalSigns → blood-pressure, heart-rate, body-height, body-weight, BMI, etc.
  - LaboratoryResults → observation-lab
  - HealthStatusAssessment (smoking) → smokingstatus
  - ClinicalTestResult → observation-clinical-result
"""
from __future__ import annotations

import math
from typing import List, TYPE_CHECKING

from ..fhir_search.query_translator import parse_date_param

from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import direct_encounter_for_source
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


class _ObservationRow:
    """Normalized intermediate representation for any observation source."""
    __slots__ = (
        "source", "source_type", "patient", "patient_id",
        "effective_dt", "obs_id_suffix", "health_screening",
    )

    def __init__(
        self,
        source,
        source_type,
        patient,
        patient_id,
        effective_dt,
        obs_id_suffix="",
        health_screening=None,
    ):
        self.source = source
        self.source_type = source_type
        self.patient = patient
        self.patient_id = patient_id
        self.effective_dt = effective_dt
        self.obs_id_suffix = obs_id_suffix
        self.health_screening = health_screening


@ProjectorRegistry.register("Observation")
class ObservationProjector(BaseProjector):
    resource_type = "Observation"
    profile_key = "us-core-vital-signs"
    supported_profile_keys = [
        "us-core-vital-signs",
        "us-core-blood-pressure",
        "us-core-body-height",
        "us-core-body-weight",
        "us-core-body-temperature",
        "us-core-heart-rate",
        "us-core-respiratory-rate",
        "us-core-pulse-oximetry",
        "us-core-pediatric-bmi-for-age",
        "us-core-pediatric-weight-for-height",
        "us-core-head-circumference-percentile",
        "us-core-observation-lab",
        "us-core-smokingstatus",
        "us-core-observation-clinical-result",
        "us-core-observation-occupation",
        "us-core-observation-pregnancystatus",
        "us-core-observation-screening-assessment",
        "us-core-care-experience-preference",
        "us-core-treatment-intervention-preference",
    ]

    SCREENING_ASSESSMENT_FIELDS = {
        "sdoh_assessment": {
            "suffix": "screening-sdoh",
            "code_key": "screening_sdoh",
            "category_key": "category_screening_sdoh",
        },
        "functional_status": {
            "suffix": "screening-functional-status",
            "code_key": "screening_functional_status",
            "category_key": "category_screening_functional_status",
        },
        "disability_status": {
            "suffix": "screening-disability-status",
            "code_key": "screening_disability_status",
            "category_key": "category_screening_disability_status",
        },
        "mental_cognitive_status": {
            "suffix": "screening-cognitive-status",
            "code_key": "screening_cognitive_status",
            "category_key": "category_screening_cognitive_status",
        },
        "physical_activity": {
            "suffix": "screening-physical-activity",
            "code_key": "screening_physical_activity",
            "category_key": "category_screening_functional_status",
        },
        "alcohol_use": {
            "suffix": "screening-alcohol-use",
            "code_key": "screening_alcohol_use",
            "category_key": "category_screening_sdoh",
        },
        "substance_use": {
            "suffix": "screening-substance-use",
            "code_key": "screening_substance_use",
            "category_key": "category_screening_sdoh",
        },
    }

    PREFERENCE_FIELDS = {
        "care_experience_preference": {
            "profile_key": "us-core-care-experience-preference",
            "code_key": "care_experience_preference",
            "category_key": "category_care_experience_preference",
            "suffix": "care-experience-preference",
        },
        "treatment_intervention_preference": {
            "profile_key": "us-core-treatment-intervention-preference",
            "code_key": "treatment_intervention_preference",
            "category_key": "category_treatment_intervention_preference",
            "suffix": "treatment-intervention-preference",
        },
    }

    # ── Query ────────────────────────────────────────────────

    def query(self, patient_id, search_params, context):
        """
        Returns a mixed list of normalized _ObservationRow objects
        from VitalSigns, Labs, Assessments, and ClinicalTests.
        """
        from apps.clinical.health_screening.models import (
            VitalSigns, LaboratoryResults, HealthStatusAssessment,
            ClinicalTestResult,
        )
        from apps.clinical.patients.models import AdvanceDirective

        rows: List[_ObservationRow] = []
        screening_filter = {}
        query_patient_id = patient_id
        if not query_patient_id and search_params.get("patient"):
            query_patient_id = identity.resolve_patient_db_id(search_params["patient"])
            if query_patient_id is None:
                return []
        if query_patient_id:
            screening_filter["health_screening__patient_id"] = query_patient_id

        # Vital Signs
        vs_qs = VitalSigns.objects.filter(**screening_filter).select_related(
            "health_screening", "health_screening__patient"
        )
        for vs in vs_qs:
            rows.extend(self._vitals_to_rows(vs))

        # Laboratory
        lab_qs = LaboratoryResults.objects.filter(**screening_filter).select_related(
            "health_screening", "health_screening__patient"
        )
        for lab in lab_qs:
            if (
                not self._has_persisted_test_name(lab.test_name)
                or not self._has_persisted_result(lab.value_result)
            ):
                continue
            rows.append(_ObservationRow(
                source=lab, source_type="lab",
                patient=lab.health_screening.patient,
                patient_id=str(lab.health_screening.patient_id),
                effective_dt=lab.health_screening.screening_date.isoformat() if lab.health_screening.screening_date else None,
                obs_id_suffix="lab",
            ))

        # Health status observations: smoking, pregnancy, occupation, screening.
        assess_qs = HealthStatusAssessment.objects.filter(**screening_filter).select_related(
            "health_screening", "health_screening__patient"
        )
        for a in assess_qs:
            patient = a.health_screening.patient
            patient_id_value = str(a.health_screening.patient_id)
            effective_dt = a.health_screening.screening_date.isoformat() if a.health_screening.screening_date else None

            if a.smoking_status:
                rows.append(_ObservationRow(
                    source=a, source_type="smoking",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="smoking",
                ))
            if a.pregnancy_status:
                rows.append(_ObservationRow(
                    source=a, source_type="pregnancy_status",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="pregnancy-status",
                ))
            if getattr(patient, "occupation", ""):
                rows.append(_ObservationRow(
                    source=a, source_type="occupation",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="occupation",
                ))

            screening_item_suffixes = self._screening_item_suffixes(a)
            if screening_item_suffixes:
                rows.append(_ObservationRow(
                    source=a, source_type="screening_panel",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="screening-panel",
                ))
                for suffix in screening_item_suffixes:
                    rows.append(_ObservationRow(
                        source=a, source_type="screening",
                        patient=patient,
                        patient_id=patient_id_value,
                        effective_dt=effective_dt,
                        obs_id_suffix=suffix,
                    ))

        # Clinical result observations require an actual persisted result.
        clinical_qs = ClinicalTestResult.objects.filter(**screening_filter).select_related(
            "health_screening", "health_screening__patient"
        )
        for test in clinical_qs:
            if (
                not self._has_persisted_test_name(test.test_name)
                or not self._has_persisted_result(test.result_value)
            ):
                continue
            rows.append(_ObservationRow(
                source=test, source_type="clinical_result",
                patient=test.health_screening.patient,
                patient_id=str(test.health_screening.patient_id),
                effective_dt=test.test_date.isoformat() if test.test_date else None,
                obs_id_suffix="clinical-result",
            ))

        # Preference profiles sourced from AdvanceDirective.
        directive_filter = {"is_active": True}
        if query_patient_id:
            directive_filter["patient_id"] = query_patient_id
        for directive in AdvanceDirective.objects.filter(**directive_filter).select_related("patient"):
            effective_dt = directive.created_at.isoformat() if directive.created_at else None
            for field_name, spec in self.PREFERENCE_FIELDS.items():
                if getattr(directive, field_name, ""):
                    rows.append(_ObservationRow(
                        source=directive,
                        source_type="preference",
                        patient=directive.patient,
                        patient_id=str(directive.patient_id),
                        effective_dt=effective_dt,
                        obs_id_suffix=spec["suffix"],
                    ))

        category_tokens = self._token_codes(search_params.get("category"))
        if category_tokens:
            rows = [row for row in rows if self._row_matches_category(row, category_tokens)]

        if search_params.get("date"):
            rows = [row for row in rows if self._row_matches_date(row, str(search_params["date"]))]

        if search_params.get("_lastUpdated"):
            rows = [row for row in rows if self._row_matches_last_updated(row, str(search_params["_lastUpdated"]))]

        if search_params.get("status"):
            status_tokens = self._token_codes(search_params.get("status"))
            rows = [row for row in rows if self._row_status(row) in status_tokens]

        if search_params.get("_id"):
            rows = [row for row in rows if self._row_observation_id(row) == search_params["_id"]]

        if search_params.get("code"):
            code_tokens = self._token_codes(search_params.get("code"))
            rows = [row for row in rows if self._row_matches_code(row, code_tokens, context)]

        return rows  # Not a QuerySet, but project_batch handles iterables

    def project_batch(self, queryset_or_list, context):
        """Override to handle list of _ObservationRow instead of QuerySet."""
        contract = self.projection_contract()
        results = []
        for row in queryset_or_list:
            resource = self.project(row, context)
            if resource:
                if isinstance(resource, list):
                    for item in resource:
                        if contract is not None:
                            from ..projectors.base import _contract_validator, logger
                            try:
                                _contract_validator.validate(item, context, contract)
                            except ValueError as exc:
                                logger.warning(
                                    "Projection contract warning for Observation/%s: %s",
                                    item.get("id"),
                                    exc,
                                )
                        results.append(item)
                else:
                    if contract is not None:
                        from ..projectors.base import _contract_validator, logger
                        try:
                            _contract_validator.validate(resource, context, contract)
                        except ValueError as exc:
                            logger.warning(
                                "Projection contract warning for Observation/%s: %s",
                                resource.get("id"),
                                exc,
                            )
                    results.append(resource)
        return results

    # ── Projection ───────────────────────────────────────────

    def project(self, row: _ObservationRow, context: "FHIRContext"):
        if row.source_type == "vitals":
            return self._project_vital(row, context)
        elif row.source_type == "bp":
            return self._project_blood_pressure(row, context)
        elif row.source_type == "lab":
            return self._project_lab(row, context)
        elif row.source_type == "smoking":
            return self._project_smoking(row, context)
        elif row.source_type == "pregnancy_status":
            return self._project_pregnancy_status(row, context)
        elif row.source_type == "occupation":
            return self._project_occupation(row, context)
        elif row.source_type == "screening_panel":
            return self._project_screening_panel(row, context)
        elif row.source_type == "screening":
            return self._project_screening_assessment(row, context)
        elif row.source_type == "clinical_result":
            return self._project_clinical_result(row, context)
        elif row.source_type == "preference":
            return self._project_preference(row, context)
        return None

    # ── Vital sign individial observations ───────────────────

    def _project_vital(self, row, context) -> dict:
        vs = row.source  # (value, unit_key, code_key, profile_key)
        value, unit_key, code_key, vprofile = vs[:4]
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        unit_coding = ts.resolve(unit_key)
        obs_id = self._row_observation_id(row)
        codings = [ts.to_fhir_coding(code_key)]
        if code_key == "pulse_oximetry":
            codings.append(ts.to_fhir_coding("pulse_oximetry_pulseox"))

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build(vprofile, extra_profiles=[
                "http://hl7.org/fhir/StructureDefinition/vitalsigns"
            ]),
            "status": "final",
            "category": [context.terminology.to_codeable_concept("category_vital_signs")],
            "code": {"coding": codings},
            "subject": ref.patient(pid),
            "valueQuantity": {
                "value": float(value),
                "unit": unit_coding.display,
                "system": unit_coding.system,
                "code": unit_coding.code,
            },
        }
        if code_key == "pulse_oximetry":
            oxygen_concentration = vs[4] if len(vs) > 4 else None
            if oxygen_concentration is not None:
                resource["component"] = [{
                    "code": ts.to_codeable_concept("inhaled_o2"),
                    "valueQuantity": {
                        "value": float(oxygen_concentration),
                        "unit": ts.resolve("unit_percent").display,
                        "system": ts.resolve("unit_percent").system,
                        "code": ts.resolve("unit_percent").code,
                    },
                }]
        return self._with_source_context(resource, row, ref)

    def _project_blood_pressure(self, row, context) -> dict:
        systolic, diastolic = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = self._row_observation_id(row)
        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-blood-pressure", extra_profiles=[
                "http://hl7.org/fhir/StructureDefinition/vitalsigns"
            ]),
            "status": "final",
            "category": [ts.to_codeable_concept("category_vital_signs")],
            "code": ts.to_codeable_concept("blood_pressure_panel"),
            "subject": ref.patient(pid),
            "component": [
                {
                    "code": ts.to_codeable_concept("systolic_bp"),
                    "valueQuantity": self._mmhg_quantity(systolic, ts),
                },
                {
                    "code": ts.to_codeable_concept("diastolic_bp"),
                    "valueQuantity": self._mmhg_quantity(diastolic, ts),
                },
            ],
        }
        return self._with_source_context(resource, row, ref)

    def _project_lab(self, row, context) -> dict:
        lab = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(lab, "lab")
        lab_code = self._lab_loinc_from_name(lab.test_name)
        status = self._lab_status(lab.result_status)
        if (
            status is None
            or not self._has_persisted_test_name(lab.test_name)
            or not self._has_persisted_result(lab.value_result)
        ):
            return None

        code = {"text": str(lab.test_name).strip()}
        if lab_code is not None:
            code["coding"] = [ts.to_fhir_coding(lab_code)]

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-lab"),
            "status": status,
            "category": [ts.to_codeable_concept("category_laboratory")],
            "code": code,
            "subject": ref.patient(pid),
        }

        value_text = str(lab.value_result).strip()
        try:
            numeric_value = float(value_text)
        except (ValueError, TypeError):
            resource["valueString"] = value_text
        else:
            if not math.isfinite(numeric_value):
                resource["valueString"] = value_text
            else:
                quantity = {"value": numeric_value}
                unit = str(lab.result_unit or "").strip()
                if unit:
                    quantity.update({
                        "unit": unit,
                        "system": "http://unitsofmeasure.org",
                        "code": unit,
                    })
                resource["valueQuantity"] = quantity

        if lab.result_reference_range:
            resource["referenceRange"] = [{"text": lab.result_reference_range}]
        if lab.result_interpretation:
            resource["interpretation"] = [{"text": lab.result_interpretation}]

        if lab.specimen_source_site:
            resource["bodySite"] = {"text": lab.specimen_source_site}
        if any((
            lab.specimen_type,
            lab.specimen_source_site,
            lab.specimen_identifier,
            lab.specimen_condition,
        )):
            resource["specimen"] = ref.specimen(identity.specimen_id(lab))

        return self._with_source_context(resource, row, ref)

    def _project_smoking(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = self._row_observation_id(row)

        smoking_codes = {
            "current": ("449868002", "Current every day smoker"),
            "former": ("8517006", "Former smoker"),
            "never": ("266919005", "Never smoker"),
        }
        persisted_status = str(assess.smoking_status or "").strip()
        if not persisted_status:
            return None

        status_lower = persisted_status.lower()
        coding = None
        if "former" in status_lower or "quit" in status_lower:
            coding = smoking_codes["former"]
        elif "never" in status_lower or "denies" in status_lower:
            coding = smoking_codes["never"]
        elif "current" in status_lower:
            coding = smoking_codes["current"]

        value = {"text": persisted_status}
        if coding is not None:
            code, display = coding
            value["coding"] = [{
                "system": "http://snomed.info/sct",
                "code": code,
                "display": display,
            }]

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-smokingstatus"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("smoking_status"),
            "subject": ref.patient(pid),
            "valueCodeableConcept": value,
        }
        return self._with_source_context(resource, row, ref)

    # ── Helpers ───────────────────────────────────────────────

    def _project_pregnancy_status(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(assess, "pregnancy-status")
        persisted_status = str(assess.pregnancy_status or "").strip()
        if not persisted_status:
            return None

        status_text = persisted_status.lower()
        value = {"text": persisted_status}
        if "not" in status_text or "no" in status_text:
            value["coding"] = [{
                "system": "http://snomed.info/sct",
                "code": "60001007",
                "display": "Not pregnant",
            }]
        elif "pregnant" in status_text:
            value["coding"] = [{
                "system": "http://snomed.info/sct",
                "code": "77386006",
                "display": "Pregnant",
            }]

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-pregnancystatus"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("pregnancy_status"),
            "subject": ref.patient(pid),
            "valueCodeableConcept": value,
        }
        return self._with_source_context(resource, row, ref)

    def _project_occupation(self, row, context) -> dict:
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        patient = row.patient
        obs_id = self._row_observation_id(row)
        occupation = str(patient.occupation or "").strip()
        if not occupation:
            return None

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-occupation"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("occupation_history"),
            "subject": ref.patient(pid),
            "valueCodeableConcept": {"text": occupation},
        }
        industry = str(patient.occupation_industry or "").strip()
        if industry:
            resource["component"] = [{
                "code": ts.to_codeable_concept("occupation_industry"),
                "valueCodeableConcept": {"text": industry},
            }]
        return self._with_source_context(resource, row, ref)

    def _project_screening_panel(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = self._row_observation_id(row)
        has_members = [
            ref.observation(self._compact_observation_id(assess, suffix))
            for suffix in self._screening_item_suffixes(assess)
        ]

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-screening-assessment"),
            "status": "final",
            "category": [
                ts.to_codeable_concept("category_survey"),
                ts.to_codeable_concept("category_screening_sdoh"),
            ],
            "code": ts.to_codeable_concept("screening_prapare_panel"),
            "subject": ref.patient(pid),
            "hasMember": has_members,
        }
        return self._with_source_context(resource, row, ref)

    def _project_screening_assessment(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        field_name, spec = self._screening_spec_from_suffix(row.obs_id_suffix)
        value = str(getattr(assess, field_name, "") or "").strip()
        if not value:
            return None
        obs_id = self._row_observation_id(row)

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-screening-assessment"),
            "status": "final",
            "category": [
                ts.to_codeable_concept("category_survey"),
                ts.to_codeable_concept(spec["category_key"]),
            ],
            "code": ts.to_codeable_concept(spec["code_key"]),
            "subject": ref.patient(pid),
            "valueString": value,
        }
        for category_key in self._screening_additional_category_keys(field_name):
            resource["category"].append(ts.to_codeable_concept(category_key))
        resource["derivedFrom"] = [ref.observation(self._compact_observation_id(assess, "screening-panel"))]
        return self._with_source_context(resource, row, ref)

    def _project_clinical_result(self, row, context) -> dict:
        source = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(source, row.obs_id_suffix)
        test_name = str(getattr(source, "test_name", "") or "").strip()
        result_value = str(getattr(source, "result_value", "") or "").strip()
        if (
            not self._has_persisted_test_name(test_name)
            or not self._has_persisted_result(result_value)
        ):
            return None

        code = {"text": test_name}
        normalized_test_name = test_name.lower()
        if "electrocardiogram" in normalized_test_name or "ecg" in normalized_test_name:
            code["coding"] = [ts.to_fhir_coding("clinical_result_ecg")]

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-clinical-result"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_clinical_test")],
            "code": code,
            "subject": ref.patient(pid),
            "valueString": result_value,
        }
        interpretation = str(getattr(source, "interpretation", "") or "").strip()
        if interpretation:
            resource["interpretation"] = [{"text": interpretation}]
        return self._with_source_context(resource, row, ref)

    def _project_preference(self, row, context) -> dict:
        directive = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        spec = self._preference_spec_from_suffix(row.obs_id_suffix)
        field_name = next(
            key for key, item in self.PREFERENCE_FIELDS.items()
            if row.obs_id_suffix == item["suffix"] or row.obs_id_suffix.startswith(f"{item['suffix']}-")
        )

        resource = {
            "resourceType": "Observation",
            "id": self._row_observation_id(row),
            "meta": MetaBuilder.build(spec["profile_key"]),
            "status": "final",
            "category": [ts.to_codeable_concept(spec["category_key"])],
            "code": ts.to_codeable_concept(spec["code_key"]),
            "subject": ref.patient(pid),
        }
        value_text = str(getattr(directive, field_name, "") or "").strip()
        if not value_text:
            return None
        resource["valueString"] = value_text
        return self._with_source_context(resource, row, ref)

    def _vitals_to_rows(self, vs) -> List[_ObservationRow]:
        """Explode a VitalSigns ORM row into individual _ObservationRow objects."""
        rows = []
        patient = vs.health_screening.patient
        patient_id = str(vs.health_screening.patient_id)
        dt = vs.health_screening.screening_date.isoformat() if vs.health_screening.screening_date else None

        # Blood Pressure (component-based)
        if (
            vs.systolic_blood_pressure is not None
            and vs.diastolic_blood_pressure is not None
        ):
            rows.append(_ObservationRow(
                source=(vs.systolic_blood_pressure, vs.diastolic_blood_pressure),
                source_type="bp", patient=patient, patient_id=patient_id,
                effective_dt=dt, obs_id_suffix=f"bp-{vs.id}",
                health_screening=vs.health_screening,
            ))

        # Individual vitals: (value, unit_key, code_key, profile_key)
        singles = [
            (vs.average_blood_pressure, "unit_mmhg", "mean_bp", "us-core-vital-signs"),
            (vs.heart_rate, "unit_bpm", "heart_rate", "us-core-heart-rate"),
            (vs.respiratory_rate, "unit_breaths_min", "respiratory_rate", "us-core-respiratory-rate"),
            (vs.body_temperature, "unit_celsius", "body_temperature", "us-core-body-temperature"),
            (vs.body_height, "unit_cm", "body_height", "us-core-body-height"),
            (vs.body_weight, "unit_kg", "body_weight", "us-core-body-weight"),
            (vs.pulse_oximetry, "unit_percent", "pulse_oximetry", "us-core-pulse-oximetry", vs.inhaled_oxygen_concentration),
            (vs.head_circumference_percentile, "unit_percent", "head_circ_percentile", "us-core-head-circumference-percentile"),
            (vs.bmi_percentile, "unit_percent", "bmi_percentile", "us-core-pediatric-bmi-for-age"),
            (vs.weight_for_length_percentile, "unit_percent", "weight_for_length", "us-core-pediatric-weight-for-height"),
        ]
        for item in singles:
            val, ukey, ckey, pkey = item[:4]
            extra = item[4:]
            if val is not None:
                rows.append(_ObservationRow(
                    source=(val, ukey, ckey, pkey, *extra),
                    source_type="vitals", patient=patient, patient_id=patient_id,
                    effective_dt=dt, obs_id_suffix=f"{ckey}-{vs.id}",
                    health_screening=vs.health_screening,
                ))

        return rows

    def _row_observation_id(self, row: _ObservationRow) -> str:
        if row.source_type == "bp":
            return self._compact_observation_id(row.patient, row.obs_id_suffix or "bp")
        if row.source_type == "vitals":
            return self._compact_observation_id(row.patient, row.obs_id_suffix)
        if row.source_type == "lab":
            return identity.observation_id(row.source, "lab")
        if row.source_type == "smoking":
            return identity.observation_id(row.source, "smoking")
        if row.source_type == "pregnancy_status":
            return identity.observation_id(row.source, "pregnancy-status")
        if row.source_type == "occupation":
            return identity.observation_id(row.source, "occupation")
        if row.source_type in {"screening_panel", "screening", "preference"}:
            return self._compact_observation_id(row.source, row.obs_id_suffix)
        if row.source_type == "clinical_result":
            return identity.observation_id(row.source, row.obs_id_suffix)
        return ""

    def _row_matches_code(self, row: _ObservationRow, code_tokens: set[str], context) -> bool:
        if not code_tokens:
            return True

        if row.source_type == "bp":
            return "85354-9" in code_tokens

        if row.source_type == "vitals":
            _, _, code_key, _ = row.source[:4]
            if code_key == "pulse_oximetry":
                return bool({"2708-6", "59408-5"} & code_tokens)
            return context.terminology.resolve(code_key).code in code_tokens

        if row.source_type == "lab":
            code_key = self._lab_loinc_from_name(row.source.test_name)
            return bool(
                code_key
                and context.terminology.resolve(code_key).code.lower() in code_tokens
            )

        if row.source_type == "smoking":
            return context.terminology.resolve("smoking_status").code in code_tokens

        code_key = self._row_code_key(row)
        if code_key:
            return context.terminology.resolve(code_key).code in code_tokens

        return False

    def _row_matches_category(self, row: _ObservationRow, category_tokens: set[str]) -> bool:
        if not category_tokens:
            return True
        return bool(self._row_category_codes(row) & category_tokens)

    def _row_category_codes(self, row: _ObservationRow) -> set[str]:
        if row.source_type in {"bp", "vitals"}:
            return {"vital-signs"}
        if row.source_type == "lab":
            return {"laboratory"}
        if row.source_type in {"smoking", "pregnancy_status", "occupation"}:
            return {"social-history"}
        if row.source_type == "clinical_result":
            return {"exam"}
        if row.source_type == "screening_panel":
            return {"survey", "sdoh"}
        if row.source_type == "screening":
            field_name, spec = self._screening_spec_from_suffix(row.obs_id_suffix)
            category_key = spec["category_key"]
            category_codes = {"survey", self._category_code_from_key(category_key)}
            category_codes.update(
                self._category_code_from_key(key)
                for key in self._screening_additional_category_keys(field_name)
            )
            return category_codes
        if row.source_type == "preference":
            spec = self._preference_spec_from_suffix(row.obs_id_suffix)
            return {self._category_code_from_key(spec["category_key"])}
        return set()

    def _row_code_key(self, row: _ObservationRow) -> str:
        if row.source_type == "pregnancy_status":
            return "pregnancy_status"
        if row.source_type == "occupation":
            return "occupation_history"
        if row.source_type == "screening_panel":
            return "screening_prapare_panel"
        if row.source_type == "screening":
            _, spec = self._screening_spec_from_suffix(row.obs_id_suffix)
            return spec["code_key"]
        if row.source_type == "clinical_result":
            test_name = str(getattr(row.source, "test_name", "") or "").lower()
            if "electrocardiogram" in test_name or "ecg" in test_name:
                return "clinical_result_ecg"
        if row.source_type == "preference":
            return self._preference_spec_from_suffix(row.obs_id_suffix)["code_key"]
        return ""

    def _screening_item_suffixes(self, assess) -> List[str]:
        suffixes = []
        for field_name, spec in self.SCREENING_ASSESSMENT_FIELDS.items():
            if getattr(assess, field_name, ""):
                suffixes.append(spec["suffix"])
        return suffixes

    def _screening_spec_from_suffix(self, suffix: str):
        for field_name, spec in self.SCREENING_ASSESSMENT_FIELDS.items():
            if spec["suffix"] == suffix:
                return field_name, spec
        raise KeyError(f"Unknown screening observation suffix: {suffix}")

    def _preference_spec_from_suffix(self, suffix: str):
        for spec in self.PREFERENCE_FIELDS.values():
            if suffix == spec["suffix"] or suffix.startswith(f"{spec['suffix']}-"):
                return spec
        raise KeyError(f"Unknown preference observation suffix: {suffix}")

    @staticmethod
    def _screening_additional_category_keys(field_name: str) -> List[str]:
        if field_name == "physical_activity":
            return ["category_activity"]
        if field_name in {"alcohol_use", "substance_use"}:
            return ["category_social_history"]
        return []

    @staticmethod
    def _compact_observation_id(source_obj, suffix: str = "") -> str:
        raw_id = str(getattr(source_obj, "id", source_obj))
        compact_source = raw_id.replace("-", "")[:12] or "source"
        compact_suffix = ObservationProjector._compact_suffix(suffix)
        if compact_suffix:
            return f"obs-{compact_source}-{compact_suffix}"[:64]
        return f"obs-{compact_source}"[:64]

    @staticmethod
    def _compact_suffix(suffix: str) -> str:
        if not suffix:
            return ""
        direct = {
            "bp": "bp",
            "mean_bp": "meanbp",
            "heart_rate": "hr",
            "respiratory_rate": "rr",
            "body_temperature": "temp",
            "body_height": "height",
            "body_weight": "weight",
            "pulse_oximetry": "spo2",
            "head_circ_percentile": "hcpf",
            "bmi_percentile": "pbmi",
            "weight_for_length": "wfl",
            "pregnancy-status": "pregstat",
            "screening-panel": "scrpanel",
            "screening-sdoh": "scrsdoh",
            "screening-functional-status": "scrfunc",
            "screening-disability-status": "scrdis",
            "screening-cognitive-status": "scrcog",
            "screening-physical-activity": "scrpa",
            "screening-alcohol-use": "scralc",
            "screening-substance-use": "scrsub",
            "clinical-result": "clinres",
            "clinical-result-ecg": "ecg",
            "care-experience-preference": "carepref",
            "treatment-intervention-preference": "txpref",
        }
        suffix_text = str(suffix)
        if len(suffix_text) > 37:
            tail = suffix_text[-36:]
            try:
                import uuid

                uuid.UUID(tail)
                prefix = suffix_text[:-37]
                suffix = f"{direct.get(prefix, prefix[:12])}-{tail.replace('-', '')[:8]}"
            except (TypeError, ValueError):
                pass
        parts = str(suffix).split("-")
        if len(parts) > 1 and len(parts[-1]) == 36:
            prefix = "-".join(parts[:-1])
            suffix = f"{direct.get(prefix, prefix[:12])}-{parts[-1].replace('-', '')[:8]}"
        elif str(suffix).endswith("-str") or str(suffix).endswith("-cc"):
            base, value_kind = str(suffix).rsplit("-", 1)
            suffix = f"{direct.get(base, base[:12])}-{value_kind}"
        else:
            suffix = direct.get(str(suffix), str(suffix)[:16])
        return "".join(ch if ch.isalnum() or ch in "-." else "-" for ch in suffix)

    @staticmethod
    def _token_codes(raw_value) -> set[str]:
        if not raw_value:
            return set()
        return {
            token.split("|")[-1].strip().lower()
            for token in str(raw_value).split(",")
            if token and token.strip()
        }

    @staticmethod
    def _category_code_from_key(category_key: str) -> str:
        if category_key.startswith("category_screening_"):
            return {
                "category_screening_sdoh": "sdoh",
                "category_screening_functional_status": "functional-status",
                "category_screening_disability_status": "disability-status",
                "category_screening_cognitive_status": "cognitive-status",
            }.get(category_key, "")
        if category_key == "category_care_experience_preference":
            return "care-experience-preference"
        if category_key == "category_treatment_intervention_preference":
            return "treatment-intervention-preference"
        return ""

    @staticmethod
    def _row_matches_date(row: _ObservationRow, date_param: str) -> bool:
        if not row.effective_dt:
            return False
        comparator, parsed_date = parse_date_param(date_param)
        actual = str(row.effective_dt).split("T")[0]
        target = parsed_date.isoformat().split("T")[0]
        if comparator == "ne":
            return actual != target
        if comparator in ("lt", "eb"):
            return actual < target
        if comparator in ("gt", "sa"):
            return actual > target
        if comparator == "le":
            return actual <= target
        if comparator == "ge":
            return actual >= target
        return actual == target

    @staticmethod
    def _row_matches_last_updated(row: _ObservationRow, date_param: str) -> bool:
        updated_at = getattr(row.source, "updated_at", None) or getattr(row.source, "created_at", None)
        if not updated_at:
            return False
        comparator, parsed_date = parse_date_param(date_param)
        actual = updated_at.date().isoformat() if hasattr(updated_at, "date") else str(updated_at).split("T")[0]
        target = parsed_date.isoformat().split("T")[0]
        if comparator == "ne":
            return actual != target
        if comparator in ("lt", "eb"):
            return actual < target
        if comparator in ("gt", "sa"):
            return actual > target
        if comparator == "le":
            return actual <= target
        if comparator == "ge":
            return actual >= target
        return actual == target

    @staticmethod
    def _has_persisted_result(value) -> bool:
        if value is None:
            return False
        text = str(value).strip()
        return bool(text) and text.lower() != "pending"

    @staticmethod
    def _has_persisted_test_name(value) -> bool:
        if value is None:
            return False
        text = str(value).strip()
        return bool(text) and text.lower() != "unknown test"

    def _row_status(self, row: _ObservationRow) -> str | None:
        if row.source_type == "lab":
            return self._lab_status(row.source.result_status)
        return "final"

    @staticmethod
    def _lab_status(value) -> str | None:
        status = str(value or "").strip().lower()
        allowed = {
            "registered",
            "preliminary",
            "final",
            "amended",
            "corrected",
            "cancelled",
            "entered-in-error",
            "unknown",
        }
        return status if status in allowed else None

    @staticmethod
    def _mmhg_quantity(value, terminology) -> dict:
        return {
            "value": float(value),
            "unit": "mmHg",
            "system": terminology.resolve("unit_mmhg").system,
            "code": terminology.resolve("unit_mmhg").code,
        }

    def _with_source_context(self, resource: dict, row: _ObservationRow, ref) -> dict:
        encounter = self._encounter_ref_from_row(row, ref)
        if encounter is not None:
            resource["encounter"] = encounter
        if row.effective_dt:
            resource["effectiveDateTime"] = row.effective_dt
        return resource

    def _encounter_ref_from_row(self, row: _ObservationRow, ref):
        screening = row.health_screening or getattr(row.source, "health_screening", None)
        if screening is None or getattr(screening, "id", None) is None:
            return None
        encounter = direct_encounter_for_source(row.source)
        if encounter is None or encounter.source_screening_id != screening.id:
            return None
        return ref.encounter(identity.encounter_id(screening))

    def supported_search_params(self):
        return {
            "patient": "reference",
            "category": "token",
            "code": "token",
            "date": "date",
            "status": "token",
            "_lastUpdated": "date",
            "_id": "token",
        }

    def supported_rev_includes(self):
        return ["Provenance:target"]

    @staticmethod
    def _lab_loinc_from_name(test_name: str) -> str | None:
        name = str(test_name or "").strip().lower()
        if "a1c" in name or "hemoglobin a1c" in name:
            return "hba1c"
        if "glucose" in name:
            return "lab_glucose"
        if "cholesterol" in name:
            return "lab_total_cholesterol"
        if name in {"hemoglobin", "haemoglobin"}:
            return "hemoglobin"
        return None
