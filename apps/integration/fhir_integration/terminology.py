"""
Terminology Service — Internal code → Standard coding system lookup.

All LOINC, SNOMED, and other coding references are centralized here.
Projectors NEVER hardcode system/code/display literals; they call:
    terminology.resolve("systolic_bp")
"""
from typing import Dict, NamedTuple, Optional


class Coding(NamedTuple):
    """Immutable representation of a FHIR coding triple."""
    system: str
    code: str
    display: str


# ─── Reusable system constants ───────────────────────────────
LOINC = "http://loinc.org"
SNOMED = "http://snomed.info/sct"
CVX = "http://hl7.org/fhir/sid/cvx"
RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
CONDITION_CATEGORY = "http://terminology.hl7.org/CodeSystem/condition-category"
OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
MEDREQ_CATEGORY = "http://terminology.hl7.org/CodeSystem/medicationrequest-category"
USCORE_MEDREQ_CATEGORY = "http://hl7.org/fhir/us/core/CodeSystem/us-core-medicationrequest-category"
USCORE_CONDITION_CATEGORY = "http://hl7.org/fhir/us/core/CodeSystem/condition-category"
USCORE_GENERIC_CATEGORY = "http://hl7.org/fhir/us/core/CodeSystem/us-core-category"
USCORE_DOCREF_CATEGORY = "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category"
V3_ACTCODE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
DISCHARGE_DISPOSITION = "http://terminology.hl7.org/CodeSystem/discharge-disposition"
PARTICIPATION_TYPE = "http://terminology.hl7.org/CodeSystem/v3-ParticipationType"
ROLE_CODE = "http://terminology.hl7.org/CodeSystem/v3-RoleCode"
SUBSCRIBER_REL = "http://terminology.hl7.org/CodeSystem/subscriber-relationship"
COVERAGE_CLASS = "http://terminology.hl7.org/CodeSystem/coverage-class"
PROVENANCE_AGENT = "http://terminology.hl7.org/CodeSystem/provenance-participant-type"
IDENTIFIER_TYPE = "http://terminology.hl7.org/CodeSystem/v2-0203"
OBS_INTERPRETATION = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
IMMUNIZATION_STATUS_REASON = "http://terminology.hl7.org/CodeSystem/immunization-status-reason"
V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"
UNITS = "http://unitsofmeasure.org"


# ─── Master Lookup Table ─────────────────────────────────────
# key → Coding(system, code, display)
# Organized by clinical domain for readability.

_TERMINOLOGY_MAP: Dict[str, Coding] = {
    # ── Vital Signs (LOINC) ──────────────────────────────────
    "vital_signs_panel":          Coding(LOINC, "85353-1", "Vital signs, weight, height, head circumference, oxygen saturation and BMI panel"),
    "blood_pressure_panel":       Coding(LOINC, "85354-9", "Blood pressure panel with all children optional"),
    "systolic_bp":                Coding(LOINC, "8480-6",  "Systolic blood pressure"),
    "diastolic_bp":               Coding(LOINC, "8462-4",  "Diastolic blood pressure"),
    "average_systolic_bp":        Coding(LOINC, "96608-5", "Average systolic blood pressure"),
    "average_diastolic_bp":       Coding(LOINC, "96609-3", "Average diastolic blood pressure"),
    "mean_bp":                    Coding(LOINC, "8478-0",  "Mean blood pressure"),
    "heart_rate":                 Coding(LOINC, "8867-4",  "Heart rate"),
    "respiratory_rate":           Coding(LOINC, "9279-1",  "Respiratory rate"),
    "body_temperature":           Coding(LOINC, "8310-5",  "Body temperature"),
    "body_height":                Coding(LOINC, "8302-2",  "Body height"),
    "body_weight":                Coding(LOINC, "29463-7", "Body weight"),
    "bmi":                        Coding(LOINC, "39156-5", "Body mass index (BMI)"),
    "pulse_oximetry":             Coding(LOINC, "2708-6",  "Oxygen saturation in Arterial blood"),
    "pulse_oximetry_pulseox":     Coding(LOINC, "59408-5", "Oxygen saturation in Arterial blood by Pulse oximetry"),
    "inhaled_o2":                 Coding(LOINC, "3150-0",  "Inhaled oxygen concentration"),
    "inhaled_o2_flow_rate":       Coding(LOINC, "3151-8",  "Inhaled oxygen flow rate"),
    "head_circumference":         Coding(LOINC, "9843-4",  "Head Occipital-frontal circumference"),
    "bmi_percentile":             Coding(LOINC, "59576-9", "Body mass index (BMI) [Percentile] Per age and sex"),
    "weight_for_length":          Coding(LOINC, "77606-2", "Weight-for-length Per age and sex"),
    "head_circ_percentile":       Coding(LOINC, "8289-1",  "Head Occipital-frontal circumference Percentile"),
    "average_blood_pressure":     Coding(LOINC, "96607-7", "Avg Blood pressure systolic and diastolic"),

    # ── Smoking / Social ─────────────────────────────────────
    "smoking_status":             Coding(LOINC, "72166-2", "Tobacco smoking status"),
    "smoking_pack_years":          Coding(SNOMED, "401201003", "Cigarette pack-years"),
    "occupation_history":          Coding(LOINC, "11341-5", "History of Occupation"),
    "occupation_industry":         Coding(LOINC, "86188-0", "History of Occupation Industry"),
    "pregnancy_status":            Coding(LOINC, "82810-3", "Pregnancy status"),
    "pregnancy_intent":            Coding(LOINC, "86645-9", "Pregnancy intention in the next year"),

    # Survey / assessment observations
    "screening_prapare_panel":     Coding(LOINC, "93025-5", "Protocol for Responding to and Assessing Patients' Assets, Risks, and Experiences"),
    "screening_sdoh":              Coding(LOINC, "93025-5", "Protocol for Responding to and Assessing Patients' Assets, Risks, and Experiences"),
    "screening_functional_status": Coding(LOINC, "54522-8", "Functional status"),
    "screening_disability_status": Coding(LOINC, "89571-4", "Disability status"),
    "screening_cognitive_status":  Coding(LOINC, "75275-8", "Cognitive status [Interpretation]"),
    "screening_physical_activity": Coding(LOINC, "89555-7", "Exercise minutes per week"),
    "screening_alcohol_use":       Coding(LOINC, "75626-2", "Total score [AUDIT-C]"),
    "screening_substance_use":     Coding(LOINC, "96842-0", "Substance use screen"),
    "clinical_result_ecg":         Coding(LOINC, "34534-8", "Electrocardiogram 12 lead panel"),
    "care_experience_preference":  Coding(LOINC, "95541-9", "Care experience preference"),
    "treatment_intervention_preference": Coding(LOINC, "75773-2", "Preferences for medical treatment"),

    # ── Lab common ───────────────────────────────────────────
    "cbc":                        Coding(LOINC, "58410-2", "Complete blood count (CBC) panel"),
    "hemoglobin":                 Coding(LOINC, "718-7",   "Hemoglobin [Mass/volume] in Blood"),
    "hba1c":                      Coding(LOINC, "4548-4",  "Hemoglobin A1c/Hemoglobin.total in Blood"),
    "lab_glucose":                Coding(LOINC, "2339-0",  "Glucose [Mass/volume] in Blood"),
    "lab_total_cholesterol":      Coding(LOINC, "2093-3",  "Cholesterol [Mass/volume] in Serum or Plasma"),

    # ── Conditions (SNOMED) ──────────────────────────────────
    "diabetes_type_2":            Coding(SNOMED, "44054006",  "Diabetes mellitus type 2"),
    "anemia":                     Coding(SNOMED, "271737000", "Anemia"),
    "hypertension":               Coding(SNOMED, "38341003",  "Hypertensive disorder"),

    # ── Procedures (SNOMED) ──────────────────────────────────
    "medication_reconciliation":  Coding(SNOMED, "430193006", "Medication Reconciliation"),

    # ── Allergy substances ───────────────────────────────────
    "penicillin":                 Coding(SNOMED, "764146007", "Penicillin"),

    # ── Device ───────────────────────────────────────────────
    "pacemaker":                  Coding(SNOMED, "34370006",  "Implantable pacemaker"),

    # ── Immunization (CVX) ───────────────────────────────────
    "covid_vaccine":              Coding(CVX, "207", "COVID-19, mRNA, LNP-S, PF, 100 mcg/0.5mL dose or 50 mcg/0.25mL dose"),

    # ── Observation categories ───────────────────────────────
    "category_vital_signs":       Coding(OBS_CATEGORY, "vital-signs",       "Vital Signs"),
    "category_laboratory":        Coding(OBS_CATEGORY, "laboratory",        "Laboratory"),
    "category_social_history":    Coding(OBS_CATEGORY, "social-history",    "Social History"),
    "category_clinical_test":     Coding(OBS_CATEGORY, "exam",              "Exam"),
    "category_survey":            Coding(OBS_CATEGORY, "survey",            "Survey"),
    "category_activity":          Coding(OBS_CATEGORY, "activity",          "Activity"),

    # ── Condition categories ─────────────────────────────────
    "category_problem_list":      Coding(CONDITION_CATEGORY, "problem-list-item",   "Problem List Item"),
    "category_encounter_dx":      Coding(CONDITION_CATEGORY, "encounter-diagnosis", "Encounter Diagnosis"),
    "category_health_concern":    Coding(USCORE_CONDITION_CATEGORY, "health-concern", "Health Concern"),
    "category_screening_sdoh":    Coding(USCORE_GENERIC_CATEGORY, "sdoh", "Screening Assessment"),
    "category_screening_functional_status": Coding(USCORE_GENERIC_CATEGORY, "functional-status", "Screening Assessment"),
    "category_screening_disability_status": Coding(USCORE_GENERIC_CATEGORY, "disability-status", "Screening Assessment"),
    "category_screening_cognitive_status": Coding(USCORE_GENERIC_CATEGORY, "cognitive-status", "Screening Assessment"),
    "category_care_experience_preference": Coding(USCORE_GENERIC_CATEGORY, "care-experience-preference", "Care Experience Preference"),
    "category_treatment_intervention_preference": Coding(USCORE_GENERIC_CATEGORY, "treatment-intervention-preference", "Treatment Intervention Preference"),
    "category_docref_clinical_note": Coding(USCORE_DOCREF_CATEGORY, "clinical-note", "Clinical Note"),
    "category_dr_lab_loinc":      Coding(LOINC, "LP29684-5", "Laboratory studies"),
    "category_dr_note_loinc":     Coding(LOINC, "LP29708-2", "Administrative and clinical note"),
    "participant_attender":       Coding(PARTICIPATION_TYPE, "ATND", "Attender"),
    "discharge_home":             Coding(DISCHARGE_DISPOSITION, "home", "Home"),

    # ── Medication categories ────────────────────────────────
    "medreq_outpatient":          Coding(MEDREQ_CATEGORY, "outpatient", "Outpatient"),
    "medreq_discharge":           Coding(USCORE_MEDREQ_CATEGORY, "discharge", "Discharge"),

    # ── Medication adherence ─────────────────────────────────
    "treatment_compliant":        Coding(SNOMED, "183964008", "Treatment compliant (finding)"),
    "immunization_status_reason_immune": Coding(IMMUNIZATION_STATUS_REASON, "IMMUNE", "Immunity"),
    "obs_interpretation_normal":  Coding(OBS_INTERPRETATION, "N", "Normal"),

    # ── Units ────────────────────────────────────────────────
    "unit_mmhg":                  Coding(UNITS, "mm[Hg]",    "mmHg"),
    "unit_bpm":                   Coding(UNITS, "/min",      "/min"),
    "unit_celsius":               Coding(UNITS, "Cel",       "Cel"),
    "unit_cm":                    Coding(UNITS, "cm",        "cm"),
    "unit_kg":                    Coding(UNITS, "kg",        "kg"),
    "unit_kg_m2":                 Coding(UNITS, "kg/m2",     "kg/m2"),
    "unit_percent":               Coding(UNITS, "%",         "%"),
    "unit_pack_years":            Coding(UNITS, "{pack-years}", "Pack years"),
    "unit_l_min":                 Coding(UNITS, "L/min",     "L/min"),
    "unit_breaths_min":           Coding(UNITS, "/min",      "/min"),
    "unit_tablet":                Coding(UNITS, "{tbl}",     "tablet"),
}


class TerminologyService:
    """
    Resolve internal clinical codes to FHIR-standard coding triples.

    Usage
    -----
    >>> ts = TerminologyService()
    >>> ts.resolve("systolic_bp")
    Coding(system='http://loinc.org', code='8480-6', display='Systolic blood pressure')
    >>> ts.to_fhir_coding("systolic_bp")
    {"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}
    """

    def __init__(self, overrides: Optional[Dict[str, Coding]] = None):
        self._map = dict(_TERMINOLOGY_MAP)
        if overrides:
            self._map.update(overrides)

    def resolve(self, key: str) -> Coding:
        """Return the Coding triple for ``key``; raise KeyError if unknown."""
        try:
            return self._map[key]
        except KeyError:
            raise KeyError(
                f"TerminologyService: unknown code key {key!r}. "
                f"Register it in terminology.py._TERMINOLOGY_MAP."
            )

    def to_fhir_coding(self, key: str) -> dict:
        """Return a ready-to-embed FHIR ``coding`` dict."""
        c = self.resolve(key)
        return {"system": c.system, "code": c.code, "display": c.display}

    def to_codeable_concept(self, key: str) -> dict:
        """Return a FHIR ``CodeableConcept`` wrapping the coding."""
        return {"coding": [self.to_fhir_coding(key)]}

    def has(self, key: str) -> bool:
        return key in self._map
