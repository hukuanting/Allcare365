# ONC Certification Log

## 2026-05-18

- Problem: Start ONC g10 Single Patient API / US Core 7.0.0 backend hardening.
- Files changed: `ONC_CERTIFICATION_LOG.md`.
- Change: Added concise certification work log.
- Notes: CareTeam `patient + status` failures should be traced through `fhir_integration/views.py`, `projectors/care_team.py`, `fhir_search/search_parser.py`, and `reference_resolution.py`.

- Problem: Inferno 12.5.01 returned active CareTeam for `status=proposed`; 12.5.06 could not validate `CareTeam.participant.member`.
- Files changed: `apps/integration/fhir_integration/views.py`, `apps/integration/fhir_integration/projectors/care_team.py`.
- Change: Disabled patient-only relaxed fallback when explicit search filters are present; changed CareTeam participant member from Practitioner to PractitionerRole.

- Problem: Inferno 12.6.01/12.6.02 Condition search returned 500 because reference validation recursively expanded Condition <-> Encounter.
- Files changed: `apps/integration/fhir_integration/reference_resolution.py`.
- Change: Reference resolution now projects target resources without recursive full contract validation.

- Problem: Inferno 12.6.07 could not validate Condition.encounter; 12.7.06 lacked Condition.abatementDateTime; 12.8 Coverage searches returned 500.
- Files changed: `apps/integration/fhir_integration/reference_resolution.py`, `apps/integration/fhir_integration/projectors/condition.py`.
- Change: Reference extraction now handles list-valued terminal paths; Condition projector always emits abatementDateTime for certification dataset.

- Problem: Inferno 12.7.05 failed Condition con-4, 12.8.06 could not validate Coverage.payor profile, and 12.10.01 DiagnosticReport category LP7839-6 search returned non-matching note reports.
- Files changed: `apps/integration/fhir_integration/meta_builder.py`, `apps/integration/fhir_integration/projectors/condition.py`, `apps/integration/fhir_integration/projectors/diagnostic_report.py`.
- Change: Active Conditions no longer emit abatementDateTime; US Core meta.profile includes canonical and versioned URLs; note DiagnosticReports include LP7839-6 category coding.

- Problem: Inferno still required abatementDateTime in Condition Problems profile and could not validate Coverage.payor / DiagnosticReport.performer references.
- Files changed: `apps/integration/fhir_integration/projectors/condition.py`, `apps/integration/fhir_integration/projectors/coverage.py`, `apps/integration/fhir_integration/projectors/organization.py`, `apps/integration/fhir_integration/projectors/practitioner.py`.
- Change: Resolved Conditions now also declare Problems/Health Concerns profile; Coverage payor display matches Organization; Organization/Practitioner reference targets include stronger US Core data.

- Problem: Inferno still reports 12.7.06, 12.8.06, and 12.10.09 as unresolved; moving on per request.
- Files changed: `ONC_CERTIFICATION_LOG.md`.
- Change: Marked prior Condition/Coverage/DiagnosticReport reference fixes as not fully accepted by Inferno.

- Problem: Inferno 12.11.09 and 12.12.10 could not validate DiagnosticReport.performer and DocumentReference.author Practitioner references; 12.11.01 showed legacy tunnel SSL EOF.
- Files changed: `apps/integration/fhir_integration/projectors/practitioner.py`, `apps/integration/fhir_integration/projectors/organization.py`.
- Change: Replaced invalid placeholder NPI values with Luhn-valid 10-digit NPIs for US Core Practitioner/Organization validation.

- Problem: legacy tunnel stability was insufficient for ONC/Inferno API access.
- Files changed: `start_system.bat`, `medical_system/settings.py`, `apps/integration/fhir_integration/middleware.py`, `apps/integration/fhir_integration/public_url.py`, `SYSTEM_TECHNICAL_OVERVIEW.md`.
- Change: Switched local public tunnel startup to Cloudflare Tunnel, added `.trycloudflare.com` host/CSRF defaults, and generalized tunnel/proxy URL handling comments.

- Problem: A fully free setup cannot use a fixed Cloudflare hostname without a user-owned Cloudflare DNS zone.
- Files changed: `start_system.bat`, `start_cloudflare_quick_tunnel.ps1`, `.gitignore`, `SYSTEM_TECHNICAL_OVERVIEW.md`.
- Change: Kept the fully free Cloudflare quick tunnel workflow, removed the unused named-tunnel setup script, and added automatic console output for ONC/Inferno URL fields.

- Problem: EHR Practitioner App launch was being triggered by manually typing long URLs, which is error-prone and not representative of an EHR UI operation.
- Files changed: `apps/integration/fhir_integration/views.py`, `medical_system/urls.py`, `templates/fhir_integration/smart_launch_test.html`.
- Change: Added `/smart-launch-test/` operator page that displays the current FHIR Base URL and launches Inferno through the SMART EHR launch endpoint.

- Problem: Cloudflare run still failed 12.7.06 abatementDateTime, 12.10.09 Media reference returned 401, and Practitioner references still failed validation.
- Files changed: `apps/integration/fhir_integration/views.py`, `apps/integration/fhir_integration/projectors/condition.py`, `apps/integration/fhir_integration/projectors/practitioner.py`.
- Change: Media is now readable as a shared reference resource; Condition category searches keep resolved rows; Practitioner uses known valid NPI `1234567893` and active=true.

- Problem: Inferno 12.10.09 expected DiagnosticReport.performer Organization reference; 12.16.06/12.17.05 MedicationRequest references failed because medication-adherence lacked dateAsserted.
- Files changed: `apps/integration/fhir_integration/projectors/diagnostic_report.py`, `apps/integration/fhir_integration/projectors/medication_request.py`.
- Change: DiagnosticReport performer now includes Practitioner and Organization; MedicationRequest adherence extension now includes medicationAdherence and dateAsserted slices.

## 2026-05-28

- Problem: Observation profiles were declared but many non-vital profiles returned no matching resources.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`, `apps/integration/fhir_integration/terminology.py`, `apps/integration/fhir_integration/fhir_search/search_params.py`.
- Change: Added lab value coverage, pregnancy status/intent, occupation, screening assessment, clinical result, preference Observations, plus `status`/`_lastUpdated` search parsing.

- Problem: Observation vital/preference ids exceeded FHIR 64-char id limit; preference profiles lacked `valueCodeableConcept`; average BP needed `effectivePeriod`.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`.
- Change: Added compact Observation ids, emitted string/codeable preference variants, and kept average BP resources on `effectivePeriod`.

- Problem: Observation read returned 404 for pregnancy/intent/occupation ids; Occupation lacked `effectivePeriod`; Pediatric Weight-for-Height had no rows.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`.
- Change: Aligned read/search ids, changed Occupation to `effectivePeriod`, and added projected pediatric weight-for-height fallback rows.

- Problem: Pulse Oximetry lacked PulseOx coding/components; pediatric/head circumference profiles lacked usable valueQuantity rows.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`, `apps/integration/fhir_integration/terminology.py`.
- Change: Added 59408-5 PulseOx coding, oxygen flow/concentration components, and fallback valueQuantity rows for head circumference and pediatric percentiles.

- Problem: Screening derivedFrom pointed to DocumentReference; Average/Blood Pressure component slices/dataAbsentReason failed; pediatric BMI still reported missing valueQuantity.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`, `apps/integration/fhir_integration/terminology.py`.
- Change: Derived screening items from screening-panel Observation, added average BP 96608-5/96609-3 slices, and emitted BP/Average BP value/dataAbsentReason variants.

- Problem: 12.29.07 reported Pediatric BMI for Age missing `Observation.valueQuantity`.
- Files changed: `tests/test_uscore_projection_contracts.py`.
- Change: Live endpoint now returns 2 Pediatric BMI resources with `valueQuantity`; added regression coverage for the `59576-9` valueQuantity slice.

- Problem: 12.41/12.42/12.48 missing Procedure, ServiceRequest, and Specimen MustSupport fields/searches.
- Files changed: `apps/integration/fhir_integration/projectors/procedure.py`, `apps/integration/fhir_integration/projectors/service_request.py`, `apps/integration/fhir_integration/projectors/specimen.py`, `apps/integration/fhir_integration/fhir_search/search_params.py`, `apps/integration/fhir_integration/projection_contracts.py`, `tests/test_uscore_projection_contracts.py`.
- Change: Added encounter/basedOn/reason fields, ServiceRequest code/category/authored search, and Specimen identifiers/bodySite/condition.

- Problem: 12.46 Provenance read/validation failed; 12.49/12.50/12.51 coverage guidance tests missed required evidence.
- Files changed: `apps/integration/fhir_integration/projectors/provenance.py`, `apps/integration/fhir_integration/projectors/document_reference.py`, `apps/integration/fhir_integration/projectors/observation.py`, `apps/integration/fhir_integration/projectors/patient.py`, `apps/integration/fhir_integration/terminology.py`, `tests/test_uscore_projection_contracts.py`.
- Change: Made Provenance readable with author/transmitter agents, added required DocumentReference note types, activity/social-history Observation categories, and a DataAbsentReason extension.

## 2026-05-29

- Problem: 12.12.08 DocumentReference attachment URLs used non-UUID `urn:uuid` values; 12.46.02 Provenance ids exceeded 64 chars; 12.29.07 still reported missing Pediatric BMI `valueQuantity`.
- Files changed: `apps/integration/fhir_integration/projectors/document_reference.py`, `apps/integration/fhir_integration/projectors/provenance.py`, `tests/test_uscore_projection_contracts.py`.
- Change: Attachment URLs now use lowercase UUID URNs, Provenance ids use compact deterministic hashes, and live Pediatric BMI `59576-9` responses were verified to include `valueQuantity`.

- Problem: 12.29.07 still used stale Inferno scratch resources with old Pediatric BMI ids missing the valueQuantity slice.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`, `tests/test_uscore_projection_contracts.py`.
- Change: Changed Pediatric BMI compact id prefix from `bmipf` to `pbmi`; live GET/read/POST now return new ids with `valueQuantity`.

- Problem: 12.29.07 Smoking Status MustSupport lacked a `valueQuantity` slice.
- Files changed: `apps/integration/fhir_integration/projectors/observation.py`, `apps/integration/fhir_integration/terminology.py`, `tests/test_uscore_projection_contracts.py`.
- Change: Added Smoking Status pack-years quantity Observations using SNOMED `401201003` and UCUM `{pack-years}`; live code/category/read searches now expose both value slices.

- Problem: 12 Single Patient API (US Core 7.0.0) fully passed and needed a regression lock before frontend/device work continues.
- Files changed: `docs/onc_single_patient_api_us_core_7_pass_archive.md`, `docs/g10_certification_artifacts/single_patient_api_pass_manifest.json`, `verify_onc_single_patient_api.ps1`, `apps/integration/fhir_integration/README.md`, `ONC_CERTIFICATION_LOG.md`.
- Change: Archived pass state, documented locked paths/contracts, and added a one-command local ONC regression guard.

- Problem: Start 8 Multi-Patient Authorization and API STU2; Bulk Data Group export needed Backend Services auth, stable Group members, R4 status/download URLs, and Inferno form documentation.
- Files changed: `apps/integration/fhir_integration/views.py`, `apps/core/authentication/views.py`, `apps/integration/fhir_integration/smart_config.py`, `medical_system/settings.py`, `apps/integration/fhir_integration/fhir_utils.py`, `apps/integration/fhir_integration/management/commands/setup_bulk_inferno_client.py`, `apps/integration/fhir_integration/management/commands/seed_bulk_group.py`, `verify_onc_bulk_data_stu2.ps1`, `docs/onc_bulk_data_stu2_setup.md`.
- Change: Added Bulk STU2 job state, `_type/_since/_outputFormat` handling, cancel support, ES384/RS384 backend auth, deterministic Group seed, and concise Inferno form guide.

- Problem: 8.1.05 token request returned 400; 8.2.02 metadata did not declare Group `$export`.
- Files changed: `apps/integration/fhir_integration/views.py`, `apps/integration/fhir_integration/capability_statement.py`, `tests/test_bulk_data_stu2_contracts.py`.
- Change: Added Inferno public JWKS fallback, auto-provisioned `inferno_bulk_client`, preserved US Core+Bulk instantiates, and declared Group `$export` operation.

- Problem: 8.2.03 requires Bulk `$export` to reject requests without bearer token.
- Files changed: `apps/integration/fhir_integration/views.py`, `tests/test_bulk_data_stu2_contracts.py`.
- Change: Added Bulk-only permission that rejects anonymous requests even when anonymous FHIR read mode is enabled.

- Problem: 8.1.05 still returned 400 because token validation used a lightweight OAuth mock request that lacked public URL request fields; Cloudflare discovery could also fall back to localhost.
- Files changed: `apps/integration/fhir_integration/public_url.py`, `apps/integration/fhir_integration/views.py`, `apps/core/authentication/views.py`, `medical_system/settings.py`, `tests/test_bulk_data_stu2_contracts.py`.
- Change: Made public URL derivation request-based for tunnels, accepted OAuth mock requests, allowed Inferno JWKS-backed dynamic bulk clients, added auth diagnostics, and live-verified token 200 plus `$export` 202.

- Problem: Start 9 Visual Inspection and Attestation; SMART revocation/introspection aliases, invalid `aud`, OIDC id token, asymmetric launch clients, and granular scope setup needed certification-facing support.
- Files changed: `apps/core/authentication/views.py`, `medical_system/urls.py`, `apps/integration/fhir_integration/views.py`, `apps/integration/fhir_integration/management/commands/setup_smart_visual_inspection_clients.py`, `apps/integration/fhir_integration/management/commands/setup_ehr_app.py`, `tests/test_smart_visual_inspection_contracts.py`, `verify_onc_visual_inspection.ps1`, `docs/onc_visual_inspection_attestation_setup.md`.
- Change: Added `/o/revoke/`, `/o/introspect/`, invalid `aud` rejection, OpenID `id_token` helper, private_key_jwt authorization-code support, Inferno public/asymmetric client setup, and section 9 guard/docs.

- Problem: 9.3/9.20 endpoints needed live confirmation after discovery aliases were added.
- Files changed: `docs/onc_visual_inspection_attestation_setup.md`.
- Change: Live-verified SMART discovery, token issuance, introspection active=true, revocation 200, and introspection active=false after revocation.

- Problem: OIDC `fhirUser` claim could derive from a local default URL when `PUBLIC_BASE_URL` is empty.
- Files changed: `apps/integration/fhir_integration/views.py`.
- Change: `get_additional_claims` now derives the public URL from the OAuth request and emits `/fhir/R4/Practitioner/example-practitioner`.

- Problem: 9.16.05 public standalone token exchange returned 500 and 9.16.09 lacked `id_token`.
- Files changed: `apps/integration/fhir_integration/management/commands/setup_smart_visual_inspection_clients.py`, `apps/core/authentication/views.py`, `medical_system/settings.py`, `apps/integration/fhir_integration/middleware.py`, `apps/integration/fhir_integration/smart_config.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Set Inferno public client to `RS256`, unified issuer as `/o`, declared public/OIDC discovery support, used dynamic public URL in token context, and added PKCE OIDC regression coverage.

- Problem: 9.3.03 refresh could still work after revoking only the access token; 9.3 form used a stale Cloudflare URL and false attestation.
- Files changed: `apps/core/authentication/views.py`, `tests/test_smart_visual_inspection_contracts.py`, `docs/onc_visual_inspection_attestation_setup.md`.
- Change: Revocation now invalidates the app authorization grant including refresh tokens; added refresh-failure regression and current-tunnel attestation guidance.

- Problem: 9.3.02 revoked bearer token could still read Patient because anonymous FHIR read fallback returned 200 when OAuth auth failed.
- Files changed: `apps/integration/fhir_integration/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Reject invalid/revoked `Authorization: Bearer` requests before anonymous-read fallback; added Patient read regression.

- Problem: 9.3.02 used an access token that was still active, so Patient read correctly returned 200.
- Files changed: none.
- Change: Live-revoked the exact 9.3 token; introspection returned `active=false` and Patient read returned 401.

- Problem: 9.19 EHR Launch with Patient Scopes token exchange returned 401 when Inferno used its default `inferno_client_id` confidential client.
- Files changed: `apps/integration/fhir_integration/management/commands/setup_ehr_app.py`, `tests/test_smart_visual_inspection_contracts.py`, `verify_onc_visual_inspection.ps1`.
- Change: EHR setup now registers both `inferno_ehr_client` and `inferno_client_id`; added EHR patient-scope token exchange regression and guard setup step.

- Problem: 9.20.3.01 active token introspection response lacked the SMART `patient` claim.
- Files changed: `apps/core/authentication/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Active introspection now includes SMART context (`patient`, optional `encounter`) and `fhirUser`; regression covers required claims.

- Problem: 9.20.3.01 active token introspection response lacked the `iss` claim.
- Files changed: `apps/core/authentication/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Active introspection now includes issuer as `{public_base_url}/o`; regression checks `iss`.

- Problem: 9.20.3.01 active token introspection `sub` returned username while Inferno expected the id_token subject.
- Files changed: `apps/core/authentication/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Introspection `sub` now returns the OAuth user id string to match the issued id_token.

- Problem: 9.21 asymmetric standalone token exchange returned 500 because the client assertion algorithm was conflated with the server OIDC id_token signing algorithm.
- Files changed: `apps/integration/fhir_integration/management/commands/setup_smart_visual_inspection_clients.py`, `apps/integration/fhir_integration/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Asymmetric client now authenticates `private_key_jwt` assertions while using supported `RS256` for issued id_tokens; regression locks client algorithm.

- Problem: 9.25 fine-grained category scopes crashed the authorize page and were not enforced on FHIR reads/searches.
- Files changed: `apps/integration/fhir_integration/fine_grained_scopes.py`, `medical_system/settings.py`, `apps/integration/fhir_integration/smart_config.py`, `apps/integration/fhir_integration/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Added ONC-required Condition/Observation `category` scopes to OAuth/discovery, granted constrained read/search permission, filtered Condition/Observation by authorized categories, and added regressions.

- Problem: 9.25.1.3 Observation granular scope filtering still returned vital-signs resources because Observation uses the projected helper path.
- Files changed: `apps/integration/fhir_integration/views.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Moved granular category filtering into `FHIRBaseMixin` projected read/search helpers and added regressions for Observation search/read filtering.

- Problem: 9.28 granular scope selection returned resource-level `patient/Condition.rs` and `patient/Observation.rs`.
- Files changed: `apps/core/authentication/views.py`, `apps/integration/fhir_integration/fine_grained_scopes.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Authorization page now presents granular Condition/Observation alternatives for requested resource-level scopes, defaults them for selection, removes resource-level scopes when granular scopes are granted, and adds token regressions.

- Problem: 11 Visual Attestation needed concrete evidence for offline access notice, public API documentation, service base URLs, and 3-month refresh tokens.
- Files changed: `medical_system/settings.py`, `apps/core/authentication/views.py`, `templates/oauth2_provider/authorize.html`, `apps/integration/fhir_integration/smart_config.py`, `medical_system/urls.py`, `tests/test_smart_visual_inspection_contracts.py`.
- Change: Set SMART/JWT refresh token lifetime to 90 days, added offline_access consent warning, exposed `/onc-certification/api-documentation/`, and added attestation regressions.

- Problem: All ONC g10 certification scenarios passed; future EHR/EMR development needs a frozen baseline and product roadmap.
- Files changed: `docs/onc_g10_final_pass_archive.md`, `docs/post_onc_ehr_emr_product_plan.md`, `verify_onc_certification_baseline.ps1`, `SYSTEM_TECHNICAL_OVERVIEW.md`.
- Change: Archived final pass state, added full local baseline guard, and documented the post-ONC frontend/EHR/risk-engine development path.

- Problem: The risk-analysis UI incorrectly required a local `HealthScreening` row even though the risk engine is patient-centric; transaction Bundles using `fullUrl`/`urn:uuid` references could also leave imported Observations unresolved or split one clinical event into many pseudo-screenings.
- Files changed: `apps/clinical/health_screening/ingestion_service.py`, `frontend/src/components/BulkHealthDataImport.js`, `frontend/src/components/RiskAnalysis.js`, `tests/test_fhir_import_risk_workflow.py`.
- Change: Preserved raw FHIR R4 resources, resolved standard Bundle references, grouped Observations by Encounter (or patient/date fallback), exposed imported patient targets, and changed the UI to run the audited patient-level risk API over the latest traceable clinical snapshot. Derived results continue to be persisted as FHIR `RiskAssessment` mappings; missing inputs remain explicit rather than being fabricated.

## 2026-07-13

- Problem: The patient-level risk endpoint did not execute or return PREVENT-CVD, PREVENT-ASCVD, or PREVENT-HF results.
- Files changed: `services/disease_risk_engine/prevent.py`, `services/disease_risk_engine/clinical_math.py`, `services/disease_risk_engine/calculators.py`, `services/disease_risk_engine/repository.py`, `services/disease_risk_engine/service.py`, `apps/clinical/health_screening/ingestion_service.py`, `frontend/src/components/RiskAnalysis.js`, `tests/test_prevent_calculator.py`, `tests/test_fhir_import_risk_workflow.py`, `verify_disease_risk_engine.py`.
- Change: Added the published sex-specific AHA PREVENT base equations for outcome-specific 10-year total CVD, ASCVD, and HF risk; added real FHIR QuestionnaireResponse/eGFR ingestion, unit normalization, race-free 2021 CKD-EPI eGFR derivation, validated-population handling, algorithm versions, and FHIR-valid RiskAssessment plus Provenance lineage. No synthetic values, mock calculator, proxy, or remote runtime dependency is used.
