---
name: django-fhir-backend
description: Implementing FHIR-compliant backend services using Django REST Framework and fhir.resources. Use when creating new FHIR API endpoints, implementing OAuth2/SMART security, or handling fhir+json payloads.
---

# Django FHIR Backend Expert

This skill provides the architectural patterns and security standards required to build an ONC-certified EHR backend for Allcare 365.

## Core Workflows

### 1. Endpoint Implementation
When asked to create a new FHIR endpoint (e.g., `DiagnosticReport`):
1. Use `drf-fhir-patterns.md` to setup the ViewSet and Renderer.
2. Ensure the model mapping uses the correct US Core profiles.
3. Register the endpoint in `apps/integration/fhir_integration/urls.py`.

### 2. Security Integration
All new endpoints **MUST** include scope validation.
- Refer to `security-scopes.md` for required patterns.
- Ensure the `FHIRScopePermission` class is applied to the ViewSet.

## Best Practices
- **Never** return proprietary JSON for USCDI data classes; always use FHIR R4.
- Use `fhir.resources` for validation before saving/returning data.
- Maintain `db_table` naming consistency to ensure database portability.