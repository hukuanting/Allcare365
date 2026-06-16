"""
Meta Builder — US Core profile meta auto-generation.

Projectors never hand-write profile URLs.  Call:
    MetaBuilder.build("us-core-patient")
"""
from datetime import datetime, timezone
from typing import List, Optional

# Current US Core IG version
_US_CORE_VERSION = "7.0.0"
_US_CORE_BASE = "http://hl7.org/fhir/us/core/StructureDefinition"

# Map logical profile name → full StructureDefinition ID
_PROFILE_MAP: dict[str, str] = {
    # Patient
    "us-core-patient": "us-core-patient",
    # Conditions
    "us-core-condition-problems-health-concerns": "us-core-condition-problems-health-concerns",
    "us-core-condition-encounter-diagnosis": "us-core-condition-encounter-diagnosis",
    # Observations
    "us-core-vital-signs": "us-core-vital-signs",
    "us-core-blood-pressure": "us-core-blood-pressure",
    "us-core-bmi": "us-core-bmi",
    "us-core-body-height": "us-core-body-height",
    "us-core-body-weight": "us-core-body-weight",
    "us-core-body-temperature": "us-core-body-temperature",
    "us-core-heart-rate": "us-core-heart-rate",
    "us-core-respiratory-rate": "us-core-respiratory-rate",
    "us-core-pulse-oximetry": "us-core-pulse-oximetry",
    "us-core-head-circumference": "us-core-head-circumference",
    "us-core-observation-lab": "us-core-observation-lab",
    "us-core-smokingstatus": "us-core-smokingstatus",
    "us-core-observation-clinical-result": "us-core-observation-clinical-result",
    "us-core-observation-screening-assessment": "us-core-observation-screening-assessment",
    "us-core-pediatric-bmi-for-age": "pediatric-bmi-for-age",
    "us-core-pediatric-weight-for-height": "pediatric-weight-for-height",
    "us-core-head-circumference-percentile": "head-occipital-frontal-circumference-percentile",
    # Encounters
    "us-core-encounter": "us-core-encounter",
    # Medications
    "us-core-medication": "us-core-medication",
    "us-core-medicationrequest": "us-core-medicationrequest",
    "us-core-medicationdispense": "us-core-medicationdispense",
    # Allergy
    "us-core-allergyintolerance": "us-core-allergyintolerance",
    # Care
    "us-core-careplan": "us-core-careplan",
    "us-core-careteam": "us-core-careteam",
    # Coverage
    "us-core-coverage": "us-core-coverage",
    # Device
    "us-core-implantable-device": "us-core-implantable-device",
    # DiagnosticReport
    "us-core-diagnosticreport-lab": "us-core-diagnosticreport-lab",
    "us-core-diagnosticreport-note": "us-core-diagnosticreport-note",
    # DocumentReference
    "us-core-documentreference": "us-core-documentreference",
    # Goal
    "us-core-goal": "us-core-goal",
    # Immunization
    "us-core-immunization": "us-core-immunization",
    # Location / Organization / Practitioner / PractitionerRole
    "us-core-location": "us-core-location",
    "us-core-organization": "us-core-organization",
    "us-core-practitioner": "us-core-practitioner",
    "us-core-practitionerrole": "us-core-practitionerrole",
    # Procedure
    "us-core-procedure": "us-core-procedure",
    # Provenance
    "us-core-provenance": "us-core-provenance",
    # RelatedPerson
    "us-core-relatedperson": "us-core-relatedperson",
    # ServiceRequest
    "us-core-servicerequest": "us-core-servicerequest",
    "us-core-specimen": "us-core-specimen",
    
    # Missing from previous Inferno tests
    "us-core-observation-occupation": "us-core-observation-occupation",
    "us-core-observation-pregnancyintent": "us-core-observation-pregnancyintent",
    "us-core-observation-pregnancystatus": "us-core-observation-pregnancystatus",
    "us-core-treatment-intervention-preference": "us-core-treatment-intervention-preference",
    "us-core-care-experience-preference": "us-core-care-experience-preference",
    "us-core-average-blood-pressure": "us-core-average-blood-pressure",
}


class MetaBuilder:
    """Build the ``meta`` element for any US Core resource."""

    @staticmethod
    def build(
        profile_key: str,
        last_updated: Optional[str] = None,
        extra_profiles: Optional[List[str]] = None,
    ) -> dict:
        """
        Parameters
        ----------
        profile_key : str
            Logical profile name, e.g. ``"us-core-patient"``.
        last_updated : str, optional
            ISO timestamp.  Defaults to ``now(UTC)``.
        extra_profiles : list[str], optional
            Additional full profile URLs to append (e.g. base vital-signs).
        """
        sd_id = _PROFILE_MAP.get(profile_key)
        if sd_id is None:
            raise ValueError(f"Unknown profile key: {profile_key!r}")

        profile_url = f"{_US_CORE_BASE}/{sd_id}"
        profiles = [profile_url, f"{profile_url}|{_US_CORE_VERSION}"]
        if extra_profiles:
            profiles.extend(extra_profiles)

        return {
            "profile": profiles,
            "lastUpdated": last_updated or datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def profile_url(profile_key: str) -> str:
        """Return the canonical profile URL (without version) for references."""
        sd_id = _PROFILE_MAP.get(profile_key)
        if sd_id is None:
            raise ValueError(f"Unknown profile key: {profile_key!r}")
        return f"{_US_CORE_BASE}/{sd_id}"
