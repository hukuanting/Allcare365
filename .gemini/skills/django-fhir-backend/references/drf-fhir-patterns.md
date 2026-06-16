# Django REST Framework FHIR Patterns

## 1. FHIR Content Negotiation
Use custom renderers to handle `application/fhir+json` correctly.

```python
from rest_framework import renderers

class FHIRRenderer(renderers.JSONRenderer):
    media_type = 'application/fhir+json'
    format = 'fhir_json'
```

## 2. Standard FHIR ViewSet
Inherit from this pattern to ensure compliance with FHIR RESTful interactions.

```python
from rest_framework import viewsets
from apps.integration.fhir_integration.views import FHIRBaseMixin

class PatientViewSet(FHIRBaseMixin, viewsets.ReadOnlyModelViewSet):
    """
    Standard FHIR Patient endpoint.
    Handles: Read, Search (GET/POST)
    """
    def retrieve(self, request, *args, **kwargs):
        # Implementation...
        pass

    def list(self, request, *args, **kwargs):
        # Implementation for Search...
        pass
```

## 3. Search Parameter Handling
FHIR search parameters often include prefixes (eq, gt, ge) and modifiers. Use this pattern to parse them.

```python
def parse_fhir_date(param_value):
    if param_value.startswith(('eq', 'gt', 'lt', 'ge', 'le')):
        prefix = param_value[:2]
        date_str = param_value[2:]
        return prefix, date_str
    return 'eq', param_value
```
