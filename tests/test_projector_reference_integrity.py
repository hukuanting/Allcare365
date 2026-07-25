import os
import re
import sys
from datetime import date, timedelta

import django
import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")
django.setup()


from django.utils import timezone
from fhirclient.models.careteam import CareTeam as FHIRCareTeam
from fhirclient.models.diagnosticreport import DiagnosticReport as FHIRDiagnosticReport
from fhirclient.models.encounter import Encounter as FHIREncounter
from fhirclient.models.location import Location as FHIRLocation
from fhirclient.models.observation import Observation as FHIRObservation
from fhirclient.models.organization import Organization as FHIROrganization
from fhirclient.models.patient import Patient as FHIRPatient
from fhirclient.models.practitioner import Practitioner as FHIRPractitioner
from fhirclient.models.practitionerrole import PractitionerRole as FHIRPractitionerRole

from apps.clinical.health_screening.models import (
    Encounter as ProductEncounter,
    HealthScreening,
    LaboratoryResults,
    VitalSigns,
)
from apps.clinical.patients.models import (
    InsuranceData,
    Organization,
    Patient,
    PatientDocument,
    PatientPractitionerLink,
    Practitioner,
)
from apps.integration.fhir_integration.fhir_context import FHIRContext
from apps.integration.fhir_integration.models import FHIRResource
from apps.integration.fhir_integration.operation_outcome import FHIRNotSupported
from apps.integration.fhir_integration.projectors.registry import ProjectorRegistry
from apps.integration.fhir_integration.resource_identity import identity
from apps.integration.fhir_integration.services import FHIRService


FHIR_MODELS = {
    "CareTeam": FHIRCareTeam,
    "DiagnosticReport": FHIRDiagnosticReport,
    "Encounter": FHIREncounter,
    "Location": FHIRLocation,
    "Observation": FHIRObservation,
    "Organization": FHIROrganization,
    "Patient": FHIRPatient,
    "Practitioner": FHIRPractitioner,
    "PractitionerRole": FHIRPractitionerRole,
}


def _patient(mrn="REFERENCE-INTEGRITY"):
    return Patient.objects.create(
        first_name="Reference",
        last_name="Integrity",
        date_of_birth=date(1980, 1, 1),
        sex="female",
        medical_record_number=mrn,
        country="",
        preferred_language="",
    )


def _project(resource_type, patient_id=None, params=None):
    context = FHIRContext(patient_id=patient_id)
    projector = ProjectorRegistry.get(resource_type)
    rows = projector.query(patient_id, params or {}, context)
    return projector.project_batch(rows, context)


def _references(value):
    if isinstance(value, dict):
        if isinstance(value.get("reference"), str):
            yield value["reference"]
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


@pytest.mark.django_db
def test_empty_database_does_not_emit_master_or_media_fixtures():
    for resource_type in ("Organization", "Practitioner", "PractitionerRole", "Location", "Media"):
        assert _project(resource_type) == []


@pytest.mark.django_db
def test_persisted_clinical_graph_has_only_resolvable_local_references():
    patient = _patient()
    organization = Organization.objects.create(
        name="Persisted General Hospital",
        identifier="ORG-PERSISTED-001",
        type="Hospital",
        country="US",
    )
    practitioner = Practitioner.objects.create(
        first_name="Avery",
        last_name="Clinician",
        identifier="PRACT-PERSISTED-001",
        organization=organization,
        status="active",
    )
    link = PatientPractitionerLink.objects.create(
        patient=patient,
        practitioner=practitioner,
        role="primary care physician",
        status="active",
    )
    screening = HealthScreening.objects.create(
        patient=patient,
        encounter_type="annual physical",
        encounter_identifier="ENC-PERSISTED-001",
        encounter_time=timezone.now(),
        screening_date=timezone.localdate(),
    )
    ProductEncounter.objects.create(
        patient=patient,
        practitioner=practitioner,
        source_screening=screening,
        encounter_type="outpatient",
        status="finished",
        reason="Annual physical",
        location="Persisted Clinic, Floor 2",
        started_at=screening.encounter_time,
        ended_at=screening.encounter_time + timedelta(hours=1),
    )
    VitalSigns.objects.create(health_screening=screening, heart_rate=72)
    lab = LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="Glucose",
        value_result="92",
        result_unit="mg/dL",
        result_status="final",
    )

    patient_id = identity.patient_id(patient)
    resources = []
    for resource_type in (
        "Patient",
        "Organization",
        "Practitioner",
        "PractitionerRole",
        "Location",
        "Encounter",
        "CareTeam",
        "Observation",
        "DiagnosticReport",
    ):
        resources.extend(_project(resource_type, patient_id))

    keys = {f"{resource['resourceType']}/{resource['id']}" for resource in resources}
    assert f"Organization/{identity.organization_id(organization)}" in keys
    assert f"Practitioner/{identity.practitioner_id(practitioner)}" in keys
    assert f"PractitionerRole/{identity.practitioner_role_id(link)}" in keys
    assert f"Encounter/{identity.encounter_id(screening)}" in keys
    assert f"Location/{identity.location_id('Persisted Clinic, Floor 2')}" in keys
    assert f"Observation/{identity.observation_id(lab, 'lab')}" in keys

    for resource in resources:
        FHIR_MODELS[resource["resourceType"]](resource, strict=True)
        for reference in _references(resource):
            if reference.startswith("urn:") or reference.startswith("http"):
                continue
            assert reference in keys, f"dangling {reference} from {resource['resourceType']}/{resource['id']}"


@pytest.mark.django_db
def test_missing_or_ambiguous_encounter_link_is_omitted_everywhere():
    patient = _patient("AMBIGUOUS-ENCOUNTER")
    screening = HealthScreening.objects.create(patient=patient, screening_date=timezone.localdate())
    VitalSigns.objects.create(health_screening=screening, heart_rate=70)
    patient_id = identity.patient_id(patient)

    observations = _project("Observation", patient_id)
    assert observations and all("encounter" not in resource for resource in observations)
    assert _project("Encounter", patient_id) == []

    for location in ("Clinic A", "Clinic B"):
        ProductEncounter.objects.create(
            patient=patient,
            source_screening=screening,
            encounter_type="outpatient",
            status="finished",
            location=location,
            started_at=timezone.now(),
        )

    observations = _project("Observation", patient_id)
    assert observations and all("encounter" not in resource for resource in observations)
    assert _project("Encounter", patient_id) == []


@pytest.mark.django_db
def test_coverage_payor_must_resolve_to_one_persisted_organization():
    patient = _patient("COVERAGE-PAYOR")
    insurance = InsuranceData.objects.create(
        patient=patient,
        coverage_status="active",
        member_identifier="MEM-PERSISTED",
        payer_identifier="PAYER-PERSISTED",
    )
    context = FHIRContext(patient_id=identity.patient_id(patient))
    projector = ProjectorRegistry.get("Coverage")

    assert projector.project(insurance, context) is None
    organization = Organization.objects.create(
        name="Persisted Payer",
        identifier="PAYER-PERSISTED",
    )
    resource = projector.project(insurance, context)
    assert resource["payor"] == [
        context.reference_builder.organization(identity.organization_id(organization))
    ]

    Organization.objects.create(name="Duplicate Persisted Payer", identifier="PAYER-PERSISTED")
    assert projector.project(insurance, context) is None


@pytest.mark.django_db
def test_document_and_provenance_optional_references_are_persisted_only():
    patient = _patient("DOC-PROVENANCE")
    patient_id = identity.patient_id(patient)
    document = PatientDocument.objects.create(
        patient=patient,
        note_type="progress",
        content="Persisted hospital note.",
        document_date=timezone.now(),
    )
    document_resource = ProjectorRegistry.get("DocumentReference").project(
        document,
        FHIRContext(patient_id=patient_id),
    )
    assert "author" not in document_resource
    assert "encounter" not in document_resource["context"]

    service = FHIRService()
    patient_resource = ProjectorRegistry.get("Patient").project(patient, FHIRContext())
    with pytest.raises(FHIRNotSupported):
        service.create_provenance_for_resource(patient_resource)

    provenance_id = "prov-persisted-reference-integrity"
    target = f"Patient/{patient_id}"
    FHIRResource.objects.create(
        resource_type="Provenance",
        resource_id=provenance_id,
        resource_data={
            "resourceType": "Provenance",
            "id": provenance_id,
            "target": [{"reference": target}],
            "recorded": timezone.now().isoformat(),
            "agent": [{"who": {"reference": target}}],
        },
    )
    assert service.create_provenance_for_resource(patient_resource)["id"] == provenance_id


def test_runtime_projection_source_contains_no_fixture_identifiers():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runtime_paths = [
        os.path.join(root, "apps", "integration", "fhir_integration", "projectors"),
        os.path.join(root, "apps", "integration", "fhir_integration", "services.py"),
        os.path.join(root, "apps", "integration", "fhir_integration", "uscore_templates.py"),
    ]
    forbidden = re.compile(
        r"example-practitioner|example-encounter|bulk-organization-1|bulk-location-1|"
        r"media-example-1|enc-placeholder|obs-placeholder|sreq-placeholder|555-555-",
        re.IGNORECASE,
    )
    for runtime_path in runtime_paths:
        paths = (
            [runtime_path]
            if os.path.isfile(runtime_path)
            else [
                os.path.join(runtime_path, name)
                for name in os.listdir(runtime_path)
                if name.endswith(".py")
            ]
        )
        for path in paths:
            with open(path, encoding="utf-8") as source:
                assert forbidden.search(source.read()) is None, path
