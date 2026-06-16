"""DiagnosticReport Projector for US Core STU7 (lab + note)."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from ..fhir_search.query_translator import parse_date_param
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity
from ..uscore_templates import (
    ORGANIZATION_ID,
    PRACTITIONER_ID,
    backbone_media_ref,
    encounter_ref_for_patient,
    lab_test_name_to_loinc_key,
    note_type_to_loinc,
)

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@dataclass
class _DRRow:
    source_type: str  # "lab" | "note"
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
        from apps.clinical.health_screening.models import HealthScreening
        from apps.clinical.patients.models import PatientDocument

        rows: List[_DRRow] = []

        lab_qs = LaboratoryResults.objects.filter(is_active=True).select_related(
            "health_screening", "health_screening__patient"
        )
        note_qs = PatientDocument.objects.filter(is_active=True).select_related("patient")

        if patient_id:
            lab_qs = lab_qs.filter(health_screening__patient_id=patient_id)
            note_qs = note_qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            pid = search_params["patient"]
            lab_qs = lab_qs.filter(health_screening__patient_id=pid)
            note_qs = note_qs.filter(patient_id=pid)

        if search_params.get("category"):
            category_token = str(search_params["category"]).lower()
            tokens = {
                t.strip().split("|")[-1].lower()
                for t in category_token.split(",")
                if t.strip()
            }
            # Exact-ish matching to avoid returning note rows for lab-only category searches.
            want_lab = bool(tokens & {"lab", "laboratory", "lp29684-5"})
            want_note = bool(tokens & {"lp29708-2", "lp7839-6", "clinical-note"})
            if not want_lab and not want_note:
                return []
            if not want_lab:
                lab_qs = lab_qs.none()
            if not want_note:
                note_qs = note_qs.none()

        if search_params.get("date"):
            comparator, parsed_date = parse_date_param(str(search_params["date"]))
            if comparator == "ne":
                lab_qs = lab_qs.exclude(health_screening__screening_date=parsed_date)
                note_qs = note_qs.exclude(document_date__date=parsed_date)
            elif comparator in ("lt", "eb"):
                lab_qs = lab_qs.filter(health_screening__screening_date__lt=parsed_date)
                note_qs = note_qs.filter(document_date__date__lt=parsed_date)
            elif comparator in ("gt", "sa"):
                lab_qs = lab_qs.filter(health_screening__screening_date__gt=parsed_date)
                note_qs = note_qs.filter(document_date__date__gt=parsed_date)
            elif comparator == "le":
                lab_qs = lab_qs.filter(health_screening__screening_date__lte=parsed_date)
                note_qs = note_qs.filter(document_date__date__lte=parsed_date)
            elif comparator == "ge":
                lab_qs = lab_qs.filter(health_screening__screening_date__gte=parsed_date)
                note_qs = note_qs.filter(document_date__date__gte=parsed_date)
            else:
                lab_qs = lab_qs.filter(health_screening__screening_date=parsed_date)
                note_qs = note_qs.filter(document_date__date=parsed_date)

        if search_params.get("code"):
            token = str(search_params["code"]).split("|")[-1]
            note_map = {
                "11488-4": "consultation",
                "18842-5": "discharge_summary",
                "34878-9": "emergency",
                "34117-2": "history_physical",
                "11504-8": "operative",
                "28570-0": "procedure",
                "11506-3": "progress",
            }
            lab_ids = [
                lab.id
                for lab in lab_qs
                if context.terminology.resolve(self._lab_loinc_from_name(lab.test_name)).code == token
                or token.lower() in (lab.test_name or "").lower()
            ]
            lab_qs = lab_qs.filter(id__in=lab_ids)
            if token in note_map:
                note_qs = note_qs.filter(note_type=note_map[token])
            else:
                note_qs = note_qs.filter(note_type__icontains=token)

        if search_params.get("status"):
            # Projected status is "final"; other statuses should not match.
            requested = {s.strip().lower() for s in str(search_params["status"]).split(",") if s.strip()}
            if requested and "final" not in requested:
                return []

        if search_params.get("_lastUpdated"):
            comparator, parsed_date = parse_date_param(str(search_params["_lastUpdated"]))
            if comparator == "ne":
                lab_qs = lab_qs.exclude(updated_at__date=parsed_date)
                note_qs = note_qs.exclude(updated_at__date=parsed_date)
            elif comparator in ("lt", "eb"):
                lab_qs = lab_qs.filter(updated_at__date__lt=parsed_date)
                note_qs = note_qs.filter(updated_at__date__lt=parsed_date)
            elif comparator in ("gt", "sa"):
                lab_qs = lab_qs.filter(updated_at__date__gt=parsed_date)
                note_qs = note_qs.filter(updated_at__date__gt=parsed_date)
            elif comparator == "le":
                lab_qs = lab_qs.filter(updated_at__date__lte=parsed_date)
                note_qs = note_qs.filter(updated_at__date__lte=parsed_date)
            elif comparator == "ge":
                lab_qs = lab_qs.filter(updated_at__date__gte=parsed_date)
                note_qs = note_qs.filter(updated_at__date__gte=parsed_date)
            else:
                lab_qs = lab_qs.filter(updated_at__date=parsed_date)
                note_qs = note_qs.filter(updated_at__date=parsed_date)

        for lab in lab_qs:
            dt = (
                lab.health_screening.screening_date.isoformat()
                if lab.health_screening and lab.health_screening.screening_date
                else "2025-01-01"
            )
            rows.append(
                _DRRow(
                    source_type="lab",
                    source=lab,
                    patient_id=str(lab.health_screening.patient_id),
                    effective_dt=dt,
                )
            )

        for note in note_qs:
            dt = note.document_date.isoformat() if note.document_date else "2025-01-01T00:00:00Z"
            rows.append(
                _DRRow(
                    source_type="note",
                    source=note,
                    patient_id=str(note.patient_id),
                    effective_dt=dt,
                )
            )

        if search_params.get("_id"):
            target_id = str(search_params["_id"])
            rows = [r for r in rows if self._row_id(r) == target_id]

        return rows

    def project_batch(self, queryset_or_list, context):
        contract = self.projection_contract()
        results = []
        for row in queryset_or_list:
            resource = self.project(row, context)
            if contract is not None:
                from ..projectors.base import _contract_validator, logger
                try:
                    _contract_validator.validate(resource, context, contract)
                except ValueError as exc:
                    logger.warning(
                        "Projection contract warning for DiagnosticReport/%s: %s",
                        resource.get("id"),
                        exc,
                    )
            results.append(resource)
        return results

    def project(self, row: _DRRow, context: "FHIRContext") -> dict:
        ref = context.reference_builder
        ts = context.terminology
        pid = row.patient_id
        media_ref = backbone_media_ref(ref)

        if row.source_type == "lab":
            lab = row.source
            drid = identity.diagnostic_report_id(lab)
            obs_id = identity.observation_id(lab, "lab")
            encounter_id = (
                identity.encounter_id(lab.health_screening)
                if getattr(lab, "health_screening", None)
                else "enc-placeholder"
            )
            return {
                "resourceType": "DiagnosticReport",
                "id": drid,
                "meta": MetaBuilder.build("us-core-diagnosticreport-lab"),
                "status": "final",
                "category": [{
                    "coding": [
                        {"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB", "display": "Laboratory department"},
                        ts.to_fhir_coding("category_dr_lab_loinc"),
                    ]
                }],
                "code": {
                    "coding": [ts.to_fhir_coding(self._lab_loinc_from_name(lab.test_name))],
                    "text": lab.test_name,
                },
                "subject": ref.patient(pid),
                "encounter": ref.encounter(encounter_id),
                "effectiveDateTime": row.effective_dt,
                "issued": row.effective_dt if "T" in row.effective_dt else row.effective_dt + "T00:00:00Z",
                "performer": [
                    ref.practitioner(PRACTITIONER_ID),
                    ref.organization(ORGANIZATION_ID),
                ],
                "result": [ref.observation(obs_id)],
                "media": [{"link": media_ref}],
            }

        note = row.source
        drid = identity.diagnostic_report_id(note)
        loinc_code, loinc_display = self._note_type_to_loinc(note.note_type)
        encoded_note = base64.b64encode((note.content or "").encode("utf-8")).decode("ascii")
        from apps.clinical.health_screening.models import LaboratoryResults
        encounter_ref = encounter_ref_for_patient(str(note.patient_id), ref, identity)
        first_lab = LaboratoryResults.objects.filter(health_screening__patient_id=note.patient_id).first()
        result_ref = ref.observation(identity.observation_id(first_lab, "lab")) if first_lab else ref.observation("obs-placeholder")
        return {
            "resourceType": "DiagnosticReport",
            "id": drid,
            "meta": MetaBuilder.build("us-core-diagnosticreport-note"),
            "status": "final",
            "category": [{
                "coding": [
                    ts.to_fhir_coding("category_dr_note_loinc"),
                    {"system": "http://loinc.org", "code": "LP7839-6", "display": "Pathology study"},
                ]
            }],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": loinc_display}],
                "text": loinc_display,
            },
            "subject": ref.patient(pid),
            "encounter": encounter_ref,
            "effectiveDateTime": row.effective_dt,
            "issued": row.effective_dt,
            "performer": [
                ref.practitioner(PRACTITIONER_ID),
                ref.organization(ORGANIZATION_ID),
            ],
            "result": [result_ref],
            "media": [{"link": media_ref}],
            "presentedForm": [{
                "contentType": "text/plain",
                "data": encoded_note,
            }],
        }

    def _row_id(self, row: _DRRow) -> str:
        return identity.diagnostic_report_id(row.source)

    @staticmethod
    def _note_type_to_loinc(note_type: str) -> tuple[str, str]:
        return note_type_to_loinc(note_type)

    @staticmethod
    def _lab_loinc_from_name(test_name: str) -> str:
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
