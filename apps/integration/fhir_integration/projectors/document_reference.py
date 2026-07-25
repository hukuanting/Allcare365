"""DocumentReference Projector — Maps ``patients.PatientDocument`` → FHIR DocumentReference."""
from __future__ import annotations
import base64
from ..fhir_search.query_translator import parse_date_param
from typing import TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import direct_encounter_for_source, note_type_to_loinc
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("DocumentReference")
class DocumentReferenceProjector(BaseProjector):
    resource_type = "DocumentReference"
    profile_key = "us-core-documentreference"
    REQUIRED_NOTE_TYPES = {
        "34117-2": ("history_physical", "History and physical note"),
        "28570-0": ("procedure", "Procedure note"),
        "18748-4": ("diagnostic_imaging", "Diagnostic imaging study"),
        "11502-2": ("laboratory_report", "Laboratory report"),
        "11526-1": ("pathology_report", "Pathology study"),
    }

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientDocument
        qs = PatientDocument.objects.filter(is_active=True)
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved_patient_id = identity.resolve_patient_db_id(patient_scope)
            if not resolved_patient_id:
                return qs.none()
            qs = qs.filter(patient_id=resolved_patient_id)

        rows = list(qs.select_related("patient"))

        if search_params.get("_id"):
            rows = [doc for doc in rows if identity.document_reference_id(doc) == str(search_params["_id"])]
        if search_params.get("category"):
            cat = str(search_params["category"]).lower()
            if "clinical-note" not in cat:
                return []
        if search_params.get("type"):
            token = str(search_params["type"]).split("|")[-1]
            rows = [
                doc
                for doc in rows
                if (type_code := self._doc_type_code(doc)) is not None and type_code[0] == token
            ]
        if search_params.get("date"):
            rows = [doc for doc in rows if self._date_matches(doc.document_date, str(search_params["date"]))]
        if search_params.get("period"):
            rows = [doc for doc in rows if self._date_matches(doc.document_date, str(search_params["period"]))]
        if search_params.get("status"):
            requested = {s.strip().lower() for s in str(search_params["status"]).split(",") if s.strip()}
            if requested and "current" not in requested:
                return []
        return rows

    def optimize_queryset(self, qs):
        return qs.select_related("patient") if hasattr(qs, "select_related") else qs

    def project(self, doc, context: "FHIRContext") -> dict:
        did = identity.document_reference_id(doc)
        pid = identity.patient_id(doc.patient)
        ref = context.reference_builder
        ts = context.terminology
        type_code = self._doc_type_code(doc)
        if type_code is None or not (doc.content or "").strip() or not doc.document_date:
            return None
        code, display = type_code

        content_b64 = base64.b64encode((doc.content or "").encode("utf-8")).decode("ascii")
        resource = {
            "resourceType": "DocumentReference",
            "id": did,
            "meta": MetaBuilder.build(self.profile_key),
            "status": "current",
            "type": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
            "category": [{"coding": [ts.to_fhir_coding("category_docref_clinical_note")]}],
            "subject": ref.patient(pid),
            "date": doc.document_date.isoformat(),
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": content_b64,
                },
                "format": {"system": "http://ihe.net/fhir/ihe.formatcode.fhir/CodeSystem/formatcode", "code": "urn:ihe:pcc:handp:2008"},
            }],
            "context": {"period": {"start": doc.document_date.isoformat()}},
        }

        practitioner = self._persisted_author(doc)
        if practitioner is not None:
            resource["author"] = [ref.practitioner(identity.practitioner_id(practitioner))]

        encounter = direct_encounter_for_source(doc)
        if encounter is not None and encounter.source_screening_id:
            resource["context"]["encounter"] = [
                ref.encounter(identity.encounter_id(encounter.source_screening))
            ]
        return resource

    @classmethod
    def _doc_type_code(cls, doc) -> tuple[str, str] | None:
        if getattr(doc, "loinc_code", ""):
            return doc.loinc_code, getattr(doc, "loinc_display", "") or doc.loinc_code
        for code, (note_type, display) in cls.REQUIRED_NOTE_TYPES.items():
            if getattr(doc, "note_type", "") == note_type:
                return code, display
        return note_type_to_loinc(doc.note_type)

    @staticmethod
    def _persisted_author(doc):
        if not getattr(doc, "created_by_id", None):
            return None
        from apps.clinical.patients.models import Practitioner

        return (
            Practitioner.objects.filter(
                user_id=doc.created_by_id,
                is_active=True,
                status__iexact="active",
            )
            .exclude(first_name="")
            .exclude(last_name="")
            .first()
        )

    @staticmethod
    def _date_matches(dt, date_param: str) -> bool:
        comparator, parsed_date = parse_date_param(date_param)
        current = dt.date() if hasattr(dt, "date") else dt
        if comparator == "ne":
            return current != parsed_date
        if comparator in ("lt", "eb"):
            return current < parsed_date
        if comparator in ("gt", "sa"):
            return current > parsed_date
        if comparator == "le":
            return current <= parsed_date
        if comparator == "ge":
            return current >= parsed_date
        return current == parsed_date

    def supported_search_params(self):
        return {
            "patient": "reference",
            "category": "token",
            "type": "token",
            "date": "date",
            "period": "date",
            "status": "token",
            "_id": "token",
        }
