# US Core STU7 Must Support Catalog (Inferno Metadata Source)

Source: `tmp_us_core_test_kit/lib/us_core_test_kit/generated/v7.0.0/*/metadata.yml`

## allergy_intolerance (`AllergyIntolerance`)
- Title: AllergyIntolerance
- Must Support count: 6
- Must Support elements: clinicalStatus, verificationStatus, code, patient, reaction, reaction.manifestation

## average_blood_pressure (`Observation`)
- Title: Observation Average Blood Pressure
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, code.coding.code, subject, effectivePeriod, component, component.valueQuantity, component.dataAbsentReason, component:systolic.code, component:systolic.value[x], component:diastolic.code, component:diastolic.value[x]

## blood_pressure (`Observation`)
- Title: Observation Blood Pressure
- Must Support count: 26
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, component, component.code, component.valueQuantity, component.dataAbsentReason, component:systolic.code, component:systolic.valueQuantity, component:systolic.valueQuantity.value, component:systolic.valueQuantity.unit, component:systolic.valueQuantity.system, component:systolic.valueQuantity.code, component:systolic.dataAbsentReason, component:diastolic.code, component:diastolic.valueQuantity, component:diastolic.valueQuantity.value, component:diastolic.valueQuantity.unit, component:diastolic.valueQuantity.system, component:diastolic.valueQuantity.code, component:diastolic.dataAbsentReason

## bmi (`Observation`)
- Title: Observation BMI
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## body_height (`Observation`)
- Title: Observation Body Height
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## body_temperature (`Observation`)
- Title: Observation Body Temperature
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## body_weight (`Observation`)
- Title: Observation Body Weight
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## care_experience_preference (`Observation`)
- Title: Observation Care Experience Preference
- Must Support count: 7
- Must Support elements: status, category, code.coding.code, subject, effectiveDateTime, valueString, valueCodeableConcept

## care_plan (`CarePlan`)
- Title: CarePlan
- Must Support count: 7
- Must Support elements: text, text.status, text.div, status, intent, category, subject

## care_team (`CareTeam`)
- Title: CareTeam
- Must Support count: 5
- Must Support elements: status, subject, participant, participant.role, participant.member

## condition_encounter_diagnosis (`Condition`)
- Title: Condition Encounter Diagnosis
- Must Support count: 6
- Must Support elements: category, code, subject, encounter, abatementDateTime, recordedDate

## condition_problems_health_concerns (`Condition`)
- Title: Condition Problems and Health Concerns
- Must Support count: 10
- Must Support elements: meta, meta.lastUpdated, clinicalStatus, verificationStatus, category, code, subject, onsetDateTime, abatementDateTime, recordedDate

## coverage (`Coverage`)
- Title: Coverage
- Must Support count: 13
- Must Support elements: identifier, identifier:memberid.type, status, type, subscriberId, beneficiary, relationship, period, payor, class, class:group.value, class:plan.value, class:plan.name

## device (`Device`)
- Title: Implantable Device
- Must Support count: 10
- Must Support elements: udiCarrier, udiCarrier.deviceIdentifier, udiCarrier.carrierHRF, distinctIdentifier, manufactureDate, expirationDate, lotNumber, serialNumber, type, patient

## diagnostic_report_lab (`DiagnosticReport`)
- Title: DiagnosticReport for Laboratory Results Reporting
- Must Support count: 11
- Must Support elements: meta, meta.lastUpdated, status, category, code, subject, encounter, effectiveDateTime, issued, performer, result

## diagnostic_report_note (`DiagnosticReport`)
- Title: DiagnosticReport for Report and Note Exchange
- Must Support count: 12
- Must Support elements: status, category, code, subject, encounter, effectiveDateTime, issued, performer, result, media, media.link, presentedForm

## document_reference (`DocumentReference`)
- Title: DocumentReference
- Must Support count: 16
- Must Support elements: identifier, status, type, category, subject, date, author, content, content.attachment, content.attachment.contentType, content.attachment.data, content.attachment.url, content.format, context, context.encounter, context.period

## encounter (`Encounter`)
- Title: Encounter
- Must Support count: 21
- Must Support elements: meta, meta.lastUpdated, identifier, identifier.system, identifier.value, status, class, type, subject, participant, participant.type, participant.period, participant.individual, period, reasonCode, reasonReference, hospitalization, hospitalization.dischargeDisposition, location, location.location, serviceProvider

## goal (`Goal`)
- Title: Goal
- Must Support count: 6
- Must Support elements: lifecycleStatus, description, subject, startDate, target, target.dueDate

## head_circumference (`Observation`)
- Title: Observation Head Circumference
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## head_circumference_percentile (`Observation`)
- Title: Observation Pediatric Head Occipital Frontal Circumference Percentile
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## heart_rate (`Observation`)
- Title: Observation Heart Rate
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## immunization (`Immunization`)
- Title: Immunization
- Must Support count: 8
- Must Support elements: status, statusReason, vaccineCode, patient, encounter, occurrenceDateTime, primarySource, location

## location (`Location`)
- Title: Location
- Must Support count: 11
- Must Support elements: identifier, status, name, type, telecom, address, address.line, address.city, address.state, address.postalCode, managingOrganization

## medication_dispense (`MedicationDispense`)
- Title: MedicationDispense
- Must Support count: 15
- Must Support elements: status, medication[x], subject, context, performer, performer.actor, authorizingPrescription, type, quantity, whenHandedOver, dosageInstruction, dosageInstruction.text, dosageInstruction.timing, dosageInstruction.doseAndRate, dosageInstruction.doseAndRate.doseQuantity

## medication_request (`MedicationRequest`)
- Title: MedicationRequest
- Must Support count: 20
- Must Support elements: status, intent, category, reportedBoolean, reportedReference, medication[x], subject, encounter, authoredOn, requester, reasonCode, reasonReference, dosageInstruction, dosageInstruction.text, dosageInstruction.timing, dosageInstruction.doseAndRate, dosageInstruction.doseAndRate.doseQuantity, dispenseRequest, dispenseRequest.numberOfRepeatsAllowed, dispenseRequest.quantity

## observation_clinical_result (`Observation`)
- Title: Observation Clinical Result
- Must Support count: 9
- Must Support elements: status, category, code, subject, encounter, effectiveDateTime, valueQuantity, valueCodeableConcept, valueString

## observation_lab (`Observation`)
- Title: Observation Laboratory Result
- Must Support count: 14
- Must Support elements: meta, meta.lastUpdated, status, category, code, subject, encounter, effectiveDateTime, valueQuantity, valueCodeableConcept, valueString, interpretation, specimen, referenceRange

## observation_occupation (`Observation`)
- Title: Observation Occupation
- Must Support count: 7
- Must Support elements: status, category, code.coding.code, subject, component, component:industry.code, component:industry.value[x]

## observation_pregnancyintent (`Observation`)
- Title: Observation Pregnancy Intent
- Must Support count: 4
- Must Support elements: status, category, code.coding.code, subject

## observation_pregnancystatus (`Observation`)
- Title: Observation Pregnancy Status
- Must Support count: 4
- Must Support elements: status, category, code.coding.code, subject

## observation_screening_assessment (`Observation`)
- Title: Observation Screening Assessment
- Must Support count: 11
- Must Support elements: status, category, code, subject, effectiveDateTime, performer, valueQuantity, valueCodeableConcept, valueString, hasMember, derivedFrom

## observation_sexual_orientation (`Observation`)
- Title: Observation Sexual Orientation
- Must Support count: 4
- Must Support elements: status, code.coding.code, subject, effectiveDateTime

## organization (`Organization`)
- Title: Organization
- Must Support count: 14
- Must Support elements: identifier, identifier.system, identifier.value, active, name, telecom, telecom.system, telecom.value, address, address.line, address.city, address.state, address.postalCode, address.country

## patient (`Patient`)
- Title: Patient
- Must Support count: 25
- Must Support elements: identifier, identifier.system, identifier.value, name, name.use, name.family, name.given, name.suffix, name.period.end, telecom, telecom.system, telecom.value, telecom.use, gender, birthDate, deceasedDateTime, address, address.use, address.line, address.city, address.state, address.postalCode, address.period.end, communication, communication.language

## pediatric_bmi_for_age (`Observation`)
- Title: Observation Pediatric BMI for Age
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## pediatric_weight_for_height (`Observation`)
- Title: Observation Pediatric Weight for Height
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## practitioner (`Practitioner`)
- Title: Practitioner
- Must Support count: 8
- Must Support elements: identifier, identifier.system, identifier.value, name, name.family, telecom, telecom.system, telecom.value

## practitioner_role (`PractitionerRole`)
- Title: PractitionerRole
- Must Support count: 9
- Must Support elements: practitioner, organization, code, specialty, location, telecom, telecom.system, telecom.value, endpoint

## procedure (`Procedure`)
- Title: Procedure
- Must Support count: 8
- Must Support elements: basedOn, status, code, subject, encounter, performedDateTime, reasonCode, reasonReference

## provenance (`Provenance`)
- Title: Provenance
- Must Support count: 9
- Must Support elements: target, target.reference, recorded, agent, agent.type, agent.who, agent.onBehalfOf, agent:ProvenanceAuthor.type, agent:ProvenanceTransmitter.type

## pulse_oximetry (`Observation`)
- Title: Observation Pulse Oximetry
- Must Support count: 29
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code, code.coding, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code, component, component.code, component.valueQuantity, component:FlowRate.code, component:FlowRate.valueQuantity, component:FlowRate.valueQuantity.value, component:FlowRate.valueQuantity.unit, component:FlowRate.valueQuantity.system, component:FlowRate.valueQuantity.code, component:Concentration.code, component:Concentration.valueQuantity, component:Concentration.valueQuantity.value, component:Concentration.valueQuantity.unit, component:Concentration.valueQuantity.system, component:Concentration.valueQuantity.code

## questionnaire_response (`QuestionnaireResponse`)
- Title: QuestionnaireResponse
- Must Support count: 15
- Must Support elements: identifier, questionnaire, status, subject, authored, author, item, item.linkId, item.text, item.answer, item.answer.valueDecimal, item.answer.valueString, item.answer.valueCoding, item.answer.item, item.item

## related_person (`RelatedPerson`)
- Title: RelatedPerson
- Must Support count: 6
- Must Support elements: active, patient, relationship, name, telecom, address

## respiratory_rate (`Observation`)
- Title: Observation Respiratory Rate
- Must Support count: 13
- Must Support elements: status, category, category:VSCat.coding, category:VSCat.coding.system, category:VSCat.coding.code, code.coding.code, subject, effectiveDateTime, valueQuantity, valueQuantity:valueQuantity.value, valueQuantity:valueQuantity.unit, valueQuantity:valueQuantity.system, valueQuantity:valueQuantity.code

## service_request (`ServiceRequest`)
- Title: ServiceRequest
- Must Support count: 11
- Must Support elements: status, intent, category, code, subject, encounter, occurrencePeriod, authoredOn, requester, reasonCode, reasonReference

## simple_observation (`Observation`)
- Title: Observation Simple
- Must Support count: 11
- Must Support elements: status, category, code, subject, effectiveDateTime, performer, valueQuantity, valueCodeableConcept, valueString, valueBoolean, derivedFrom

## smokingstatus (`Observation`)
- Title: Observation Smoking Status
- Must Support count: 6
- Must Support elements: status, category, code, subject, effective[x], value[x]

## specimen (`Specimen`)
- Title: Specimen
- Must Support count: 7
- Must Support elements: identifier, accessionIdentifier, type, subject, collection, collection.bodySite, condition

## treatment_intervention_preference (`Observation`)
- Title: Observation Treatment Intervention Preference
- Must Support count: 7
- Must Support elements: status, category, code.coding.code, subject, effectiveDateTime, valueString, valueCodeableConcept

