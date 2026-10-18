"""Django admin enforcement for patient-scoped clinical models."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from .access_policy import patient_clinical_access_policy


class PatientScopedAdminMixin:
    """Apply clinical object authorization after Django's model permissions.

    ``patient_lookup`` is an ORM path from the registered model to Patient.
    Model-level admin permissions remain necessary; this mixin narrows their
    effect to the user's active care relationship or explicit global grant.
    """

    patient_lookup = "patient"
    access_policy = patient_clinical_access_policy

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        allowed_patients = self.access_policy.queryset(request.user)
        if self.patient_lookup:
            return queryset.filter(**{f"{self.patient_lookup}__in": allowed_patients})
        return allowed_patients

    def _patient_for_object(self, obj):
        patient = obj
        for attribute in self.patient_lookup.split("__"):
            patient = getattr(patient, attribute)
        return patient

    def _can_write_object(self, request, obj) -> bool:
        return self.access_policy.has_access(
            request.user, self._patient_for_object(obj), operation="write"
        )

    def has_view_permission(self, request, obj=None):
        allowed = super().has_view_permission(request, obj)
        return allowed and (
            obj is None
            or self.access_policy.has_access(request.user, self._patient_for_object(obj))
        )

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        return allowed and (obj is None or self._can_write_object(request, obj))

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        return allowed and (obj is None or self._can_write_object(request, obj))

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and not self._can_write_object(request, obj):
            return [field.name for field in obj._meta.fields] + [
                field.name for field in obj._meta.many_to_many
            ]
        return super().get_readonly_fields(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "patient":
            kwargs["queryset"] = self.access_policy.queryset(request.user, operation="write")
        elif db_field.name == "health_screening":
            from apps.clinical.health_screening.models import HealthScreening

            kwargs["queryset"] = HealthScreening.objects.filter(
                patient__in=self.access_policy.queryset(request.user, operation="write")
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if change:
            # The existing object was obtained through get_queryset; verify
            # again so a crafted POST cannot reassign it to another patient.
            if not self._can_write_object(request, obj):
                raise PermissionDenied("You do not have write access to this patient.")
        elif not self.access_policy.has_access(
            request.user, self._patient_for_object(obj), operation="write"
        ):
            raise PermissionDenied("You do not have write access to this patient.")
        super().save_model(request, obj, form, change)

    def get_inline_instances(self, request, obj=None):
        if obj is not None and not self._can_write_object(request, obj):
            return []
        return super().get_inline_instances(request, obj)


class PatientAdminMixin(PatientScopedAdminMixin):
    patient_lookup = ""

    def _patient_for_object(self, obj):
        return obj

    def has_add_permission(self, request):
        return super().has_add_permission(request) and (
            request.user.is_superuser
            or request.user.has_perm("patients.create_patient_records")
        )
