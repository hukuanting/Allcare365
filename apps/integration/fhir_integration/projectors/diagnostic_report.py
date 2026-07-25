"""Project persisted laboratory results and clinical notes as DiagnosticReport."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..fhir_search.query_translator import parse_date_param
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity
from ..uscore_templates import (
    direct_encounter_for_source,
    encounter_ref_for_source,
    lab_test_name_to_loinc_key,
    note_type_to_loinc,
)

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


LAB_STATUSES = {
    "registered",
    "preliminary",
    "final",
    "amended",
    "corrected",
    "cancelled",
    "entered-in-error",
    "unknown",
}


@dataclass(frozen=True)
class _DRRow:
    source_type: str
    source: object
    patient_id: str
    effective_dt: str


@ProjectorRegistry.register("DiagnosticReport")
class DiagnosticReportProjector(BaseProjector):
    resource_type = "DiagnosticReport"
    profile_key = "us-core-diagnosticreport-lab"
    supported_profile_keys = [
        "us-core-diagnosticreport-lab",
        "us-core-diagnosticreport-note",
    ]

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import LaboratoryResults
        from apps.clinical.patients.models import PatientDocument

        lab_qs = LaboratoryResults.objects.filter(is_active=True).select_related(
            "health_screening", "health_screening__patient"
        )
        note_qs = PatientDocument.objects.filter(is_active=True).select_related("patient")

        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return []
            lab_qs = lab_qs.filter(health_screening__patient_id=resolved)
            note_qs = note_qs.filter(patient_id=resolved)

        requested_category = self._tokens(search_params.get("category"))
        if requested_category:
            want_lab = bool(requested_category & {"lab", "laboratory", "lp29684-5"})
            want_note = bool(requested_category & {"lp29708-2", "clinical-note"})
            if not want_lab:
                lab_qs = lab_qs.none()
            if not want_note:
                note_qs = note_qs.none()
            if not want_lab and not want_note:
                return []

        if search_params.get("date"):
            lab_qs = self._filter_date_queryset(
                lab_qs, "health_screening__screening_date", str(search_params["date"])
            )
            note_qs = self._filter_date_queryset(
                note_qs, "document_date__date", str(search_params["date"])
            )
        if search_params.get("_lastUpdated"):
            lab_qs = self._filter_date_queryset(lab_qs, "updated_at__date", str(search_params["_lastUpdated"]))
            note_qs = self._filter_date_queryset(note_qs, "updated_at__date", str(search_params["_lastUpdated"]))

        rows = []
        for lab in lab_qs:
            screening = lab.health_screening
            if (
                screening is None
                or not screening.screening_date
                or lab_test_name_to_loinc_key(lab.test_name) is None
                or not _usable_result(lab.value_result)
                or (lab.result_status or "").strip().casefold() not in LAB_STATUSES
            ):
                continue
            rows.append(_DRRow(
                source_type="lab",
                source=lab,
                patient_id=str(screening.patient_id),
                effective_dt=screening.screening_date.isoformat(),
            ))

        for note in note_qs:
            if not note.document_date or not (note.content or "").strip() or note_type_to_loinc(note.note_type) is None:
                continue
            rows.append(_DRRow(
                source_type="note",
                source=note,
                patient_id=str(note.patient_id),
                effective_dt=note.document_date.isoformat(),
            ))

        requested_code = self._tokens(search_params.get("code"))
        if requested_code:
            rows = [row for row in rows if self._row_code(row, context) in requested_code]
        if search_params.get("status"):
            requested_status = self._tokens(search_params["status"])
            rows = [row for row in rows if self._row_status(row) in requested_status]
        if search_params.get("_id"):
            requested_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            rows = [row for row in rows if self._row_id(row) == requested_id]
        return rows

    def project(self, row: _DRRow, context: "FHIRContext") -> dict | None:
        return self._project_lab(row, context) if row.source_type == "lab" else self._project_note(row, context)

    def _project_lab(self, row: _DRRow, context: "FHIRContext") -> dict | None:
        lab = row.source
        loinc_key = lab_test_name_to_loinc_key(lab.test_name)
        status = (lab.result_status or "").strip().casefold()
        if loinc_key is None or status not in LAB_STATUSES or not _usable_result(lab.value_result):
            return None

        ref = context.reference_builder
        resource = {
            "resourceType": "DiagnosticReport",
            "id": identity.diagnostic_report_id(lab),
            "meta": MetaBuilder.build("us-core-diagnosticreport-lab"),
            "status": status,
            "category": [{"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "LAB",
            }]}],
            "code": {
                "coding": [context.terminology.to_fhir_coding(loinc_key)],
                "text": lab.test_name.strip(),
            },
            "subject": ref.patient(identity.patient_id(lab.health_screening.patient)),
            "effectiveDateTime": row.effective_dt,
            "result": [ref.observation(identity.observation_id(lab, "lab"))],
        }

        encounter_ref = encounter_ref_for_source(lab, ref, identity)
        if encounter_ref is not None:
            resource["encounter"] = encounter_ref

        encounter = direct_encounter_for_source(lab)
        performers = []
        if encounter is not None and _projectable_practitioner(encounter.practitioner):
            performers.append(ref.practitioner(identity.practitioner_id(encounter.practitioner)))
            organization = encounter.practitioner.organization
            if _projectable_organization(organization):
                performers.append(ref.organization(identity.organization_id(organization)))
        if performers:
            resource["performer"] = performers
        return resource

    def _project_note(self, row: _DRRow, context: "FHIRContext") -> dict | None:
        note = row.source
        loinc = note_type_to_loinc(note.note_type)
        content = (note.content or "").strip()
        if loinc is None or not content or not note.document_date:
            return None
        code, display = loinc
        ref = context.reference_builder
        resource = {
            "resourceType": "DiagnosticReport",
            "id": identity.diagnostic_report_id(note),
            "meta": MetaBuilder.build("us-core-diagnosticreport-note"),
            "status": "final",
            "category": [{"coding": [context.terminology.to_fhir_coding("category_dr_note_loinc")]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": code, "display": display}],
                "text": display,
            },
            "subject": ref.patient(identity.patient_id(note.patient)),
            "effectiveDateTime": row.effective_dt,
            "issued": row.effective_dt,
            "presentedForm": [{
                "contentType": "text/plain",
                "data": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            }],
        }
        practitioner = _document_author(note)
        if _projectable_practitioner(practitioner):
            resource["performer"] = [ref.practitioner(identity.practitioner_id(practitioner))]
        return resource

    @staticmethod
    def _filter_date_queryset(qs, field_name: str, raw_value: str):
        comparator, parsed_date = parse_date_param(raw_value)
        lookup = {
            "ne": "exact",
            "lt": "lt",
            "eb": "lt",
            "gt": "gt",
            "sa": "gt",
            "le": "lte",
            "ge": "gte",
        }.get(comparator, "exact")
        criteria = {f"{field_name}__{lookup}": parsed_date}
        return qs.exclude(**criteria) if comparator == "ne" else qs.filter(**criteria)

    @staticmethod
    def _tokens(raw_value) -> set[str]:
        if not raw_value:
            return set()
        values = raw_value if isinstance(raw_value, (list, tuple)) else str(raw_value).split(",")
        return {str(value).strip().split("|")[-1].casefold() for value in values if str(value).strip()}

    @staticmethod
    def _row_id(row: _DRRow) -> str:
        return identity.diagnostic_report_id(row.source)

    @staticmethod
    def _row_status(row: _DRRow) -> str:
        return (row.source.result_status or "").strip().casefold() if row.source_type == "lab" else "final"

    @staticmethod
    def _row_code(row: _DRRow, context: "FHIRContext") -> str:
        if row.source_type == "lab":
            key = lab_test_name_to_loinc_key(row.source.test_name)
            return context.terminology.resolve(key).code.casefold() if key else ""
        loinc = note_type_to_loinc(row.source.note_type)
        return loinc[0].casefold() if loinc else ""

    @staticmethod
    def _note_type_to_loinc(note_type: str):
        return note_type_to_loinc(note_type)

    @staticmethod
    def _lab_loinc_from_name(test_name: str):
        return lab_test_name_to_loinc_key(test_name)

    def supported_search_params(self):
        return {
            "patient": "reference",
            "category": "token",
            "code": "token",
            "date": "date",
            "status": "token",
            "_lastUpdated": "date",
            "_id": "token",
        }


def _usable_result(value) -> bool:
    text = str(value or "").strip()
    return bool(text and text.casefold() != "pending")


def _projectable_practitioner(practitioner) -> bool:
    return bool(
        practitioner is not None
        and practitioner.is_active
        and (practitioner.status or "").strip().casefold() == "active"
        and ((practitioner.first_name or "").strip() or (practitioner.last_name or "").strip())
    )


def _projectable_organization(organization) -> bool:
    return bool(
        organization is not None
        and organization.is_active
        and (organization.name or "").strip()
        and organization.name.strip().casefold() != "unknown"
    )


def _document_author(note):
    if not getattr(note, "created_by_id", None):
        return None
    from apps.clinical.patients.models import Practitioner

    return Practitioner.objects.filter(
        user_id=note.created_by_id,
        is_active=True,
        status__iexact="active",
    ).first()
