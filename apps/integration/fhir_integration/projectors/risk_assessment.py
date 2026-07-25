"""Expose validated disease-risk outputs already persisted as FHIR R4."""
from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import F
from fhirclient.models.riskassessment import RiskAssessment as FHIRRiskAssessment

from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


logger = logging.getLogger("medical_system")


@ProjectorRegistry.register("RiskAssessment")
class RiskAssessmentProjector(BaseProjector):
    """Read/search RiskAssessment without calculating or fabricating results.

    A row is eligible only when its persisted FHIR payload has a consistent,
    unique active-patient ``FHIRResourceMapping``. The mapping is the
    compartment boundary; the JSON ``subject`` alone never grants access.
    """

    resource_type = "RiskAssessment"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.clinical_scope import clinical_patients

        from ..models import FHIRResource

        patient_queryset = None
        if not getattr(settings, "FHIR_INCLUDE_CONFORMANCE_FIXTURES", False):
            patient_queryset = clinical_patients()

        qs = FHIRResource.objects.filter(
            resource_type=self.resource_type,
            is_active=True,
            local_mappings__fhir_resource_type=self.resource_type,
            local_mappings__fhir_resource_id=F("resource_id"),
            local_mappings__patient__is_active=True,
        )
        if patient_queryset is not None:
            qs = qs.filter(local_mappings__patient__in=patient_queryset)

        resource_id = str(search_params.get("_id") or "").strip()
        if resource_id:
            qs = qs.filter(resource_id=resource_id)

        requested_patient_ids: list[str] = []
        for token in (
            patient_id,
            search_params.get("patient"),
            search_params.get("subject"),
        ):
            if token in (None, ""):
                continue
            resolved = identity.resolve_patient_db_id(str(token))
            if resolved is None:
                return qs.none()
            requested_patient_ids.append(str(resolved))

        if len(set(requested_patient_ids)) > 1:
            return qs.none()
        if requested_patient_ids:
            qs = qs.filter(local_mappings__patient_id=requested_patient_ids[0])

        return qs.order_by("resource_id").distinct()

    def project(self, persisted, context: "FHIRContext") -> dict | None:
        from ..models import FHIRResourceMapping

        data = copy.deepcopy(getattr(persisted, "resource_data", None))
        persisted_id = str(getattr(persisted, "resource_id", "") or "").strip()
        if (
            not isinstance(data, dict)
            or not persisted_id
            or data.get("resourceType") != self.resource_type
            or data.get("id") != persisted_id
        ):
            return None

        mappings = list(
            FHIRResourceMapping.objects.select_related("patient").filter(
                fhir_resource_ref=persisted,
                fhir_resource_type=self.resource_type,
                fhir_resource_id=persisted_id,
                patient__is_active=True,
            )
        )
        patient_ids = {str(mapping.patient_id) for mapping in mappings}
        if not mappings or len(patient_ids) != 1:
            return None
        if any(mapping.fhir_json != data for mapping in mappings):
            return None

        patient = mappings[0].patient
        if (
            not getattr(settings, "FHIR_INCLUDE_CONFORMANCE_FIXTURES", False)
            and (patient.metadata_json or {}).get("clinical_use_prohibited") is True
        ):
            return None
        expected_subject = f"Patient/{identity.patient_id(patient)}"
        subject = data.get("subject")
        if not isinstance(subject, dict) or subject.get("reference") != expected_subject:
            return None

        try:
            FHIRRiskAssessment(data, strict=True)
        except Exception as exc:
            logger.warning(
                "Persisted RiskAssessment/%s failed strict FHIR R4 validation: %s",
                persisted_id,
                exc,
            )
            return None
        return data

    def supported_search_params(self):
        return {
            "_id": "token",
            "patient": "reference",
            "subject": "reference",
        }

    def supported_rev_includes(self):
        return ["Provenance:target"]
