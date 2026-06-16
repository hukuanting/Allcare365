# Projectors — ORM → FHIR Resource Mapping

每個 projector 負責將一種 Django ORM model 映射成一個 FHIR R4 resource。

## 架構 (Architecture)

```
@ProjectorRegistry.register("Observation")
class ObservationProjector(BaseProjector):
    resource_type = "Observation"

    def query(patient_id, search_params, context) → QuerySet
    def project(instance, context) → dict   # FHIR JSON
```

## Pipeline

```
query()  →  optimize_queryset()  →  project_batch()
                                      ├─ normalize()
                                      ├─ project()        ← 你要實作的核心
                                      ├─ apply_extensions()
                                      └─ returns list[dict]
```

## 新增一個 Projector (How to Add)

### 1. 建立檔案

```python
# projectors/my_resource.py

from .base import BaseProjector
from .registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity

@ProjectorRegistry.register("MyResource")
class MyResourceProjector(BaseProjector):
    resource_type = "MyResource"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import MyModel
        qs = MyModel.objects.filter(patient_id=patient_id)
        # Apply search_params filtering here
        return qs

    def project(self, instance, context):
        return {
            "resourceType": "MyResource",
            "id": identity.resource_id("myresource", instance),
            "meta": MetaBuilder.us_core("myresource"),
            "subject": context.reference_builder.patient(context.patient_id),
            # ... your FHIR mapping
        }

    def supported_search_params(self):
        return {"patient": "reference", "status": "token"}

    def supported_rev_includes(self):
        return ["Provenance:target"]
```

### 2. 在 `__init__.py` 加入 import

```python
from . import my_resource  # noqa: F401
```

### 3. Done — 不需要改 views.py

## 現有 Projectors (24 files, 25 resource types)

| File | FHIR Type(s) |
|------|-------------|
| `patient.py` | Patient |
| `condition.py` | Condition |
| `observation.py` | Observation (all vitals, labs, smoking, screening) |
| `encounter.py` | Encounter |
| `medication_request.py` | MedicationRequest |
| `medication_dispense.py` | MedicationDispense |
| `medication.py` | Medication |
| `allergy_intolerance.py` | AllergyIntolerance |
| `care_plan.py` | CarePlan |
| `care_team.py` | CareTeam |
| `coverage.py` | Coverage |
| `device.py` | Device |
| `diagnostic_report.py` | DiagnosticReport |
| `document_reference.py` | DocumentReference |
| `goal.py` | Goal |
| `immunization.py` | Immunization |
| `procedure.py` | Procedure |
| `service_request.py` | ServiceRequest |
| `specimen.py` | Specimen |
| `location.py` | Location |
| `organization.py` | Organization |
| `practitioner.py` | Practitioner + PractitionerRole |
| `related_person.py` | RelatedPerson |
| `provenance.py` | Provenance |

## 重要規則 (Rules)

1. **永遠不要在 projector 裡硬寫 profile URL** — 用 `MetaBuilder.us_core()`
2. **永遠不要在 projector 裡硬寫 reference** — 用 `context.reference_builder.patient(id)`
3. **永遠不要在 projector 裡硬寫 resource ID** — 用 `identity.resource_id(prefix, instance)`
4. **需要 _include 時** → 呼叫 `context.include_tracker.add(type, id)`
