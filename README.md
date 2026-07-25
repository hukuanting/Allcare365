# Allcare 365

Allcare 365 is a full-stack clinical data platform and portfolio project. It combines a Django REST/FHIR R4 backend, SMART on FHIR OAuth 2.0 flows, a React clinical interface, and a disease-risk analysis engine.

> **Demo software — not for real clinical use.** The public deployment must contain synthetic data only. It is not a production service, a certified EHR, or a HIPAA/PHI hosting environment.

## What it demonstrates

- FHIR R4 resource APIs, search, export, `CapabilityStatement`, and USCDI-oriented projections.
- SMART on FHIR discovery and OAuth 2.0/OIDC-compatible authorization endpoints.
- Patient, health-screening, cohort, research-report, data-quality, and risk-analysis workflows.
- A modular risk engine with algorithm catalogues, formulas, units, provenance, and FHIR `RiskAssessment` projection.
- React UI with authentication, patient charting, bulk import, research, and clinical-risk views.

## Architecture

```text
React SPA (frontend/, optional static host)
            │ HTTPS / Bearer token
            ▼
Django 5 / DRF (medical_system/, apps/)
  ├── Authentication + SMART OAuth2/OIDC
  ├── Clinical patient and screening APIs
  ├── FHIR R4 facade, search, bulk export, projectors
  └── Disease-risk application service
            │
            ▼
PostgreSQL (clinical source data + FHIR resources + audit data)
```

## Quick start

Prerequisites: Python 3.10+, PostgreSQL, Node.js 20+.

```bash
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In another terminal:

```bash
cd frontend
npm ci
npm start
```

The frontend runs at `http://localhost:3000`; the Django service runs at `http://localhost:8000`.

## Quality checks

```bash
python manage.py check
pytest
cd frontend && CI=true npm test -- --watchAll=false && npm run build
```

GitHub Actions runs these checks for pushes and pull requests. The full handoff map, risks, and code ownership are in [docs/SYSTEM_TECH_REVIEW.md](docs/SYSTEM_TECH_REVIEW.md). Deployment instructions are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Repository guidance

- Keep `.env`, database dumps, uploads, source clinical files, and keys out of Git.
- Do not use the free demo deployment with real patient information.
- Review [docs/PUBLISHING_CHECKLIST.md](docs/PUBLISHING_CHECKLIST.md) before making the repository public.
- A license has intentionally not been chosen. Confirm code and data ownership before adding one; MIT is often appropriate for a public portfolio, while a private repository is safer during handoff.
