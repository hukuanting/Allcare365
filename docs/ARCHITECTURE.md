# Allcare 365 System Architecture

## Overview
Allcare 365 is currently a certification-oriented EHR demonstration system. It is **not** a formally ONC-certified product and must not be represented as one without current certification evidence. The implementation is hybrid: relational clinical models, persisted FHIR payloads, and FHIR projections coexist while the canonical data boundary is being consolidated.

The target architecture and migration gates are documented in [`PLATFORM_REFACTOR_PLAN_2026-08-29.md`](PLATFORM_REFACTOR_PLAN_2026-08-29.md).

## Architectural Principles
1.  **Domain-Driven Design (DDD):** Code is organized by business domain (Clinical, Integration, Core) rather than technical layer.
2.  **FHIR Contract First:** External exchange and canonical clinical semantics use HL7 FHIR R4. Relational read models may be used internally, but they must be derived from one versioned clinical write path and retain source references.
3.  **Service-Oriented:** Business logic is encapsulated in services, not views or models.
4.  **Security by Design:** SMART on FHIR scopes and OAuth2/OIDC are the primary security mechanisms.

## Directory Structure

```
allcare365/
├── apps/                  # Domain-specific applications
│   ├── clinical/          # Clinical domain (Patients, Health Screening)
│   │   ├── patients/
│   │   └── health_screening/
│   ├── integration/       # Interoperability domain (FHIR, Devices)
│   │   ├── fhir_integration/
│   │   └── wearable_integration/
│   └── core/              # Infrastructure domain (Auth, Common)
│       ├── authentication/
│       └── common/
├── config/                # Project configuration (Settings, WSGI)
├── docs/                  # Documentation
├── services/              # Cross-domain services (Disease Risk Engine)
└── manage.py
```

## Key Components

### 1. Clinical Domain (`apps/clinical`)
*   **Patients:** Manages patient demographics and identity (USCDI v6).
*   **Health Screening:** Manages clinical data (Vitals, Labs) and risk assessments.

### 2. Integration Domain (`apps/integration`)
*   **FHIR Integration:** Handles FHIR API requests, resource mapping, and bulk data export.
*   **Wearable Integration:** Ingests data from external devices.

### 3. Disease Risk Engine (`services/disease_risk_engine`)
*   A standalone service that calculates hospital-approved deterministic disease risks from canonical clinical inputs.
*   **Input:** Patient, Observation, and QuestionnaireResponse source data.
*   **Output:** Disease risk result records plus FHIR Observation/RiskAssessment and provenance mappings.
*   **Algorithms:** 42 approved models bound exactly once in `formula_catalog.py`; registry metadata and runtime orchestration remain separate.

## Technology Stack
*   **Backend:** Python 3.10+, Django 5.0+
*   **Database:** PostgreSQL (Production), SQLite (Dev)
*   **Frontend:** React 18+
*   **API:** Django REST Framework, FHIR R4 (fhir.resources)
*   **Auth:** OAuth2 (django-oauth-toolkit), OIDC

## Conformance Implementation Status
*   **g10 Standardized API:** Certification-oriented implementation exists in `fhir_integration`; passing local tests is not certification evidence.
*   **US Core / USCDI:** Current code contains US Core 7.0.0 projections and USCDI v6-oriented mappings. A single, explicit certification target still needs to replace these mixed claims.
*   **SMART on FHIR:** OAuth2/OIDC and granular scope enforcement are implemented, subject to full security and Inferno validation.
