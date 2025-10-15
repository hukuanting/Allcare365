"""
FHIR Integration Services for ONC Certification
"""
import pandas as pd
import json
import uuid
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from django.contrib.auth.models import User
from django.db import transaction

from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.observation import Observation as FHIRObservation
from fhir.resources.condition import Condition as FHIRCondition

from .models import FHIRResource, USCDIDataElement, FHIRPatientResource
from patients.models import Patient
from health_screening.models import HealthScreening, VitalSigns, LaboratoryResults


class FHIRService:
    """
    Core FHIR R4 service for data conversion and compliance
    """
    
    def create_patient_bundle(self, patient: Patient) -> Bundle:
        """
        Create comprehensive FHIR bundle for a patient
        """
        bundle_data = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "collection",
            "timestamp": datetime.now().isoformat(),
            "entry": []
        }
        
        # Add Patient resource
        try:
            fhir_patient_resource = patient.fhirpatientresource
            patient_fhir = fhir_patient_resource.to_fhir()
            bundle_data["entry"].append({
                "resource": patient_fhir.dict()
            })
        except:
            # Create basic patient resource if FHIR resource doesn't exist
            patient_fhir = self._create_basic_patient_resource(patient)
            bundle_data["entry"].append({
                "resource": patient_fhir.dict()
            })
        
        # Add Observations (Vital Signs, Lab Results)
        for screening in patient.health_screenings.all():
            observations = self._create_observation_resources(screening)
            for obs in observations:
                bundle_data["entry"].append({
                    "resource": obs.dict()
                })
        
        return Bundle(**bundle_data)
    
    def create_search_bundle(self, patients: List[Patient], resource_type: str) -> Bundle:
        """
        Create FHIR search result bundle
        """
        bundle_data = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "searchset",
            "timestamp": datetime.now().isoformat(),
            "total": len(patients),
            "entry": []
        }
        
        for patient in patients:
            try:
                fhir_patient = patient.fhirpatientresource.to_fhir()
                bundle_data["entry"].append({
                    "resource": fhir_patient.dict(),
                    "search": {"mode": "match"}
                })
            except:
                # Create basic resource if FHIR resource doesn't exist
                fhir_patient = self._create_basic_patient_resource(patient)
                bundle_data["entry"].append({
                    "resource": fhir_patient.dict(),
                    "search": {"mode": "match"}
                })
        
        return Bundle(**bundle_data)
    
    def create_observation_bundle(self, screenings: List[HealthScreening]) -> Bundle:
        """
        Create FHIR bundle for observations
        """
        bundle_data = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "searchset",
            "timestamp": datetime.now().isoformat(),
            "entry": []
        }
        
        for screening in screenings:
            observations = self._create_observation_resources(screening)
            for obs in observations:
                bundle_data["entry"].append({
                    "resource": obs.dict(),
                    "search": {"mode": "match"}
                })
        
        bundle_data["total"] = len(bundle_data["entry"])
        return Bundle(**bundle_data)
    
    def generate_uscdi_compliance_report(self, patient: Patient) -> Dict[str, Any]:
        """
        Generate USCDI v6 compliance report for a patient
        """
        report = {
            "patient_id": str(patient.id),
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "report_date": datetime.now().isoformat(),
            "uscdi_compliance": {},
            "missing_elements": [],
            "compliance_score": 0
        }
        
        # Check Demographics
        demographics_score = self._check_demographics_compliance(patient)
        report["uscdi_compliance"]["demographics"] = demographics_score
        
        # Check Vital Signs
        vital_signs_score = self._check_vital_signs_compliance(patient)
        report["uscdi_compliance"]["vital_signs"] = vital_signs_score
        
        # Check Laboratory
        lab_score = self._check_laboratory_compliance(patient)
        report["uscdi_compliance"]["laboratory"] = lab_score
        
        # Calculate overall compliance score
        total_categories = len(report["uscdi_compliance"])
        total_score = sum(report["uscdi_compliance"].values())
        report["compliance_score"] = (total_score / total_categories) * 100
        
        return report
    
    def _create_basic_patient_resource(self, patient: Patient) -> FHIRPatient:
        """
        Create basic FHIR Patient resource
        """
        patient_data = {
            "resourceType": "Patient",
            "id": str(patient.id),
            "identifier": [{
                "system": "http://hospital.smarthealthit.org",
                "value": str(patient.id)
            }],
            "name": [{
                "family": patient.last_name or "",
                "given": [patient.first_name or ""]
            }],
            "gender": patient.gender.lower() if patient.gender else "unknown"
        }
        
        if patient.date_of_birth:
            patient_data["birthDate"] = patient.date_of_birth.isoformat()
        
        return FHIRPatient(**patient_data)
    
    def _create_observation_resources(self, screening: HealthScreening) -> List[FHIRObservation]:
        """
        Create FHIR Observation resources from health screening
        """
        observations = []
        
        try:
            vital_signs = screening.vital_signs
            
            # Blood Pressure
            if vital_signs.blood_pressure_systolic and vital_signs.blood_pressure_diastolic:
                bp_obs = {
                    "resourceType": "Observation",
                    "id": f"{screening.id}-bp",
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
                            "display": "Blood pressure panel"
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{screening.patient.id}"
                    },
                    "effectiveDateTime": screening.screening_date.isoformat(),
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
                observations.append(FHIRObservation(**bp_obs))
            
            # Height
            if vital_signs.height_cm:
                height_obs = {
                    "resourceType": "Observation",
                    "id": f"{screening.id}-height",
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
                            "code": "8302-2",
                            "display": "Body height"
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{screening.patient.id}"
                    },
                    "effectiveDateTime": screening.screening_date.isoformat(),
                    "valueQuantity": {
                        "value": float(vital_signs.height_cm),
                        "unit": "cm",
                        "system": "http://unitsofmeasure.org",
                        "code": "cm"
                    }
                }
                observations.append(FHIRObservation(**height_obs))
            
            # Weight
            if vital_signs.weight_kg:
                weight_obs = {
                    "resourceType": "Observation",
                    "id": f"{screening.id}-weight",
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
                            "code": "29463-7",
                            "display": "Body weight"
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{screening.patient.id}"
                    },
                    "effectiveDateTime": screening.screening_date.isoformat(),
                    "valueQuantity": {
                        "value": float(vital_signs.weight_kg),
                        "unit": "kg",
                        "system": "http://unitsofmeasure.org",
                        "code": "kg"
                    }
                }
                observations.append(FHIRObservation(**weight_obs))
        
        except Exception as e:
            # Log error but continue
            pass
        
        return observations
    
    def _check_demographics_compliance(self, patient: Patient) -> float:
        """Check demographics compliance with USCDI v6"""
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender']
        present_fields = 0
        
        for field in required_fields:
            if getattr(patient, field, None):
                present_fields += 1
        
        return (present_fields / len(required_fields)) * 100
    
    def _check_vital_signs_compliance(self, patient: Patient) -> float:
        """Check vital signs compliance with USCDI v6"""
        screenings = patient.health_screenings.all()
        if not screenings:
            return 0
        
        vital_signs_present = 0
        total_screenings = len(screenings)
        
        for screening in screenings:
            try:
                vital_signs = screening.vital_signs
                if (vital_signs.height_cm and vital_signs.weight_kg and 
                    vital_signs.blood_pressure_systolic and vital_signs.blood_pressure_diastolic):
                    vital_signs_present += 1
            except:
                continue
        
        return (vital_signs_present / total_screenings) * 100 if total_screenings > 0 else 0
    
    def _check_laboratory_compliance(self, patient: Patient) -> float:
        """Check laboratory compliance with USCDI v6"""
        screenings = patient.health_screenings.all()
        if not screenings:
            return 0
        
        lab_results_present = 0
        total_screenings = len(screenings)
        
        for screening in screenings:
            try:
                lab_results = screening.lab_results
                if (lab_results.cholesterol_total or lab_results.glucose_fasting or 
                    lab_results.hemoglobin_a1c):
                    lab_results_present += 1
            except:
                continue
        
        return (lab_results_present / total_screenings) * 100 if total_screenings > 0 else 0
    
    def import_fhir_bundle(self, fhir_data: Any, data_format: str = 'json') -> Dict[str, Any]:
        """
        Import FHIR Bundle data
        """
        result = {
            'success': False,
            'success_count': 0,
            'error_count': 0,
            'total_count': 0,
            'created_patients': 0,
            'created_screenings': 0,
            'fhir_resources': [],
            'errors': []
        }
        
        try:
            # Parse FHIR data
            if data_format == 'json':
                if isinstance(fhir_data, str):
                    bundle_data = json.loads(fhir_data)
                else:
                    bundle_data = fhir_data
            else:
                # For XML format, you would need additional parsing
                result['errors'].append('XML format not fully implemented')
                return result
            
            # Process Bundle or single resource
            resources = []
            if bundle_data.get('resourceType') == 'Bundle':
                if 'entry' in bundle_data:
                    for entry in bundle_data['entry']:
                        if 'resource' in entry:
                            resources.append(entry['resource'])
            elif bundle_data.get('resourceType'):
                resources.append(bundle_data)
            
            result['total_count'] = len(resources)
            
            # Process resources in order: Patients first, then Observations
            patient_mapping = {}  # Map fullUrl to Patient objects
            observations_by_patient = {}  # Group observations by patient
            
            # First pass: Process Patients and create mapping
            for entry in bundle_data.get('entry', []):
                resource = entry.get('resource', {})
                full_url = entry.get('fullUrl', '')
                
                if resource.get('resourceType') == 'Patient':
                    try:
                        with transaction.atomic():
                            patient = self._process_fhir_patient(resource)
                            if patient:
                                patient_mapping[full_url] = patient
                                result['created_patients'] += 1
                        
                        # Store FHIR resource outside transaction
                        try:
                            fhir_resource, created = FHIRResource.objects.get_or_create(
                                resource_type='Patient',
                                resource_id=resource.get('id', str(uuid.uuid4())),
                                defaults={'resource_data': resource}
                            )
                            result['fhir_resources'].append(str(fhir_resource.id))
                        except Exception as fhir_error:
                            # Log but don't fail the entire process
                            logger.warning(f'FHIR resource storage failed: {str(fhir_error)}')
                        
                        result['success_count'] += 1
                                
                    except Exception as e:
                        result['error_count'] += 1
                        result['errors'].append(f'Patient processing error: {str(e)}')
            
            # Second pass: Process Observations with patient mapping
            for entry in bundle_data.get('entry', []):
                resource = entry.get('resource', {})
                
                if resource.get('resourceType') == 'Observation':
                    try:
                        subject_ref = resource.get('subject', {}).get('reference', '')
                        patient = patient_mapping.get(subject_ref)
                        
                        if patient:
                            if patient not in observations_by_patient:
                                observations_by_patient[patient] = []
                            observations_by_patient[patient].append(resource)
                            
                            # Store FHIR resource
                            try:
                                fhir_resource, created = FHIRResource.objects.get_or_create(
                                    resource_type='Observation',
                                    resource_id=resource.get('id', str(uuid.uuid4())),
                                    defaults={'resource_data': resource}
                                )
                                result['fhir_resources'].append(str(fhir_resource.id))
                            except Exception as fhir_error:
                                # Log but don't fail the entire process
                                logger.warning(f'FHIR resource storage failed: {str(fhir_error)}')
                            
                            result['success_count'] += 1
                        else:
                            result['errors'].append(f'Observation {resource.get("id")}: Patient not found for reference {subject_ref}')
                            result['error_count'] += 1
                            
                    except Exception as e:
                        result['error_count'] += 1
                        result['errors'].append(f'Observation processing error: {str(e)}')
            
            # Third pass: Create health screenings with all observations
            for patient, observations in observations_by_patient.items():
                try:
                    with transaction.atomic():
                        screening = self._create_health_screening_from_observations(patient, observations)
                        if screening:
                            result['created_screenings'] += 1
                except Exception as e:
                    result['errors'].append(f'Health screening creation error for patient {patient.id}: {str(e)}')
                    result['error_count'] += 1
            
            result['success'] = result['success_count'] > 0
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f'FHIR processing error: {str(e)}')
        
        return result
    
    def _process_fhir_patient(self, patient_resource: Dict[str, Any]) -> Optional[Patient]:
        """Process FHIR Patient resource"""
        try:
            # Extract patient data
            patient_id = patient_resource.get('id')
            identifiers = patient_resource.get('identifier', [])
            names = patient_resource.get('name', [])
            gender = patient_resource.get('gender')
            birth_date = patient_resource.get('birthDate')
            
            # Get medical record number from identifiers
            medical_record_number = patient_id
            for identifier in identifiers:
                identifier_value = identifier.get('value')
                identifier_system = identifier.get('system', '')
                
                if identifier_value:
                    # Prioritize Taiwan national ID (身份證號)
                    if 'oid:2.16.886.101.1.1.1.2' in identifier_system:
                        medical_record_number = identifier_value
                        break
                    # Otherwise use any available identifier
                    elif not medical_record_number or medical_record_number == patient_id:
                        medical_record_number = identifier_value
            
            # Extract name
            first_name = ''
            last_name = ''
            if names:
                name = names[0]
                if 'given' in name and name['given']:
                    first_name = ' '.join(name['given'])
                if 'family' in name:
                    last_name = name['family']
            
            # Try to find existing patient
            try:
                patient = Patient.objects.get(medical_record_number=medical_record_number)
                return patient
            except Patient.DoesNotExist:
                pass
            
            # Create new patient
            patient_data = {
                'medical_record_number': medical_record_number,
                'first_name': first_name or f'Patient_{patient_id}',
                'last_name': last_name or '',
                'is_active': True
            }
            
            # Handle gender
            if gender:
                if gender.lower() in ['male', 'm']:
                    patient_data['gender'] = 'M'
                elif gender.lower() in ['female', 'f']:
                    patient_data['gender'] = 'F'
                else:
                    patient_data['gender'] = 'U'
            
            # Handle birth date
            if birth_date:
                try:
                    from datetime import datetime
                    patient_data['date_of_birth'] = datetime.fromisoformat(birth_date.replace('Z', '+00:00')).date()
                except:
                    pass
            
            patient = Patient.objects.create(**patient_data)
            return patient
            
        except Exception as e:
            raise Exception(f'Patient creation error: {str(e)}')
    
    def _process_fhir_observation(self, observation_resource: Dict[str, Any]) -> Optional[HealthScreening]:
        """Process FHIR Observation resource"""
        try:
            # Extract patient reference - handle both UUID and regular references
            subject_ref = observation_resource.get('subject', {}).get('reference', '')
            patient = None
            
            if subject_ref.startswith('Patient/'):
                patient_id = subject_ref.replace('Patient/', '')
                try:
                    patient = Patient.objects.get(medical_record_number=patient_id)
                except Patient.DoesNotExist:
                    try:
                        patient = Patient.objects.get(id=patient_id)
                    except Patient.DoesNotExist:
                        pass
            elif subject_ref.startswith('urn:uuid:'):
                # Handle UUID references - find patient created in same bundle
                uuid_ref = subject_ref.replace('urn:uuid:', '')
                # Try to find patient by the UUID or any identifier
                try:
                    # Since we processed patients first, find by most recent creation
                    patient = Patient.objects.filter(is_active=True).order_by('-created_at').first()
                    if not patient:
                        return None
                except:
                    return None
            
            if not patient:
                return None
            
            # Extract observation date
            effective_date = observation_resource.get('effectiveDateTime')
            if effective_date:
                try:
                    from datetime import datetime
                    screening_date = datetime.fromisoformat(effective_date.replace('Z', '+00:00')).date()
                except:
                    screening_date = datetime.now().date()
            else:
                screening_date = datetime.now().date()
            
            # Create or get health screening
            screening, created = HealthScreening.objects.get_or_create(
                patient=patient,
                screening_date=screening_date,
                defaults={
                    'screening_type': 'fhir_import',
                    'notes': 'FHIR匯入資料'
                }
            )
            
            # Process observation data based on LOINC code
            code_system = observation_resource.get('code', {}).get('coding', [])
            loinc_code = None
            for coding in code_system:
                if coding.get('system') == 'http://loinc.org':
                    loinc_code = coding.get('code')
                    break
            
            if loinc_code:
                self._process_observation_by_loinc(screening, observation_resource, loinc_code)
            
            return screening
            
        except Exception as e:
            raise Exception(f'Observation processing error: {str(e)}')
    
    def _process_observation_by_loinc(self, screening: HealthScreening, observation: Dict[str, Any], loinc_code: str):
        """Process observation based on LOINC code"""
        try:
            # Get or create vital signs
            vital_signs, created = VitalSigns.objects.get_or_create(
                health_screening=screening,
                defaults={}
            )
            
            # Get or create lab results
            lab_results, created = LaboratoryResults.objects.get_or_create(
                health_screening=screening,
                defaults={}
            )
            
            # Process based on LOINC code
            value_quantity = observation.get('valueQuantity', {})
            value = value_quantity.get('value')
            
            if value is not None:
                # Blood pressure handling
                if loinc_code == '85354-9':  # Blood pressure panel
                    components = observation.get('component', [])
                    for component in components:
                        comp_code = component.get('code', {}).get('coding', [{}])[0].get('code')
                        comp_value = component.get('valueQuantity', {}).get('value')
                        
                        if comp_code == '8480-6' and comp_value:  # Systolic BP
                            vital_signs.systolic_bp_mmhg = float(comp_value)
                        elif comp_code == '8462-4' and comp_value:  # Diastolic BP
                            vital_signs.diastolic_bp_mmhg = float(comp_value)
                    
                    vital_signs.save()
                
                # Individual vital signs
                elif loinc_code == '8302-2':  # Body height
                    vital_signs.height_cm = float(value)
                    vital_signs.save()
                elif loinc_code == '29463-7':  # Body weight
                    vital_signs.weight_kg = float(value)
                    vital_signs.save()
                elif loinc_code == '8867-4':  # Heart rate
                    vital_signs.pulse_rate_bpm = float(value)
                    vital_signs.save()
                
                # Laboratory results
                elif loinc_code == '1558-6':  # Fasting glucose
                    lab_results.fasting_glucose_mgdl = float(value)
                    lab_results.save()
                elif loinc_code == '4548-4':  # HbA1c
                    lab_results.hba1c_percent = float(value)
                    lab_results.save()
                elif loinc_code == '2093-3':  # Total cholesterol
                    lab_results.total_cholesterol_mgdl = float(value)
                    lab_results.save()
                elif loinc_code == '2085-9':  # HDL cholesterol
                    lab_results.hdl_cholesterol_mgdl = float(value)
                    lab_results.save()
                elif loinc_code == '18261-8':  # LDL cholesterol
                    lab_results.ldl_cholesterol_mgdl = float(value)
                    lab_results.save()
                elif loinc_code == '2571-8':  # Triglycerides
                    lab_results.triglycerides_mgdl = float(value)
                    lab_results.save()
                
        except Exception as e:
            # Log error but don't fail the entire import
            pass
    
    def _create_health_screening_from_observations(self, patient: Patient, observations: List[Dict[str, Any]]) -> Optional[HealthScreening]:
        """Create a health screening record from multiple FHIR observations"""
        try:
            # Determine screening date from observations
            screening_date = None
            for obs in observations:
                effective_date = obs.get('effectiveDateTime')
                if effective_date:
                    try:
                        from datetime import datetime
                        screening_date = datetime.fromisoformat(effective_date.replace('Z', '+00:00').replace('+08:00', '+08:00')).date()
                        break
                    except:
                        continue
            
            if not screening_date:
                screening_date = datetime.now().date()
            
            # Create health screening record
            screening = HealthScreening.objects.create(
                patient=patient,
                screening_date=screening_date,
                screening_type='fhir_comprehensive'
            )
            
            # Group observations by category
            vital_signs_data = {}
            lab_results_data = {}
            
            for obs in observations:
                loinc_code = self._extract_loinc_code(obs)
                if loinc_code:
                    self._process_observation_data(obs, loinc_code, vital_signs_data, lab_results_data)
            
            # Create vital signs record if we have data
            if vital_signs_data:
                VitalSigns.objects.create(health_screening=screening, **vital_signs_data)
            
            # Create laboratory results record if we have data
            if lab_results_data:
                LaboratoryResults.objects.create(health_screening=screening, **lab_results_data)
            
            return screening
            
        except Exception as e:
            raise Exception(f'Health screening creation error: {str(e)}')
    
    def _extract_loinc_code(self, observation: Dict[str, Any]) -> Optional[str]:
        """Extract LOINC code from observation"""
        code_section = observation.get('code', {})
        codings = code_section.get('coding', [])
        
        for coding in codings:
            if coding.get('system') == 'http://loinc.org':
                return coding.get('code')
        
        return None
    
    def _process_observation_data(self, observation: Dict[str, Any], loinc_code: str, 
                                vital_signs_data: Dict, lab_results_data: Dict):
        """Process observation data and add to appropriate data dictionaries"""
        try:
            # Handle blood pressure panel (component-based)
            if loinc_code == '85354-9':  # Blood pressure panel
                components = observation.get('component', [])
                for component in components:
                    comp_coding = component.get('code', {}).get('coding', [])
                    for coding in comp_coding:
                        if coding.get('system') == 'http://loinc.org':
                            comp_code = coding.get('code')
                            comp_value = component.get('valueQuantity', {}).get('value')
                            
                            if comp_code == '8480-6' and comp_value:  # Systolic BP
                                vital_signs_data['systolic_bp_mmhg'] = float(comp_value)
                            elif comp_code == '8462-4' and comp_value:  # Diastolic BP
                                vital_signs_data['diastolic_bp_mmhg'] = float(comp_value)
                return
            
            # Handle single-value observations
            value_quantity = observation.get('valueQuantity', {})
            value = value_quantity.get('value')
            
            if value is not None:
                value = float(value)
                
                # Vital signs mapping
                if loinc_code == '8302-2':  # Body height
                    vital_signs_data['height_cm'] = value
                elif loinc_code == '29463-7':  # Body weight
                    vital_signs_data['weight_kg'] = value
                elif loinc_code == '8867-4':  # Heart rate
                    vital_signs_data['pulse_rate_bpm'] = value
                
                # Laboratory results mapping
                elif loinc_code == '1558-6':  # Fasting glucose
                    lab_results_data['fasting_glucose_mgdl'] = value
                elif loinc_code == '2339-0':  # Glucose (general)
                    lab_results_data['fasting_glucose_mgdl'] = value
                elif loinc_code == '4548-4':  # HbA1c
                    lab_results_data['hba1c_percent'] = value
                elif loinc_code == '2093-3':  # Total cholesterol
                    lab_results_data['total_cholesterol_mgdl'] = value
                elif loinc_code == '2085-9':  # HDL cholesterol
                    lab_results_data['hdl_cholesterol_mgdl'] = value
                elif loinc_code == '18261-8':  # LDL cholesterol
                    lab_results_data['ldl_cholesterol_mgdl'] = value
                elif loinc_code == '2571-8':  # Triglycerides
                    lab_results_data['triglycerides_mgdl'] = value
                elif loinc_code == '2160-0':  # Serum creatinine
                    lab_results_data['serum_creatinine_mgdl'] = value
                
        except Exception as e:
            # Log error but continue processing
            pass


class BulkDataProcessor:
    """
    Service for processing bulk health data imports
    """
    
    def process_file(self, file, data_format: str, patient_id: Optional[str] = None, 
                    user: Optional[User] = None) -> Dict[str, Any]:
        """
        Process uploaded file and convert to FHIR resources
        """
        result = {
            "status": "success",
            "processed_records": 0,
            "errors": [],
            "created_resources": []
        }
        
        try:
            if data_format == 'csv':
                data = pd.read_csv(file)
            elif data_format == 'xlsx':
                data = pd.read_excel(file)
            elif data_format == 'json':
                data = json.load(file)
            elif data_format == 'fhir':
                return self._process_fhir_bundle(file, user)
            else:
                raise ValueError(f"Unsupported format: {data_format}")
            
            with transaction.atomic():
                if data_format in ['csv', 'xlsx']:
                    result = self._process_tabular_data(data, patient_id, user)
                elif data_format == 'json':
                    result = self._process_json_data(data, patient_id, user)
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
        
        return result
    
    def _process_tabular_data(self, data: pd.DataFrame, patient_id: Optional[str], 
                            user: Optional[User]) -> Dict[str, Any]:
        """Process CSV/Excel data"""
        result = {
            "status": "success",
            "processed_records": 0,
            "errors": [],
            "created_resources": []
        }
        
        for index, row in data.iterrows():
            try:
                # Process each row as a health screening record
                screening_data = self._map_tabular_row_to_screening(row, patient_id)
                screening = self._create_health_screening(screening_data, user)
                
                # Create FHIR resources
                fhir_service = FHIRService()
                observations = fhir_service._create_observation_resources(screening)
                
                for obs in observations:
                    fhir_resource = FHIRResource.objects.create(
                        resource_type="Observation",
                        resource_id=obs.id,
                        resource_data=obs.dict(),
                        created_by=user
                    )
                    result["created_resources"].append(str(fhir_resource.id))
                
                result["processed_records"] += 1
                
            except Exception as e:
                result["errors"].append(f"Row {index + 1}: {str(e)}")
        
        return result
    
    def _process_fhir_bundle(self, file, user: Optional[User]) -> Dict[str, Any]:
        """Process FHIR Bundle"""
        result = {
            "status": "success",
            "processed_records": 0,
            "errors": [],
            "created_resources": []
        }
        
        try:
            bundle_data = json.load(file)
            bundle = Bundle(**bundle_data)
            
            for entry in bundle.entry:
                try:
                    resource = entry.resource
                    fhir_resource = FHIRResource.objects.create(
                        resource_type=resource.resource_type,
                        resource_id=resource.id,
                        resource_data=resource.dict(),
                        created_by=user
                    )
                    result["created_resources"].append(str(fhir_resource.id))
                    result["processed_records"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"Resource {resource.id}: {str(e)}")
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
        
        return result
    
    def _map_tabular_row_to_screening(self, row: pd.Series, patient_id: Optional[str]) -> Dict:
        """Map tabular data row to health screening data"""
        # This is a basic mapping - should be customized based on actual data format
        return {
            'patient_id': patient_id or row.get('patient_id'),
            'screening_date': row.get('date', datetime.now().date()),
            'height_cm': row.get('height'),
            'weight_kg': row.get('weight'),
            'blood_pressure_systolic': row.get('systolic_bp'),
            'blood_pressure_diastolic': row.get('diastolic_bp'),
            'heart_rate': row.get('heart_rate'),
            'cholesterol_total': row.get('total_cholesterol'),
            'cholesterol_hdl': row.get('hdl_cholesterol'),
            'cholesterol_ldl': row.get('ldl_cholesterol'),
            'glucose_fasting': row.get('fasting_glucose')
        }
    
    def _create_health_screening(self, data: Dict, user: Optional[User]) -> HealthScreening:
        """Create health screening from processed data"""
        patient = Patient.objects.get(id=data['patient_id'])
        
        screening = HealthScreening.objects.create(
            patient=patient,
            screening_date=data['screening_date'],
            created_by=user
        )
        
        # Create vital signs
        VitalSigns.objects.create(
            health_screening=screening,
            height_cm=data.get('height_cm'),
            weight_kg=data.get('weight_kg'),
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            heart_rate=data.get('heart_rate'),
            created_by=user
        )
        
        # Create lab results if present
        if any(data.get(field) for field in ['cholesterol_total', 'cholesterol_hdl', 'cholesterol_ldl', 'glucose_fasting']):
            LaboratoryResults.objects.create(
                health_screening=screening,
                cholesterol_total=data.get('cholesterol_total'),
                cholesterol_hdl=data.get('cholesterol_hdl'),
                cholesterol_ldl=data.get('cholesterol_ldl'),
                glucose_fasting=data.get('glucose_fasting'),
                created_by=user
            )
        
        return screening