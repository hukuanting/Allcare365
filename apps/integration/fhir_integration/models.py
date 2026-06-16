"""
FHIR R4 Resource Models for ONC Certification
Implements USCDI v6 data standards
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import json
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.observation import Observation as FHIRObservation
from fhir.resources.condition import Condition as FHIRCondition
from fhir.resources.encounter import Encounter as FHIREncounter


class FHIRResource(models.Model):
    """Base model for FHIR resources"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100, unique=True)
    version_id = models.CharField(max_length=50, default="1")
    last_updated = models.DateTimeField(auto_now=True)
    resource_data = models.JSONField()
    
    # ONC Certification Requirements
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ['resource_type', 'resource_id']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"{self.resource_type}/{self.resource_id}"


class FHIRResourceMapping(models.Model):
    """內部資料列與 FHIR Resource 的投影對應。"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, null=True, blank=True, related_name='fhir_resource_mappings')
    fhir_resource_ref = models.ForeignKey(FHIRResource, on_delete=models.SET_NULL, null=True, blank=True, related_name='local_mappings')
    local_table = models.CharField(max_length=100)
    local_id = models.UUIDField()
    fhir_resource_type = models.CharField(max_length=100)
    fhir_resource_id = models.CharField(max_length=150)
    profile_url = models.URLField(max_length=500, blank=True, default='')
    fhir_json = models.JSONField(default=dict, blank=True)
    sync_status = models.CharField(max_length=50, default='pending')
    last_synced_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fhir_resource_mappings'
        db_table_comment = '內部 relational schema 到 FHIR R4/US Core resource 的投影對應；保存 profile、FHIR JSON 與同步狀態。FHIR 對應：Provenance。'
        indexes = [
            models.Index(fields=['local_table', 'local_id']),
            models.Index(fields=['fhir_resource_type', 'fhir_resource_id']),
            models.Index(fields=['patient', 'fhir_resource_type']),
            models.Index(fields=['sync_status']),
        ]
        unique_together = ['local_table', 'local_id', 'fhir_resource_type']


class AuditLog(models.Model):
    """安全與醫療資料稽核紀錄。"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50)
    target_table = models.CharField(max_length=100, blank=True, default='')
    target_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metadata_json = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'audit_logs'
        db_table_comment = '系統稽核紀錄；保存 create/read/update/delete/export/import/login/disease_risk_assess 等行為。FHIR 對應：AuditEvent、Provenance。'
        indexes = [
            models.Index(fields=['actor_user', '-occurred_at']),
            models.Index(fields=['patient', '-occurred_at']),
            models.Index(fields=['action']),
            models.Index(fields=['target_table', 'target_id']),
        ]


class USCDIDataElement(models.Model):
    """USCDI v6 Data Elements Mapping"""
    USCDI_CLASSES = [
        ('allergies', 'Allergies and Intolerances'),
        ('care_plan', 'Care Plan'),
        ('care_team', 'Care Team Members'),
        ('clinical_notes', 'Clinical Notes'),
        ('clinical_tests', 'Clinical Tests'),
        ('diagnostic_imaging', 'Diagnostic Imaging'),
        ('encounter_information', 'Encounter Information'),
        ('facility_information', 'Facility Information'),
        ('family_health_history', 'Family Health History'),
        ('goals_and_preferences', 'Goals and Preferences'),
        ('health_insurance_information', 'Health Insurance Information'),
        ('health_status_assessments', 'Health Status Assessments'),
        ('immunizations', 'Immunizations'),
        ('laboratory', 'Laboratory'),
        ('medical_devices', 'Medical Devices'),
        ('medications', 'Medications'),
        ('orders', 'Orders'),
        ('patient_demographics', 'Patient Demographics/Information'),
        ('problems', 'Problems'),
        ('procedures', 'Procedures'),
        ('provenance', 'Provenance'),
        ('vital_signs', 'Vital Signs'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uscdi_class = models.CharField(max_length=50, choices=USCDI_CLASSES)
    data_element = models.CharField(max_length=200)
    fhir_resource = models.ForeignKey(FHIRResource, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['uscdi_class', 'data_element', 'fhir_resource']


class FHIRPatientResource(models.Model):
    """Patient Resource for USCDI Demographics"""
    patient = models.OneToOneField('patients.Patient', on_delete=models.CASCADE)
    fhir_resource = models.OneToOneField(FHIRResource, on_delete=models.CASCADE)
    
    # USCDI v6 Required Demographics
    identifier_system = models.CharField(max_length=200, null=True, blank=True)
    identifier_value = models.CharField(max_length=200, null=True, blank=True)
    
    def to_fhir(self):
        """Convert to FHIR Patient resource using FHIRService"""
        from .services import FHIRService
        service = FHIRService()
        return service._create_basic_patient_resource(self.patient)


class FHIRObservationResource(models.Model):
    """Observation Resource for Vital Signs and Lab Results"""
    health_screening = models.ForeignKey('health_screening.HealthScreening', 
                                       on_delete=models.CASCADE, null=True, blank=True)
    # lab_result = models.ForeignKey('laboratory.LabResult', 
    #                              on_delete=models.CASCADE, null=True, blank=True)
    fhir_resource = models.OneToOneField(FHIRResource, on_delete=models.CASCADE)
    
    # LOINC codes for standardization
    loinc_code = models.CharField(max_length=20, null=True, blank=True)
    loinc_display = models.CharField(max_length=200, null=True, blank=True)
    
    def to_fhir(self):
        """Convert to FHIR Observation resource"""
        if self.health_screening:
            return self._vital_signs_to_fhir()
        # elif self.lab_result:
        #     return self._lab_result_to_fhir()
        return []
    
    def _vital_signs_to_fhir(self):
        """Convert vital signs to FHIR Observation"""
        vital_signs = self.health_screening.vital_signs
        observations = []
        
        # Blood Pressure
        if vital_signs.blood_pressure_systolic and vital_signs.blood_pressure_diastolic:
            bp_data = {
                "resourceType": "Observation",
                "id": f"{self.health_screening.id}-bp",
                "status": "final",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs"
                    }]
                }],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional"
                    }]
                },
                "subject": {
                    "reference": f"Patient/{self.health_screening.patient.id}"
                },
                "effectiveDateTime": self.health_screening.screening_date.isoformat(),
                "component": [
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": float(vital_signs.blood_pressure_systolic),
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    },
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": float(vital_signs.blood_pressure_diastolic),
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    }
                ]
            }
            observations.append(FHIRObservation(**bp_data))
        
        return observations
