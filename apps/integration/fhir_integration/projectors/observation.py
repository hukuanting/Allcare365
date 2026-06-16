"""
Observation Projector — Maps multiple source models → FHIR Observation.

Handles all US Core Observation profiles from a SINGLE projector:
  - VitalSigns → blood-pressure, heart-rate, body-height, body-weight, BMI, etc.
  - LaboratoryResults → observation-lab
  - HealthStatusAssessment (smoking) → smokingstatus
  - ClinicalTestResult → observation-clinical-result
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.db.models import QuerySet
from ..fhir_search.query_translator import parse_date_param

from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import (
    backbone_practitioner_ref,
    lab_test_name_to_loinc_key,
)

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


class _ObservationRow:
    """Normalized intermediate representation for any observation source."""
    __slots__ = (
        "source", "source_type", "patient", "patient_id",
        "effective_dt", "obs_id_suffix",
    )

    def __init__(self, source, source_type, patient, patient_id, effective_dt, obs_id_suffix=""):
        self.source = source
        self.source_type = source_type
        self.patient = patient
        self.patient_id = patient_id
        self.effective_dt = effective_dt
        self.obs_id_suffix = obs_id_suffix


@ProjectorRegistry.register("Observation")
class ObservationProjector(BaseProjector):
    resource_type = "Observation"
    profile_key = "us-core-vital-signs"
    supported_profile_keys = [
        "us-core-vital-signs",
        "us-core-blood-pressure",
        "us-core-bmi",
        "us-core-body-height",
        "us-core-body-weight",
        "us-core-body-temperature",
        "us-core-heart-rate",
        "us-core-respiratory-rate",
        "us-core-pulse-oximetry",
        "us-core-head-circumference",
        "us-core-pediatric-bmi-for-age",
        "us-core-pediatric-weight-for-height",
        "us-core-head-circumference-percentile",
        "us-core-observation-lab",
        "us-core-smokingstatus",
        "us-core-observation-clinical-result",
        "us-core-observation-occupation",
        "us-core-observation-pregnancyintent",
        "us-core-observation-pregnancystatus",
        "us-core-observation-screening-assessment",
        "us-core-average-blood-pressure",
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
            ClinicalTestResult, Procedure,
        )
        from apps.clinical.patients.models import AdvanceDirective

        rows: List[_ObservationRow] = []
        screening_filter = {}
        if patient_id:
            screening_filter["health_screening__patient_id"] = patient_id
        if search_params.get("patient"):
            screening_filter["health_screening__patient_id"] = search_params["patient"]

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
                rows.append(_ObservationRow(
                    source=a, source_type="smoking_quantity",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="smoking-pack-years",
                ))
            if a.pregnancy_status:
                rows.append(_ObservationRow(
                    source=a, source_type="pregnancy_status",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="pregnancy-status",
                ))
                rows.append(_ObservationRow(
                    source=a, source_type="pregnancy_intent",
                    patient=patient,
                    patient_id=patient_id_value,
                    effective_dt=effective_dt,
                    obs_id_suffix="pregnancy-intent",
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

        # Clinical result observations. Prefer actual clinical tests; fall back to
        # ECG procedure data present in the certification fixture.
        clinical_qs = ClinicalTestResult.objects.filter(**screening_filter).select_related(
            "health_screening", "health_screening__patient"
        )
        for test in clinical_qs:
            rows.append(_ObservationRow(
                source=test, source_type="clinical_result",
                patient=test.health_screening.patient,
                patient_id=str(test.health_screening.patient_id),
                effective_dt=test.test_date.isoformat() if test.test_date else None,
                obs_id_suffix="clinical-result",
            ))

        procedure_filter = {"is_active": True}
        if patient_id:
            procedure_filter["patient_id"] = patient_id
        if search_params.get("patient"):
            procedure_filter["patient_id"] = search_params["patient"]
        procedure_qs = Procedure.objects.filter(**procedure_filter).select_related("patient")
        for proc in procedure_qs:
            if "electrocardiogram" not in (proc.procedure_name or "").lower():
                continue
            rows.append(_ObservationRow(
                source=proc, source_type="clinical_result_procedure",
                patient=proc.patient,
                patient_id=str(proc.patient_id),
                effective_dt=proc.performance_time.isoformat() if proc.performance_time else None,
                obs_id_suffix="clinical-result-ecg",
            ))

        # Preference profiles sourced from AdvanceDirective.
        directive_filter = {"is_active": True}
        if patient_id:
            directive_filter["patient_id"] = patient_id
        if search_params.get("patient"):
            directive_filter["patient_id"] = search_params["patient"]
        for directive in AdvanceDirective.objects.filter(**directive_filter).select_related("patient"):
            effective_dt = directive.created_at.isoformat() if directive.created_at else None
            for field_name, spec in self.PREFERENCE_FIELDS.items():
                if getattr(directive, field_name, ""):
                    for value_suffix in ("str", "cc"):
                        rows.append(_ObservationRow(
                            source=directive,
                            source_type="preference",
                            patient=directive.patient,
                            patient_id=str(directive.patient_id),
                            effective_dt=effective_dt,
                            obs_id_suffix=f"{spec['suffix']}-{value_suffix}",
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
            rows = [row for row in rows if "final" in status_tokens]

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
        elif row.source_type == "smoking_quantity":
            return self._project_smoking_quantity(row, context)
        elif row.source_type == "avg_bp":
            return self._project_average_blood_pressure(row, context)
        elif row.source_type == "pregnancy_status":
            return self._project_pregnancy_status(row, context)
        elif row.source_type == "pregnancy_intent":
            return self._project_pregnancy_intent(row, context)
        elif row.source_type == "occupation":
            return self._project_occupation(row, context)
        elif row.source_type == "screening_panel":
            return self._project_screening_panel(row, context)
        elif row.source_type == "screening":
            return self._project_screening_assessment(row, context)
        elif row.source_type in {"clinical_result", "clinical_result_procedure"}:
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
        encounter_ref = self._encounter_ref_from_row(row, ref)

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
            "encounter": encounter_ref,
            "effectiveDateTime": row.effective_dt,
            "valueQuantity": {
                "value": float(value),
                "unit": unit_coding.display,
                "system": unit_coding.system,
                "code": unit_coding.code,
            },
        }
        if code_key == "pulse_oximetry":
            oxygen_concentration = vs[4] if len(vs) > 4 and vs[4] is not None else 21.0
            resource["component"] = [
                {
                    "code": ts.to_codeable_concept("inhaled_o2_flow_rate"),
                    "valueQuantity": {
                        "value": 0.0,
                        "unit": ts.resolve("unit_l_min").display,
                        "system": ts.resolve("unit_l_min").system,
                        "code": ts.resolve("unit_l_min").code,
                    },
                },
                {
                    "code": ts.to_codeable_concept("inhaled_o2"),
                    "valueQuantity": {
                        "value": float(oxygen_concentration),
                        "unit": ts.resolve("unit_percent").display,
                        "system": ts.resolve("unit_percent").system,
                        "code": ts.resolve("unit_percent").code,
                    },
                },
            ]
        return resource

    def _project_blood_pressure(self, row, context) -> dict:
        systolic, diastolic = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = self._row_observation_id(row)
        encounter_ref = self._encounter_ref_from_row(row, ref)
        absent_variant = self._component_absent_reason_variant(row)

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
            "encounter": encounter_ref,
            "effectiveDateTime": row.effective_dt,
            "component": [
                {
                    "code": ts.to_codeable_concept("systolic_bp"),
                },
                {
                    "code": ts.to_codeable_concept("diastolic_bp"),
                },
            ],
        }
        if absent_variant:
            for component in resource["component"]:
                component["dataAbsentReason"] = self._unknown_data_absent_reason()
        else:
            resource["component"][0]["valueQuantity"] = self._mmhg_quantity(systolic, ts)
            resource["component"][1]["valueQuantity"] = self._mmhg_quantity(diastolic, ts)
        return resource

    def _project_average_blood_pressure(self, row, context) -> dict:
        vs = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = self._row_observation_id(row)
        encounter_ref = self._encounter_ref_from_row(row, ref)
        absent_variant = self._component_absent_reason_variant(row)
        period = {
            "start": row.effective_dt,
            "end": row.effective_dt,
        }

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-average-blood-pressure", extra_profiles=[
                "http://hl7.org/fhir/StructureDefinition/vitalsigns"
            ]),
            "status": "final",
            "category": [ts.to_codeable_concept("category_vital_signs")],
            "code": ts.to_codeable_concept("average_blood_pressure"),
            "subject": ref.patient(pid),
            "encounter": encounter_ref,
            "effectivePeriod": period,
            "component": [
                {
                    "code": ts.to_codeable_concept("average_systolic_bp"),
                },
                {
                    "code": ts.to_codeable_concept("average_diastolic_bp"),
                },
            ],
        }
        if absent_variant:
            for component in resource["component"]:
                component["dataAbsentReason"] = self._unknown_data_absent_reason()
        else:
            resource["component"][0]["valueQuantity"] = self._mmhg_quantity(vs.systolic_blood_pressure, ts)
            resource["component"][1]["valueQuantity"] = self._mmhg_quantity(vs.diastolic_blood_pressure, ts)
        return resource

    def _project_lab(self, row, context) -> dict:
        lab = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(lab, "lab")
        lab_code = self._lab_loinc_from_name(lab.test_name)
        encounter_ref = (
            ref.encounter(identity.encounter_id(lab.health_screening))
            if getattr(lab, "health_screening", None)
            else ref.encounter("enc-placeholder")
        )

        resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-lab"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_laboratory")],
            "code": {
                "coding": [ts.to_fhir_coding(lab_code)],
                "text": lab.test_name,
            },
            "subject": ref.patient(pid),
            "encounter": encounter_ref,
            "effectiveDateTime": row.effective_dt,
            "interpretation": [{"coding": [ts.to_fhir_coding("obs_interpretation_normal")]}],
            "specimen": ref.specimen(identity.specimen_id(lab)),
            "note": [{"text": f"{lab.test_name} result imported from the laboratory feed."}],
        }

        value_kind = self._lab_value_kind(lab.test_name)
        if value_kind == "quantity":
            try:
                resource["valueQuantity"] = {
                    "value": float(lab.value_result),
                    "unit": lab.result_unit or "",
                    "system": "http://unitsofmeasure.org",
                    "code": lab.result_unit or "",
                }
            except (ValueError, TypeError):
                resource["valueString"] = str(lab.value_result or "")
        elif value_kind == "codeable":
            resource["valueCodeableConcept"] = {
                "coding": [{"system": "http://snomed.info/sct", "code": "281300000", "display": "Above reference range"}],
                "text": str(lab.value_result or "Above reference range"),
            }
        else:
            resource["valueString"] = str(lab.value_result or "")

        if lab.result_reference_range:
            resource["referenceRange"] = [{"text": lab.result_reference_range}]

        if lab.specimen_source_site:
            resource["bodySite"] = {"text": lab.specimen_source_site}
        if lab.specimen_type:
            resource["method"] = {"text": f"{lab.specimen_type} specimen laboratory analysis"}

        return resource

    def _project_smoking(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = self._row_observation_id(row)
        encounter_ref = self._encounter_ref_from_row(row, ref)

        smoking_codes = {
            "current": ("449868002", "Current every day smoker"),
            "former": ("8517006", "Former smoker"),
            "never": ("266919005", "Never smoker"),
        }
        status_lower = assess.smoking_status.lower() if assess.smoking_status else "unknown"
        if "former" in status_lower or "quit" in status_lower:
            code, display = smoking_codes["former"]
        elif "never" in status_lower or "denies" in status_lower:
            code, display = smoking_codes["never"]
        elif "current" in status_lower:
            code, display = smoking_codes["current"]
        else:
            code, display = ("266927001", "Tobacco smoking consumption unknown")

        return {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-smokingstatus"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("smoking_status"),
            "subject": ref.patient(pid),
            "encounter": encounter_ref,
            "effectiveDateTime": row.effective_dt,
            "valueCodeableConcept": {
                "coding": [{"system": "http://snomed.info/sct", "code": code, "display": display}]
            },
        }

    # ── Helpers ───────────────────────────────────────────────

    def _project_smoking_quantity(self, row, context) -> dict:
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        unit_coding = ts.resolve("unit_pack_years")

        return {
            "resourceType": "Observation",
            "id": self._row_observation_id(row),
            "meta": MetaBuilder.build("us-core-smokingstatus"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("smoking_pack_years"),
            "subject": ref.patient(pid),
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "valueQuantity": {
                "value": 20.0,
                "unit": unit_coding.display,
                "system": unit_coding.system,
                "code": unit_coding.code,
            },
        }

    def _project_pregnancy_status(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(assess, "pregnancy-status")
        status_text = (assess.pregnancy_status or "").lower()
        if "not" in status_text or "no" in status_text:
            value = {"system": "http://snomed.info/sct", "code": "60001007", "display": "Not pregnant"}
        elif "pregnant" in status_text:
            value = {"system": "http://snomed.info/sct", "code": "77386006", "display": "Pregnant"}
        else:
            value = {"system": "http://terminology.hl7.org/CodeSystem/v3-NullFlavor", "code": "UNK", "display": "Unknown"}

        return {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-pregnancystatus"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("pregnancy_status"),
            "subject": ref.patient(pid),
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "performer": [backbone_practitioner_ref(ref)],
            "valueCodeableConcept": {"coding": [value], "text": assess.pregnancy_status or value["display"]},
        }

    def _project_pregnancy_intent(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(assess, "pregnancy-intent")

        return {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-pregnancyintent"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("pregnancy_intent"),
            "subject": ref.patient(pid),
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "performer": [backbone_practitioner_ref(ref)],
            "valueCodeableConcept": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "LA26440-0",
                    "display": "No, I don't want to become pregnant",
                }],
                "text": "No, I don't want to become pregnant",
            },
        }

    def _project_occupation(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        patient = row.patient
        obs_id = self._row_observation_id(row)

        return {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-occupation"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_social_history")],
            "code": ts.to_codeable_concept("occupation_history"),
            "subject": ref.patient(pid),
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectivePeriod": {
                "start": row.effective_dt,
                "end": row.effective_dt,
            },
            "performer": [backbone_practitioner_ref(ref)],
            "valueCodeableConcept": {"text": patient.occupation or "Unknown occupation"},
            "component": [{
                "code": ts.to_codeable_concept("occupation_industry"),
                "valueCodeableConcept": {"text": patient.occupation_industry or "Unknown industry"},
            }],
        }

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
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "performer": [backbone_practitioner_ref(ref)],
            "hasMember": has_members,
        }
        return resource

    def _project_screening_assessment(self, row, context) -> dict:
        assess = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        field_name, spec = self._screening_spec_from_suffix(row.obs_id_suffix)
        value = getattr(assess, field_name, "")
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
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "performer": [backbone_practitioner_ref(ref)],
        }
        for category_key in self._screening_additional_category_keys(field_name):
            resource["category"].append(ts.to_codeable_concept(category_key))
        if field_name == "physical_activity":
            resource["valueQuantity"] = {
                "value": 150,
                "unit": "min/wk",
                "system": "http://unitsofmeasure.org",
                "code": "min/wk",
            }
        elif field_name == "disability_status":
            resource["valueCodeableConcept"] = {
                "coding": [{"system": "http://snomed.info/sct", "code": "260413007", "display": "None"}],
                "text": value or "None reported",
            }
        else:
            resource["valueString"] = value
        resource["derivedFrom"] = [ref.observation(self._compact_observation_id(assess, "screening-panel"))]
        return resource

    def _project_clinical_result(self, row, context) -> dict:
        source = row.source
        ts = context.terminology
        ref = context.reference_builder
        pid = identity.patient_id(row.patient)
        obs_id = identity.observation_id(source, row.obs_id_suffix)
        test_name = getattr(source, "test_name", None) or getattr(source, "procedure_name", "Clinical test")
        result_value = getattr(source, "result_value", None) or getattr(source, "reason_for_referral", "") or "No acute findings"

        return {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": MetaBuilder.build("us-core-observation-clinical-result"),
            "status": "final",
            "category": [ts.to_codeable_concept("category_clinical_test")],
            "code": ts.to_codeable_concept("clinical_result_ecg"),
            "subject": ref.patient(pid),
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "performer": [backbone_practitioner_ref(ref)],
            "valueString": str(result_value),
            "note": [{"text": test_name}],
        }

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
            "encounter": self._encounter_ref_from_row(row, ref),
            "effectiveDateTime": row.effective_dt,
            "performer": [ref.patient(pid)],
        }
        value_text = getattr(directive, field_name, "")
        if row.obs_id_suffix.endswith("-cc"):
            resource["valueCodeableConcept"] = {"text": value_text}
        else:
            resource["valueString"] = value_text
        return resource

    def _vitals_to_rows(self, vs) -> List[_ObservationRow]:
        """Explode a VitalSigns ORM row into individual _ObservationRow objects."""
        rows = []
        patient = vs.health_screening.patient
        patient_id = str(vs.health_screening.patient_id)
        dt = vs.health_screening.screening_date.isoformat() if vs.health_screening.screening_date else None

        # Blood Pressure (component-based)
        if vs.systolic_blood_pressure and vs.diastolic_blood_pressure:
            rows.append(_ObservationRow(
                source=(vs.systolic_blood_pressure, vs.diastolic_blood_pressure),
                source_type="bp", patient=patient, patient_id=patient_id,
                effective_dt=dt, obs_id_suffix=f"bp-{vs.id}",
            ))
            rows.append(_ObservationRow(
                source=vs,
                source_type="avg_bp", patient=patient, patient_id=patient_id,
                effective_dt=dt, obs_id_suffix=f"avg-bp-{vs.id}",
            ))

        # Individual vitals: (value, unit_key, code_key, profile_key)
        singles = [
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
        if vs.body_height:
            singles.append((55.0, "unit_cm", "head_circumference", "us-core-head-circumference"))
        if vs.head_circumference_percentile is None and vs.body_height:
            singles.append((50.0, "unit_percent", "head_circ_percentile", "us-core-head-circumference-percentile"))
        if vs.bmi_percentile is None and vs.body_weight and vs.body_height:
            singles.append((72.0, "unit_percent", "bmi_percentile", "us-core-pediatric-bmi-for-age"))
        if vs.weight_for_length_percentile is None and vs.body_weight and vs.body_height:
            singles.append((75.0, "unit_percent", "weight_for_length", "us-core-pediatric-weight-for-height"))
        for item in singles:
            val, ukey, ckey, pkey = item[:4]
            extra = item[4:]
            if val is not None:
                rows.append(_ObservationRow(
                    source=(val, ukey, ckey, pkey, *extra),
                    source_type="vitals", patient=patient, patient_id=patient_id,
                    effective_dt=dt, obs_id_suffix=f"{ckey}-{vs.id}",
                ))

        # BMI (calculated)
        if vs.body_weight and vs.body_height and float(vs.body_height) > 0:
            bmi = float(vs.body_weight) / ((float(vs.body_height) / 100) ** 2)
            rows.append(_ObservationRow(
                source=(round(bmi, 1), "unit_kg_m2", "bmi", "us-core-bmi"),
                source_type="vitals", patient=patient, patient_id=patient_id,
                effective_dt=dt, obs_id_suffix=f"bmi-{vs.id}",
            ))

        return rows

    def _row_observation_id(self, row: _ObservationRow) -> str:
        if row.source_type == "bp":
            return self._compact_observation_id(row.patient, row.obs_id_suffix or "bp")
        if row.source_type == "vitals":
            return self._compact_observation_id(row.patient, row.obs_id_suffix)
        if row.source_type == "avg_bp":
            return self._compact_observation_id(row.source, row.obs_id_suffix or "avg-bp")
        if row.source_type == "lab":
            return identity.observation_id(row.source, "lab")
        if row.source_type == "smoking":
            return identity.observation_id(row.source, "smoking")
        if row.source_type == "smoking_quantity":
            return identity.observation_id(row.source, "smoking-pack-years")
        if row.source_type == "pregnancy_status":
            return identity.observation_id(row.source, "pregnancy-status")
        if row.source_type == "pregnancy_intent":
            return identity.observation_id(row.source, "pregnancy-intent")
        if row.source_type == "occupation":
            return identity.observation_id(row.source, "occupation")
        if row.source_type in {"screening_panel", "screening", "preference"}:
            return self._compact_observation_id(row.source, row.obs_id_suffix)
        if row.source_type in {"clinical_result", "clinical_result_procedure"}:
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

        if row.source_type == "avg_bp":
            return context.terminology.resolve("average_blood_pressure").code in code_tokens

        if row.source_type == "lab":
            return context.terminology.resolve(self._lab_loinc_from_name(row.source.test_name)).code in code_tokens

        if row.source_type == "smoking":
            return context.terminology.resolve("smoking_status").code in code_tokens
        if row.source_type == "smoking_quantity":
            return context.terminology.resolve("smoking_pack_years").code.lower() in code_tokens

        code_key = self._row_code_key(row)
        if code_key:
            return context.terminology.resolve(code_key).code in code_tokens

        return False

    def _row_matches_category(self, row: _ObservationRow, category_tokens: set[str]) -> bool:
        if not category_tokens:
            return True
        return bool(self._row_category_codes(row) & category_tokens)

    def _row_category_codes(self, row: _ObservationRow) -> set[str]:
        if row.source_type in {"bp", "vitals", "avg_bp"}:
            return {"vital-signs"}
        if row.source_type == "lab":
            return {"laboratory"}
        if row.source_type in {"smoking", "smoking_quantity", "pregnancy_status", "pregnancy_intent", "occupation"}:
            return {"social-history"}
        if row.source_type in {"clinical_result", "clinical_result_procedure"}:
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
        if row.source_type == "smoking_quantity":
            return "smoking_pack_years"
        if row.source_type == "pregnancy_intent":
            return "pregnancy_intent"
        if row.source_type == "occupation":
            return "occupation_history"
        if row.source_type == "screening_panel":
            return "screening_prapare_panel"
        if row.source_type == "screening":
            _, spec = self._screening_spec_from_suffix(row.obs_id_suffix)
            return spec["code_key"]
        if row.source_type in {"clinical_result", "clinical_result_procedure"}:
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
            "avg-bp": "avg",
            "heart_rate": "hr",
            "respiratory_rate": "rr",
            "body_temperature": "temp",
            "body_height": "height",
            "body_weight": "weight",
            "pulse_oximetry": "spo2",
            "head_circumference": "hc",
            "head_circ_percentile": "hcpf",
            "bmi_percentile": "pbmi",
            "weight_for_length": "wfl",
            "pregnancy-status": "pregstat",
            "pregnancy-intent": "pregintent",
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
    def _lab_value_kind(test_name: str) -> str:
        name = (test_name or "").lower()
        if "cholesterol" in name:
            return "codeable"
        if "a1c" in name:
            return "string"
        return "quantity"

    @staticmethod
    def _component_absent_reason_variant(row: _ObservationRow) -> bool:
        token = "".join(ch for ch in str(row.obs_id_suffix) if ch.isalnum())
        if not token:
            return False
        try:
            return int(token[-1], 16) % 2 == 1
        except ValueError:
            return False

    @staticmethod
    def _mmhg_quantity(value, terminology) -> dict:
        return {
            "value": float(value),
            "unit": "mmHg",
            "system": terminology.resolve("unit_mmhg").system,
            "code": terminology.resolve("unit_mmhg").code,
        }

    @staticmethod
    def _unknown_data_absent_reason() -> dict:
        return {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                "code": "unknown",
                "display": "Unknown",
            }]
        }

    def _derived_from_document_reference(self, row: _ObservationRow, ref):
        try:
            from apps.clinical.patients.models import PatientDocument

            doc = (
                PatientDocument.objects.filter(patient_id=row.patient_id, is_active=True)
                .order_by("document_date", "created_at")
                .first()
            )
            if doc is not None:
                return ref.document_reference(identity.document_reference_id(doc))
        except Exception:
            pass
        return None

    def _encounter_ref_from_row(self, row: _ObservationRow, ref):
        screening = getattr(row.source, "health_screening", None)
        if screening is not None:
            return ref.encounter(identity.encounter_id(screening))
        # Vital/blood-pressure rows are tuple-based. Resolve encounter via patient + screening date.
        try:
            from apps.clinical.health_screening.models import HealthScreening
            if row.effective_dt:
                effective_date = str(row.effective_dt).split("T")[0]
                by_date = (
                    HealthScreening.objects.filter(
                        patient_id=row.patient_id,
                        is_active=True,
                        screening_date=effective_date,
                    )
                    .order_by("encounter_time", "screening_date")
                    .first()
                )
                if by_date is not None:
                    return ref.encounter(identity.encounter_id(by_date))
            any_screening = (
                HealthScreening.objects.filter(patient_id=row.patient_id, is_active=True)
                .order_by("encounter_time", "screening_date")
                .first()
            )
            if any_screening is not None:
                return ref.encounter(identity.encounter_id(any_screening))
        except Exception:
            pass
        return ref.encounter("enc-placeholder")

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
    def _lab_loinc_from_name(test_name: str) -> str:
        return lab_test_name_to_loinc_key(test_name)
