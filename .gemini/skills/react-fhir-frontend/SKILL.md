---
name: react-fhir-frontend
description: Expertise in building SMART on FHIR user interfaces using React, Material UI, and fhirclient. Use when creating patient dashboards, clinical data visualizations, or implementing SMART App Launch flows.
---

# React SMART on FHIR Expert

This skill provides specialized knowledge for building secure and compliant medical user interfaces for the Allcare 365 system.

## Core Workflows

### 1. SMART App Launch Flow
Refer to `fhirclient-setup.md` to implement the authorization and ready sequence. Ensure the `clientId` matches the configuration in the Django backend.

### 2. Clinical Data Visualization
When asked to display medical data (Vitals, Labs, Risks):
1. Use the `useFHIRResource` hook to fetch data asynchronously.
2. Apply patterns from `medical-ui-components.md` to ensure a consistent, professional medical UI.
3. **Important**: Always handle the `loading` state and potential 401 Unauthorized errors (session expired).

## Design Principles
- **Patient Context**: Always validate that the patient ID in the UI matches the SMART launch context.
- **Mobile First**: Medical professionals often use tablets or phones; ensure all MUI components are responsive.
- **Privacy**: Mask sensitive data (PII) by default unless in a secure clinical view.