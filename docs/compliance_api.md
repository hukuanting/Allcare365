# USCDI v6 Compliance Dashboard API Documentation

## Overview
The USCDI v6 Compliance Dashboard provides visual verification of your database's compliance with all 22 USCDI v6 data classes. This API allows you to programmatically check compliance status and identify missing data elements.

## API Endpoints

### 1. Get Compliance Dashboard
**Endpoint:** `GET /fhir/api/compliance/dashboard/`

**Description:** Returns comprehensive compliance analysis for all 22 USCDI v6 data classes.

**Response Example:**
```json
{
  "generated_at": "2025-11-28T14:10:00",
  "overall_score": 45.5,
  "total_classes": 22,
  "classes_with_data": 10,
  "total_resources": 150,
  "total_uscdi_elements": 85,
  "class_details": [
    {
      "class_key": "vital_signs",
      "class_name": "Vital Signs",
      "resource_count": 45,
      "completeness_score": 85.0,
      "status": "complete",
      "missing_elements": []
    },
    ...
  ],
  "summary": {
    "overall_status": "partial",
    "coverage_percentage": 45.5,
    "complete_count": 5,
    "partial_count": 5,
    "missing_count": 12,
    "recommendation": "System has moderate USCDI v6 compliance..."
  }
}
```

**Status Levels:**
- `complete`: >80% completeness
- `partial`: 50-80% completeness
- `minimal`: 1-49% completeness
- `missing`: 0% completeness

---

### 2. Get Class Details
**Endpoint:** `GET /fhir/api/compliance/class_details/?class_key=<class_key>`

**Description:** Returns detailed analysis for a specific USCDI data class.

**Parameters:**
- `class_key` (required): USCDI class identifier (e.g., `vital_signs`, `patient_demographics`)

**Available Class Keys:**
- `allergies`
- `care_plan`
- `care_team`
- `clinical_notes`
- `clinical_tests`
- `diagnostic_imaging`
- `encounter_information`
- `facility_information`
- `family_health_history`
- `goals_and_preferences`
- `health_insurance_information`
- `health_status_assessments`
- `immunizations`
- `laboratory`
- `medical_devices`
- `medications`
- `orders`
- `patient_demographics`
- `problems`
- `procedures`
- `provenance`
- `vital_signs`

**Response Example:**
```json
{
  "class_key": "vital_signs",
  "class_name": "Vital Signs",
  "description": "Vital signs measurements",
  "resource_count": 45,
  "has_data": true,
  "required_elements_total": 10,
  "required_elements_present": 8,
  "required_elements_missing": 2,
  "completeness_score": 80.0,
  "status": "complete",
  "missing_elements": ["temperature", "respiratory_rate"],
  "sample_resource_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "sample_resources": [
    {
      "id": "uuid-1",
      "resource_type": "Observation",
      "created_at": "2025-11-28T10:00:00",
      "data_preview": {
        "code": "{...}",
        "value": "120/80",
        "effectiveDateTime": "2025-11-28"
      }
    }
  ]
}
```

---

### 3. Export Compliance Report
**Endpoint:** `GET /fhir/api/compliance/export/?format=<format>`

**Description:** Export compliance report in different formats.

**Parameters:**
- `format` (optional): Export format (`json` or `summary`, default: `json`)

**Response (format=summary):**
```json
{
  "generated_at": "2025-11-28T14:10:00",
  "overall_score": 45.5,
  "summary": {
    "overall_status": "partial",
    "coverage_percentage": 45.5,
    "complete_count": 5,
    "partial_count": 5,
    "missing_count": 12,
    "recommendation": "System has moderate USCDI v6 compliance..."
  },
  "classes_with_data": 10,
  "total_classes": 22,
  "missing_classes": [
    "Care Plan",
    "Clinical Tests",
    "Diagnostic Imaging",
    ...
  ]
}
```

---

## Usage Examples

### cURL Examples

```bash
# Get full compliance dashboard
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/fhir/api/compliance/dashboard/

# Get details for vital signs
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/fhir/api/compliance/class_details/?class_key=vital_signs

# Export summary report
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/fhir/api/compliance/export/?format=summary
```

### Python Example

```python
import requests

# Setup
base_url = "http://localhost:8000/fhir/api"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

# Get dashboard
response = requests.get(f"{base_url}/compliance/dashboard/", headers=headers)
dashboard = response.json()

print(f"Overall Score: {dashboard['overall_score']}%")
print(f"Classes with Data: {dashboard['classes_with_data']}/{dashboard['total_classes']}")

# Check specific class
response = requests.get(
    f"{base_url}/compliance/class_details/",
    params={"class_key": "vital_signs"},
    headers=headers
)
details = response.json()
print(f"Vital Signs Completeness: {details['completeness_score']}%")
```

---

## Integration with ONC Certification

This compliance dashboard helps prepare for ONC (g)(10) certification by:

1. **Identifying Gaps**: Shows which USCDI v6 data classes are missing
2. **Measuring Completeness**: Calculates coverage percentage for each class
3. **Guiding Implementation**: Provides specific missing elements to implement
4. **Tracking Progress**: Monitor compliance score as you add data

**Next Steps for ONC Certification:**
1. Achieve >80% compliance score across all classes
2. Implement US Core v9.0.0 profiles
3. Add SMART on FHIR authentication
4. Test with Inferno test suite

---

## Authentication

All endpoints require authentication. Include your authorization token in the request headers:

```
Authorization: Bearer YOUR_TOKEN
```

---

## Error Responses

**400 Bad Request:**
```json
{
  "error": "Missing required parameter: class_key"
}
```

**404 Not Found:**
```json
{
  "error": "Unknown USCDI class: invalid_class",
  "available_classes": ["allergies", "care_plan", ...]
}
```
