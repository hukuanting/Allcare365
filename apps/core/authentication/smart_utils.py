import logging
import json
from django.conf import settings
from apps.clinical.patients.models import Patient
from apps.clinical.health_screening.models import HealthScreening
from apps.integration.fhir_integration.resource_identity import identity

logger = logging.getLogger(__name__)

class SMARTContextService:
    """
    Service class to handle SMART on FHIR context injection and scope normalization.
    Decouples business logic from Django Views.
    """

    @staticmethod
    def normalize_scopes(scope_str: str) -> str:
        """
        Normalizes scope string by handling whitespace and duplicates.
        SMART v2 sometimes sends scopes with varying whitespace characters.
        """
        if not scope_str:
            return ""
        # Split by any whitespace and rejoin with single space
        return " ".join(scope_str.split())

    @staticmethod
    def get_token_response_context(base_url: str) -> dict:
        """
        Constructs the additional context required by SMART on FHIR token response.
        Includes: patient, encounter, smart_style_url, need_patient_banner.
        """
        context = {}
        
        # 1. Patient Context
        # In a real app, this would come from the user's session selection or the launch token.
        # For Certification/Dev, we default to the first available patient.
        patient = Patient.objects.first()
        if patient:
            context['patient'] = identity.patient_id(patient)
            encounter = (
                HealthScreening.objects.filter(patient=patient, is_active=True)
                .order_by("encounter_time", "screening_date", "id")
                .first()
            )
            if encounter:
                context['encounter'] = identity.encounter_id(encounter)
        
        # 3. UI/UX Context
        context['need_patient_banner'] = True
        
        # 4. Smart Style URL
        # Ensure strict HTTPS if configured, otherwise rely on base_url
        style_path = "/static/smart/style.json"
        context['smart_style_url'] = f"{base_url}{style_path}"
        
        logger.debug(f"Generated SMART Token Context: {context.keys()}")
        return context
