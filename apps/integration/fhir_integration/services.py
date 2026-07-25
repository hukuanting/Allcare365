import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

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
from .fhir_context import FHIRContext
from .operation_outcome import FHIRBadRequest, FHIRNotSupported, FHIRServerError
from .projectors.registry import ProjectorRegistry
import apps.integration.fhir_integration.projectors  # noqa: F401 - register projectors
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
        context = self._patient_context(patient)
        return self._project_persisted("Patient", patient, context)

    def create_search_bundle(self, items, resource_type: str, rev_includes: List[str] = None) -> Dict[str, Any]:
        if not ProjectorRegistry.has(resource_type):
            raise FHIRNotSupported(f"No persisted-data projector is registered for {resource_type}.")

        bundle = self.create_empty_bundle(resource_type)
        entries = []
        primary_count = 0
        for item in items:
            context = self._patient_context(item) if resource_type == "Patient" else FHIRContext()
            resource = self._project_persisted(resource_type, item, context)
            entries.append({"resource": resource, "search": {"mode": "match"}})
            primary_count += 1
            if rev_includes and "Provenance:target" in rev_includes:
                provenance = ProjectorRegistry.get("Provenance").for_resource(resource, context)
                if provenance is not None:
                    entries.append({"resource": provenance, "search": {"mode": "include"}})
        bundle["entry"] = entries
        bundle["total"] = primary_count
        return bundle

    def create_provenance_for_resource(
        self,
        resource: Dict[str, Any],
        *,
        context: FHIRContext = None,
    ) -> Dict[str, Any]:
        if not isinstance(resource, dict) or not resource.get("resourceType") or not resource.get("id"):
            raise FHIRBadRequest("Provenance projection requires a persisted resourceType and id.")
        provenance = ProjectorRegistry.get("Provenance").for_resource(
            resource,
            context or FHIRContext(),
        )
        if provenance is None:
            raise FHIRNotSupported(
                "No unique persisted Provenance resource exists for the requested target."
            )
        return provenance

    def _project_persisted(self, resource_type: str, instance: Any, context: FHIRContext) -> Dict[str, Any]:
        if not ProjectorRegistry.has(resource_type):
            raise FHIRNotSupported(f"No persisted-data projector is registered for {resource_type}.")
        try:
            resource = ProjectorRegistry.get(resource_type).project(instance, context)
        except Exception as exc:
            logger.exception("FHIR projection failed for persisted %s data", resource_type)
            raise FHIRServerError(
                f"Unable to project persisted {resource_type} data; no synthetic fallback was used."
            ) from exc
        if not isinstance(resource, dict) or resource.get("resourceType") != resource_type:
            raise FHIRServerError(
                f"Persisted-data projector returned an invalid {resource_type} resource."
            )
        return resource

    @staticmethod
    def _patient_context(patient: Patient) -> FHIRContext:
        context = FHIRContext()
        try:
            context.patient_id = context.identity.patient_id(patient)
        except Exception as exc:
            logger.exception("FHIR identity resolution failed for persisted Patient data")
            raise FHIRServerError(
                "Unable to resolve persisted Patient identity; no synthetic fallback was used."
            ) from exc
        return context
