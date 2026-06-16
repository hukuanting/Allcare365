"""
FHIR OperationOutcome Error Model.

All FHIR errors are returned as OperationOutcome resources per the spec.
Raise FHIRError subclasses anywhere in the projection/search pipeline;
the view layer catches them and returns proper JSON + HTTP status.
"""
from typing import Optional


class FHIRError(Exception):
    """Base FHIR error that auto-converts to OperationOutcome JSON."""

    http_status: int = 500
    severity: str = "error"
    code: str = "exception"

    def __init__(self, diagnostics: str, code: Optional[str] = None):
        self.diagnostics = diagnostics
        if code:
            self.code = code
        super().__init__(diagnostics)

    def to_operation_outcome(self) -> dict:
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": self.severity,
                    "code": self.code,
                    "diagnostics": self.diagnostics,
                }
            ],
        }


class FHIRBadRequest(FHIRError):
    """400 — invalid search parameter, missing required param, etc."""
    http_status = 400
    code = "invalid"


class FHIRNotFound(FHIRError):
    """404 — resource not found."""
    http_status = 404
    code = "not-found"


class FHIRNotSupported(FHIRError):
    """422 — unsupported search modifier or operation."""
    http_status = 422
    code = "not-supported"


class FHIRServerError(FHIRError):
    """500 — unexpected internal error."""
    http_status = 500
    code = "exception"
