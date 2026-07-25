"""
Patient Projector — Maps ``patients.Patient`` → FHIR Patient (US Core 7.0).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.db.models import Q
from django.conf import settings

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
    # ── Query ────────────────────────────────────────────────

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Patient
        from apps.clinical.patients.clinical_scope import clinical_patients

        qs = Patient.objects.filter(is_active=True)
        if not getattr(settings, "FHIR_INCLUDE_CONFORMANCE_FIXTURES", False):
            qs = clinical_patients(qs)
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
                qs = qs.filter(medical_record_number=value)
                if system:
                    qs = qs.filter(metadata_json__fhir_mrn_system=system)
            else:
                value = token.strip()
                if not value:
                    return qs.none()
                qs = qs.filter(medical_record_number=value)
        if search_params.get("death-date"):
            qs = qs.filter(date_to_q("date_of_death", str(search_params["death-date"])))
        return qs

    def optimize_queryset(self, qs):
        return qs.prefetch_related("care_team", "insurance_info")

    # ── Projection ───────────────────────────────────────────

    def project(self, patient, context: "FHIRContext") -> dict:
        pid = identity.patient_id(patient)
        resource = {
            "resourceType": "Patient",
            "id": pid,
            "meta": MetaBuilder.build(self.profile_key),
            "active": self._is_active(patient),
        }

        if patient.medical_record_number:
            identifier = {"value": str(patient.medical_record_number)}
            identifier_system = str(
                (patient.metadata_json or {}).get("fhir_mrn_system") or ""
            ).strip()
            if identifier_system:
                identifier["system"] = identifier_system
            resource["identifier"] = [identifier]

        names = self._build_names(patient)
        if names:
            resource["name"] = names

        telecom = self._build_telecom(patient)
        if telecom:
            resource["telecom"] = telecom

        fhir_gender = self._normalize_gender(patient.sex)
        if fhir_gender:
            resource["gender"] = fhir_gender
        else:
            resource["_gender"] = self._data_absent_primitive()

        if patient.date_of_birth:
            resource["birthDate"] = self._date_value(patient.date_of_birth)
        else:
            resource["_birthDate"] = self._data_absent_primitive()

        addresses = self._build_addresses(patient)
        if addresses:
            resource["address"] = addresses

        if patient.preferred_language:
            resource["communication"] = [{
                "language": {
                    "coding": [{
                        "system": "urn:ietf:bcp:47",
                        "code": str(patient.preferred_language),
                    }]
                },
                "preferred": True,
            }]

        extensions = self._build_extensions(patient)
        if extensions:
            resource["extension"] = extensions

        if patient.date_of_death:
            resource["deceasedDateTime"] = self._date_value(patient.date_of_death)

        return resource

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _build_names(patient) -> list:
        names = []
        official = {"use": "official"}
        if patient.last_name:
            official["family"] = str(patient.last_name)
        given = [str(value) for value in (patient.first_name, patient.middle_name) if value]
        if given:
            official["given"] = given
        if patient.name_suffix:
            official["suffix"] = [str(patient.name_suffix)]
        if len(official) > 1:
            names.append(official)
        if patient.previous_name:
            names.append({"use": "old", "text": str(patient.previous_name)})
        return names

    @staticmethod
    def _build_telecom(patient) -> list:
        entries = []
        if patient.phone_number:
            phone = {"system": "phone", "value": str(patient.phone_number)}
            phone_use = str(patient.phone_number_type or "").strip().lower()
            if phone_use in {"home", "work", "temp", "old", "mobile"}:
                phone["use"] = phone_use
            entries.append(phone)
        if patient.email_address:
            entries.append({"system": "email", "value": str(patient.email_address)})
        return entries

    @staticmethod
    def _build_addresses(patient) -> list:
        addresses = []
        current_lines = [
            str(value)
            for value in (patient.current_address_line1, patient.current_address_line2)
            if value
        ]
        if current_lines or patient.city or patient.state or patient.postal_code:
            home = {"use": "home"}
            if current_lines:
                home["line"] = current_lines
            if patient.city:
                home["city"] = str(patient.city)
            if patient.state:
                home["state"] = str(patient.state)
            if patient.postal_code:
                home["postalCode"] = str(patient.postal_code)
            if patient.country:
                home["country"] = str(patient.country)
            addresses.append(home)
        if patient.previous_address:
            addresses.append({
                "use": "old",
                "line": [str(patient.previous_address)],
            })
        return addresses

    @staticmethod
    def _build_extensions(patient) -> list:
        extensions = []
        if patient.race:
            extensions.append({
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                "extension": [{"url": "text", "valueString": str(patient.race)}],
            })
        if patient.ethnicity:
            extensions.append({
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                "extension": [{"url": "text", "valueString": str(patient.ethnicity)}],
            })
        if patient.tribal_affiliation:
            extensions.append({
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-tribal-affiliation",
                "extension": [{
                    "url": "tribalAffiliation",
                    "valueCodeableConcept": {"text": str(patient.tribal_affiliation)},
                }],
            })
        return extensions

    @staticmethod
    def _normalize_gender(value) -> Optional[str]:
        normalized = str(value or "").strip().lower()
        return {
            "m": "male",
            "male": "male",
            "f": "female",
            "female": "female",
            "o": "other",
            "other": "other",
            "u": "unknown",
            "unk": "unknown",
            "unknown": "unknown",
        }.get(normalized)

    @staticmethod
    def _data_absent_primitive() -> dict:
        return {
            "extension": [{
                "url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason",
                "valueCode": "unknown",
            }]
        }

    @staticmethod
    def _date_value(value) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @staticmethod
    def _is_active(patient) -> bool:
        inactive_statuses = {"inactive", "entered-in-error"}
        return bool(patient.is_active) and str(patient.status or "").strip().lower() not in inactive_statuses

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
