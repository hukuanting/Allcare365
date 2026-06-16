"""
CapabilityStatement generator driven by US Core STU7 projection contracts.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .projectors.registry import ProjectorRegistry
from .meta_builder import MetaBuilder
from .projection_contracts import all_projection_contracts


def _supported_profile_urls(projector, contract) -> list[str]:
    urls = list(contract.supported_profile_urls)
    for key in getattr(projector, "supported_profile_keys", [getattr(projector, "profile_key", "")]):
        if not key:
            continue
        try:
            url = MetaBuilder.profile_url(key)
        except ValueError:
            continue
        if url not in urls:
            urls.append(url)
    return urls


def _bulk_group_resource_entry() -> dict:
    return {
        "type": "Group",
        "profile": "http://hl7.org/fhir/StructureDefinition/Group",
        "interaction": [{"code": "read"}],
        "operation": [{
            "name": "$export",
            "definition": "http://hl7.org/fhir/uv/bulkdata/OperationDefinition/group-export",
            "documentation": "FHIR Bulk Data STU2 Group export operation.",
        }],
    }


def generate_capability_statement(base_url: str = "") -> dict:
    """
    Build a FHIR CapabilityStatement from implementation contracts.
    """
    resources = []
    contracts = all_projection_contracts()

    for resource_type, projector in sorted(ProjectorRegistry.all_projectors().items()):
        contract = contracts.get(resource_type)
        if contract is None:
            continue

        search_params = []
        supported_params = projector.supported_search_params()
        for param_name in contract.deterministic_search_params:
            param_type = supported_params.get(param_name)
            if not param_type:
                continue
            search_params.append({"name": param_name, "type": param_type})

        resource_entry = {
            "type": resource_type,
            "profile": f"http://hl7.org/fhir/StructureDefinition/{resource_type}",
            "supportedProfile": _supported_profile_urls(projector, contract),
            "interaction": [{"code": "read"}, {"code": "search-type"}],
        }

        if search_params:
            resource_entry["searchParam"] = search_params

        includes = projector.supported_includes()
        if includes:
            resource_entry["searchInclude"] = includes

        rev_includes = projector.supported_rev_includes()
        if rev_includes:
            resource_entry["searchRevInclude"] = rev_includes

        resources.append(resource_entry)

    if not any(resource["type"] == "Group" for resource in resources):
        resources.append(_bulk_group_resource_entry())

    return {
        "resourceType": "CapabilityStatement",
        "id": "allcare365-capability",
        "name": "Allcare365CapabilityStatement",
        "title": "Allcare365 FHIR Server Capability Statement",
        "status": "active",
        "experimental": False,
        "date": datetime.now(timezone.utc).isoformat(),
        "publisher": "Allcare365",
        "description": "Capability Statement for the Allcare365 FHIR Server supporting US Core 7.0.0",
        "kind": "instance",
        "instantiates": ["http://hl7.org/fhir/us/core/CapabilityStatement/us-core-server"],
        "fhirVersion": "4.0.1",
        "format": ["json", "application/fhir+json", "application/fhir+ndjson"],
        "implementationGuide": ["http://hl7.org/fhir/us/core/ImplementationGuide/hl7.fhir.us.core"],
        "implementation": {
            "description": "Allcare365 FHIR Server supporting US Core 7.0.0",
            "url": base_url or "https://allcare365.com/fhir",
        },
        "rest": [{
            "mode": "server",
            "security": {
                "service": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                        "code": "SMART-on-FHIR",
                    }]
                }],
                "extension": [{
                    "url": "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris",
                    "extension": [
                        {"url": "authorize", "valueUri": f"{base_url}/o/authorize/"},
                        {"url": "token", "valueUri": f"{base_url}/o/token/"},
                    ],
                }],
            },
            "resource": resources,
        }],
    }
