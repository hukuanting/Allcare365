"""Export synthetic trial input; never writes to a database."""
import json
import os
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings_security_tests")
import django
django.setup()
from apps.clinical.health_screening.golden_patient import build_golden_patient_bundle

bundle = build_golden_patient_bundle()
replacements = {}
for entry in bundle["entry"]:
    resource = entry["resource"]
    old_id = resource["id"]
    new_id = old_id.replace("golden-risk", "trial-golden-20261010")
    replacements[old_id] = new_id
    replacements[entry["fullUrl"]] = "urn:uuid:" + str(uuid5(NAMESPACE_URL, "allcare365:trial:" + new_id))

def replace(value):
    if isinstance(value, dict):
        return {key: replace(item) for key, item in value.items()}
    if isinstance(value, list):
        return [replace(item) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value.replace("2026-07-15", "2026-10-10"))
    return value

bundle = replace(bundle)
bundle["id"] = "trial-golden-20261010-bundle"
for entry in bundle["entry"]:
    resource = entry["resource"]
    resource["meta"] = {"tag": [{"system": "https://allcare365.local/fhir/CodeSystem/test-data", "code": "synthetic-only", "display": "Synthetic test data; not a real patient"}]}
    if resource["resourceType"] == "Patient":
        resource["identifier"] = [{"use": "usual", "system": "https://allcare365.local/identifier/synthetic-trial-mrn", "value": "SYNTHETIC-GOLDEN-20261010-001"}]
        resource["name"] = [{"use": "official", "family": "Synthetic", "given": ["Golden"], "text": "Golden Synthetic (TEST ONLY)"}]
    if resource["resourceType"] == "Encounter":
        resource["identifier"][0]["value"] = "SYNTHETIC-ENC-20261010-001"
        resource["reasonCode"] = [{"text": "Synthetic risk-engine import trial"}]
    if resource["resourceType"] == "Observation":
        coding = resource["code"]["coding"][0]
        # Local variables are not LOINC codes. AST ULN is a reference limit,
        # not a measured AST result, so use an explicit local concept.
        if coding["code"] == "1916-6":
            coding["code"] = "allcare365-ast-uln"
            coding["display"] = "AST ULN"
            resource["code"]["text"] = "AST ULN"
        if coding["code"].startswith("allcare365-"):
            coding["system"] = "https://allcare365.local/fhir/CodeSystem/risk-input"
        if coding["code"] == "72166-2":
            resource["valueCodeableConcept"] = {"coding": [{"system": "http://snomed.info/sct", "code": "8517006", "display": "Ex-smoker"}], "text": "Former smoker"}
    if resource["resourceType"] == "QuestionnaireResponse":
        resource["questionnaire"] = "https://allcare365.local/fhir/Questionnaire/allcare365-risk-intake-v1"
        updates = {"former_smoker": True, "ever_smoker": True, "cigarettes_per_day": 0, "years_since_quitting": 8}
        for item in resource["item"]:
            if item["linkId"] in updates:
                value = updates[item["linkId"]]
                item["answer"] = [{"valueBoolean" if isinstance(value, bool) else "valueInteger": value}]
path = Path(__file__).with_name("golden_patient.fhir.json")
path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(str(path))

# Matching XML input for exercising the XML upload path.
import xml.etree.ElementTree as ET
FHIR_NS = "http://hl7.org/fhir"
ET.register_namespace("", FHIR_NS)

def xml_resource(resource):
    node = ET.Element("{" + FHIR_NS + "}" + resource["resourceType"])
    def append(parent, key, value):
        if isinstance(value, list):
            for item in value:
                append(parent, key, item)
            return
        child = ET.SubElement(parent, "{" + FHIR_NS + "}" + key)
        if isinstance(value, dict):
            if "resourceType" in value:
                child.append(xml_resource(value))
            else:
                for name, item in value.items():
                    append(child, name, item)
        else:
            child.set("value", str(value).lower() if isinstance(value, bool) else str(value))
    for name, value in resource.items():
        if name != "resourceType":
            append(node, name, value)
    return node

xml_node = xml_resource(bundle)
ET.indent(xml_node, space="  ")
xml_path = path.with_suffix(".xml")
xml_path.write_bytes(ET.tostring(xml_node, encoding="utf-8", xml_declaration=True))
print(str(xml_path))
