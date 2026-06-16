"""
FHIR Search Parser — Parse raw query parameters into structured search terms.

Handles FHIR search modifiers, prefixes, and multi-value parameters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import unquote

from ..operation_outcome import FHIRBadRequest
from .search_params import get_params_for


@dataclass
class ParsedSearch:
    """Result of parsing a FHIR search request."""
    resource_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    includes: Set[str] = field(default_factory=set)
    rev_includes: Set[str] = field(default_factory=set)
    count: int = 50
    offset: int = 0
    sort: Optional[str] = None


class SearchParser:
    """
    Parse raw HTTP query parameters into a ``ParsedSearch`` object.

    Usage::

        parsed = SearchParser.parse("Observation", request.GET)
    """

    # Parameters that are handled by the framework, not by projectors
    _FRAMEWORK_PARAMS = {
        "_include", "_revinclude", "_count", "_getpagesoffset",
        "_sort", "_format", "_pretty", "_summary", "_elements",
        "_total", "_contained", "_containedType",
    }

    @classmethod
    def parse(cls, resource_type: str, query_dict: dict) -> ParsedSearch:
        """
        Parameters
        ----------
        resource_type : str
            FHIR resource type (e.g. ``"Observation"``).
        query_dict : dict
            Django ``request.GET`` or similar multi-value dict.
        """
        known_params = get_params_for(resource_type)
        result = ParsedSearch(resource_type=resource_type)

        for key, value in query_dict.items():
            # Handle lists (Django QueryDict)
            if hasattr(query_dict, "getlist"):
                values = query_dict.getlist(key)
            else:
                values = [value] if not isinstance(value, list) else value

            # Framework-level params
            if key in cls._FRAMEWORK_PARAMS:
                cls._handle_framework_param(key, values, result)
                continue

            # Strip modifiers (e.g. "code:text" → "code")
            base_key = key.split(":")[0] if ":" in key else key

            # Validate against known params (lenient: allow unknown for forward compat)
            if base_key not in known_params and base_key not in ("_id",):
                # Lenient mode: skip unknown params instead of 400
                continue

            # Flatten comma-separated values
            flat = []
            for v in values:
                flat.extend(v.split(","))

            # Strip resource prefixes from reference parameters (e.g. "Patient/123" -> "123")
            if base_key in known_params and known_params[base_key].get("type") == "reference":
                flat = [item.split("/")[-1] if "/" in item else item for item in flat]

            result.params[base_key] = ",".join(flat) if len(flat) > 1 else flat[0]

        return result

    @classmethod
    def _handle_framework_param(cls, key: str, values: list, result: ParsedSearch):
        if key == "_include":
            for v in values:
                for token in v.split(","):
                    result.includes.add(token.strip())
        elif key == "_revinclude":
            for v in values:
                for token in v.split(","):
                    result.rev_includes.add(token.strip())
        elif key == "_count":
            try:
                result.count = min(int(values[0]), 500)
            except (ValueError, IndexError):
                pass
        elif key == "_getpagesoffset":
            try:
                result.offset = int(values[0])
            except (ValueError, IndexError):
                pass
        elif key == "_sort":
            result.sort = values[0] if values else None
