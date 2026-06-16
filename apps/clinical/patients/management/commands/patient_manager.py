"""
Advanced Patient Management Commands

This command provides advanced patient management functionality including:
- Duplicate patient detection and reporting
- Patient data validation and cleanup
- Bulk patient operations
- Patient statistics and reporting
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from apps.clinical.patients.models import Patient
from apps.clinical.patients.services import (
    PatientSearchService, DuplicatePatientDetector, 
    PatientDataValidator, PatientStatsService
)
import json


class Command(BaseCommand):
    help = 'Advanced patient management operations'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # Find duplicates
        duplicate_parser = subparsers.add_parser('find-duplicates', help='Find potential duplicate patients')
        duplicate_parser.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold (0.0-1.0)')
        duplicate_parser.add_argument('--output', type=str, help='Output file for results')
        duplicate_parser.add_argument('--auto-merge', action='store_true', help='Automatically merge high-confidence duplicates')
        
        # Validate patients
        validate_parser = subparsers.add_parser('validate', help='Validate patient data')
        validate_parser.add_argument('--fix', action='store_true', help='Automatically fix common issues')
        validate_parser.add_argument('--patient-id', type=str, help='Validate specific patient by ID')
        
        # Patient statistics
        stats_parser = subparsers.add_parser('stats', help='Generate patient statistics')
        stats_parser.add_argument('--output', type=str, help='Output file for statistics')
        
        # Search patients
        search_parser = subparsers.add_parser('search', help='Search patients')
        search_parser.add_argument('--query', type=str, help='Search query')
        search_parser.add_argument('--first-name', type=str, help='First name')
        search_parser.add_argument('--last-name', type=str, help='Last name')
        search_parser.add_argument('--dob', type=str, help='Date of birth (YYYY-MM-DD)')
        search_parser.add_argument('--phone', type=str, help='Phone number')
        search_parser.add_argument('--limit', type=int, default=10, help='Maximum results')
        
        # Merge patients
        merge_parser = subparsers.add_parser('merge', help='Merge duplicate patients')
        merge_parser.add_argument('primary_id', type=str, help='Primary patient ID (to keep)')
        merge_parser.add_argument('duplicate_id', type=str, help='Duplicate patient ID (to merge)')
        merge_parser.add_argument('--user', type=str, default='system', help='Username performing merge')
    
    def handle(self, *args, **options):
        """Execute the command based on action"""
        action = options.get('action')
        
        if not action:
            self.print_help('manage.py', 'patient_manager')
            return
        
        try:
            if action == 'find-duplicates':
                self.find_duplicates(options)
            elif action == 'validate':
                self.validate_patients(options)
            elif action == 'stats':
                self.generate_statistics(options)
            elif action == 'search':
                self.search_patients(options)
            elif action == 'merge':
                self.merge_patients(options)
            else:
                raise CommandError(f'Unknown action: {action}')
                
        except Exception as e:
            raise CommandError(f'❌ Command failed: {str(e)}')
    
    def find_duplicates(self, options):
        """Find potential duplicate patients"""
        self.stdout.write(
            self.style.SUCCESS('🔍 Finding potential duplicate patients...')
        )
        
        threshold = options['threshold']
        output_file = options.get('output')
        auto_merge = options.get('auto_merge', False)
        
        all_duplicates = []
        processed_pairs = set()
        
        # Get all active patients
        patients = Patient.objects.filter(is_active=True).order_by('created_at')
        total_patients = patients.count()
        
        self.stdout.write(f'📊 Analyzing {total_patients} patients...')
        
        processed = 0
        for patient in patients:
            if processed % 100 == 0:
                self.stdout.write(f'   Progress: {processed}/{total_patients}')
            
            duplicates = DuplicatePatientDetector.find_potential_duplicates(
                patient, threshold
            )
            
            for dup_patient, score, details in duplicates:
                # Avoid duplicate pairs
                pair_key = tuple(sorted([str(patient.id), str(dup_patient.id)]))
                if pair_key not in processed_pairs:
                    processed_pairs.add(pair_key)
                    
                    duplicate_info = {
                        'primary_patient': {
                            'id': str(patient.id),
                            'name': patient.get_full_name(),
                            'dob': str(patient.date_of_birth),
                            'phone': patient.phone_mobile or patient.phone_home,
                            'email': patient.email,
                            'created_at': patient.created_at.isoformat()
                        },
                        'duplicate_patient': {
                            'id': str(dup_patient.id),
                            'name': dup_patient.get_full_name(),
                            'dob': str(dup_patient.date_of_birth),
                            'phone': dup_patient.phone_mobile or dup_patient.phone_home,
                            'email': dup_patient.email,
                            'created_at': dup_patient.created_at.isoformat()
                        },
                        'similarity_score': score,
                        'match_details': details
                    }
                    
                    all_duplicates.append(duplicate_info)
            
            processed += 1
        
        # Sort by similarity score
        all_duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        self.stdout.write(f'🎯 Found {len(all_duplicates)} potential duplicate pairs')
        
        # Display top results
        for i, dup in enumerate(all_duplicates[:10]):
            self.stdout.write(
                f"\n{i+1}. Similarity: {dup['similarity_score']:.2f}"
            )
            self.stdout.write(
                f"   Primary: {dup['primary_patient']['name']} (DOB: {dup['primary_patient']['dob']})"
            )
            self.stdout.write(
                f"   Duplicate: {dup['duplicate_patient']['name']} (DOB: {dup['duplicate_patient']['dob']})"
            )
        
        # Auto-merge high-confidence duplicates
        if auto_merge:
            self.stdout.write('\n🤖 Auto-merging high-confidence duplicates...')
            
            high_confidence = [d for d in all_duplicates if d['similarity_score'] >= 0.95]
            merged_count = 0
            
            try:
                admin_user = User.objects.filter(is_superuser=True).first()
                if not admin_user:
                    self.stdout.write(
                        self.style.WARNING('⚠️  No admin user found for auto-merge')
                    )
                else:
                    for dup in high_confidence:
                        try:
                            primary = Patient.objects.get(id=dup['primary_patient']['id'])
                            duplicate = Patient.objects.get(id=dup['duplicate_patient']['id'])
                            
                            # Use older patient as primary
                            if duplicate.created_at < primary.created_at:
                                primary, duplicate = duplicate, primary
                            
                            with transaction.atomic():
                                merge_result = DuplicatePatientDetector.merge_patients(
                                    primary, duplicate, admin_user
                                )
                                merged_count += 1
                                
                                self.stdout.write(
                                    f"   ✅ Merged {duplicate.get_full_name()} into {primary.get_full_name()}"
                                )
                                
                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f'   ⚠️  Failed to merge: {str(e)}')
                            )
                
                self.stdout.write(f'✅ Auto-merged {merged_count} duplicate pairs')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Auto-merge failed: {str(e)}')
                )
        
        # Save results to file
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump({
                        'generated_at': timezone.now().isoformat(),
                        'threshold': threshold,
                        'total_duplicates': len(all_duplicates),
                        'duplicates': all_duplicates
                    }, f, indent=2)
                
                self.stdout.write(f'💾 Results saved to {output_file}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Failed to save results: {str(e)}')
                )
    
    def validate_patients(self, options):
        """Validate patient data"""
        self.stdout.write(
            self.style.SUCCESS('✅ Validating patient data...')
        )
        
        fix_issues = options.get('fix', False)
        patient_id = options.get('patient_id')
        
        if patient_id:
            # Validate specific patient
            try:
                patient = Patient.objects.get(id=patient_id)
                patients = [patient]
            except Patient.DoesNotExist:
                raise CommandError(f'Patient not found: {patient_id}')
        else:
            # Validate all patients
            patients = Patient.objects.filter(is_active=True)
        
        total_patients = len(patients) if isinstance(patients, list) else patients.count()
        issues_found = 0
        issues_fixed = 0
        
        self.stdout.write(f'📊 Validating {total_patients} patients...')
        
        for i, patient in enumerate(patients):
            if i % 100 == 0 and i > 0:
                self.stdout.write(f'   Progress: {i}/{total_patients}')
            
            # Prepare patient data for validation
            patient_data = {
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'date_of_birth': patient.date_of_birth,
                'gender': patient.gender,
                'phone_home': patient.phone_home,
                'phone_mobile': patient.phone_mobile,
                'phone_work': patient.phone_work,
                'email': patient.email,
            }
            
            is_valid, errors = PatientDataValidator.validate_patient_data(patient_data)
            
            if not is_valid:
                issues_found += 1
                
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Patient {patient.get_full_name()} (ID: {patient.id}):"
                    )
                )
                for error in errors:
                    self.stdout.write(f"   - {error}")
                
                if fix_issues:
                    # Attempt to fix common issues
                    fixed = self._fix_patient_issues(patient, errors)
                    if fixed:
                        issues_fixed += 1
                        self.stdout.write("   ✅ Fixed automatically")
        
        self.stdout.write(f'\n📈 Validation Summary:')
        self.stdout.write(f'   Total patients checked: {total_patients}')
        self.stdout.write(f'   Issues found: {issues_found}')
        if fix_issues:
            self.stdout.write(f'   Issues fixed: {issues_fixed}')
    
    def _fix_patient_issues(self, patient, errors):
        """Attempt to fix common patient data issues"""
        fixed = False
        
        # Normalize data
        normalized_data = PatientDataValidator.normalize_patient_data({
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'middle_name': patient.middle_name,
            'phone_home': patient.phone_home,
            'phone_mobile': patient.phone_mobile,
            'phone_work': patient.phone_work,
            'email': patient.email,
            'address_street': patient.address_street,
            'address_city': patient.address_city,
            'address_state': patient.address_state,
            'address_zip': patient.address_zip,
        })
        
        # Apply normalized data
        for field, value in normalized_data.items():
            if hasattr(patient, field) and value:
                if getattr(patient, field) != value:
                    setattr(patient, field, value)
                    fixed = True
        
        if fixed:
            patient.save()
        
        return fixed
    
    def generate_statistics(self, options):
        """Generate patient statistics"""
        self.stdout.write(
            self.style.SUCCESS('📊 Generating patient statistics...')
        )
        
        output_file = options.get('output')
        
        stats = PatientStatsService.get_patient_demographics()
        
        # Display statistics
        self.stdout.write(f"\n👥 Patient Demographics:")
        self.stdout.write(f"   Total Patients: {stats['total_patients']}")
        
        self.stdout.write(f"\n🚻 Gender Distribution:")
        for gender, count in stats['gender_distribution'].items():
            gender_name = {'M': 'Male', 'F': 'Female', 'O': 'Other', 'U': 'Unknown'}.get(gender, gender)
            percentage = (count / stats['total_patients'] * 100) if stats['total_patients'] > 0 else 0
            self.stdout.write(f"   {gender_name}: {count} ({percentage:.1f}%)")
        
        self.stdout.write(f"\n📅 Age Distribution:")
        for age_group, count in stats['age_distribution'].items():
            percentage = (count / stats['total_patients'] * 100) if stats['total_patients'] > 0 else 0
            self.stdout.write(f"   {age_group}: {count} ({percentage:.1f}%)")
        
        self.stdout.write(f"\n📈 Registration Trends (Last 12 Months):")
        for trend in stats['registration_trends'][-12:]:
            month = trend['month'].strftime('%Y-%m') if hasattr(trend['month'], 'strftime') else str(trend['month'])
            self.stdout.write(f"   {month}: {trend['count']} new registrations")
        
        # Save to file
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump({
                        'generated_at': timezone.now().isoformat(),
                        'statistics': stats
                    }, f, indent=2, default=str)
                
                self.stdout.write(f'💾 Statistics saved to {output_file}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Failed to save statistics: {str(e)}')
                )
    
    def search_patients(self, options):
        """Search patients"""
        self.stdout.write(
            self.style.SUCCESS('🔍 Searching patients...')
        )
        
        search_params = {
            'query': options.get('query'),
            'first_name': options.get('first_name'),
            'last_name': options.get('last_name'),
            'date_of_birth': options.get('dob'),
            'phone': options.get('phone'),
            'limit': options.get('limit', 10)
        }
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        if not any(search_params.values()):
            raise CommandError('At least one search parameter is required')
        
        results = PatientSearchService.search_patients(**search_params)
        
        self.stdout.write(f'📊 Found {len(results)} patients:')
        
        for i, patient in enumerate(results, 1):
            self.stdout.write(f"\n{i}. {patient.get_full_name()}")
            self.stdout.write(f"   ID: {patient.id}")
            self.stdout.write(f"   DOB: {patient.date_of_birth}")
            self.stdout.write(f"   Phone: {patient.phone_mobile or patient.phone_home or 'N/A'}")
            self.stdout.write(f"   Email: {patient.email or 'N/A'}")
            self.stdout.write(f"   Created: {patient.created_at.strftime('%Y-%m-%d')}")
    
    def merge_patients(self, options):
        """Merge duplicate patients"""
        self.stdout.write(
            self.style.SUCCESS('🔀 Merging patients...')
        )
        
        primary_id = options['primary_id']
        duplicate_id = options['duplicate_id']
        username = options.get('user', 'system')
        
        try:
            primary_patient = Patient.objects.get(id=primary_id, is_active=True)
            duplicate_patient = Patient.objects.get(id=duplicate_id, is_active=True)
            
            if username == 'system':
                user = User.objects.filter(is_superuser=True).first()
                if not user:
                    raise CommandError('No admin user found for system merge')
            else:
                user = User.objects.get(username=username)
            
        except Patient.DoesNotExist as e:
            raise CommandError(f'Patient not found: {str(e)}')
        except User.DoesNotExist:
            raise CommandError(f'User not found: {username}')
        
        # Display patients for confirmation
        self.stdout.write(f"\n🎯 Primary Patient (to keep):")
        self.stdout.write(f"   {primary_patient.get_full_name()} (ID: {primary_patient.id})")
        self.stdout.write(f"   DOB: {primary_patient.date_of_birth}")
        self.stdout.write(f"   Created: {primary_patient.created_at}")
        
        self.stdout.write(f"\n🗑️  Duplicate Patient (to merge):")
        self.stdout.write(f"   {duplicate_patient.get_full_name()} (ID: {duplicate_patient.id})")
        self.stdout.write(f"   DOB: {duplicate_patient.date_of_birth}")
        self.stdout.write(f"   Created: {duplicate_patient.created_at}")
        
        # Perform merge
        with transaction.atomic():
            merge_result = DuplicatePatientDetector.merge_patients(
                primary_patient, duplicate_patient, user
            )
        
        self.stdout.write(f"\n✅ Merge completed successfully!")
        self.stdout.write(f"📊 Merge Summary:")
        
        for category, count in merge_result['merged_data'].items():
            if isinstance(count, int):
                self.stdout.write(f"   {category.replace('_', ' ').title()}: {count}")
            elif isinstance(count, list):
                self.stdout.write(f"   {category.replace('_', ' ').title()}: {', '.join(count)}")
        
        self.stdout.write(f"🕒 Merged at: {merge_result['merged_at']}")
        self.stdout.write(f"👤 Merged by: {user.username}")
