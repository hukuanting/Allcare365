# US Core Compliance Checklist

Use this checklist to verify that a FHIR resource generated for Allcare 365 complies with US Core 7.0.0 (ONC g10) requirements.

## Condition Resources
- [ ] Profile set to `http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns`
- [ ] Category includes `problem-list-item` or `health-concern` from `http://hl7.org/fhir/us/core/CodeSystem/condition-category`
- [ ] `clinicalStatus` present and valid
- [ ] `onsetDateTime` present (if known)
- [ ] `recordedDate` present
- [ ] Extension `http://hl7.org/fhir/StructureDefinition/condition-assertedDate` present
- [ ] `abatementDateTime` present if status is resolved

## Observation Resources (Lab)
- [ ] Profile set to `http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab`
- [ ] Status is `final`
- [ ] Category is `laboratory`
- [ ] Code is a valid LOINC code
- [ ] `effectiveDateTime` present
- [ ] `subject` references a US Core Patient

## Patient Resources
- [ ] Profile set to `http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient`
- [ ] `identifier` contains MRN with system
- [ ] Race extension present (OMB category + text)
- [ ] Ethnicity extension present (OMB category + text)
- [ ] Birthsex extension present (M/F/UNK)
- [ ] `telecom` and `address` present with `use` tags
