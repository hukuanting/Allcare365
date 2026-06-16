"""
Advanced Patient Management Services

This module provides advanced patient management functionality including:
- Patient search and filtering
- Duplicate patient detection and merging
- Patient data validation and normalization
- Bulk operations
"""

from django.db.models import Q, Count, F
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from dateutil.relativedelta import relativedelta
import re
from typing import List, Dict, Tuple, Optional

from .models import Patient, EmergencyContact, PatientNote
from .serializers import PatientSerializer, PatientDetailSerializer


class PatientSearchService:
    """
    Advanced patient search service with fuzzy matching and smart filtering
    """
    
    @staticmethod
    def search_patients(
        query: str = None,
        first_name: str = None,
        last_name: str = None,
        date_of_birth: str = None,
        phone: str = None,
        email: str = None,
        medical_record_number: str = None,
        insurance_id: str = None,
        fuzzy_match: bool = True,
        limit: int = 50
    ) -> List[Patient]:
        """
        Advanced patient search with multiple criteria and fuzzy matching
        
        Args:
            query: General search query
            first_name: First name filter
            last_name: Last name filter
            date_of_birth: Date of birth filter (YYYY-MM-DD)
            phone: Phone number filter
            email: Email filter
            medical_record_number: MRN filter
            insurance_id: Insurance ID filter
            fuzzy_match: Enable fuzzy matching for names
            limit: Maximum results to return
            
        Returns:
            List of matching Patient objects
        """
        queryset = Patient.objects.filter(is_active=True)
        
        # General query search
        if query:
            query_terms = query.strip().split()
            q_objects = Q()
            
            for term in query_terms:
                q_objects |= (
                    Q(first_name__icontains=term) |
                    Q(last_name__icontains=term) |
                    Q(medical_record_number__icontains=term) |
                    Q(phone_home__icontains=term) |
                    Q(phone_mobile__icontains=term) |
                    Q(email__icontains=term)
                )
            
            queryset = queryset.filter(q_objects)
        
        # Specific field filters
        if first_name:
            if fuzzy_match:
                queryset = queryset.filter(first_name__icontains=first_name)
            else:
                queryset = queryset.filter(first_name__iexact=first_name)
        
        if last_name:
            if fuzzy_match:
                queryset = queryset.filter(last_name__icontains=last_name)
            else:
                queryset = queryset.filter(last_name__iexact=last_name)
        
        if date_of_birth:
            try:
                dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                queryset = queryset.filter(date_of_birth=dob)
            except ValueError:
                pass  # Invalid date format, ignore
        
        if phone:
            # Normalize phone number
            normalized_phone = PatientSearchService.normalize_phone(phone)
            queryset = queryset.filter(
                Q(phone_home__icontains=normalized_phone) |
                Q(phone_mobile__icontains=normalized_phone) |
                Q(phone_work__icontains=normalized_phone)
            )
        
        if email:
            queryset = queryset.filter(email__iexact=email)
        
        if medical_record_number:
            queryset = queryset.filter(medical_record_number__iexact=medical_record_number)
        
        if insurance_id:
            queryset = queryset.filter(insurances__policy_number__icontains=insurance_id)
        
        # Order by relevance and limit results
        queryset = queryset.select_related().distinct()
        
        # If we have specific name criteria, order by name match quality
        if first_name or last_name:
            # Custom ordering could be implemented here
            queryset = queryset.order_by('last_name', 'first_name')
        else:
            queryset = queryset.order_by('-updated_at')
        
        return list(queryset[:limit])
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number by removing non-digits"""
        return re.sub(r'[^\d]', '', phone)
    
    @staticmethod
    def search_by_demographics(
        first_name: str,
        last_name: str,
        date_of_birth: str,
        threshold: float = 0.8
    ) -> List[Tuple[Patient, float]]:
        """
        Search patients by demographics with similarity scoring
        
        Args:
            first_name: First name to match
            last_name: Last name to match
            date_of_birth: Date of birth (YYYY-MM-DD)
            threshold: Minimum similarity score (0.0-1.0)
            
        Returns:
            List of (Patient, similarity_score) tuples
        """
        try:
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        except ValueError:
            return []
        
        # Get candidates with exact DOB match
        candidates = Patient.objects.filter(
            date_of_birth=dob,
            is_active=True
        )
        
        results = []
        for patient in candidates:
            # Calculate name similarity
            first_name_sim = SequenceMatcher(
                None,
                first_name.lower(),
                patient.first_name.lower()
            ).ratio()
            
            last_name_sim = SequenceMatcher(
                None,
                last_name.lower(),
                patient.last_name.lower()
            ).ratio()
            
            # Combined similarity score (weighted)
            total_similarity = (first_name_sim * 0.4) + (last_name_sim * 0.6)
            
            if total_similarity >= threshold:
                results.append((patient, total_similarity))
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results


class DuplicatePatientDetector:
    """
    Service for detecting and managing duplicate patient records
    """
    
    @staticmethod
    def find_potential_duplicates(
        patient: Patient,
        similarity_threshold: float = 0.85
    ) -> List[Tuple[Patient, float, Dict]]:
        """
        Find potential duplicate patients based on multiple criteria
        
        Args:
            patient: Patient to check for duplicates
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of (Patient, similarity_score, match_details) tuples
        """
        candidates = Patient.objects.filter(
            is_active=True
        ).exclude(id=patient.id)
        
        # Filter candidates by date of birth (exact or close)
        if patient.date_of_birth:
            dob_range_start = patient.date_of_birth - timedelta(days=365)  # Allow 1 year difference
            dob_range_end = patient.date_of_birth + timedelta(days=365)
            
            candidates = candidates.filter(
                date_of_birth__range=(dob_range_start, dob_range_end)
            )
        
        duplicates = []
        
        for candidate in candidates:
            score, details = DuplicatePatientDetector._calculate_similarity(patient, candidate)
            
            if score >= similarity_threshold:
                duplicates.append((candidate, score, details))
        
        # Sort by similarity score (descending)
        duplicates.sort(key=lambda x: x[1], reverse=True)
        
        return duplicates
    
    @staticmethod
    def _calculate_similarity(patient1: Patient, patient2: Patient) -> Tuple[float, Dict]:
        """
        Calculate similarity score between two patients
        
        Returns:
            Tuple of (similarity_score, match_details)
        """
        scores = {}
        details = {}
        
        # Name similarity (40% weight)
        first_name_sim = SequenceMatcher(
            None,
            patient1.first_name.lower(),
            patient2.first_name.lower()
        ).ratio()
        
        last_name_sim = SequenceMatcher(
            None,
            patient1.last_name.lower(),
            patient2.last_name.lower()
        ).ratio()
        
        name_score = (first_name_sim + last_name_sim) / 2
        scores['name'] = name_score
        details['first_name_match'] = first_name_sim
        details['last_name_match'] = last_name_sim
        
        # Date of birth similarity (30% weight)
        if patient1.date_of_birth and patient2.date_of_birth:
            dob_diff = abs((patient1.date_of_birth - patient2.date_of_birth).days)
            
            if dob_diff == 0:
                dob_score = 1.0
            elif dob_diff <= 7:  # Within a week
                dob_score = 0.9
            elif dob_diff <= 30:  # Within a month
                dob_score = 0.7
            elif dob_diff <= 365:  # Within a year
                dob_score = 0.3
            else:
                dob_score = 0.0
            
            scores['dob'] = dob_score
            details['dob_difference_days'] = dob_diff
        else:
            scores['dob'] = 0.0
        
        # Phone similarity (15% weight)
        phone_score = 0.0
        if patient1.phone_mobile and patient2.phone_mobile:
            phone1 = PatientSearchService.normalize_phone(patient1.phone_mobile)
            phone2 = PatientSearchService.normalize_phone(patient2.phone_mobile)
            
            if phone1 == phone2:
                phone_score = 1.0
            elif len(phone1) >= 7 and len(phone2) >= 7:
                # Compare last 7 digits
                if phone1[-7:] == phone2[-7:]:
                    phone_score = 0.8
        
        scores['phone'] = phone_score
        details['phone_match'] = phone_score > 0
        
        # Email similarity (10% weight)
        email_score = 0.0
        if patient1.email and patient2.email:
            if patient1.email.lower() == patient2.email.lower():
                email_score = 1.0
        
        scores['email'] = email_score
        details['email_match'] = email_score > 0
        
        # Gender similarity (5% weight)
        gender_score = 1.0 if patient1.gender == patient2.gender else 0.0
        scores['gender'] = gender_score
        details['gender_match'] = gender_score > 0
        
        # Calculate weighted total score
        total_score = (
            scores['name'] * 0.40 +
            scores['dob'] * 0.30 +
            scores['phone'] * 0.15 +
            scores['email'] * 0.10 +
            scores['gender'] * 0.05
        )
        
        details['component_scores'] = scores
        details['total_score'] = total_score
        
        return total_score, details
    
    @staticmethod
    def merge_patients(
        primary_patient: Patient,
        duplicate_patient: Patient,
        user: User
    ) -> Dict:
        """
        Merge duplicate patient into primary patient
        
        Args:
            primary_patient: Patient to keep
            duplicate_patient: Patient to merge (will be deactivated)
            user: User performing the merge
            
        Returns:
            Dictionary with merge results
        """
        merge_results = {
            'primary_patient_id': primary_patient.id,
            'duplicate_patient_id': duplicate_patient.id,
            'merged_at': timezone.now(),
            'merged_by': user.id,
            'merged_data': {}
        }
        
        # Merge emergency contacts
        for contact in duplicate_patient.emergency_contacts.all():
            # Check if similar contact exists
            existing = primary_patient.emergency_contacts.filter(
                first_name__iexact=contact.first_name,
                last_name__iexact=contact.last_name
            ).first()
            
            if not existing:
                contact.patient = primary_patient
                contact.save()
                merge_results['merged_data']['emergency_contacts'] = merge_results['merged_data'].get('emergency_contacts', 0) + 1
        
        # Merge insurance records (if insurance model exists)
        # This would be implemented when insurance model is available
        
        # Merge medical records (appointments, encounters, etc.)
        from medical_records.models import MedicalRecord
        medical_records = MedicalRecord.objects.filter(patient=duplicate_patient)
        medical_records.update(patient=primary_patient)
        merge_results['merged_data']['medical_records'] = medical_records.count()
        
        # Merge appointments
        from appointments.models import Appointment
        appointments = Appointment.objects.filter(patient=duplicate_patient)
        appointments.update(patient=primary_patient)
        merge_results['merged_data']['appointments'] = appointments.count()
        
        # Merge documents
        from documents.models import Document
        documents = Document.objects.filter(patient=duplicate_patient)
        documents.update(patient=primary_patient)
        merge_results['merged_data']['documents'] = documents.count()
        
        # Update primary patient with any missing information
        updated_fields = []
        
        if not primary_patient.phone_mobile and duplicate_patient.phone_mobile:
            primary_patient.phone_mobile = duplicate_patient.phone_mobile
            updated_fields.append('phone_mobile')
        
        if not primary_patient.email and duplicate_patient.email:
            primary_patient.email = duplicate_patient.email
            updated_fields.append('email')
        
        if not primary_patient.address_street and duplicate_patient.address_street:
            primary_patient.address_street = duplicate_patient.address_street
            primary_patient.address_city = duplicate_patient.address_city
            primary_patient.address_state = duplicate_patient.address_state
            primary_patient.address_zip = duplicate_patient.address_zip
            updated_fields.extend(['address_street', 'address_city', 'address_state', 'address_zip'])
        
        if updated_fields:
            primary_patient.updated_by = user
            primary_patient.save(update_fields=updated_fields + ['updated_at', 'updated_by'])
            merge_results['merged_data']['updated_fields'] = updated_fields
        
        # Deactivate duplicate patient
        duplicate_patient.is_active = False
        duplicate_patient.updated_by = user
        duplicate_patient.save()
        
        # Create merge audit log
        PatientNote.objects.create(
            patient=primary_patient,
            note_type='system',
            title='Patient Merge',
            content=f'Patient {duplicate_patient.get_full_name()} (ID: {duplicate_patient.id}) merged into this record',
            created_by=user
        )
        
        return merge_results


class PatientDataValidator:
    """
    Service for validating and normalizing patient data
    """
    
    @staticmethod
    def validate_patient_data(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate patient data for completeness and accuracy
        
        Args:
            data: Dictionary with patient data
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Required fields
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender']
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field.replace("_", " ").title()} is required')
        
        # Date of birth validation
        if data.get('date_of_birth'):
            try:
                dob = datetime.strptime(str(data['date_of_birth']), '%Y-%m-%d').date()
                
                # Check if DOB is in the future
                if dob > timezone.now().date():
                    errors.append('Date of birth cannot be in the future')
                
                # Check if age is reasonable (0-150 years)
                age = (timezone.now().date() - dob).days / 365.25
                if age > 150:
                    errors.append('Date of birth indicates age over 150 years')
                
            except ValueError:
                errors.append('Invalid date of birth format (use YYYY-MM-DD)')
        
        # Phone number validation
        phone_fields = ['phone_home', 'phone_mobile', 'phone_work']
        for field in phone_fields:
            if data.get(field):
                normalized = PatientSearchService.normalize_phone(data[field])
                if len(normalized) < 10:
                    errors.append(f'{field.replace("_", " ").title()} must be at least 10 digits')
        
        # Email validation
        if data.get('email'):
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, data['email']):
                errors.append('Invalid email format')
        
        # Gender validation
        if data.get('gender'):
            valid_genders = ['M', 'F', 'O', 'U']
            if data['gender'] not in valid_genders:
                errors.append('Invalid gender value')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def normalize_patient_data(data: Dict) -> Dict:
        """
        Normalize patient data for consistent storage
        
        Args:
            data: Dictionary with patient data
            
        Returns:
            Normalized data dictionary
        """
        normalized = data.copy()
        
        # Normalize names
        name_fields = ['first_name', 'last_name', 'middle_name']
        for field in name_fields:
            if normalized.get(field):
                normalized[field] = normalized[field].strip().title()
        
        # Normalize phone numbers
        phone_fields = ['phone_home', 'phone_mobile', 'phone_work']
        for field in phone_fields:
            if normalized.get(field):
                # Keep original format but ensure it's clean
                normalized[field] = re.sub(r'[^\d\+\-\(\)\s]', '', normalized[field]).strip()
        
        # Normalize email
        if normalized.get('email'):
            normalized['email'] = normalized['email'].strip().lower()
        
        # Normalize address
        address_fields = ['address_street', 'address_city']
        for field in address_fields:
            if normalized.get(field):
                normalized[field] = normalized[field].strip().title()
        
        if normalized.get('address_state'):
            normalized['address_state'] = normalized['address_state'].strip().upper()
        
        if normalized.get('address_zip'):
            # Remove non-digits from ZIP code
            normalized['address_zip'] = re.sub(r'[^\d\-]', '', normalized['address_zip'])
        
        return normalized


class PatientStatsService:
    """
    Service for generating patient statistics and analytics
    """
    
    @staticmethod
    def get_patient_demographics() -> Dict:
        """Get patient demographic statistics"""
        total_patients = Patient.objects.filter(is_active=True).count()
        
        # Gender distribution
        gender_stats = Patient.objects.filter(is_active=True).values('gender').annotate(
            count=Count('id')
        )
        
        # Age distribution
        from django.db.models import Case, When, IntegerField
        from dateutil.relativedelta import relativedelta
        from django.utils import timezone
        
        current_date = timezone.now().date()
        
        patients_with_age = Patient.objects.filter(is_active=True, date_of_birth__isnull=False)
        age_stats = []
        
        age_groups = {
            'Under 18': 0,
            '18-34': 0,
            '35-49': 0,
            '50-64': 0,
            '65+': 0
        }
        
        for patient in patients_with_age:
            age = relativedelta(current_date, patient.date_of_birth).years
            
            if age < 18:
                age_groups['Under 18'] += 1
            elif age < 35:
                age_groups['18-34'] += 1
            elif age < 50:
                age_groups['35-49'] += 1
            elif age < 65:
                age_groups['50-64'] += 1
            else:
                age_groups['65+'] += 1
        
        # Registration trends (last 12 months)
        from django.db.models.functions import TruncMonth
        
        registration_stats = Patient.objects.filter(
            is_active=True,
            created_at__gte=timezone.now() - timedelta(days=365)
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        return {
            'total_patients': total_patients,
            'gender_distribution': {item['gender']: item['count'] for item in gender_stats},
            'age_distribution': age_groups,
            'registration_trends': list(registration_stats)
        }
    
    @staticmethod
    def get_dashboard_stats() -> Dict:
        """Get dashboard statistics for frontend"""
        total_patients = Patient.objects.filter(is_active=True).count()
        active_patients = total_patients  # All active patients
        
        # New patients this month
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month = Patient.objects.filter(
            created_at__gte=current_month_start,
            is_active=True
        ).count()
        
        # Potential duplicates (simplified for now)
        potential_duplicates = 0  # This would use the duplicate detection service
        
        return {
            'total_patients': total_patients,
            'active_patients': active_patients,
            'new_this_month': new_this_month,
            'potential_duplicates': potential_duplicates
        }


# ===== 根據RECONSTRUCTION_GUIDE.md建議新增的服務 =====

class EnhancedPatientService:
    """
    增強的患者服務，實現RECONSTRUCTION_GUIDE.md中建議的功能
    """
    
    @staticmethod
    def get_patient_balance(patient_id: str):
        """
        計算患者餘額 - 關鍵功能，需要與billing模組整合
        """
        from decimal import Decimal
        
        # TODO: 需要與billing模組整合
        # 暫時返回0，等billing模組完成後再實現完整邏輯
        try:
            from billing.models import Billing, Payment
            from django.db.models import Sum
            
            # 獲取患者的所有費用
            total_charges = Billing.objects.filter(
                patient_id=patient_id,
                is_active=True
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            # 獲取患者的所有付款
            total_payments = Payment.objects.filter(
                patient_id=patient_id,
                is_active=True
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            return total_charges - total_payments
            
        except ImportError:
            # billing模組還未完成，返回0
            return Decimal('0.00')
    
    @staticmethod
    def is_patient_deceased(patient_id: str) -> bool:
        """檢查患者是否已故"""
        try:
            patient = Patient.objects.get(id=patient_id)
            return patient.status == 'deceased' or patient.deceased_date is not None
        except Patient.DoesNotExist:
            return False
    
    @staticmethod
    def advanced_patient_search(search_params: Dict[str, any]):
        """
        高級患者搜索功能，支援多種搜索條件
        """
        from django.db.models import Q
        
        queryset = Patient.objects.filter(is_active=True)
        
        # 按姓名搜索
        if search_params.get('name'):
            name = search_params['name']
            queryset = queryset.filter(
                Q(first_name__icontains=name) |
                Q(last_name__icontains=name) |
                Q(middle_name__icontains=name)
            )
        
        # 按身份證號搜索
        if search_params.get('ssn'):
            queryset = queryset.filter(
                social_security_number__icontains=search_params['ssn']
            )
        
        # 按出生日期搜索
        if search_params.get('date_of_birth'):
            if isinstance(search_params['date_of_birth'], str):
                try:
                    from datetime import datetime
                    dob = datetime.strptime(search_params['date_of_birth'], '%Y-%m-%d').date()
                    queryset = queryset.filter(date_of_birth=dob)
                except ValueError:
                    pass
            else:
                queryset = queryset.filter(date_of_birth=search_params['date_of_birth'])
        
        # 按電話號碼搜索
        if search_params.get('phone'):
            phone = search_params['phone']
            queryset = queryset.filter(
                Q(phone_home__icontains=phone) |
                Q(phone_mobile__icontains=phone) |
                Q(phone_work__icontains=phone)
            )
        
        # 按病歷號搜索
        if search_params.get('medical_record_number'):
            queryset = queryset.filter(
                medical_record_number__icontains=search_params['medical_record_number']
            )
        
        return queryset.order_by('last_name', 'first_name')
    
    @staticmethod
    def detect_duplicate_patients(patient_data: Dict[str, any]):
        """
        重複患者檢測邏輯 - 實現updateDupScore功能
        """
        potential_duplicates = []
        
        # 精確匹配條件
        exact_matches = Patient.objects.filter(
            first_name__iexact=patient_data.get('first_name', ''),
            last_name__iexact=patient_data.get('last_name', ''),
            date_of_birth=patient_data.get('date_of_birth'),
            is_active=True
        )
        
        if exact_matches.exists():
            potential_duplicates.extend(exact_matches)
        
        # 身份證號匹配
        if patient_data.get('social_security_number'):
            ssn_matches = Patient.objects.filter(
                social_security_number=patient_data['social_security_number'],
                is_active=True
            )
            potential_duplicates.extend(ssn_matches)
        
        # 電話號碼匹配
        phone_numbers = [
            patient_data.get('phone_home'),
            patient_data.get('phone_mobile'),
            patient_data.get('phone_work')
        ]
        
        for phone in phone_numbers:
            if phone:
                phone_matches = Patient.objects.filter(
                    Q(phone_home=phone) | Q(phone_mobile=phone) | Q(phone_work=phone),
                    is_active=True
                )
                potential_duplicates.extend(phone_matches)
        
        # 去除重複並返回
        return list(set(potential_duplicates))


class InsuranceManagementService:
    """保險信息管理服務"""
    
    @staticmethod
    def create_insurance_data(patient_id: str, insurance_data: Dict[str, any]):
        """創建患者保險信息"""
        from .models import InsuranceData
        from django.db import transaction
        
        patient = Patient.objects.get(id=patient_id)
        
        with transaction.atomic():
            insurance = InsuranceData.objects.create(
                patient=patient,
                **insurance_data
            )
        
        return insurance
    
    @staticmethod
    def get_active_insurance(patient_id: str, insurance_type: str = None):
        """獲取患者活躍的保險信息"""
        from .models import InsuranceData
        from django.db.models import Q
        
        queryset = InsuranceData.objects.filter(
            patient_id=patient_id,
            is_active=True
        )
        
        if insurance_type:
            queryset = queryset.filter(type=insurance_type)
        
        # 檢查是否在有效期內
        today = timezone.now().date()
        queryset = queryset.filter(
            Q(effective_date__lte=today) | Q(effective_date__isnull=True),
            Q(expiration_date__gte=today) | Q(expiration_date__isnull=True)
        )
        
        return queryset.order_by('type')


class PatientReportService:
    """患者報告生成服務"""
    
    @staticmethod
    def generate_patient_summary_report(patient_id: str) -> Dict[str, any]:
        """生成患者摘要報告"""
        patient = Patient.objects.get(id=patient_id)
        
        # 基本信息
        basic_info = {
            'patient_id': str(patient.id),
            'full_name': patient.full_name,
            'medical_record_number': patient.medical_record_number,
            'date_of_birth': str(patient.date_of_birth),
            'age': patient.age,
            'gender': patient.get_gender_display(),
            'status': patient.get_status_display() if hasattr(patient, 'get_status_display') else 'Active',
            'contact_info': {
                'phone_mobile': patient.phone_mobile,
                'phone_home': patient.phone_home,
                'email': patient.email,
                'address': patient.address
            }
        }
        
        # 過敏信息
        allergies = []
        if hasattr(patient, 'allergies'):
            for allergy in patient.allergies.filter(is_active=True):
                allergies.append({
                    'allergen': allergy.allergen,
                    'reaction': allergy.reaction,
                    'severity': allergy.severity
                })
        
        # 當前用藥
        medications = []
        if hasattr(patient, 'medications'):
            for medication in patient.medications.filter(is_active=True):
                medications.append({
                    'medication_name': medication.medication_name,
                    'dosage': medication.dosage,
                    'frequency': medication.frequency,
                    'prescribing_doctor': medication.prescribing_doctor
                })
        
        # 財務餘額
        balance = EnhancedPatientService.get_patient_balance(patient_id)
        
        return {
            'basic_info': basic_info,
            'allergies': allergies,
            'current_medications': medications,
            'financial_balance': float(balance),
            'generated_at': timezone.now().isoformat()
        }
