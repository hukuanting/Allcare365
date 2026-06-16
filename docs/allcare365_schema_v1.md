# AllCare365 Database Schema v1

Status: implemented baseline  
Database: PostgreSQL  
ORM: Django migrations  
Last updated: 2026-06-10

## 1. Database Architecture

AllCare365 uses an internal clinical relational schema as the operational source of truth.
FHIR resources are generated through projection and tracked in `fhir_resource_mappings`; the database is not designed as a pure FHIR resource store.

Core design:

- UUID primary keys for product domain tables.
- PostgreSQL JSONB via Django `JSONField` for raw import data, questionnaire answers, disease-risk output, FHIR JSON, and flexible metadata.
- Every patient-related table carries `patient_id` directly or through a required parent.
- Certification-facing FHIR/SMART/Bulk Data code remains isolated under `apps/integration/fhir_integration`.
- Audit logs track create/read/update/delete/export/import/login/disease_risk_assess actions.

## 2. Schema Catalog

### users

Purpose: 產品使用者主檔，連接 Django `auth_user` 與 AllCare365 角色權限。  
Model: `authentication.ProductUser`  
FHIR: `Practitioner`, `Patient`, `RelatedPerson` by role.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| auth_user_id | integer | FK -> auth_user |
| display_name | varchar(200) |  |
| role | varchar(50) | index with status |
| status | varchar(50) | index with role |
| organization_name | varchar(200) | index |
| metadata_json | jsonb |  |
| created_at / updated_at | timestamptz |  |

### patients

Purpose: 病患主檔，保存 EHR/EMR 人口學資料與來源系統識別。  
Model: `patients.Patient`  
FHIR: `Patient`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| first_name / last_name / middle_name | varchar |  |
| date_of_birth / date_of_death | date |  |
| sex / race / ethnicity / preferred_language | varchar |  |
| phone_number / email_address | varchar |  |
| medical_record_number | varchar(50) | index |
| status | varchar(20) | index |
| source_system / source_record_id | varchar | composite index |
| last_imported_at | timestamptz |  |
| metadata_json | jsonb |  |
| created_at / updated_at | timestamptz |  |

### practitioners

Purpose: 醫師與醫事人員主檔。  
Model: `patients.Practitioner`  
FHIR: `Practitioner`, `PractitionerRole`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| user_id | integer | FK -> auth_user, nullable |
| organization_id | uuid | FK -> organizations |
| identifier / npi / license_number | varchar | indexes on identifier, npi |
| first_name / last_name / specialty | varchar |  |
| phone / email / status | varchar | status index |
| metadata_json | jsonb |  |
| created_at / updated_at | timestamptz |  |

### patient_practitioner_links

Purpose: 醫病關聯與資料存取授權。  
Model: `patients.PatientPractitionerLink`  
FHIR: `CareTeam`, `Consent`, `PractitionerRole`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, indexed with status |
| practitioner_id | uuid | FK -> practitioners, indexed with status |
| link_type / role / status | varchar | unique with patient/practitioner/link_type |
| start_at / end_at | timestamptz |  |
| permissions_json / metadata_json | jsonb |  |
| created_at / updated_at | timestamptz |  |

### encounters

Purpose: 就醫、健檢、遠距或裝置資料輸入事件。  
Model: `health_screening.Encounter`  
FHIR: `Encounter`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, index with started_at |
| practitioner_id | uuid | FK -> practitioners |
| source_screening_id | uuid | FK -> health_screening_healthscreening |
| encounter_type / status / reason / location | varchar | indexes on type/status |
| started_at / ended_at | timestamptz |  |
| source_type | varchar(100) |  |
| metadata_json | jsonb |  |

### observations

Purpose: 標準化觀測資料，支援 blood pressure、glucose、weight、heart rate、lab result、home test、wearable data、lifestyle data。  
Model: `health_screening.Observation`  
FHIR: `Observation`, `DiagnosticReport.result`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, index with effective_at |
| encounter_id | uuid | FK -> encounters |
| practitioner_id | uuid | FK -> practitioners |
| observation_type / category / source_type | varchar | indexed |
| code_system / code / display | varchar | category+code index |
| value_quantity | numeric(14,4) |  |
| value_unit / value_string / value_boolean | varchar / bool |  |
| value_json / component_json | jsonb |  |
| reference_range_json / source_payload_json | jsonb |  |
| status / effective_at / issued_at / device_identifier | mixed |  |

### questionnaires

Purpose: 問卷版本與題目定義。  
Model: `health_screening.Questionnaire`  
FHIR: `Questionnaire`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| title / version | varchar | unique together |
| status / code_system / code | varchar | indexes |
| questionnaire_json / scoring_json / metadata_json | jsonb |  |

### questionnaire_responses

Purpose: 問卷填答結果，保存完整 `response_json` 與 `score_json`。  
Model: `health_screening.QuestionnaireResponse`  
FHIR: `QuestionnaireResponse`, survey `Observation`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, index with authored_at |
| questionnaire_id | uuid | FK -> questionnaires |
| encounter_id | uuid | FK -> encounters |
| authored_at / status / source_type | mixed | indexed |
| response_json / score_json / metadata_json | jsonb |  |

### data_import_batches

Purpose: 資料匯入批次，支援 CSV、Excel、FHIR Bulk、hospital API、device API。  
Model: `health_screening.DataImportBatch`  
FHIR: `Provenance`, Bulk Data lineage.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| created_by_user_id | integer | FK -> auth_user |
| source_type / original_filename / status | varchar | source_type+status index |
| total_rows / processed_rows / success_rows / failed_rows | integer |  |
| started_at / completed_at | timestamptz |  |
| import_options_json / summary_json | jsonb |  |

### data_import_rows

Purpose: 匯入列級結果，保存 raw data、normalized data 與落庫目標。  
Model: `health_screening.DataImportRow`  
FHIR: `Provenance`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| batch_id | uuid | FK -> data_import_batches, unique with row_number |
| patient_id | uuid | FK -> patients |
| row_number / status | integer / varchar | indexes |
| target_table / target_id | varchar / uuid | composite index |
| raw_json / normalized_json | jsonb |  |
| error_message | text |  |

### disease risk jobs

Purpose: 疾病風險判讀工作，保存模型、輸入快照與執行狀態。  
Current model/table: `health_screening.AIAnalysisJob` / `ai_analysis_jobs`  
Target rename: `DiseaseRiskJob` / `disease_risk_jobs`  
FHIR: `ServiceRequest`, `Provenance`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients |
| requested_by_user_id | integer | FK -> auth_user |
| encounter_id | uuid | FK -> encounters |
| job_type / status / model_name / model_version | varchar | indexed |
| input_json | jsonb |  |
| started_at / completed_at | timestamptz |  |
| error_message | text |  |

### disease risk results

Purpose: 疾病風險判讀結果，保存 model_version、confidence_score、explanation_json、recommendation_text、requires_doctor_review。  
Current model/table: `health_screening.AIAnalysisResult` / `ai_analysis_results`  
Target rename: `DiseaseRiskResult` / `disease_risk_results`  
FHIR: `RiskAssessment`, `Observation`, `DiagnosticReport`, `DocumentReference`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| job_id | uuid | FK -> ai_analysis_jobs, target disease_risk_jobs |
| patient_id | uuid | FK -> patients, index with created_at |
| result_type / model_version / risk_level | varchar | indexed |
| confidence_score | numeric(6,4) |  |
| result_json / explanation_json | jsonb |  |
| recommendation_text | text |  |
| requires_doctor_review | boolean | index |
| reviewed_by_practitioner_id / reviewed_at | FK / timestamptz |  |

### care_plans

Purpose: 照護計畫，保存疾病風險判讀或醫師建立的追蹤計畫、目標與活動。  
Model: `patients.CarePlan`  
FHIR: `CarePlan`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, index with status |
| care_plan / assessment_and_plan | text |  |
| status / title / category / intent | varchar | category index |
| start_date / period_start / period_end | date/timestamptz |  |
| source_ai_result_id | uuid | index, target source_risk_result_id |
| goal_json / activity_json / metadata_json | jsonb |  |

### care_tasks

Purpose: 照護追蹤任務。  
Model: `health_screening.CareTask`  
FHIR: `Task`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, index with status |
| care_plan_id | uuid | FK -> care_plans, index with status |
| assigned_practitioner_id | uuid | FK -> practitioners |
| source_ai_result_id | uuid | FK -> ai_analysis_results, target disease_risk_results |
| title / description / status / priority | mixed | indexed |
| due_at / completed_at | timestamptz |  |
| metadata_json | jsonb |  |

### consents

Purpose: 病患同意與資料授權。  
Model: `health_screening.Consent`  
FHIR: `Consent`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients, index with status |
| practitioner_id | uuid | FK -> practitioners |
| status / category / scope | varchar | indexed |
| granted_at / revoked_at | timestamptz |  |
| policy_uri | url |  |
| provision_json / source_json / metadata_json | jsonb |  |

### fhir_resource_mappings

Purpose: 內部資料列與 FHIR Resource 的投影對應。  
Model: `fhir_integration.FHIRResourceMapping`  
FHIR: `Provenance`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| patient_id | uuid | FK -> patients |
| fhir_resource_ref_id | uuid | FK -> fhir_integration_fhirresource |
| local_table / local_id | varchar / uuid | composite index |
| fhir_resource_type / fhir_resource_id | varchar | composite index |
| profile_url | url |  |
| fhir_json | jsonb |  |
| sync_status / last_synced_at / error_message | mixed | indexed |
| metadata_json | jsonb |  |

### audit_logs

Purpose: 系統稽核紀錄，保存 create/read/update/delete/export/import/login/disease_risk_assess 等行為。  
Model: `fhir_integration.AuditLog`  
FHIR: `AuditEvent`, `Provenance`.

| Column | Type | Key |
| --- | --- | --- |
| id | uuid | PK |
| actor_user_id | integer | FK -> auth_user, index with occurred_at |
| action | varchar(50) | index |
| target_table / target_id | varchar / uuid | composite index |
| patient_id | uuid | FK -> patients, index with occurred_at |
| ip_address | inet |  |
| user_agent | text |  |
| metadata_json | jsonb |  |
| occurred_at | timestamptz |  |
| created_at / updated_at | timestamptz |  |

## 3. ORM Migrations

Implemented migrations:

- `apps/core/authentication/migrations/0003_productuser.py`
- `apps/clinical/patients/migrations/0007_patientpractitionerlink_practitioner_and_more.py`
- `apps/clinical/health_screening/migrations/0008_aianalysisjob_aianalysisresult_caretask_consent_and_more.py`
- `apps/integration/fhir_integration/migrations/0003_auditlog_fhirresourcemapping.py`
- `apps/integration/fhir_integration/migrations/0004_audit_log_legacy_defaults.py`

Apply:

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

SQL preview:

```powershell
.\venv\Scripts\python.exe manage.py sqlmigrate health_screening 0008
.\venv\Scripts\python.exe manage.py sqlmigrate patients 0007
.\venv\Scripts\python.exe manage.py sqlmigrate fhir_integration 0003
```

## 4. Seed Data

Seed command:

```powershell
.\venv\Scripts\python.exe manage.py seed_product_schema_v1
```

Seeded records:

| Type | ID / Key |
| --- | --- |
| Patient | `20000000-0000-4000-a000-000000000001`, MRN `AC365-SEED-001` |
| Doctor | `30000000-0000-4000-a000-000000000001`, identifier `PRAC-AC365-001` |
| Observation | `50000000-0000-4000-a000-000000000001`, blood pressure |
| QuestionnaireResponse | `70000000-0000-4000-a000-000000000001` |
| DiseaseRiskResult | `91000000-0000-4000-a000-000000000001` |
| CarePlan | `92000000-0000-4000-a000-000000000001` |
| CareTask | `93000000-0000-4000-a000-000000000001` |
| FHIR Mapping | local `observations` -> FHIR `Observation` |
| AuditLog | action `disease_risk_assess` |

## 5. Data Flow Example

1. `patients` stores the patient master record.
2. `observations` stores blood pressure or lab/wearable/lifestyle values.
3. `questionnaire_responses` stores lifestyle response JSON and score JSON.
4. `ai_analysis_jobs` stores the model input snapshot. Target table name: `disease_risk_jobs`.
5. `ai_analysis_results` stores risk result, confidence, explanation, and recommendation. Target table name: `disease_risk_results`.
6. `care_plans` stores the clinician/risk-model follow-up plan.
7. `care_tasks` stores the operational follow-up task.
8. `fhir_resource_mappings` stores the US Core/FHIR projection state.
9. `audit_logs` records the `disease_risk_assess` action and links actor, target, and patient.

## 6. API Endpoint Recommendations

- `POST /patients`
- `GET /patients/:id`
- `POST /patients/:id/practitioner-links`
- `POST /patients/:id/encounters`
- `POST /patients/:id/observations`
- `GET /patients/:id/observations`
- `POST /patients/:id/questionnaire-responses`
- `GET /patients/:id/questionnaire-responses`
- `POST /imports/batches`
- `GET /imports/batches/:id`
- `POST /disease-risk/jobs`
- `GET /patients/:id/disease-risk-results`
- `POST /care-plans`
- `POST /care-plans/:id/tasks`
- `GET /patients/:id/care-tasks`
- `POST /patients/:id/consents`
- `GET /patients/:id/audit-logs`
- `GET /fhir/Patient/:id`
- `GET /fhir/Observation?patient=:id`
- `GET /fhir/metadata`
- `GET /bulk/$export`
