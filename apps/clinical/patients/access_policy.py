"""Object-level access policies for patient care workflows.

The policy deliberately binds a Django user to a persisted ``Practitioner``
and then to a current ``PatientPractitionerLink``.  It never guesses an
identity from email, MRN, display name, or whichever database row happens to
come first.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from .clinical_scope import (
    clinical_patients,
    is_golden_demo_patient,
    risk_selectable_patients,
)
from .models import Patient, PatientPractitionerLink


class PatientCareAccessPolicy:
    """Authorize one care relationship without inferring user or patient identity."""

    GLOBAL_PERMISSION = ""
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

    def require_access(self, user: Any, patient: Patient) -> Patient:
        """Return ``patient`` when authorized, otherwise raise an HTTP 403."""

        if self.has_access(user, patient):
            return patient
        raise PermissionDenied(self.PERMISSION_DENIED_MESSAGE)

    def has_access(self, user: Any, patient: Patient) -> bool:
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
            return False

        if getattr(user, "is_superuser", False) or (
            self.GLOBAL_PERMISSION and user.has_perm(self.GLOBAL_PERMISSION)
        ):
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
        return True

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

    def has_access(self, user: Any, patient: Patient) -> bool:
        # Golden Patient contains synthetic conformance data only. It is the
        # deliberate shared demo context and never grants access to real PHI.
        if is_golden_demo_patient(patient):
            return bool(
                getattr(user, "is_authenticated", False)
                and getattr(user, "is_active", False)
            )
        return super().has_access(user, patient)

    def _explicitly_denies_risk(self, permissions: Any) -> bool:
        return self._explicitly_denies_access(permissions)


class PatientSMARTLaunchAccessPolicy(PatientCareAccessPolicy):
    """Authorize EHR launch context for one exact persisted patient."""

    GLOBAL_PERMISSION = "patients.launch_any_patient_smart_context"
    DENY_KEYS = ("smart_launch", "patient_data")
    PERMISSION_DENIED_MESSAGE = "You do not have access to launch this patient context."


patient_risk_access_policy = PatientRiskAccessPolicy()
patient_smart_launch_access_policy = PatientSMARTLaunchAccessPolicy()
