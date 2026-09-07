from django.http import JsonResponse

from .fine_grained_scopes import fine_grained_scopes_supported
from .public_url import get_public_base_url


def smart_configuration(request):
    """SMART on FHIR discovery endpoint with CORS support."""
    base_url = get_public_base_url(request)
    issuer_url = f"{base_url}/o"
    fhir_base_url = f"{base_url}/fhir/R4"

    config = {
        "issuer": issuer_url,
        "jwks_uri": f"{fhir_base_url}/jwks",
        "authorization_endpoint": f"{base_url}/o/authorize/",
        "token_endpoint": f"{base_url}/o/token/",
        "registration_endpoint": f"{base_url}/o/register/",
        "management_endpoint": f"{base_url}/o/applications/",
        "introspection_endpoint": f"{base_url}/o/introspect/",
        "revocation_endpoint": f"{base_url}/o/revoke/",
        "token_endpoint_auth_signing_alg_values_supported": ["ES384", "RS384", "RS256"],
        "token_endpoint_auth_methods_supported": [
            "none",
            "client_secret_basic",
            "client_secret_post",
            "private_key_jwt",
        ],
        "id_token_signing_alg_values_supported": ["RS256"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": [
            "openid", "profile", "fhirUser", "launch", "launch/patient",
            "offline_access", "online_access",
            "patient/*.read", "patient/*.rs", "user/*.read", "user/*.rs",
            "system/*.read", "system/*.rs", "system/*.*",
            "patient/Patient.rs", "patient/AllergyIntolerance.rs", "patient/CarePlan.rs",
            "patient/CareTeam.rs", "patient/Condition.rs", "patient/Device.rs",
            "patient/DiagnosticReport.rs", "patient/DocumentReference.rs", "patient/Encounter.rs",
            "patient/Goal.rs", "patient/Immunization.rs", "patient/Location.rs",
            "patient/Medication.rs", "patient/MedicationRequest.rs", "patient/Observation.rs",
            "patient/Organization.rs", "patient/Practitioner.rs", "patient/PractitionerRole.rs",
            "patient/Procedure.rs", "patient/Provenance.rs", "patient/ServiceRequest.rs",
            "patient/Specimen.rs", "patient/Coverage.rs", "patient/MedicationDispense.rs",
            "user/Patient.rs", "user/AllergyIntolerance.rs", "user/CarePlan.rs",
            "user/CareTeam.rs", "user/Condition.rs", "user/Device.rs",
            "user/DiagnosticReport.rs", "user/DocumentReference.rs", "user/Encounter.rs",
            "user/Goal.rs", "user/Immunization.rs", "user/Location.rs",
            "user/Medication.rs", "user/MedicationRequest.rs", "user/Observation.rs",
            "user/Organization.rs", "user/Practitioner.rs", "user/PractitionerRole.rs",
            "user/Procedure.rs", "user/Provenance.rs", "user/ServiceRequest.rs",
            "user/Specimen.rs", "user/Coverage.rs", "user/MedicationDispense.rs",
            *fine_grained_scopes_supported(),
        ],
        "response_types_supported": ["code"],
        "capabilities": [
            "launch-ehr",
            "launch-standalone",
            "client-public",
            "client-confidential-symmetric",
            "client-confidential-asymmetric",
            "sso-openid-connect",
            "context-ehr-patient",
            "context-ehr-encounter",
            "context-standalone-patient",
            "context-style",
            "context-banner",
            "permission-patient",
            "permission-user",
            "permission-v1",
            "permission-v2",
            "permission-offline",
            "authorize-post",
            "smart-app-launch-1",
            "smart-app-launch-2",
        ],
    }

    response = JsonResponse(config)
    # 明確加入 CORS 標頭，解決 Inferno 1.8.03 錯誤
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def onc_certification_api_documentation(request):
    """Public documentation for certification-candidate API inspection."""
    base_url = get_public_base_url(request)
    fhir_base_url = f"{base_url}/fhir/R4"
    documentation = {
        "name": "Allcare 365 Certification Candidate API Technology",
        "certification_status": "not_certified",
        "certification_notice": (
            "This endpoint documents a certification candidate implementation; "
            "it is not evidence of ONC certification."
        ),
        "standards": {
            "fhir": "FHIR R4",
            "us_core": "US Core 7.0.0",
            "smart_app_launch": "SMART App Launch STU2",
            "bulk_data": "FHIR Bulk Data Access STU2",
        },
        "service_base_urls": {
            "fhir_r4": fhir_base_url,
            "smart_configuration": f"{fhir_base_url}/.well-known/smart-configuration",
            "authorization": f"{base_url}/o/authorize/",
            "token": f"{base_url}/o/token/",
            "revocation": f"{base_url}/o/revoke/",
            "introspection": f"{base_url}/o/introspect/",
            "jwks": f"{fhir_base_url}/jwks",
            "bulk_group_export": f"{fhir_base_url}/Group/example-group/$export",
        },
        "client_registration": {
            "single_patient": {
                "public_client": "inferno_public_client",
                "confidential_symmetric_client": "inferno_ehr_client",
                "confidential_asymmetric_client": "inferno_asymmetric_client",
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
            },
            "multi_patient": {
                "backend_services_client": "inferno_bulk_client",
                "jwks_url": "https://inferno.healthit.gov/suites/custom/g10_certification/.well-known/jwks.json",
                "group_id": "example-group",
            },
        },
        "security_attestations": {
            "refresh_token_minimum_lifetime_seconds": 7776000,
            "offline_access_notice": "Authorization UI informs users that offline_access grants refresh-token based continued access.",
            "tls": "The public certification endpoint is served through HTTPS with TLS 1.2 or newer enforced at the public edge/tunnel termination layer.",
            "jwks_caching": "Remote JWKS used for Backend Services client assertions is fetched per validation and is not cached beyond the provider cache-control header.",
            "bulk_since": "Group export accepts the _since parameter and stores it with the export job request.",
            "granular_scopes": "Condition and Observation category-constrained SMART v2 scopes are supported, including clinical-test Observation selection.",
        },
    }
    response = JsonResponse(documentation)
    response["Access-Control-Allow-Origin"] = "*"
    response["Cache-Control"] = "no-store"
    return response
