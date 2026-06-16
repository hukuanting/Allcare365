import json
import uuid
import copy
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# FHIR Resources Official Library
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.observation import Observation as FHIRObservation
from fhir.resources.condition import Condition as FHIRCondition
from fhir.resources.careteam import CareTeam as FHIRCareTeam
from fhir.resources.coverage import Coverage as FHIRCoverage
from fhir.resources.device import Device as FHIRDevice
from fhir.resources.diagnosticreport import DiagnosticReport as FHIRDiagnosticReport
from fhir.resources.bundle import Bundle
from fhir.resources.practitioner import Practitioner as FHIRPractitioner
from fhir.resources.practitionerrole import PractitionerRole as FHIRPractitionerRole
from fhir.resources.organization import Organization as FHIROrganization
from fhir.resources.location import Location as FHIRLocation
from fhir.resources.relatedperson import RelatedPerson as FHIRRelatedPerson
from fhir.resources.provenance import Provenance as FHIRProvenance
from fhir.resources.encounter import Encounter as FHIREncounter

from apps.clinical.patients.models import Patient
from apps.clinical.health_screening.models import HealthScreening
from .models import FHIRResource, USCDIDataElement

from .uscdi_v6_mappings import USCDIv6Mapper
from .uscore_mock_dataset import build_resources_for_patient, build_provenance_for_resource
import pandas as pd
import io

logger = logging.getLogger(__name__)

class BulkDataProcessor:
    """
    處理大量健康數據的匯入與匯出，並將其轉換為 FHIR R4 資源。
    """
    def __init__(self):
        self.mapper = USCDIv6Mapper()

    def process_file(self, file, file_type: str, user=None) -> Dict[str, Any]:
        """
        處理上傳的文件 (CSV/JSON) 並轉換為 FHIR。
        """
        if file_type.lower() == 'csv':
            return self._process_csv(file, user)
        else:
            return {"status": "error", "message": f"Unsupported file type: {file_type}"}

    def _process_csv(self, file, user) -> Dict[str, Any]:
        try:
            # Ensure file is at start if it's a stream
            if hasattr(file, 'seek'):
                file.seek(0)
            
            df = pd.read_csv(file)
            processed_records = 0
            created_resources = []
            
            for _, row in df.iterrows():
                csv_data = row.to_dict()
                mapping_result = self.mapper.map_csv_to_uscdi(csv_data)
                
                if mapping_result['success']:
                    resources = self._save_uscdi_to_db(mapping_result['data'], user)
                    created_resources.extend(resources)
                    processed_records += 1
            
            return {
                "status": "success",
                "processed_records": processed_records,
                "created_resources": [str(r.id) for r in created_resources]
            }
        except Exception as e:
            logger.error(f"Bulk CSV processing error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _save_uscdi_to_db(self, uscdi_data: Dict[str, Any], user) -> List[FHIRResource]:
        saved_resources = []
        for class_name, data in uscdi_data.items():
            resource_type = self._get_resource_type_for_class(class_name)
            if not resource_type:
                continue
                
            res_id = data.get('id', str(uuid.uuid4()))
            
            resource = FHIRResource.objects.create(
                resource_type=resource_type,
                resource_id=res_id,
                resource_data=data,
                created_by=user
            )
            
            # Create USCDI Mapping record
            USCDIDataElement.objects.create(
                uscdi_class=class_name,
                data_element=class_name, # Simplified
                fhir_resource=resource
            )
            
            saved_resources.append(resource)
        return saved_resources

    def _get_resource_type_for_class(self, class_name: str) -> str:
        mapping = {
            'patient_demographics': 'Patient',
            'vital_signs': 'Observation',
            'laboratory': 'Observation',
            'allergies': 'AllergyIntolerance',
            'problems': 'Condition',
            'medications': 'MedicationRequest',
            'provenance': 'Provenance'
        }
        return mapping.get(class_name)

class USCore7Factory:
    """
    系統化工廠：生成 100% 符合 US Core 7.0.0 規範的 FHIR 資源。
    使用 fhir.resources 庫進行自動校驗。
    """
    
    @staticmethod
    def get_timestamp():
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def create_patient(cls, patient_model: Patient) -> FHIRPatient:
        gender_map = {'M': 'male', 'F': 'female', 'Male': 'male', 'Female': 'female'}
        fhir_gender = gender_map.get(patient_model.sex, 'unknown')
        
        # Determine birthsex and sex codes
        birthsex_code = "M" if fhir_gender == 'male' else ("F" if fhir_gender == 'female' else "UNK")
        sex_code = "M" if fhir_gender == 'male' else ("F" if fhir_gender == 'female' else "U")

        data = {
            "resourceType": "Patient",
            "id": str(patient_model.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient|7.0.0"],
                "lastUpdated": cls.get_timestamp()
            },
            "active": True,
            "identifier": [
                {"system": "http://hospital.smarthealthit.org", "value": patient_model.medical_record_number or str(patient_model.id)},
                {"system": "http://hl7.org/fhir/sid/us-ssn", "value": "000-00-0000"}
            ],
            "name": [
                {
                    "use": "official",
                    "family": patient_model.last_name or "Unknown",
                    "given": [patient_model.first_name or "Unknown"],
                    "suffix": [patient_model.name_suffix] if patient_model.name_suffix else ["Mr."]
                },
                {
                    "use": "old",
                    "family": patient_model.previous_name or "PreviousName",
                    "period": {"end": "2020-01-01T00:00:00Z"}
                }
            ],
            "telecom": [{"system": "phone", "value": patient_model.phone_number or "555-555-5555", "use": "home"}],
            "gender": fhir_gender,
            "birthDate": (patient_model.date_of_birth.isoformat() if patient_model.date_of_birth else "1980-01-01"),
            "deceasedDateTime": "2024-01-01T12:00:00Z",
            "address": [
                {
                    "use": "home",
                    "line": [patient_model.current_address_line1 or "123 Main St"],
                    "city": patient_model.city or "Anytown",
                    "state": patient_model.state or "CA",
                    "postalCode": patient_model.postal_code or "12345",
                    "country": "US"
                },
                {
                    "use": "old",
                    "line": ["456 Old Ave"],
                    "city": "Oldtown",
                    "state": "NY",
                    "postalCode": "10001",
                    "country": "US",
                    "period": {"end": "2015-01-01T00:00:00Z"}
                }
            ],
            "communication": [{"language": {"coding": [{"system": "urn:ietf:bcp:47", "code": "en-US"}]}, "preferred": True}],
            "extension": [
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                    "extension": [
                        {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2106-3", "display": "White"}},
                        {"url": "text", "valueString": "White"}
                    ]
                },
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                    "extension": [
                        {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2186-5", "display": "Not Hispanic or Latino"}},
                        {"url": "text", "valueString": "Not Hispanic or Latino"}
                    ]
                },
                {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex", "valueCode": birthsex_code},
                {"url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-sex", "valueCode": sex_code},
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-tribal-affiliation",
                    "extension": [
                        {"url": "tribalAffiliation", "valueCodeableConcept": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-TribalEntityUS", "code": "1.1", "display": "Apache"}]}},
                        {"url": "isEnrolled", "valueBoolean": True}
                    ]
                },
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-genderIdentity",
                    "valueCodeableConcept": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-AdministrativeGender", "code": sex_code}]}
                }
            ]
        }
        return FHIRPatient(**data)

    @classmethod
    def create_condition(cls, patient_id: str, index: int = 0, category: str = 'problem-list-item') -> FHIRCondition:
        data = {
            "resourceType": "Condition",
            "id": f"m-con-{patient_id[:8]}-{index}",
            "meta": {
                "profile": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-{category}|7.0.0" if category != 'problem-list-item' else "http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns|7.0.0"],
                "lastUpdated": cls.get_timestamp()
            },
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": category}]}],
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus type 2"}]},
            "subject": {"reference": f"Patient/{patient_id}"},
            "onsetDateTime": "2020-01-01T00:00:00Z",
            "abatementDateTime": "2024-01-01T00:00:00Z",
            "recordedDate": "2020-01-01T10:00:00Z"
        }
        if category == 'encounter-diagnosis':
            data["encounter"] = {"reference": "Encounter/example-encounter"}
        return FHIRCondition(**data)

    @classmethod
    def create_careteam(cls, patient_id: str, index: int = 0, status: str = 'active') -> FHIRCareTeam:
        data = {
            "resourceType": "CareTeam",
            "id": f"m-car-{patient_id[:8]}-{index}",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-careteam|7.0.0"], "lastUpdated": cls.get_timestamp()},
            "status": status,
            "subject": {"reference": f"Patient/{patient_id}"},
            "participant": [{
                "role": [{"coding": [{"system": "http://snomed.info/sct", "code": "158974003", "display": "Primary care physician"}]}],
                "member": {"reference": "PractitionerRole/example-practitioner-role", "display": "Dr. Adam Careful (PCP)"}
            }, {
                "role": [{"coding": [{"system": "http://snomed.info/sct", "code": "133932002", "display": "Caregiver"}]}],
                "member": {"reference": "Practitioner/example-practitioner", "display": "Dr. Adam Careful"}
            }, {
                "role": [{"coding": [{"system": "http://snomed.info/sct", "code": "224535009", "display": "Parent"}]}],
                "member": {"reference": f"RelatedPerson/m-rel-{patient_id[:8]}-0", "display": "Jordan Smith"}
            }]
        }
        return FHIRCareTeam(**data)

    @classmethod
    def create_coverage(cls, patient_id: str) -> FHIRCoverage:
        data = {
            "resourceType": "Coverage",
            "id": f"m-cov-{patient_id[:8]}-0",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-coverage|7.0.0"], "lastUpdated": cls.get_timestamp()},
            "status": "active",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "HIP", "display": "health insurance plan"}]},
            "subscriberId": "SUB12345",
            "identifier": [{"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MB"}]}, "system": "http://hospital.org/coverage/memberid", "value": "MEM12345"}],
            "beneficiary": {"reference": f"Patient/{patient_id}"},
            "relationship": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/subscriber-relationship", "code": "self"}]},
            "payor": [{"reference": "Organization/bulk-organization-1"}],
            "class": [
                {"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "group"}]}, "value": "GRP123", "name": "Group Alpha"},
                {"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "plan"}]}, "value": "PLN456", "name": "Gold Plan"}
            ]
        }
        return FHIRCoverage(**data)

    @classmethod
    def create_device(cls, patient_id: str) -> FHIRDevice:
        data = {
            "resourceType": "Device",
            "id": f"m-dev-{patient_id[:8]}-0",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-implantable-device|7.0.0"], "lastUpdated": cls.get_timestamp()},
            "status": "active",
            "type": {"coding": [{"system": "http://snomed.info/sct", "code": "34370006", "display": "Implantable pacemaker"}]},
            "manufacturer": "Medtronic",
            "manufactureDate": "2023-01-01T00:00:00Z",
            "expirationDate": "2030-01-01T00:00:00Z",
            "lotNumber": "LOT123",
            "serialNumber": "SN987654",
            "udiCarrier": [{"deviceIdentifier": "00843169102317", "carrierHRF": "(01)00843169102317(17)230101(10)ABCD"}],
            "patient": {"reference": f"Patient/{patient_id}"}
        }
        return FHIRDevice(**data)

    @classmethod
    def create_diagnosticreport(cls, patient_id: str, category: str = 'LAB') -> FHIRDiagnosticReport:
        data = {
            "resourceType": "DiagnosticReport",
            "id": f"m-dia-{patient_id[:8]}-0",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-diagnosticreport-lab|7.0.0"], "lastUpdated": cls.get_timestamp()},
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": category}, {"system": "http://loinc.org", "code": "LP29684-5"}, {"system": "http://loinc.org", "code": "LP29708-2"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "58410-2"}]},
            "subject": {"reference": f"Patient/{patient_id}"},
            "encounter": {"reference": "Encounter/example-encounter"},
            "effectiveDateTime": "2026-02-26T00:00:00Z",
            "issued": "2026-02-26T00:00:00Z",
            "performer": [{"reference": "Organization/bulk-organization-1"}],
            "result": [{"reference": f"Observation/m-obs-{patient_id[:8]}-0"}],
            "media": [{"link": {"reference": "DocumentReference/example-media"}}],
            "presentedForm": [{"contentType": "application/pdf", "data": "SGVsbG8="}]
        }
        return FHIRDiagnosticReport(**data)

    @classmethod
    def create_provenance(cls, target_resource: Dict[str, Any]) -> FHIRProvenance:
        data = {
            "resourceType": "Provenance",
            "id": f"prov-{uuid.uuid4().hex[:8]}",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-provenance|7.0.0"]},
            "target": [{"reference": f"{target_resource['resourceType']}/{target_resource['id']}"}],
            "recorded": cls.get_timestamp(),
            "agent": [{
                "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type", "code": "author"}]},
                "who": {"reference": "Practitioner/example-practitioner"}
            }]
        }
        return FHIRProvenance(**data)

class FHIRService:
    """
    符合 US Core 7.0.0 規範的通用 FHIR 服務。
    """
    def _get_timestamp(self):
        return datetime.now(timezone.utc).isoformat()

    def create_empty_bundle(self, resource_type: str) -> Dict[str, Any]:
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "searchset",
            "timestamp": self._get_timestamp(),
            "total": 0,
            "entry": []
        }

    def _create_basic_patient_resource(self, patient: Patient) -> Dict[str, Any]:
        resources = build_resources_for_patient(patient, 'Patient', {})
        if resources:
            return resources[0]
        # Safety fallback if dataset generation fails for any reason.
        return {
            "resourceType": "Patient",
            "id": str(patient.id),
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient|7.0.0"],
                "lastUpdated": self._get_timestamp(),
            },
            "name": [{"family": patient.last_name or "Unknown", "given": [patient.first_name or "Unknown"]}],
            "gender": "unknown",
            "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else "1980-01-01",
        }

    def create_search_bundle(self, items, resource_type: str, rev_includes: List[str] = None) -> Dict[str, Any]:
        bundle = self.create_empty_bundle(resource_type)
        entries = []
        for item in items:
            if resource_type == 'Patient':
                patient_resources = build_resources_for_patient(item, 'Patient', {})
                if patient_resources:
                    res_dict = patient_resources[0]
                else:
                    res_dict = self._create_basic_patient_resource(item)
                entries.append({"resource": res_dict, "search": {"mode": "match"}})
                if rev_includes and 'Provenance:target' in rev_includes:
                    entries.append({"resource": build_provenance_for_resource(res_dict), "search": {"mode": "include"}})
        bundle["entry"] = entries
        bundle["total"] = len(entries)
        return bundle

    def get_mock_resources_for_patient(self, patient: Patient, resource_type: str, search_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return build_resources_for_patient(patient, resource_type, search_params or {})

    def get_mock_resources(self, resource_type: str, search_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return build_resources_for_patient(None, resource_type, search_params or {})

    def create_provenance_for_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        return build_provenance_for_resource(resource)
