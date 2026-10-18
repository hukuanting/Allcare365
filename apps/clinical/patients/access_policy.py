"""Object-level access policies for patient care workflows.

The policy deliberately binds a Django user to a persisted ``Practitioner``
and then to a current ``PatientPractitionerLink``.  It never guesses an
identity from email, MRN, display name, or whichever database row happens to
come first.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from django.db.models import Q, QuerySet
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from .clinical_scope import (
    clinical_patients,
    is_golden_demo_patient,
    risk_selectable_patients,
)
from .models import Patient, PatientPractitionerLink, PatientUserLink


class PatientCareAccessPolicy:
    """Authorize one care relationship without inferring user or patient identity."""

    GLOBAL_PERMISSION = ""
    WRITE_GLOBAL_PERMISSION = ""
    DENY_KEYS = ("patient_data",)
    PERMISSION_DENIED_MESSAGE = "You do not have access to this patient."
    DENY_STRINGS = {
        "deny",
        "denied",
        "false",
        "forbidden",
        "none",
        "no_access",
        "revoked",
    }

    def patient_queryset(self):
        return clinical_patients()

    def resolve_patient(self, identifier: Any) -> Patient:
        """Resolve an exact UUID or unique MRN; ambiguous MRNs fail closed."""

        raw_identifier = str(identifier or "").strip()
        if not raw_identifier:
            raise NotFound("Patient not found.")

        try:
            patient_uuid = uuid.UUID(raw_identifier)
        except (TypeError, ValueError, AttributeError):
            patients = list(
                self.patient_queryset()
                .filter(medical_record_number=raw_identifier)
                .order_by("id")[:2]
            )
            if len(patients) != 1:
                raise NotFound("Patient not found.")
            return patients[0]

        try:
            return self.patient_queryset().get(id=patient_uuid)
        except Patient.DoesNotExist as exc:
            raise NotFound("Patient not found.") from exc

    def require_access(self, user: Any, patient: Patient, *, operation: str = "read") -> Patient:
        """Return ``patient`` when authorized, otherwise raise an HTTP 403."""

        if self.has_access(user, patient, operation=operation):
            return patient
        raise PermissionDenied(self.PERMISSION_DENIED_MESSAGE)

    def has_access(self, user: Any, patient: Patient, *, operation: str = "read") -> bool:
        if not self._is_active_user(user):
            return False

        if getattr(user, "is_superuser", False):
            return True
        if operation != "write" and self.GLOBAL_PERMISSION and user.has_perm(self.GLOBAL_PERMISSION):
            return True
        if operation == "write" and self.WRITE_GLOBAL_PERMISSION and user.has_perm(self.WRITE_GLOBAL_PERMISSION):
            return True

        if operation != "write" and self._has_active_patient_user_link(user, patient):
            return True

        now = timezone.now()
        links = list(
            PatientPractitionerLink.objects.filter(
                patient=patient,
                practitioner__user_id=user.pk,
                practitioner__is_active=True,
                practitioner__status__iexact="active",
                is_active=True,
                status__iexact="active",
                start_at__lte=now,
            )
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
            .only("permissions_json")
        )
        if not links:
            return False

        # A current patient-specific denial wins over another current care-link
        # allowance for the same practitioner.
        if any(self._explicitly_denies_access(link.permissions_json) for link in links):
            return False
        return any(self._allows_operation(link.permissions_json, operation) for link in links)

    def queryset(self, user: Any, *, operation: str = "read", queryset: QuerySet | None = None) -> QuerySet:
        """Return only clinical patients the user may access for ``operation``.

        This is intentionally derived from the same policy as detail access so
        list endpoints cannot disclose records that a subsequent retrieve would
        reject.  JSON denials are evaluated in Python because they take
        precedence over allowances on another current care link.
        """

        source = self.patient_queryset() if queryset is None else queryset
        if not self._is_active_user(user):
            return source.none()
        if getattr(user, "is_superuser", False):
            return source
        if operation != "write" and self.GLOBAL_PERMISSION and user.has_perm(self.GLOBAL_PERMISSION):
            return source
        if operation == "write" and self.WRITE_GLOBAL_PERMISSION and user.has_perm(self.WRITE_GLOBAL_PERMISSION):
            return source

        now = timezone.now()
        linked_ids = PatientPractitionerLink.objects.filter(
            practitioner__user_id=user.pk,
            practitioner__is_active=True,
            practitioner__status__iexact="active",
            is_active=True,
            status__iexact="active",
            start_at__lte=now,
        ).filter(Q(end_at__isnull=True) | Q(end_at__gte=now)).values_list("patient_id", flat=True).distinct()
        permitted_ids = {
            patient_id
            for patient_id in linked_ids
            if self.has_access(user, Patient(id=patient_id), operation=operation)
        }
        if operation != "write":
            permitted_ids.update(
                PatientUserLink.objects.filter(
                    user_id=user.pk,
                    is_active=True,
                    status__iexact="active",
                    start_at__lte=now,
                )
                .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
                .values_list("patient_id", flat=True)
            )
        return source.filter(id__in=permitted_ids)

    @staticmethod
    def _has_active_patient_user_link(user: Any, patient: Patient) -> bool:
        now = timezone.now()
        return PatientUserLink.objects.filter(
            user_id=user.pk,
            patient_id=patient.id,
            is_active=True,
            status__iexact="active",
            start_at__lte=now,
        ).filter(Q(end_at__isnull=True) | Q(end_at__gte=now)).exists()

    # A concise alias is useful to non-DRF callers such as FHIR projection.
    allowed_patient_queryset = queryset

    def allowed_patient_ids(self, user: Any, *, operation: str = "read") -> set:
        return set(self.queryset(user, operation=operation).values_list("id", flat=True))

    @staticmethod
    def _is_active_user(user: Any) -> bool:
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
            return False
        # A suspended ProductUser must lose clinical access even if Django's
        # auth_user row remains active for administrative recovery.
        try:
            product_user = getattr(user, "product_user", None)
        except ObjectDoesNotExist:
            product_user = None
        return product_user is None or str(getattr(product_user, "status", "active")).lower() == "active"

    @staticmethod
    def _allows_operation(permissions: Any, operation: str) -> bool:
        if not isinstance(permissions, Mapping) or "patient_data" not in permissions:
            # Legacy care links predate operation-level grants. They retain
            # their established care access unless an explicit denial exists.
            return True
        value = permissions["patient_data"]
        if value is True:
            return True
        if not isinstance(value, str):
            return False
        normalized = value.strip().lower()
        if operation == "write":
            return normalized in {"write", "read_write", "full", "manage"}
        return normalized in {"read", "read_write", "full", "manage"}

    def _explicitly_denies_access(self, permissions: Any) -> bool:
        if not isinstance(permissions, Mapping):
            return False
        if permissions.get("deny") is True or permissions.get("denied") is True:
            return True
        return any(
            key in permissions and self._is_deny_value(permissions[key])
            for key in self.DENY_KEYS
        )

    def _is_deny_value(self, value: Any) -> bool:
        if value is False:
            return True
        if isinstance(value, str):
            return value.strip().lower() in self.DENY_STRINGS
        if isinstance(value, Mapping):
            if value.get("allowed") is False or value.get("enabled") is False:
                return True
            return any(
                key in value and self._is_deny_value(value[key])
                for key in ("access", "permission", "status")
            )
        return False


class PatientRiskAccessPolicy(PatientCareAccessPolicy):
    """Resolve a patient exactly and authorize a disease-risk assessment."""

    GLOBAL_PERMISSION = "patients.run_all_patient_risk_assessments"
    DENY_KEYS = (
        "risk_analysis",
        "disease_risk_assessment",
        "patient_data",
    )
    PERMISSION_DENIED_MESSAGE = "You do not have access to this patient's risk analysis."

    def patient_queryset(self):
        return risk_selectable_patients(include_golden_demo=True)

    def has_access(self, user: Any, patient: Patient, *, operation: str = "read") -> bool:
        # Golden Patient contains synthetic conformance data only. It is the
        # deliberate shared demo context and never grants access to real PHI.
        if is_golden_demo_patient(patient):
            return bool(
                self._is_active_user(user)
            )
        return super().has_access(user, patient, operation=operation)

    def _explicitly_denies_risk(self, permissions: Any) -> bool:
        return self._explicitly_denies_access(permissions)


class PatientSMARTLaunchAccessPolicy(PatientCareAccessPolicy):
    """Authorize EHR launch context for one exact persisted patient."""

    GLOBAL_PERMISSION = "patients.launch_any_patient_smart_context"
    DENY_KEYS = ("smart_launch", "patient_data")
    PERMISSION_DENIED_MESSAGE = "You do not have access to launch this patient context."


patient_risk_access_policy = PatientRiskAccessPolicy()
patient_smart_launch_access_policy = PatientSMARTLaunchAccessPolicy()


class PatientClinicalAccessPolicy(PatientCareAccessPolicy):
    """Object-level policy for ordinary clinical record APIs."""

    GLOBAL_PERMISSION = "patients.access_all_clinical_records"
    WRITE_GLOBAL_PERMISSION = "patients.edit_all_clinical_records"


patient_clinical_access_policy = PatientClinicalAccessPolicy()
