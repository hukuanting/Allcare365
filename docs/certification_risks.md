# ONC g10 Certification Risks & Mitigation Strategies

## 1. FHIR Data Fidelity (USCDI v6)
*   **Risk:** The current "Hybrid" approach (storing raw JSON in `FHIRResource` while shredding to SQL `VitalSigns`/`LaboratoryResults`) creates a "Source of Truth" conflict. If the SQL data is edited via the Admin panel, the raw FHIR JSON might become stale.
*   **Mitigation:**
    *   Implement `post_save` signals on SQL models to update the corresponding `FHIRResource`.
    *   Or, treat `FHIRResource` as the read-only audit trail and SQL as the active operational data (acceptable for some certifications but risky for "Data Portability" if they diverge).

## 2. SMART on FHIR Scopes
*   **Risk:** The `settings.py` defines scopes like `patient/Observation.rs`. The standard ONC/Inferno tests expect `patient/Observation.read`. While aliases exist, strict validators might flag this.
*   **Mitigation:** Update `OAUTH2_PROVIDER` settings to strictly follow the [HL7 SMART App Launch](http://hl7.org/fhir/smart-app-launch/) implementation guide.

## 3. Bulk Data Import (g10)
*   **Risk:** The `BulkImportService` converts FHIR Bundles into internal SQL models. If the input Bundle contains USCDI v6 elements that are *not* mapped to SQL columns (e.g., specific SDOH `Observation` codes), that data is "lost" from the operational view, even if stored in `FHIRResource`.
*   **Mitigation:** Ensure the `USCDIv6Mapper` covers 100% of the USCDI v6 data classes, or implement a generic "Unmapped Data" viewer.

## 4. Risk Analysis Provenance
*   **Risk:** The calculated `RiskAssessment` resources are created by the "System". ONC often requires clear Provenance (who calculated this? when? using what data?).
*   **Mitigation:** When saving `RiskAssessment`, also create a `Provenance` resource linking to the `Device` (the risk engine) and the source `Observation` resources used in the calculation.

## 5. Terminology Binding
*   **Risk:** The system currently accepts strings (e.g., "Glucose"). ONC requires strict binding to LOINC, SNOMED CT, and RxNorm.
*   **Mitigation:** Implement a strict terminology validation layer that rejects imports without valid standard codes.
