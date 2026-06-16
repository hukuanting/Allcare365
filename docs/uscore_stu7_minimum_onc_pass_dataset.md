# Minimum ONC-pass Dataset (US Core STU7, Inferno Single Patient)

Status: `LOCK DRAFT`  
Goal: smallest non-optional dataset expected to satisfy Inferno Single Patient profile/search/reference checks.

## 1. Included Resource Scope (Non-Optional)

The minimum dataset includes these resources (at least one instance unless noted):

1. Patient
2. Encounter (>=2)
3. Condition (>=3)
4. Observation (lab + vital/smoking minimums)
5. DiagnosticReport (lab + note)
6. DocumentReference
7. Specimen
8. Coverage
9. Device
10. Immunization
11. MedicationRequest
12. MedicationDispense
13. Procedure
14. ServiceRequest
15. AllergyIntolerance
16. CarePlan
17. CareTeam
18. Goal
19. RelatedPerson
20. Location (singleton)
21. Organization (singleton)
22. Practitioner (singleton)
23. PractitionerRole (singleton)
24. Provenance (projected per target)
25. Media (singleton for `DiagnosticReport.media.link`)

## 2. Minimum Relational Row Counts

Per Golden Patient (single patient id):

- `patients.Patient`: 1
- `health_screening.HealthScreening`: 2
- `health_screening.Problem`: 3
- `health_screening.LaboratoryResults`: 3
- `health_screening.VitalSigns`: 1
- `health_screening.HealthStatusAssessment`: 1
- `health_screening.ClinicalTestResult`: 1
- `patients.PatientDocument`: 2
- `patients.InsuranceData`: 1
- `patients.MedicalDevice`: 1
- `health_screening.Immunization`: 1
- `patients.PatientMedication`: 2
- `health_screening.Procedure`: 1
- `patients.MedicalOrder`: 1
- `patients.PatientAllergy`: 1
- `patients.CarePlan`: 1
- `patients.CareTeamMember`: 1
- `patients.AdvanceDirective`: 1

## 3. Minimum Searchability Contract

For this minimum dataset:

1. All `SHALL` search combos in `search_catalog.json` for included resources must return >=1 matching result.
2. Selected high-risk `SHOULD` combos (date/status/_lastUpdated and category intersections) must also return >=1 result.
3. `_id` read for every referenced resource id must resolve.

## 4. Minimum Reference Integrity Contract

Must hold for every projected response set:

1. `Condition.encounter` references an existing Encounter.
2. `Encounter.reasonReference` references existing Condition(s), including encounter-diagnosis profile path.
3. `Observation.specimen` references existing Specimen.
4. `DiagnosticReport.result` references existing Observation.
5. `DiagnosticReport.media.link` references existing Media.
6. `DocumentReference.author` references existing Practitioner.
7. `Coverage.payor` references existing Organization.
8. `MedicationDispense.authorizingPrescription` references existing MedicationRequest.
9. `MedicationDispense.context` references existing Encounter.

## 5. Out-of-Scope for This Minimum Contract

No expansion into additional optional profiles/resources beyond the listed non-optional set until contract is approved and phase-2 is opened.

