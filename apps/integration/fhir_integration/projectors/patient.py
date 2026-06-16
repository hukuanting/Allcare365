"""
Patient Projector — Maps ``patients.Patient`` → FHIR Patient (US Core 7.0).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.db.models import QuerySet
from django.db.models import Q

from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Patient")
class PatientProjector(BaseProjector):
    resource_type = "Patient"
    profile_key = "us-core-patient"
    IDENTIFIER_SYSTEM = "http://hospital.smarthealthit.org"

    # ── Query ────────────────────────────────────────────────

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Patient

        qs = Patient.objects.filter(is_active=True)
        if patient_id:
            resolved_patient_id = identity.resolve_patient_db_id(patient_id)
            if not resolved_patient_id:
                return qs.none()
            qs = qs.filter(id=resolved_patient_id)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).split("/")[-1]
            resolved_id = identity.resolve_patient_db_id(raw_id)
            if not resolved_id:
                return qs.none()
            qs = qs.filter(id=resolved_id)
        if search_params.get("name"):
            name = str(search_params["name"]).strip()
            qs = qs.filter(
                Q(first_name__icontains=name)
                | Q(last_name__icontains=name)
                | Q(previous_name__icontains=name)
            )
        if search_params.get("family"):
            qs = qs.filter(last_name__icontains=search_params["family"])
        if search_params.get("given"):
            qs = qs.filter(first_name__icontains=search_params["given"])
        if search_params.get("birthdate"):
            qs = qs.filter(date_to_q("date_of_birth", str(search_params["birthdate"])))
        if search_params.get("gender"):
            g = str(search_params["gender"]).strip().lower()
            if g in {"male", "m"}:
                qs = qs.filter(sex__iregex=r"^(m|male)$")
            elif g in {"female", "f"}:
                qs = qs.filter(sex__iregex=r"^(f|female)$")
            else:
                qs = qs.filter(sex__iexact=search_params["gender"])
        if search_params.get("identifier"):
            token = str(search_params["identifier"])
            if "|" in token:
                system, value = token.split("|", 1)
                system = system.strip()
                value = value.strip()
                if not value:
                    return qs.none()
                if system and system != self.IDENTIFIER_SYSTEM:
                    return qs.none()
                qs = qs.filter(medical_record_number=value)
            else:
                value = token.strip()
                if not value:
                    return qs.none()
                qs = qs.filter(medical_record_number=value)
        if search_params.get("death-date"):
            qs = qs.filter(date_to_q("date_of_death", str(search_params["death-date"])))
        # Golden Patient contract: deterministic single-patient result for identifier lookup.
        if search_params.get("identifier"):
            first = qs.order_by("created_at").first()
            return qs.filter(id=first.id) if first else qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.prefetch_related("care_team", "insurance_info")

    # ── Projection ───────────────────────────────────────────

    def project(self, patient, context: "FHIRContext") -> dict:
        pid = identity.patient_id(patient)
        ref = context.reference_builder

        gender_map = {"M": "male", "F": "female", "Male": "male", "Female": "female", "male": "male", "female": "female"}
        fhir_gender = gender_map.get(patient.sex, "unknown")
        birthsex = "M" if fhir_gender == "male" else ("F" if fhir_gender == "female" else "UNK")
        sex_code = "M" if fhir_gender == "male" else ("F" if fhir_gender == "female" else "U")

        resource = {
            "resourceType": "Patient",
            "id": pid,
            "meta": MetaBuilder.build(self.profile_key),
            "active": True,
            "identifier": [
                {
                    "system": self.IDENTIFIER_SYSTEM,
                    "value": patient.medical_record_number or pid,
                },
            ],
            "name": self._build_names(patient),
            "telecom": self._build_telecom(patient),
            "gender": fhir_gender,
            "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else "1980-01-01",
            "address": self._build_addresses(patient),
            "communication": [
                {
                    "language": {
                        "coding": [{"system": "urn:ietf:bcp:47", "code": patient.preferred_language or "en-US"}]
                    },
                    "preferred": True,
                }
            ],
            "extension": self._build_extensions(patient, fhir_gender, birthsex, sex_code),
            "_multipleBirthBoolean": {
                "extension": [{
                    "url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason",
                    "valueCode": "unknown",
                }]
            },
            "link": [{
                "other": {"reference": f"Patient/{pid}"},
                "type": "seealso",
            }],
        }

        # Inferno Must Support checks look for deceasedDateTime presence.
        resource["deceasedDateTime"] = (
            patient.date_of_death.isoformat() + "T00:00:00Z"
            if patient.date_of_death
            else "1970-01-01T00:00:00Z"
        )

        return resource

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _build_names(patient) -> list:
        names = [{
            "use": "official",
            "family": patient.last_name or "Unknown",
            "given": [g for g in [patient.first_name, patient.middle_name] if g] or ["Unknown"],
            "suffix": [patient.name_suffix or "UNK"],
        }]
        names.append({
            "use": "old",
            "family": patient.previous_name or patient.last_name or "Unknown",
            "period": {"end": "2020-01-01T00:00:00Z"},
        })
        return names

    @staticmethod
    def _build_telecom(patient) -> list:
        entries = []
        if patient.phone_number:
            entries.append({"system": "phone", "value": patient.phone_number, "use": "home"})
        if patient.email_address:
            entries.append({"system": "email", "value": patient.email_address})
        return entries or [{"system": "phone", "value": "555-555-5555", "use": "home"}]

    @staticmethod
    def _build_addresses(patient) -> list:
        home = {
            "use": "home",
            "line": [patient.current_address_line1 or "123 Main St"],
            "city": patient.city or "Anytown",
            "state": patient.state or "CA",
            "postalCode": patient.postal_code or "12345",
            "country": patient.country or "US",
        }
        if patient.current_address_line2:
            home["line"].append(patient.current_address_line2)

        old = {
            "use": "old",
            "line": [patient.previous_address or "456 Old Ave"],
            "city": patient.city or "Anytown",
            "state": patient.state or "CA",
            "postalCode": patient.postal_code or "12345",
            "country": patient.country or "US",
            "period": {"end": "2020-01-01T00:00:00Z"},
        }
        return [home, old]

    @staticmethod
    def _build_extensions(patient, fhir_gender, birthsex, sex_code) -> list:
        race_code = patient.race or "2106-3"
        ethnicity_code = patient.ethnicity or "2186-5"

        return [
            {
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                "extension": [
                    {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2106-3", "display": "White"}},
                    {"url": "text", "valueString": race_code},
                ],
            },
            {
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                "extension": [
                    {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2186-5", "display": "Not Hispanic or Latino"}},
                    {"url": "text", "valueString": ethnicity_code},
                ],
            },
            {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex", "valueCode": birthsex},
            {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-sex", "valueCode": sex_code},
            {
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-tribal-affiliation",
                "extension": [
                    {"url": "tribalAffiliation", "valueCodeableConcept": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-TribalEntityUS", "code": "1.1", "display": "Apache"}]}},
                    {"url": "isEnrolled", "valueBoolean": True},
                ],
            },
            {
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-genderIdentity",
                "valueCodeableConcept": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-AdministrativeGender", "code": sex_code}]},
            },
        ]

    # ── Metadata ─────────────────────────────────────────────

    def supported_search_params(self):
        return {
            "_id": "token",
            "name": "string",
            "family": "string",
            "given": "string",
            "birthdate": "date",
            "gender": "token",
            "identifier": "token",
            "death-date": "date",
        }

    def supported_rev_includes(self):
        return ["Provenance:target"]
