import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient
from apps.clinical.patients.models import Patient
from apps.clinical.health_screening.models import Observation, QuestionnaireResponse
from apps.clinical.health_screening.fhir_import_formats import decode_fhir, merge_fhir, fetch_rest_fhir

ROOT = Path(__file__).resolve().parents[1]
NS = "http://hl7.org/fhir"


def xml_from_json(resource):
    def append(parent, key, value):
        if isinstance(value, list):
            for item in value:
                append(parent, key, item)
            return
        element = ET.SubElement(parent, "{" + NS + "}" + key)
        if isinstance(value, dict):
            if "resourceType" in value:
                element.append(build(value))
            else:
                for name, item in value.items():
                    append(element, name, item)
        else:
            element.set("value", str(value).lower() if isinstance(value, bool) else str(value))
    def build(value):
        element = ET.Element("{" + NS + "}" + value["resourceType"])
        for key, item in value.items():
            if key != "resourceType":
                append(element, key, item)
        return element
    return ET.tostring(build(resource), encoding="utf-8", xml_declaration=True)


def test_golden_xml_preserves_all_resources_and_primitive_types():
    bundle = json.loads((ROOT / "artifacts/golden_patient/golden_patient.fhir.json").read_text(encoding="utf-8"))
    assert decode_fhir(xml_from_json(bundle), "xml") == bundle


def test_xml_preserves_singleton_arrays_false_zero_and_extensions():
    xml = b'<Patient xmlns="http://hl7.org/fhir"><id value="xml-test"/><active value="false"/><name><family value="Synthetic"/><given value="Golden"/></name><birthDate value="1961-02-14" id="dob"><extension url="https://example.org/source"><valueString value="synthetic"/></extension></birthDate></Patient>'
    data = decode_fhir(xml)
    assert data["active"] is False
    assert data["name"] == [{"family": "Synthetic", "given": ["Golden"]}]
    assert data["_birthDate"]["id"] == "dob"
    assert data["_birthDate"]["extension"][0]["valueString"] == "synthetic"
    observation = decode_fhir('<Observation xmlns="http://hl7.org/fhir"><status value="final"/><code><text value="synthetic"/></code><valueInteger value="0"/></Observation>')
    assert observation["valueInteger"] == 0


@pytest.mark.parametrize("raw", [
    '<!DOCTYPE Patient [<!ENTITY x SYSTEM "file:///secret">]><Patient xmlns="http://hl7.org/fhir"/>',
    '<Patient/>',
    '<Patient xmlns="http://hl7.org/fhir"><active value="yes"/></Patient>',
    '<Patient xmlns="http://hl7.org/fhir"><active value="true"/><active value="false"/></Patient>',
    '<Patient xmlns="http://hl7.org/fhir"><unknown value="1"/></Patient>',
])
def test_rejects_unsafe_or_malformed_xml(raw):
    with pytest.raises(ValueError):
        decode_fhir(raw)


def test_merge_rejects_conflicting_ids_before_import_and_deduplicates_identical_entries():
    patient = {"resourceType": "Patient", "id": "shared", "gender": "male"}
    assert len(merge_fhir([patient, patient])["entry"]) == 1
    with pytest.raises(ValueError, match="衝突"):
        merge_fhir([patient, {**patient, "gender": "female"}])


@pytest.fixture
def import_client(db):
    user = User.objects.create_user(username="fhir-format-importer")
    user.user_permissions.add(Permission.objects.get(content_type__app_label="health_screening", codename="import_clinical_records"))
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@override_settings(FHIR_DEFAULT_ORIGIN_NAMESPACE="test:formats:inbox")
def test_multifile_preview_has_no_writes_and_import_resolves_cross_file_patient(import_client):
    bundle = json.loads((ROOT / "artifacts/golden_patient/golden_patient.fhir.json").read_text(encoding="utf-8"))
    patient_bundle = {**bundle, "entry": bundle["entry"][:1]}
    observations_bundle = {**bundle, "entry": bundle["entry"][1:]}
    def files():
        return [SimpleUploadedFile("patient.fhir", json.dumps(patient_bundle).encode()), SimpleUploadedFile("clinical.xml", xml_from_json(observations_bundle))]
    initial_count = Patient.objects.count()
    preview = import_client.post("/api/health-screening/fhir-preview/", {"files": files()}, format="multipart")
    assert preview.status_code == 200, preview.data
    assert preview.data["totalResources"] == 44
    assert preview.data["byType"]["Observation"] == 40
    assert Patient.objects.count() == initial_count
    imported = import_client.post("/api/health-screening/fhir-import/", {"files": files()}, format="multipart")
    assert imported.status_code == 201, imported.data
    assert imported.data["error_count"] == 0
    assert imported.data["created_patients"] == 1
    assert imported.data["created_observations"] == 40


@pytest.mark.parametrize("input_format", ["json", "xml"])
@override_settings(FHIR_DEFAULT_ORIGIN_NAMESPACE="test:formats:inbox")
def test_reimport_reports_only_new_observations_and_responses(import_client, input_format):
    path = ROOT / "artifacts/golden_patient/golden_patient.fhir.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if input_format == "json" else path.with_suffix(".xml").read_text(encoding="utf-8")
    request = {"fhir_data": payload, "format": input_format}
    first = import_client.post("/api/health-screening/fhir-import/", request, format="json")
    assert first.status_code == 201, first.data
    assert first.data["created_observations"] == 40
    assert first.data["created_questionnaire_responses"] == 1
    patient_id = first.data["primary_patient_id"]
    second = import_client.post("/api/health-screening/fhir-import/", request, format="json")
    assert second.status_code == 201, second.data
    assert second.data["success_count"] == 44
    assert second.data["error_count"] == 0
    assert second.data["created_patients"] == 0
    assert second.data["created_screenings"] == 0
    assert second.data["created_observations"] == 0
    assert second.data["created_questionnaire_responses"] == 0
    assert second.data["primary_patient_id"] == patient_id
    assert Observation.objects.filter(patient_id=patient_id).count() == 40
    assert QuestionnaireResponse.objects.filter(patient_id=patient_id).count() == 1


def test_malformed_second_file_prevents_all_writes(import_client):
    count = Patient.objects.count()
    files = [SimpleUploadedFile("patient.json", b'{"resourceType":"Patient","id":"safe"}'), SimpleUploadedFile("bad.xml", b'<bad>')]
    response = import_client.post("/api/health-screening/fhir-import/", {"files": files}, format="multipart")
    assert response.status_code == 400
    assert "bad.xml" in response.data["detail"]
    assert Patient.objects.count() == count


def test_viewer_cannot_preview_files_or_contact_rest_endpoint(db):
    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username="fhir-viewer"))
    with patch("apps.clinical.health_screening.fhir_import_formats.requests.Session") as session:
        response = client.post("/api/health-screening/fhir-preview/", {"url": "https://trusted.example/fhir/Patient"}, format="json")
        assert response.status_code == 403
        session.assert_not_called()


def _response(document, status=200):
    response = MagicMock()
    response.__enter__.return_value = response
    response.status_code = status
    response.iter_content.return_value = [json.dumps(document).encode()]
    return response


@override_settings(FHIR_IMPORT_ALLOWED_ORIGINS=["https://trusted.example"])
def test_rest_fetch_follows_same_origin_pages_and_sends_only_explicit_token():
    first = {"resourceType": "Bundle", "type": "searchset", "entry": [{"resource": {"resourceType": "Patient", "id": "remote-a"}}], "link": [{"relation": "next", "url": "?page=2"}]}
    second = {"resourceType": "Bundle", "type": "searchset", "entry": [{"resource": {"resourceType": "Patient", "id": "remote-b"}}]}
    with patch("apps.clinical.health_screening.fhir_import_formats.requests.Session") as factory:
        session = factory.return_value.__enter__.return_value
        session.get.side_effect = [_response(first), _response(second)]
        data = fetch_rest_fhir("https://trusted.example/fhir/Patient", "synthetic-token")
        assert [entry["resource"]["id"] for entry in data["entry"]] == ["remote-a", "remote-b"]
        assert session.get.call_count == 2
        assert session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer synthetic-token"
        assert session.get.call_args.kwargs["allow_redirects"] is False
        assert session.trust_env is False


@override_settings(FHIR_IMPORT_ALLOWED_ORIGINS=["https://trusted.example"])
def test_rest_rejects_untrusted_origin_and_cross_origin_paging_without_leaking_token():
    with patch("apps.clinical.health_screening.fhir_import_formats.requests.Session") as factory:
        with pytest.raises(ValueError, match="尚未啟用"):
            fetch_rest_fhir("http://169.254.169.254/latest/meta-data/")
        factory.assert_not_called()
        session = factory.return_value.__enter__.return_value
        session.get.return_value = _response({"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": "remote"}}], "link": [{"relation": "next", "url": "https://untrusted.example/steal"}]})
        with pytest.raises(ValueError, match="跨來源"):
            fetch_rest_fhir("https://trusted.example/fhir/Patient", "synthetic-token")
        assert session.get.call_count == 1


@override_settings(FHIR_IMPORT_ALLOWED_ORIGINS=["https://trusted.example"])
def test_rest_rejects_redirect_and_does_not_echo_token_or_url():
    with patch("apps.clinical.health_screening.fhir_import_formats.requests.Session") as factory:
        factory.return_value.__enter__.return_value.get.return_value = _response({}, status=302)
        with pytest.raises(ValueError, match="HTTP 302") as error:
            fetch_rest_fhir("https://trusted.example/fhir/Patient", "synthetic-token")
        assert "synthetic-token" not in str(error.value)


@override_settings(FHIR_IMPORT_ALLOWED_ORIGINS=["https://trusted.example"])
def test_rest_xml_preview_can_be_confirmed_without_refetch(import_client):
    xml = b'<Patient xmlns="http://hl7.org/fhir"><id value="remote-xml"/><identifier><system value="https://example.org/synthetic-mrn"/><value value="REST-SYNTHETIC-001"/></identifier><name><family value="Synthetic"/></name><gender value="male"/><birthDate value="1961-02-14"/></Patient>'
    with patch("apps.clinical.health_screening.fhir_import_formats.requests.Session") as factory:
        session = factory.return_value.__enter__.return_value
        response = _response({})
        response.iter_content.return_value = [xml]
        session.get.return_value = response
        preview = import_client.post("/api/health-screening/fhir-preview/", {"url": "https://trusted.example/fhir/Patient/remote-xml"}, format="json")
        assert preview.status_code == 200, preview.data
        assert preview.data["byType"] == {"Patient": 1}
        assert session.get.call_args.kwargs["headers"].get("Authorization") is None
        with override_settings(FHIR_DEFAULT_ORIGIN_NAMESPACE="test:remote:inbox"):
            imported = import_client.post("/api/health-screening/fhir-import/", {"fhir_data": preview.data["fhir_data"]}, format="json")
        assert imported.status_code == 201, imported.data
        assert session.get.call_count == 1


@override_settings(FHIR_IMPORT_ALLOWED_ORIGINS=["https://trusted.example"])
def test_rest_ten_page_limit_returns_error_instead_of_truncated_result():
    documents = [{"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": f"page-{index}"}}], "link": [{"relation": "next", "url": f"?page={index + 1}"}]} for index in range(10)]
    with patch("apps.clinical.health_screening.fhir_import_formats.requests.Session") as factory:
        session = factory.return_value.__enter__.return_value
        session.get.side_effect = [_response(document) for document in documents]
        with pytest.raises(ValueError, match="超過 10 頁"):
            fetch_rest_fhir("https://trusted.example/fhir/Patient")
        assert session.get.call_count == 10


def test_file_count_limit_and_duplicate_json_xml_preview(import_client):
    response = import_client.post("/api/health-screening/fhir-preview/", {"files": [SimpleUploadedFile(f"patient-{index}.json", b'{}') for index in range(21)]}, format="multipart")
    assert response.status_code == 400
    assert "最多 20" in response.data["detail"]
    patient = {"resourceType": "Patient", "id": "duplicate-test", "gender": "male"}
    response = import_client.post("/api/health-screening/fhir-preview/", {"files": [SimpleUploadedFile("patient.json", json.dumps(patient).encode()), SimpleUploadedFile("patient.xml", xml_from_json(patient))]}, format="multipart")
    assert response.status_code == 200, response.data
    assert response.data["totalResources"] == 1


def test_saved_golden_json_xml_duplicate_entries_merge_without_false_conflict():
    folder = ROOT / "artifacts/golden_patient"
    json_bundle = decode_fhir((folder / "golden_patient.fhir.json").read_bytes())
    xml_bundle = decode_fhir((folder / "golden_patient.fhir.xml").read_bytes())
    merged = merge_fhir([json_bundle, xml_bundle])
    assert len(merged["entry"]) == 44
    assert [entry["resource"] for entry in merged["entry"]] == [entry["resource"] for entry in json_bundle["entry"]]


def test_xml_decimal_lexical_integer_and_fraction_remain_distinct_for_merging():
    def observation(value):
        return decode_fhir('<Observation xmlns="http://hl7.org/fhir"><id value="precision"/><status value="final"/><code><text value="Synthetic"/></code><valueQuantity><value value="' + value + '"/></valueQuantity></Observation>')
    whole = observation("2")
    fraction = observation("2.0")
    assert type(whole["valueQuantity"]["value"]) is int
    assert type(fraction["valueQuantity"]["value"]) is float
    with pytest.raises(ValueError, match="衝突"):
        merge_fhir([whole, fraction])


def test_saved_golden_json_xml_multipart_preview_deduplicates_without_writes(import_client):
    folder = ROOT / "artifacts/golden_patient"
    initial_count = Patient.objects.count()
    files = [
        SimpleUploadedFile("golden.json", (folder / "golden_patient.fhir.json").read_bytes()),
        SimpleUploadedFile("golden.xml", (folder / "golden_patient.fhir.xml").read_bytes()),
    ]
    response = import_client.post("/api/health-screening/fhir-preview/", {"files": files}, format="multipart")
    assert response.status_code == 200, response.data
    assert response.data["totalResources"] == 44
    assert response.data["byType"] == {"Patient": 1, "Encounter": 1, "Observation": 40, "Condition": 1, "QuestionnaireResponse": 1}
    assert Patient.objects.count() == initial_count
