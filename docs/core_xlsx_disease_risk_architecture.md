# CORE.xlsx Disease Risk Architecture

Status: implementation v1  
Last updated: 2026-06-11

## 1. Product Decision

The product feature name is **疾病風險判讀**.

Avoid using "AI 判讀" for this workflow. The first version is a deterministic disease-risk rules engine based on `CORE.xlsx`, not a generative AI module.

## 2. CORE.xlsx Role

`CORE.xlsx` is the source specification for the first disease-risk engine.

Workbook structure:

| Sheet | System Role | Database Equivalent |
| --- | --- | --- |
| `A1 KEY IN` | Large health-check data input sheet | `observations`, `encounters`, patient demographics |
| `HQ` | Patient questionnaire / lifestyle survey | `questionnaires`, `questionnaire_responses` |
| `FHS DM` | Framingham diabetes risk model | disease risk algorithm |
| `CH DM` | Chinese diabetes risk model | disease risk algorithm |
| `MetS` | Metabolic syndrome model | disease risk algorithm |
| `NAFLD` | Fatty liver / fibrosis model | disease risk algorithm |
| `FHSFLD` | Framingham fatty liver model | disease risk algorithm |
| `AusDM` | Australian diabetes risk model | disease risk algorithm |
| `GVR CAIDE` | Global vascular / CAIDE risk model | disease risk algorithm |
| `Summary` | Report aggregation | frontend disease-risk summary |

## 3. Data Flow

### Input

Manual entry, batch import, FHIR import, hospital API, and device API all normalize into:

- `patients`
- `encounters`
- `observations`
- `questionnaire_responses`
- `data_import_batches`
- `data_import_rows`

This is the database replacement for Excel `A1 KEY IN` and `HQ`.

Current implementation:

- Manual single-patient input sends `vital_signs`, `laboratory_results`, `a1_key_in`, `hq`, `assessments`, and `problems`.
- Batch import maps CORE-style CSV/Excel columns into the same normalized payload before persistence.
- `A1 KEY IN` values become `observations` rows with code/category/unit metadata where possible.
- `HQ` values become `questionnaire_responses.response_json` and are also available to the risk input adapter.

### Disease Risk Assessment

Risk model sheets such as `FHS DM`, `CH DM`, `MetS`, and `NAFLD` should not own source data.

They become backend algorithm modules:

```text
observations + questionnaire_responses
  -> disease risk input vector
  -> CORE formula-compatible calculator
  -> disease_risk_jobs / disease_risk_results
  -> care_plans / care_tasks
  -> fhir_resource_mappings
  -> audit_logs
```

Missing-data rule:

- Each calculator declares the data elements required by its formula.
- The repository fetches those elements from `patients`, `observations`, `questionnaire_responses`, and legacy compatibility tables.
- Selection is field-level, not visit-level: every required field chooses the latest available valid value for that field.
- If one patient has an old comprehensive exam, a newer partial exam, and a newest small exam, the risk input can combine old urine data, newer blood data, and newest body measurements.
- When two sources have the same effective date, normalized product `observations` take priority over legacy compatibility rows.
- Every selected field records its source table, source id, effective date, and `selection_policy=latest_available_per_field`.
- Missing values are not treated as `false` or `0`.
- If a required element is missing, the result is returned as `資料不足`, with `missing_data` keys for auditability and `missing_data_labels` for frontend display.
- Partial scores must not be presented as clinically valid risk values.

## 4. Formula Dependency Summary

Observed workbook dependencies:

| Sheet | Formula Count | Main Dependencies |
| --- | ---: | --- |
| `A1 KEY IN` | 41 | `HQ` |
| `FHS DM` | 32 | `A1 KEY IN` |
| `CH DM` | 22 | `A1 KEY IN`, `HQ`, `MetS` |
| `MetS` | 54 | `A1 KEY IN`, `HQ` |
| `NAFLD` | 26 | `A1 KEY IN`, `FHSFLD`, `FHS DM` |
| `FHSFLD` | 32 | `A1 KEY IN` |
| `AusDM` | 22 | `A1 KEY IN`, `HQ` |
| `HQ` | 8 | `A1 KEY IN`, `MetS` |
| `GVR CAIDE` | 77 | `A1 KEY IN`, `HQ` |

## 5. Database Mapping

### A1 KEY IN

Every clinical measurement should be represented as an `observations` row.

Examples:

| Excel Concept | Target Table | Key Fields |
| --- | --- | --- |
| Age, sex | `patients` | `date_of_birth`, `sex` |
| Height, weight, BMI | `observations` | `category=vital-signs`, LOINC code where available |
| Blood pressure | `observations` | `component_json` systolic/diastolic |
| Glucose, HDL, triglyceride, AST, ALT, platelets | `observations` | `category=laboratory`, `code`, `value_quantity` |
| Derived BMI or ratios | `observations` or risk input transform | generated with provenance |

### HQ

Questionnaire answers should be represented as:

- `questionnaires`: survey definition and version.
- `questionnaire_responses`: answer payload in `response_json`, scoring in `score_json`.

### Risk Model Sheets

Each risk sheet becomes a model definition:

| Sheet | Engine Name |
| --- | --- |
| `FHS DM` | `framingham_diabetes` |
| `CH DM` | `chinese_diabetes` |
| `MetS` | `metabolic_syndrome` |
| `NAFLD` | `nafld_fibrosis` |
| `FHSFLD` | `framingham_fatty_liver` |
| `AusDM` | `ausdrisk_diabetes` |
| `GVR CAIDE` | `caide_dementia_20y` (`vascular_caide` retired as an ambiguous legacy ID) |

## 6. Old Module Retirement

The current legacy risk path is:

```text
HealthScreening / VitalSigns / LaboratoryResults
  -> services/risk_engine (deleted)
  -> AIAnalysis naming in database/frontend
```

Target path:

```text
Encounter / Observation / QuestionnaireResponse
  -> services/disease_risk_engine
  -> DiseaseRiskJob / DiseaseRiskResult
  -> CarePlan / CareTask
```

Retirement sequence:

1. Extract CORE workbook cell map and formula dependency map.
2. Build normalized observation/questionnaire input adapter.
3. Implement `services/disease_risk_engine` with one model at a time. Status: FHS DM, CH DM, MetS, NAFLD, FHSFLD, AusDM, and GVR CAIDE implemented as v1 calculators.
4. Rename product tables and API labels from AI analysis to disease risk. Status: UI/API language changed; physical table rename still pending.
5. Move frontend to disease-risk endpoints. Status: compatibility endpoint remains; new `/api/health-screening/disease-risk/` added.
6. Delete legacy `services/risk_engine`. Status: done.
7. Decide when to retire old `HealthScreening` compatibility endpoints after ONC/projector impact review.
8. Re-run ONC baseline after each deletion group.

Do not delete ONC projectors or certification seed commands.

## 7. User-Facing Language

Use:

- 疾病風險判讀
- 風險模型
- 追蹤建議
- 風險結果

Avoid:

- AI 判讀
- AI 建議
- AI 追蹤
