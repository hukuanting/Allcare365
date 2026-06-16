"""
Reference Builder — Centralized FHIR reference factory.

Projectors NEVER write ``f"Patient/{id}"`` inline.
Instead: ``context.reference_builder.patient(id)``

Future changes (absolute URLs, versioned refs, contained resources)
happen here only — zero projector changes required.
"""


class ReferenceBuilder:
    """
    Build FHIR ``Reference`` dicts with a consistent strategy.

    Parameters
    ----------
    base_url : str
        Server base URL (e.g. ``https://example.trycloudflare.com``).
        When non-empty, ``full_url()`` returns absolute references.
    """

    def __init__(self, base_url: str = ""):
        self._base = base_url.rstrip("/") if base_url else ""

    # ── Helpers ───────────────────────────────────────────────

    def _ref(self, resource_type: str, resource_id: str) -> dict:
        return {"reference": f"{resource_type}/{resource_id}"}

    def full_url(self, resource_type: str, resource_id: str) -> str:
        """Absolute URL for Bundle ``fullUrl``."""
        if self._base:
            return f"{self._base}/{resource_type}/{resource_id}"
        return f"{resource_type}/{resource_id}"

    # ── Resource-specific builders ────────────────────────────

    def patient(self, pid: str) -> dict:
        return self._ref("Patient", pid)

    def encounter(self, eid: str) -> dict:
        return self._ref("Encounter", eid)

    def condition(self, cid: str) -> dict:
        return self._ref("Condition", cid)

    def observation(self, oid: str) -> dict:
        return self._ref("Observation", oid)

    def medication(self, mid: str) -> dict:
        return self._ref("Medication", mid)

    def medication_request(self, mid: str) -> dict:
        return self._ref("MedicationRequest", mid)

    def medication_dispense(self, mid: str) -> dict:
        return self._ref("MedicationDispense", mid)

    def allergy_intolerance(self, aid: str) -> dict:
        return self._ref("AllergyIntolerance", aid)

    def care_plan(self, cid: str) -> dict:
        return self._ref("CarePlan", cid)

    def care_team(self, cid: str) -> dict:
        return self._ref("CareTeam", cid)

    def coverage(self, cid: str) -> dict:
        return self._ref("Coverage", cid)

    def device(self, did: str) -> dict:
        return self._ref("Device", did)

    def diagnostic_report(self, did: str) -> dict:
        return self._ref("DiagnosticReport", did)

    def document_reference(self, did: str) -> dict:
        return self._ref("DocumentReference", did)

    def media(self, mid: str) -> dict:
        return self._ref("Media", mid)

    def goal(self, gid: str) -> dict:
        return self._ref("Goal", gid)

    def immunization(self, iid: str) -> dict:
        return self._ref("Immunization", iid)

    def location(self, lid: str) -> dict:
        return self._ref("Location", lid)

    def organization(self, oid: str) -> dict:
        return self._ref("Organization", oid)

    def practitioner(self, pid: str) -> dict:
        return self._ref("Practitioner", pid)

    def practitioner_role(self, pid: str) -> dict:
        return self._ref("PractitionerRole", pid)

    def procedure(self, pid: str) -> dict:
        return self._ref("Procedure", pid)

    def provenance(self, pid: str) -> dict:
        return self._ref("Provenance", pid)

    def related_person(self, rid: str) -> dict:
        return self._ref("RelatedPerson", rid)

    def service_request(self, sid: str) -> dict:
        return self._ref("ServiceRequest", sid)

    def specimen(self, sid: str) -> dict:
        return self._ref("Specimen", sid)
