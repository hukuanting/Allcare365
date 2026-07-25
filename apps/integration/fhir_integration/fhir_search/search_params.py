"""
Declarative FHIR Search Parameter Definitions.

Config-driven mapping from FHIR search param names → ORM field paths.
To support a new US Core version, edit this file ONLY — the engine stays untouched.
"""

# type values: "reference", "token", "date", "string", "number"
# orm_path: Django ORM lookup path from the model root

FHIR_SEARCH_PARAMETERS: dict[str, dict[str, dict]] = {
    "Patient": {
        "_id":        {"orm_path": "id",                     "type": "token"},
        "name":       {"orm_path": "last_name",              "type": "string", "also": "first_name"},
        "family":     {"orm_path": "last_name",              "type": "string"},
        "given":      {"orm_path": "first_name",             "type": "string"},
        "birthdate":  {"orm_path": "date_of_birth",          "type": "date"},
        "gender":     {"orm_path": "sex",                    "type": "token"},
        "identifier": {"orm_path": "medical_record_number",  "type": "token"},
        "death-date": {"orm_path": "date_of_death",          "type": "date"},
    },
    "Condition": {
        "_id":              {"orm_path": "id",                "type": "token"},
        "patient":          {"orm_path": "patient_id",        "type": "reference"},
        "category":         {"orm_path": "_virtual_category", "type": "token"},
        "clinical-status":  {"orm_path": "status",            "type": "token"},
        "code":             {"orm_path": "problem_name",      "type": "token"},
        "onset-date":       {"orm_path": "date_of_onset",     "type": "date"},
        "abatement-date":   {"orm_path": "date_of_resolution","type": "date"},
        "recorded-date":    {"orm_path": "date_of_diagnosis", "type": "date"},
        "asserted-date":    {"orm_path": "date_of_onset",     "type": "date"},
        "encounter":        {"orm_path": "_virtual_encounter","type": "reference"},
        "_lastUpdated":     {"orm_path": "updated_at",        "type": "date"},
    },
    "Observation": {
        "_id":      {"orm_path": "id",                                   "type": "token"},
        "patient":  {"orm_path": "health_screening__patient_id",         "type": "reference"},
        "category": {"orm_path": "_virtual_category",                    "type": "token"},
        "code":     {"orm_path": "test_name",                            "type": "token"},
        "date":     {"orm_path": "health_screening__screening_date",     "type": "date"},
        "status":   {"orm_path": "_static",                              "type": "token"},
        "_lastUpdated": {"orm_path": "updated_at",                       "type": "date"},
    },
    "Encounter": {
        "_id":     {"orm_path": "id",               "type": "token"},
        "identifier": {"orm_path": "encounter_identifier", "type": "token"},
        "patient": {"orm_path": "patient_id",        "type": "reference"},
        "date":    {"orm_path": "screening_date",    "type": "date"},
        "class":   {"orm_path": "encounter_type",    "type": "token"},
        "type":    {"orm_path": "encounter_type",    "type": "token"},
        "_lastUpdated": {"orm_path": "updated_at",   "type": "date"},
        "status":  {"orm_path": "_static",           "type": "token"},
        "location": {"orm_path": "_virtual_location","type": "reference"},
        "discharge-disposition": {"orm_path": "encounter_disposition", "type": "token"},
    },
    "MedicationRequest": {
        "_id":     {"orm_path": "id",                "type": "token"},
        "patient": {"orm_path": "patient_id",        "type": "reference"},
        "intent":  {"orm_path": "_static_order",     "type": "token"},
        "encounter": {"orm_path": "_virtual_encounter", "type": "reference"},
        "authoredon": {"orm_path": "start_date", "type": "date"},
        "status":  {"orm_path": "dispense_status",   "type": "token"},
    },
    "MedicationDispense": {
        "_id":     {"orm_path": "id",                "type": "token"},
        "patient": {"orm_path": "patient_id",        "type": "reference"},
        "status":  {"orm_path": "dispense_status",   "type": "token"},
        "type":    {"orm_path": "_static_ffp",       "type": "token"},
    },
    "AllergyIntolerance": {
        "_id":             {"orm_path": "id",          "type": "token"},
        "patient":         {"orm_path": "patient_id",  "type": "reference"},
        "clinical-status": {"orm_path": "_static",     "type": "token"},
    },
    "CarePlan": {
        "_id":      {"orm_path": "id",          "type": "token"},
        "patient":  {"orm_path": "patient_id",  "type": "reference"},
        "category": {"orm_path": "_static",     "type": "token"},
        "status":   {"orm_path": "status",      "type": "token"},
    },
    "CareTeam": {
        "_id":     {"orm_path": "id",   "type": "token"},
        "patient": {"orm_path": "id",   "type": "reference"},
        "status":  {"orm_path": "_static", "type": "token"},
    },
    "Coverage": {
        "_id":     {"orm_path": "id",          "type": "token"},
        "patient": {"orm_path": "patient_id",  "type": "reference"},
    },
    "Device": {
        "_id":     {"orm_path": "id",          "type": "token"},
        "patient": {"orm_path": "patient_id",  "type": "reference"},
        "status":  {"orm_path": "status",      "type": "token"},
        "type":    {"orm_path": "device_name", "type": "token"},
    },
    "DiagnosticReport": {
        "_id":      {"orm_path": "id",                                   "type": "token"},
        "patient":  {"orm_path": "health_screening__patient_id",         "type": "reference"},
        "category": {"orm_path": "_static",                              "type": "token"},
        "code":     {"orm_path": "test_name",                            "type": "token"},
        "date":     {"orm_path": "health_screening__screening_date",     "type": "date"},
        "status":   {"orm_path": "_static",                              "type": "token"},
        "_lastUpdated": {"orm_path": "updated_at",                       "type": "date"},
    },
    "DocumentReference": {
        "_id":      {"orm_path": "id",             "type": "token"},
        "patient":  {"orm_path": "patient_id",     "type": "reference"},
        "category": {"orm_path": "_static",        "type": "token"},
        "type":     {"orm_path": "note_type",      "type": "token"},
        "date":     {"orm_path": "document_date",  "type": "date"},
        "period":   {"orm_path": "document_date",  "type": "date"},
        "status":   {"orm_path": "_static",        "type": "token"},
    },
    "Goal": {
        "_id":              {"orm_path": "id",          "type": "token"},
        "patient":          {"orm_path": "patient_id",  "type": "reference"},
        "lifecycle-status": {"orm_path": "_static",     "type": "token"},
    },
    "Immunization": {
        "_id":     {"orm_path": "id",          "type": "token"},
        "patient": {"orm_path": "patient_id",  "type": "reference"},
        "status":  {"orm_path": "_static",     "type": "token"},
        "date":    {"orm_path": "administration_date", "type": "date"},
    },
    "Location": {
        "_id":  {"orm_path": "id",    "type": "token"},
        "name": {"orm_path": "name",  "type": "string"},
        "address": {"orm_path": "address", "type": "string"},
        "address-city": {"orm_path": "address_city", "type": "string"},
        "address-state": {"orm_path": "address_state", "type": "string"},
        "address-postalcode": {"orm_path": "address_postalcode", "type": "string"},
    },
    "Medication": {
        "_id": {"orm_path": "id", "type": "token"},
    },
    "Organization": {
        "_id":  {"orm_path": "id",    "type": "token"},
        "name": {"orm_path": "name",  "type": "string"},
        "address": {"orm_path": "address", "type": "string"},
    },
    "Practitioner": {
        "_id":        {"orm_path": "id",   "type": "token"},
        "name":       {"orm_path": "name", "type": "string"},
        "identifier": {"orm_path": "npi",  "type": "token"},
    },
    "PractitionerRole": {
        "_id":          {"orm_path": "id",            "type": "token"},
        "practitioner": {"orm_path": "practitioner",  "type": "reference"},
        "specialty":    {"orm_path": "specialty",     "type": "token"},
    },
    "Procedure": {
        "_id":     {"orm_path": "id",               "type": "token"},
        "patient": {"orm_path": "patient_id",        "type": "reference"},
        "date":    {"orm_path": "performance_time",  "type": "date"},
        "code":    {"orm_path": "procedure_name",    "type": "token"},
        "status":  {"orm_path": "_static",           "type": "token"},
    },
    "Provenance": {
        "_id":    {"orm_path": "id",      "type": "token"},
        "target": {"orm_path": "target",  "type": "reference"},
    },
    "RiskAssessment": {
        "_id":     {"orm_path": "resource_id", "type": "token"},
        "patient": {"orm_path": "local_mappings__patient_id", "type": "reference"},
        "subject": {"orm_path": "local_mappings__patient_id", "type": "reference"},
    },
    "RelatedPerson": {
        "_id":     {"orm_path": "id",  "type": "token"},
        "patient": {"orm_path": "id",  "type": "reference"},
    },
    "ServiceRequest": {
        "_id":      {"orm_path": "id",          "type": "token"},
        "patient":  {"orm_path": "patient_id",  "type": "reference"},
        "status":   {"orm_path": "_static",     "type": "token"},
        "category": {"orm_path": "order_type",  "type": "token"},
        "code":     {"orm_path": "order_detail", "type": "token"},
        "authored": {"orm_path": "order_date",   "type": "date"},
    },
    "Specimen": {
        "_id":     {"orm_path": "id",                            "type": "token"},
        "patient": {"orm_path": "health_screening__patient_id",  "type": "reference"},
    },
    "Media": {
        "_id": {"orm_path": "id", "type": "token"},
    },
}


def get_params_for(resource_type: str) -> dict[str, dict]:
    """Return the search parameter definitions for a resource type."""
    return FHIR_SEARCH_PARAMETERS.get(resource_type, {})


def supported_resource_types() -> list[str]:
    """Return all resource types with registered search parameters."""
    return sorted(FHIR_SEARCH_PARAMETERS.keys())
