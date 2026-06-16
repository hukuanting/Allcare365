# Allcare 365 System Architecture

## Overview
Allcare 365 is an ONC-certified, FHIR-native Electronic Health Record (EHR) system designed for scalability and interoperability.

## Architectural Principles
1.  **Domain-Driven Design (DDD):** Code is organized by business domain (Clinical, Integration, Core) rather than technical layer.
2.  **FHIR First:** All clinical data storage and exchange uses HL7 FHIR R4 standards.
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
*   A standalone service that calculates disease risk from CORE.xlsx-compatible inputs.
*   **Input:** Patient, Observation, and QuestionnaireResponse source data.
*   **Output:** Disease risk result records and FHIR RiskAssessment mappings.
*   **Algorithms:** FHS DM, CH DM, MetS, NAFLD, FHSFLD, AusDM, and GVR CAIDE v1.

## Technology Stack
*   **Backend:** Python 3.10+, Django 5.0+
*   **Database:** PostgreSQL (Production), SQLite (Dev)
*   **Frontend:** React 18+
*   **API:** Django REST Framework, FHIR R4 (fhir.resources)
*   **Auth:** OAuth2 (django-oauth-toolkit), OIDC

## ONC Certification Strategy
*   **g10 Standardized API:** Implemented via `fhir_integration` app.
*   **USCDI v6:** Data models in `health_screening` are mapped to USCDI v6 classes.
*   **SMART on FHIR:** OAuth2 scopes enforce granular access control.
