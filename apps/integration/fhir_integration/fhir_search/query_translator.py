"""
FHIR Query Translator — Compose Django Q objects from parsed search terms.

This module is a bridge between the FHIR search abstraction and Django ORM.
Not heavily used in Phase 4 because each Projector already implements its own
``query()`` method — but this provides shared utility for date comparators
and token system|code parsing that projectors can import.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, Tuple

from django.db.models import Q


def parse_date_param(value: str) -> Tuple[str, date]:
    """
    Parse a FHIR date search parameter with optional prefix.

    Returns (comparator, date_value).
    Comparators: eq, ne, lt, gt, le, ge, sa, eb, ap
    Default: eq
    """
    prefixes = ("eq", "ne", "lt", "gt", "le", "ge", "sa", "eb", "ap")
    comparator = "eq"
    date_str = value

    for p in prefixes:
        if value.startswith(p) and len(value) > 2:
            comparator = p
            date_str = value[2:]
            break

    # Parse date (supports YYYY, YYYY-MM, YYYY-MM-DD, full ISO)
    try:
        if len(date_str) == 4:
            parsed = date(int(date_str), 1, 1)
        elif len(date_str) == 7:
            parsed = date(int(date_str[:4]), int(date_str[5:7]), 1)
        elif "T" in date_str:
            parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        else:
            parsed = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        parsed = date.today()

    return comparator, parsed


def date_to_q(field_name: str, value: str) -> Q:
    """Build a Django Q object for a FHIR date search parameter."""
    comparator, parsed = parse_date_param(value)
    lookup_map = {
        "eq": "",         # exact
        "ne": "",         # handled differently
        "lt": "__lt",
        "gt": "__gt",
        "le": "__lte",
        "ge": "__gte",
        "sa": "__gt",     # starts after
        "eb": "__lt",     # ends before
    }
    suffix = lookup_map.get(comparator, "")

    if comparator == "ne":
        return ~Q(**{field_name: parsed})
    if comparator == "eq" or not suffix:
        return Q(**{field_name: parsed})
    return Q(**{f"{field_name}{suffix}": parsed})


def parse_token_param(value: str) -> Tuple[Optional[str], str]:
    """
    Parse a FHIR token search parameter ``system|code``.

    Returns (system_or_None, code).
    """
    if "|" in value:
        parts = value.split("|", 1)
        return (parts[0] or None, parts[1])
    return (None, value)


def token_to_q(field_name: str, value: str) -> Q:
    """Build a Django Q for a simple token (just match the code portion)."""
    _system, code = parse_token_param(value)
    return Q(**{field_name: code})


def string_to_q(field_name: str, value: str) -> Q:
    """Case-insensitive contains search for FHIR string params."""
    return Q(**{f"{field_name}__icontains": value})
