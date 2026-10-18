"""Intersect SMART user scopes with persisted clinical relationships.

OAuth scopes describe operations, not which patients a human may access.
Resources without a provable patient relationship fail closed for user scopes.
"""
from .models import FHIRResourceMapping
from .resource_identity import identity
from apps.clinical.patients.access_policy import patient_clinical_access_policy


class FHIRUserAccess:
    def __init__(self, user):
        self.user = user
        self.patient_ids = set(map(str, patient_clinical_access_policy.allowed_patient_ids(user)))

    def allows(self, resource):
        if not resource or not getattr(self.user, 'is_authenticated', False):
            return False
        resource_type = resource.get('resourceType')
        resource_id = resource.get('id')
        if resource_type == 'Patient':
            return str(identity.resolve_patient_db_id(resource_id)) in self.patient_ids
        # Nonclinical directory resources do not establish patient access.
        if resource_type in {'Organization', 'Location'}:
            return True
        if resource_type == 'Practitioner' and resource_id == identity.practitioner_id(self.user):
            return True

        patient_refs = list(self._patient_references(resource))
        if patient_refs:
            resolved = {identity.resolve_patient_db_id(reference) for reference in patient_refs}
            return None not in resolved and set(map(str, resolved)).issubset(self.patient_ids)

        mapped_patient_ids = set(map(str, FHIRResourceMapping.objects.filter(
            fhir_resource_type=resource_type, fhir_resource_id=resource_id,
        ).values_list('patient_id', flat=True)))
        if mapped_patient_ids:
            return mapped_patient_ids.issubset(self.patient_ids)

        # Derived Provenance may reference an Observation/RiskAssessment instead
        # of a Patient. Every target must be mapped to an authorized patient.
        if resource_type == 'Provenance':
            targets = resource.get('target') or []
            if not targets:
                return False
            for target in targets:
                parts = str(target.get('reference', '')).rstrip('/').split('/')
                if len(parts) < 2:
                    return False
                target_patients = set(map(str, FHIRResourceMapping.objects.filter(
                    fhir_resource_type=parts[-2], fhir_resource_id=parts[-1],
                ).values_list('patient_id', flat=True)))
                if not target_patients or not target_patients.issubset(self.patient_ids):
                    return False
            return True
        return False

    @classmethod
    def _patient_references(cls, value):
        if isinstance(value, dict):
            reference = value.get('reference')
            if isinstance(reference, str):
                parts = reference.rstrip('/').split('/')
                if len(parts) >= 2 and parts[-2] == 'Patient':
                    yield reference
            for item in value.values():
                yield from cls._patient_references(item)
        elif isinstance(value, list):
            for item in value:
                yield from cls._patient_references(item)
