"""Persistent, fail-closed SMART App Launch context handling."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, Grant, RefreshToken

from apps.clinical.health_screening.models import HealthScreening
from apps.clinical.patients.access_policy import patient_smart_launch_access_policy
from apps.clinical.patients.models import Patient, Practitioner
from apps.integration.fhir_integration.resource_identity import identity

from .models import (
    SmartAccessTokenContext,
    SmartAuthorizationContext,
    SmartLaunchContext,
    SmartRefreshTokenContext,
)


logger = logging.getLogger(__name__)


class SMARTContextError(ValueError):
    """A SMART context is missing, expired, reused, or internally inconsistent."""


class SMARTContextService:
    """Single authority for SMART launch, grant, access, and refresh context."""

    @staticmethod
    def normalize_scopes(scope_str: str) -> str:
        if not scope_str:
            return ""
        return " ".join(str(scope_str).split())

    @staticmethod
    def has_patient_scopes(scope_str: str) -> bool:
        return any(
            scope.startswith("patient/")
            for scope in SMARTContextService.normalize_scopes(scope_str).split()
        )

    @staticmethod
    def _digest(secret_value: str) -> str:
        return hashlib.sha256(str(secret_value).encode("utf-8")).hexdigest()

    @classmethod
    def create_launch_context(
        cls,
        *,
        patient_token: str,
        user,
        encounter_token: str | None = None,
        target_launch_uri: str = "",
    ) -> tuple[str, SmartLaunchContext]:
        """Create a short-lived opaque launch secret for one exact patient."""

        if not getattr(user, "is_authenticated", False):
            raise SMARTContextError("An authenticated EHR user is required to create launch context.")

        patient_db_id = identity.resolve_patient_db_id(patient_token)
        if not patient_db_id:
            raise SMARTContextError("The requested patient does not resolve uniquely.")
        patient = Patient.objects.filter(id=patient_db_id, is_active=True).first()
        if patient is None or str(patient.status or "").strip().lower() in {
            "inactive",
            "entered-in-error",
        }:
            raise SMARTContextError("The requested patient is not active.")
        if not patient_smart_launch_access_policy.has_access(user, patient):
            raise SMARTContextError("The EHR user is not authorized for the requested patient.")

        encounter = cls._resolve_encounter(encounter_token, patient) if encounter_token else None
        opaque_token = secrets.token_urlsafe(32)
        ttl_seconds = int(getattr(settings, "SMART_LAUNCH_CONTEXT_TTL_SECONDS", 300))
        launch_context = SmartLaunchContext.objects.create(
            token_digest=cls._digest(opaque_token),
            patient=patient,
            encounter=encounter,
            created_by=user,
            target_launch_uri=str(target_launch_uri or ""),
            expires_at=timezone.now() + timedelta(seconds=max(1, ttl_seconds)),
        )
        return opaque_token, launch_context

    @staticmethod
    def _resolve_encounter(encounter_token: str, patient: Patient) -> HealthScreening:
        raw = str(encounter_token or "").rstrip("/").split("/")[-1].strip()
        if raw.startswith("enc-"):
            raw = raw[4:]
        encounter = HealthScreening.objects.filter(id=raw, patient=patient, is_active=True).first()
        if encounter is None:
            raise SMARTContextError("The requested encounter does not belong to the launch patient.")
        return encounter

    @classmethod
    def resolve_launch_context(
        cls,
        opaque_token: str,
        *,
        user=None,
        for_update: bool = False,
    ) -> SmartLaunchContext:
        if not opaque_token:
            raise SMARTContextError("A persisted SMART launch context is required.")
        if for_update:
            # Do not join the nullable encounter while locking; PostgreSQL
            # rejects FOR UPDATE on the nullable side of an outer join.
            queryset = SmartLaunchContext.objects.select_for_update()
        else:
            queryset = SmartLaunchContext.objects.select_related(
                "patient", "encounter", "created_by"
            )
        launch_context = queryset.filter(token_digest=cls._digest(opaque_token)).first()
        if launch_context is None:
            raise SMARTContextError("The SMART launch context is unknown.")
        if launch_context.consumed_at is not None:
            raise SMARTContextError("The SMART launch context has already been used.")
        if launch_context.expires_at <= timezone.now():
            raise SMARTContextError("The SMART launch context has expired.")
        if user is not None and launch_context.created_by_id != getattr(user, "pk", None):
            raise SMARTContextError("The SMART launch context belongs to a different EHR user.")
        return launch_context

    @classmethod
    def bind_authorization_code(
        cls,
        *,
        authorization_code: str,
        launch_token: str,
        user,
        client_id: str,
    ) -> SmartAuthorizationContext:
        """Consume one launch and bind it to the exact OAuth code and client."""

        if not authorization_code:
            raise SMARTContextError("OAuth authorization code was not created.")
        with transaction.atomic():
            launch_context = cls.resolve_launch_context(
                launch_token,
                user=user,
                for_update=True,
            )
            application = Application.objects.filter(client_id=client_id).first()
            if application is None:
                raise SMARTContextError("The OAuth application does not exist.")
            context = SmartAuthorizationContext.objects.create(
                authorization_code_digest=cls._digest(authorization_code),
                launch_context=launch_context,
                patient=launch_context.patient,
                encounter=launch_context.encounter,
                user=user,
                application=application,
            )
            launch_context.consumed_at = timezone.now()
            launch_context.save(update_fields=["consumed_at"])
        return context

    @classmethod
    def authorization_context_for_code(cls, code: str) -> SmartAuthorizationContext | None:
        if not code:
            return None
        return (
            SmartAuthorizationContext.objects.select_related(
                "patient",
                "encounter",
                "user",
                "application",
            )
            .filter(authorization_code_digest=cls._digest(code))
            .first()
        )

    @staticmethod
    def grant_scope_for_code(code: str) -> str:
        if not code:
            return ""
        grant = Grant.objects.filter(code=code).only("scope").first()
        return grant.scope if grant else ""

    @classmethod
    def authorization_context_for_refresh(cls, refresh_value: str) -> SmartAuthorizationContext | None:
        if not refresh_value:
            return None
        link = (
            SmartRefreshTokenContext.objects.select_related(
                "authorization_context__patient",
                "authorization_context__encounter",
                "authorization_context__user",
                "authorization_context__application",
            )
            .filter(refresh_token__token=refresh_value)
            .first()
        )
        return link.authorization_context if link else None

    @classmethod
    def refresh_scope(cls, refresh_value: str) -> str:
        token = (
            RefreshToken.objects.select_related("access_token")
            .filter(token=refresh_value, revoked__isnull=True)
            .first()
        )
        return token.access_token.scope if token and token.access_token else ""

    @classmethod
    def bind_token_response(
        cls,
        *,
        token_payload: dict,
        authorization_context: SmartAuthorizationContext | None,
    ) -> SmartAuthorizationContext | None:
        """Persist access/refresh links; patient-scoped tokens may never be unbound."""

        scope = cls.normalize_scopes(token_payload.get("scope") or "")
        requires_context = cls.has_patient_scopes(scope)
        if authorization_context is None:
            if requires_context:
                raise SMARTContextError("Patient-scoped access token has no persisted patient context.")
            return None

        access_value = token_payload.get("access_token")
        access_token = (
            AccessToken.objects.select_related("application", "user")
            .filter(token=access_value)
            .first()
        )
        if access_token is None:
            raise SMARTContextError("The issued access token could not be persisted with its SMART context.")
        if (
            access_token.application_id != authorization_context.application_id
            or access_token.user_id != authorization_context.user_id
        ):
            raise SMARTContextError("The issued token identity does not match its authorization context.")

        with transaction.atomic():
            SmartAccessTokenContext.objects.update_or_create(
                access_token=access_token,
                defaults={"authorization_context": authorization_context},
            )
            refresh_value = token_payload.get("refresh_token")
            if refresh_value:
                refresh_token = RefreshToken.objects.filter(token=refresh_value).first()
                if refresh_token is None:
                    raise SMARTContextError(
                        "The issued refresh token could not be persisted with its SMART context."
                    )
                SmartRefreshTokenContext.objects.update_or_create(
                    refresh_token=refresh_token,
                    defaults={"authorization_context": authorization_context},
                )
            if authorization_context.exchanged_at is None:
                authorization_context.exchanged_at = timezone.now()
                authorization_context.save(update_fields=["exchanged_at"])
        return authorization_context

    @classmethod
    def authorization_context_for_access_token(cls, access_token) -> SmartAuthorizationContext | None:
        token_pk = getattr(access_token, "pk", None)
        token_value = getattr(access_token, "token", None)
        filters = {}
        if token_pk is not None:
            filters["access_token_id"] = token_pk
        elif token_value:
            filters["access_token__token"] = token_value
        else:
            return None
        link = (
            SmartAccessTokenContext.objects.select_related(
                "authorization_context__patient",
                "authorization_context__encounter",
                "authorization_context__user",
                "authorization_context__application",
            )
            .filter(**filters)
            .first()
        )
        return link.authorization_context if link else None

    @staticmethod
    def fhir_user_reference(base_url: str, user) -> str | None:
        """Return fhirUser only for an active Practitioner persisted for this exact user."""

        if user is None or getattr(user, "pk", None) is None:
            return None
        practitioner = (
            Practitioner.objects.filter(user_id=user.pk, is_active=True)
            .exclude(status__in=["inactive", "entered-in-error"])
            .first()
        )
        if practitioner is None:
            return None
        return f"{base_url}/fhir/R4/Practitioner/{identity.practitioner_id(practitioner)}"

    @classmethod
    def get_token_response_context(
        cls,
        base_url: str,
        authorization_context: SmartAuthorizationContext | None,
    ) -> dict:
        context = {
            "need_patient_banner": True,
            "smart_style_url": f"{base_url}/static/smart/style.json",
        }
        if authorization_context is None:
            return context
        context["patient"] = identity.patient_id(authorization_context.patient)
        if authorization_context.encounter is not None:
            context["encounter"] = identity.encounter_id(authorization_context.encounter)
        fhir_user = cls.fhir_user_reference(base_url, authorization_context.user)
        if fhir_user:
            context["fhirUser"] = fhir_user
        return context
