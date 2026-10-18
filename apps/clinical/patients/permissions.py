"""DRF mixins that apply one patient policy to every clinical resource."""

from __future__ import annotations

from rest_framework.exceptions import PermissionDenied, ValidationError

from .access_policy import patient_clinical_access_policy


class PatientScopedModelViewSetMixin:
    """Filter patient-owned models and reject cross-patient reassignment."""

    patient_field = "patient"
    access_policy = patient_clinical_access_policy

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_field = self.patient_field
        return queryset.filter(**{f"{patient_field}__in": self.access_policy.queryset(self.request.user)})

    def _require_target_access(self, serializer, *, operation: str) -> None:
        patient = serializer.validated_data.get(self.patient_field)
        if patient is None:
            patient = getattr(serializer.instance, self.patient_field, None)
        if patient is None:
            raise ValidationError({self.patient_field: "This field is required."})
        self.access_policy.require_access(self.request.user, patient, operation=operation)

    def perform_create(self, serializer):
        self._require_target_access(serializer, operation="write")
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        original_patient = getattr(serializer.instance, self.patient_field)
        self.access_policy.require_access(self.request.user, original_patient, operation="write")
        self._require_target_access(serializer, operation="write")
        # Audit ownership is server-controlled.  Do not allow an update payload
        # to rewrite who originally created a clinical record.
        serializer.validated_data.pop("created_by", None)
        serializer.validated_data.pop("updated_by", None)
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        self.access_policy.require_access(
            self.request.user, getattr(instance, self.patient_field), operation="write"
        )
        instance.delete()
