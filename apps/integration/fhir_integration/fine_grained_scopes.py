"""SMART v2 fine-grained clinical scope support for ONC g10 testing."""

from __future__ import annotations

from urllib.parse import parse_qs

from .terminology import (
    CONDITION_CATEGORY,
    OBS_CATEGORY,
    USCORE_CONDITION_CATEGORY,
    USCORE_GENERIC_CATEGORY,
)


FINE_GRAINED_CATEGORY_CONSTRAINTS = (
    (
        "Condition",
        CONDITION_CATEGORY,
        "encounter-diagnosis",
        "Condition Encounter Diagnosis",
    ),
    (
        "Condition",
        USCORE_CONDITION_CATEGORY,
        "health-concern",
        "Condition Health Concern",
    ),
    (
        "Condition",
        CONDITION_CATEGORY,
        "problem-list-item",
        "Condition Problem List",
    ),
    (
        "Observation",
        OBS_CATEGORY,
        "procedure",
        "Observation Clinical Test",
    ),
    (
        "Observation",
        OBS_CATEGORY,
        "laboratory",
        "Observation Laboratory",
    ),
    (
        "Observation",
        OBS_CATEGORY,
        "social-history",
        "Observation Social History",
    ),
    (
        "Observation",
        OBS_CATEGORY,
        "vital-signs",
        "Observation Vital Signs",
    ),
    (
        "Observation",
        OBS_CATEGORY,
        "survey",
        "Observation Survey",
    ),
    (
        "Observation",
        USCORE_GENERIC_CATEGORY,
        "sdoh",
        "Observation SDOH",
    ),
)


def fine_grained_scope_descriptions(include_read_aliases: bool = True) -> dict[str, str]:
    """Return OAuth scope descriptions for all ONC-required category scopes."""
    descriptions = {}
    for prefix in ("patient", "user"):
        for access in ("rs", "read"):
            if access == "read" and not include_read_aliases:
                continue
            for resource_type, system, code, description in FINE_GRAINED_CATEGORY_CONSTRAINTS:
                scope = f"{prefix}/{resource_type}.{access}?category={system}|{code}"
                label = "Read/search" if access == "rs" else "Read"
                descriptions[scope] = f"{label} {description} ({prefix})"
    return descriptions


def fine_grained_scopes_supported() -> list[str]:
    """Return SMART discovery scope strings for the ONC-required v2 `.rs` scopes."""
    return sorted(
        scope
        for scope in fine_grained_scope_descriptions(include_read_aliases=False)
    )


def granular_scope_selection_options(resource_level_scope: str) -> list[str]:
    """Return sub-resource scopes to show when a resource-level scope is requested."""
    parsed = _parse_resource_level_scope(resource_level_scope)
    if parsed is None:
        return []

    compartment, resource_type, access = parsed
    if resource_type not in {"Condition", "Observation"}:
        return []

    return [
        f"{compartment}/{resource_type}.{access}?category={system}|{code}"
        for candidate_resource, system, code, _description in FINE_GRAINED_CATEGORY_CONSTRAINTS
        if candidate_resource == resource_type
    ]


def is_granular_scope_for_resource(scope: str, resource_type: str) -> bool:
    """Return True if scope is a category-constrained scope for resource_type."""
    parsed = parse_fine_grained_category_scope(scope)
    return bool(parsed and parsed["resource_type"] == resource_type)


def parse_fine_grained_category_scope(scope: str) -> dict[str, str] | None:
    """Parse `patient/Observation.rs?category=system|code` style scopes."""
    scope = (scope or "").strip()
    if "?" not in scope or "/" not in scope:
        return None

    compartment, resource_access_query = scope.split("/", 1)
    if compartment not in {"patient", "user", "system"}:
        return None

    resource_access, query = resource_access_query.split("?", 1)
    if "." not in resource_access:
        return None

    resource_type, access = resource_access.split(".", 1)
    if "r" not in access and "s" not in access and access != "read":
        return None

    params = parse_qs(query, keep_blank_values=True)
    category_values = params.get("category")
    if not category_values or "|" not in category_values[0]:
        return None

    system, code = category_values[0].split("|", 1)
    if not system or not code:
        return None

    return {
        "compartment": compartment,
        "resource_type": resource_type,
        "system": system,
        "code": code,
    }


def _parse_resource_level_scope(scope: str) -> tuple[str, str, str] | None:
    scope = (scope or "").strip()
    if "?" in scope or "/" not in scope or "." not in scope:
        return None
    compartment, resource_access = scope.split("/", 1)
    if compartment not in {"patient", "user", "system"}:
        return None
    resource_type, access = resource_access.split(".", 1)
    if access not in {"rs", "read"}:
        return None
    return compartment, resource_type, access


def allowed_category_tokens(token_scopes: list[str], resource_type: str) -> set[tuple[str, str]]:
    """Extract fine-grained category tokens for a resource from granted scopes."""
    allowed: set[tuple[str, str]] = set()
    for scope in token_scopes:
        parsed = parse_fine_grained_category_scope(scope)
        if parsed and parsed["resource_type"] == resource_type:
            allowed.add((parsed["system"], parsed["code"]))
    return allowed


def has_broad_resource_scope(token_scopes: list[str], resource_type: str) -> bool:
    """Return True when the token grants unconstrained read/search for resource_type."""
    patterns = {
        f"patient/{resource_type}.read",
        f"patient/{resource_type}.rs",
        f"patient/{resource_type}.*",
        "patient/*.read",
        "patient/*.rs",
        "patient/*.*",
        f"user/{resource_type}.read",
        f"user/{resource_type}.rs",
        f"user/{resource_type}.*",
        "user/*.read",
        "user/*.rs",
        "user/*.*",
        f"system/{resource_type}.read",
        f"system/{resource_type}.rs",
        f"system/{resource_type}.*",
        "system/*.read",
        "system/*.rs",
        "system/*.*",
    }
    return any(scope in patterns for scope in token_scopes)


def resource_matches_allowed_categories(
    resource: dict,
    allowed_tokens: set[tuple[str, str]],
) -> bool:
    """Match FHIR `category` codings against allowed `(system, code)` tokens."""
    if not allowed_tokens:
        return True
    for category in resource.get("category") or []:
        for coding in category.get("coding") or []:
            token = (coding.get("system"), coding.get("code"))
            if token in allowed_tokens:
                return True
    return False
