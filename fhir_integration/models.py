"""
FHIR R4 Resource Models for ONC Certification
Implements USCDI v6 data standards
"""
from django.db import models
from django.contrib.auth.models import User
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


class USCDIDataElement(models.Model):
    """USCDI v6 Data Elements Mapping"""
    USCDI_CLASSES = [
        ('demographics', 'Patient Demographics'),
        ('vital_signs', 'Vital Signs'),
        ('laboratory', 'Laboratory'),
        ('medications', 'Medications'),
        ('allergies', 'Allergies and Intolerances'),
        ('conditions', 'Problems'),
        ('procedures', 'Procedures'),
        ('immunizations', 'Immunizations'),
        ('care_team', 'Care Team Members'),
        ('clinical_notes', 'Clinical Notes'),
        ('provenance', 'Provenance'),
        ('smoking_status', 'Smoking Status'),
        ('pediatric', 'Pediatric'),
        ('health_concerns', 'Health Concerns'),
        ('goals', 'Goals'),
        ('assessments', 'Assessments'),
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
        """Convert to FHIR Patient resource"""
        patient_data = {
            "resourceType": "Patient",
            "id": str(self.patient.id),
            "identifier": [{
                "system": self.identifier_system or "http://hospital.smarthealthit.org",
                "value": self.identifier_value or str(self.patient.id)
            }],
            "name": [{
                "family": self.patient.last_name,
                "given": [self.patient.first_name]
            }],
            "gender": self.patient.gender.lower() if self.patient.gender else "unknown",
            "birthDate": self.patient.date_of_birth.isoformat() if self.patient.date_of_birth else None,
            "address": [{
                "line": [self.patient.address_line_1 or ""],
                "city": self.patient.city or "",
                "state": self.patient.state or "",
                "postalCode": self.patient.postal_code or "",
                "country": self.patient.country or "US"
            }],
            "telecom": []
        }
        
        if self.patient.phone_home:
            patient_data["telecom"].append({
                "system": "phone",
                "value": self.patient.phone_home,
                "use": "home"
            })
        
        if self.patient.email:
            patient_data["telecom"].append({
                "system": "email",
                "value": self.patient.email
            })
        
        return FHIRPatient(**patient_data)


class FHIRObservationResource(models.Model):
    """Observation Resource for Vital Signs and Lab Results"""
    health_screening = models.ForeignKey('health_screening.HealthScreening', 
                                       on_delete=models.CASCADE, null=True, blank=True)
    lab_result = models.ForeignKey('laboratory.LabResult', 
                                 on_delete=models.CASCADE, null=True, blank=True)
    fhir_resource = models.OneToOneField(FHIRResource, on_delete=models.CASCADE)
    
    # LOINC codes for standardization
    loinc_code = models.CharField(max_length=20, null=True, blank=True)
    loinc_display = models.CharField(max_length=200, null=True, blank=True)
    
    def to_fhir(self):
        """Convert to FHIR Observation resource"""
        if self.health_screening:
            return self._vital_signs_to_fhir()
        elif self.lab_result:
            return self._lab_result_to_fhir()
    
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