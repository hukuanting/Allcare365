"""
Code Systems Services

This module provides business logic and services for managing
medical coding systems including search, validation, and import functions.
"""

from django.db import transaction
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import List, Dict, Optional, Any
import logging
import hashlib
import csv
import json

from .models import (
    CodeSystemVersion, ICD10Code, CPTCode, SNOMEDConcept,
    RxNormConcept, LOINCCode, CodeMapping, CustomCodeSet, CustomCode
)

logger = logging.getLogger(__name__)


class CodeSystemService:
    """Service for managing code systems"""
    
    @staticmethod
    def search_codes(
        system: str,
        query: str,
        limit: int = 50,
        exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for codes across different coding systems
        
        Args:
            system: Code system to search ('icd10', 'cpt', 'snomed', etc.)
            query: Search query
            limit: Maximum number of results
            exact_match: Whether to perform exact match
            
        Returns:
            List of matching codes
        """
        results = []
        
        try:
            if system == 'icd10':
                queryset = ICD10Code.objects.filter(is_active=True)
                if exact_match:
                    queryset = queryset.filter(code__iexact=query)
                else:
                    queryset = queryset.filter(
                        Q(code__icontains=query) |
                        Q(short_description__icontains=query) |
                        Q(long_description__icontains=query)
                    )
                
                for code in queryset[:limit]:
                    results.append({
                        'system': 'icd10',
                        'code': code.code,
                        'description': code.short_description,
                        'long_description': code.long_description,
                        'billable': code.billable,
                        'category': code.category
                    })
                    
            elif system == 'cpt':
                queryset = CPTCode.objects.filter(is_active=True)
                if exact_match:
                    queryset = queryset.filter(code__iexact=query)
                else:
                    queryset = queryset.filter(
                        Q(code__icontains=query) |
                        Q(short_description__icontains=query) |
                        Q(long_description__icontains=query)
                    )
                
                for code in queryset[:limit]:
                    results.append({
                        'system': 'cpt',
                        'code': code.code,
                        'description': code.short_description,
                        'long_description': code.long_description,
                        'category': code.category,
                        'modifier_allowed': code.modifier_allowed
                    })
                    
            elif system == 'snomed':
                queryset = SNOMEDConcept.objects.filter(is_active=True)
                if exact_match:
                    queryset = queryset.filter(concept_id__iexact=query)
                else:
                    queryset = queryset.filter(
                        Q(concept_id__icontains=query) |
                        Q(preferred_term__icontains=query) |
                        Q(fully_specified_name__icontains=query)
                    )
                
                for concept in queryset[:limit]:
                    results.append({
                        'system': 'snomed',
                        'code': concept.concept_id,
                        'description': concept.preferred_term,
                        'fully_specified_name': concept.fully_specified_name,
                        'semantic_tag': concept.semantic_tag
                    })
                    
            elif system == 'rxnorm':
                queryset = RxNormConcept.objects.filter(
                    is_active=True,
                    suppress='N'
                )
                if exact_match:
                    queryset = queryset.filter(rxcui__iexact=query)
                else:
                    queryset = queryset.filter(
                        Q(rxcui__icontains=query) |
                        Q(concept_name__icontains=query)
                    )
                
                for concept in queryset[:limit]:
                    results.append({
                        'system': 'rxnorm',
                        'code': concept.rxcui,
                        'description': concept.concept_name,
                        'tty': concept.tty,
                        'source': concept.source
                    })
                    
            elif system == 'loinc':
                queryset = LOINCCode.objects.filter(is_active=True)
                if exact_match:
                    queryset = queryset.filter(loinc_num__iexact=query)
                else:
                    queryset = queryset.filter(
                        Q(loinc_num__icontains=query) |
                        Q(short_name__icontains=query) |
                        Q(long_common_name__icontains=query)
                    )
                
                for code in queryset[:limit]:
                    results.append({
                        'system': 'loinc',
                        'code': code.loinc_num,
                        'description': code.short_name,
                        'long_common_name': code.long_common_name,
                        'component': code.component,
                        'property': code.property
                    })
                    
            logger.info(f"Code search completed: {system}, query: {query}, results: {len(results)}")
            
        except Exception as e:
            logger.error(f"Error searching codes: {str(e)}")
            raise
            
        return results
    
    @staticmethod
    def validate_code(system: str, code: str) -> Dict[str, Any]:
        """
        Validate a code in a specific system
        
        Args:
            system: Code system name
            code: Code to validate
            
        Returns:
            Validation result with code details
        """
        try:
            if system == 'icd10':
                try:
                    code_obj = ICD10Code.objects.get(code=code, is_active=True)
                    return {
                        'valid': True,
                        'code': code_obj.code,
                        'description': code_obj.short_description,
                        'billable': code_obj.billable,
                        'valid_for_coding': code_obj.valid_for_coding
                    }
                except ICD10Code.DoesNotExist:
                    return {'valid': False, 'message': 'Code not found'}
                    
            elif system == 'cpt':
                try:
                    code_obj = CPTCode.objects.get(code=code, is_active=True)
                    return {
                        'valid': True,
                        'code': code_obj.code,
                        'description': code_obj.short_description,
                        'category': code_obj.category,
                        'modifier_allowed': code_obj.modifier_allowed
                    }
                except CPTCode.DoesNotExist:
                    return {'valid': False, 'message': 'Code not found'}
                    
            elif system == 'snomed':
                try:
                    concept = SNOMEDConcept.objects.get(concept_id=code, is_active=True)
                    return {
                        'valid': True,
                        'code': concept.concept_id,
                        'description': concept.preferred_term,
                        'semantic_tag': concept.semantic_tag
                    }
                except SNOMEDConcept.DoesNotExist:
                    return {'valid': False, 'message': 'Concept not found'}
                    
            else:
                return {'valid': False, 'message': f'Unknown system: {system}'}
                
        except Exception as e:
            logger.error(f"Error validating code {code} in {system}: {str(e)}")
            return {'valid': False, 'message': str(e)}
    
    @staticmethod
    def get_code_mappings(
        source_system: str,
        source_code: str,
        target_system: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get code mappings between systems
        
        Args:
            source_system: Source code system
            source_code: Source code
            target_system: Target system (optional)
            
        Returns:
            List of mappings
        """
        try:
            queryset = CodeMapping.objects.filter(
                source_system=source_system,
                source_code=source_code,
                is_active=True
            )
            
            if target_system:
                queryset = queryset.filter(target_system=target_system)
            
            mappings = []
            for mapping in queryset:
                mappings.append({
                    'source_system': mapping.source_system,
                    'source_code': mapping.source_code,
                    'target_system': mapping.target_system,
                    'target_code': mapping.target_code,
                    'mapping_type': mapping.mapping_type,
                    'confidence': float(mapping.confidence),
                    'notes': mapping.notes
                })
            
            return mappings
            
        except Exception as e:
            logger.error(f"Error getting code mappings: {str(e)}")
            return []
    
    @staticmethod
    def get_system_statistics() -> Dict[str, Any]:
        """
        Get statistics about installed code systems
        
        Returns:
            Dictionary with system statistics
        """
        try:
            stats = {}
            
            # Get installed versions
            versions = CodeSystemVersion.objects.filter(
                status='installed'
            ).values('system_name').annotate(
                count=Count('id')
            )
            
            for version in versions:
                system = version['system_name']
                stats[system] = {
                    'versions_installed': version['count'],
                    'total_codes': 0,
                    'latest_version': None
                }
                
                # Get latest version
                latest = CodeSystemVersion.objects.filter(
                    system_name=system,
                    status='installed'
                ).order_by('-revision_date').first()
                
                if latest:
                    stats[system]['latest_version'] = latest.version
                    stats[system]['total_codes'] = latest.records_count
            
            # Get code counts
            stats['icd10'] = stats.get('icd10', {})
            stats['icd10']['total_codes'] = ICD10Code.objects.filter(is_active=True).count()
            
            stats['cpt'] = stats.get('cpt', {})
            stats['cpt']['total_codes'] = CPTCode.objects.filter(is_active=True).count()
            
            stats['snomed'] = stats.get('snomed', {})
            stats['snomed']['total_codes'] = SNOMEDConcept.objects.filter(is_active=True).count()
            
            stats['rxnorm'] = stats.get('rxnorm', {})
            stats['rxnorm']['total_codes'] = RxNormConcept.objects.filter(is_active=True).count()
            
            stats['loinc'] = stats.get('loinc', {})
            stats['loinc']['total_codes'] = LOINCCode.objects.filter(is_active=True).count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {str(e)}")
            return {}
    
    @staticmethod
    def get_code_info(system, code):
        """
        Get detailed information about a specific code.
        
        Args:
            system (str): Code system ('icd10', 'cpt', 'snomed', 'rxnorm', 'loinc')
            code (str): The code to look up
            
        Returns:
            dict: Code information or None if not found
        """
        try:
            if system == 'icd10':
                try:
                    code_obj = ICD10Code.objects.get(code=code, is_active=True)
                    return {
                        'system': 'icd10',
                        'code': code_obj.code,
                        'description': code_obj.short_description,
                        'long_description': code_obj.long_description,
                        'billable': code_obj.billable,
                        'category': code_obj.category,
                        'valid_for_coding': code_obj.valid_for_coding
                    }
                except ICD10Code.DoesNotExist:
                    return None
                    
            elif system == 'cpt':
                try:
                    code_obj = CPTCode.objects.get(code=code, is_active=True)
                    return {
                        'system': 'cpt',
                        'code': code_obj.code,
                        'description': code_obj.short_description,
                        'long_description': code_obj.long_description,
                        'category': code_obj.category
                    }
                except CPTCode.DoesNotExist:
                    return None
                    
            elif system == 'snomed':
                try:
                    concept = SNOMEDConcept.objects.get(concept_id=code, is_active=True)
                    return {
                        'system': 'snomed',
                        'code': concept.concept_id,
                        'description': concept.preferred_term,
                        'fully_specified_name': concept.fully_specified_name,
                        'definition': concept.definition,
                        'semantic_tag': concept.semantic_tag
                    }
                except SNOMEDConcept.DoesNotExist:
                    return None
                    
            elif system == 'rxnorm':
                try:
                    concept = RxNormConcept.objects.get(rxcui=code, is_active=True)
                    return {
                        'system': 'rxnorm',
                        'code': concept.rxcui,
                        'description': concept.preferred_term,
                        'tty': concept.tty
                    }
                except RxNormConcept.DoesNotExist:
                    return None
                    
            elif system == 'loinc':
                try:
                    code_obj = LOINCCode.objects.get(loinc_num=code, is_active=True)
                    return {
                        'system': 'loinc',
                        'code': code_obj.loinc_num,
                        'description': code_obj.short_name,
                        'long_common_name': code_obj.long_common_name,
                        'component': code_obj.component,
                        'property': code_obj.property,
                        'time_aspect': code_obj.time_aspect,
                        'system': code_obj.system,
                        'scale_typ': code_obj.scale_typ,
                        'method_typ': code_obj.method_typ
                    }
                except LOINCCode.DoesNotExist:
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting code info for {system}:{code}: {str(e)}")
            return None


class CodeImportService:
    """Service for importing code data"""
    
    def __init__(self, version_id: str):
        """
        Initialize the service with a specific code system version.

        Args:
            version_id: The UUID of the CodeSystemVersion to import codes for.
        """
        try:
            self.version = CodeSystemVersion.objects.get(id=version_id)
        except CodeSystemVersion.DoesNotExist:
            raise ValueError("Invalid CodeSystemVersion ID")
    
    def import_codes(self, system: str, file_obj, file_format: str = 'csv', user=None) -> str:
        """
        Import codes from a file
        
        Args:
            system: Code system to import ('icd10', 'cpt', 'snomed', etc.)
            file_obj: File object to import from
            file_format: Format of the file ('csv', 'json', 'xml')
            user: User performing the import
            
        Returns:
            Task ID for tracking import progress
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        try:
            # This is a simplified implementation
            # In production, this should be handled by a background task queue
            if file_format == 'csv':
                return self._import_csv(system, file_obj, task_id, user)
            elif file_format == 'json':
                return self._import_json(system, file_obj, task_id, user)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
        
        except Exception as e:
            logger.error(f"Import failed for task {task_id}: {str(e)}")
            raise
    
    def _import_csv(self, system: str, file_obj, task_id: str, user=None) -> str:
        """Import codes from CSV file"""
        import csv
        import io
        
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        csv_reader = csv.DictReader(io.StringIO(content))
        
        # Use the existing version instead of creating a new one
        version = self.version
        
        # Process the CSV data
        imported_count = 0
        
        # Validate the system is supported
        supported_systems = ['icd10', 'cpt', 'snomed', 'rxnorm', 'loinc']
        if system not in supported_systems:
            raise ValueError(f"Unsupported system: {system}. Supported systems are: {', '.join(supported_systems)}")
        
        for row in csv_reader:
            try:
                if system == 'icd10':
                    ICD10Code.objects.create(
                        code=row.get('code', row.get('Code', '')),
                        short_description=row.get('short_description', row.get('Short Description', '')),
                        long_description=row.get('long_description', row.get('Long Description', '')),
                        category=row.get('category', row.get('Category', '')),
                        billable=str(row.get('billable', row.get('Billable', 'false'))).lower() == 'true',
                        valid_for_coding=True,
                        version=version,
                        created_by=user
                    )
                elif system == 'cpt':
                    CPTCode.objects.create(
                        code=row.get('code', row.get('Code', '')),
                        short_description=row.get('short_description', row.get('Short Description', '')),
                        long_description=row.get('long_description', row.get('Long Description', '')),
                        category=row.get('category', row.get('Category', '')),
                        version=version,
                        created_by=user
                    )
                elif system == 'snomed':
                    SNOMEDConcept.objects.create(
                        concept_id=row.get('concept_id', row.get('Concept ID', '')),
                        fully_specified_name=row.get('fully_specified_name', row.get('Fully Specified Name', '')),
                        preferred_term=row.get('preferred_term', row.get('Preferred Term', '')),
                        definition=row.get('definition', row.get('Definition', '')),
                        semantic_tag=row.get('semantic_tag', row.get('Semantic Tag', '')),
                        module_id=row.get('module_id', row.get('Module ID', '')),
                        version=version,
                        created_by=user
                    )
                elif system == 'rxnorm':
                    RxNormConcept.objects.create(
                        rxcui=row.get('rxcui', row.get('RXCUI', '')),
                        preferred_term=row.get('preferred_term', row.get('Preferred Term', '')),
                        tty=row.get('tty', row.get('TTY', '')),
                        source=row.get('source', row.get('Source', '')),
                        suppress=row.get('suppress', row.get('Suppress', 'N')),
                        version=version,
                        created_by=user
                    )
                elif system == 'loinc':
                    LOINCCode.objects.create(
                        loinc_num=row.get('loinc_num', row.get('LOINC Number', '')),
                        component=row.get('component', row.get('Component', '')),
                        property=row.get('property', row.get('Property', '')),
                        time_aspct=row.get('time_aspct', row.get('time_aspect', row.get('Time Aspect', ''))),
                        system=row.get('system', row.get('System', '')),
                        scale_typ=row.get('scale_typ', row.get('Scale Type', '')),
                        method_typ=row.get('method_typ', row.get('Method Type', '')),
                        short_name=row.get('short_name', row.get('Short Name', '')),
                        long_common_name=row.get('long_common_name', row.get('Long Common Name', '')),
                        status=row.get('status', row.get('Status', 'ACTIVE')),
                        version=version,
                        created_by=user
                    )
                imported_count += 1
            except Exception as e:
                logger.error(f"Error importing row {row}: {str(e)}")
                continue
        
        # Update version status
        version.status = 'current'
        version.save()
        
        logger.info(f"Completed CSV import for {system} with task ID {task_id}. Imported {imported_count} codes.")
        
        return task_id
    
    def _import_json(self, system: str, file_obj, task_id: str, user=None) -> str:
        """Import codes from JSON file"""
        import json
        
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        data = json.loads(content)
        
        # Create a version for the import
        version = CodeSystemVersion.objects.create(
            system_name=system,
            version=f'import_{task_id[:8]}',
            revision_date=timezone.now().date(),
            status='installing',
            file_name=getattr(file_obj, 'name', 'unknown'),
            created_by=user
        )
        
        # This is a simplified implementation
        # In production, you would parse the JSON and create the appropriate model instances
        logger.info(f"Started JSON import for {system} with task ID {task_id}")
        
        return task_id


class CustomCodeService:
    """Service for managing custom code sets"""
    
    @staticmethod
    @transaction.atomic
    def create_code_set(
        name: str,
        description: str,
        prefix: str = '',
        user=None
    ) -> CustomCodeSet:
        """
        Create a new custom code set
        
        Args:
            name: Code set name
            description: Description
            prefix: Code prefix
            user: User creating the code set
            
        Returns:
            Created CustomCodeSet instance
        """
        try:
            code_set = CustomCodeSet.objects.create(
                name=name,
                description=description,
                prefix=prefix,
                created_by=user
            )
            
            logger.info(f"Created custom code set: {name}")
            return code_set
            
        except Exception as e:
            logger.error(f"Error creating custom code set: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def add_codes_to_set(
        code_set_id: str,
        codes: List[Dict[str, Any]],
        user=None
    ) -> Dict[str, Any]:
        """
        Add codes to a custom code set
        
        Args:
            code_set_id: Code set ID
            codes: List of code dictionaries
            user: User adding the codes
            
        Returns:
            Result of the operation
        """
        try:
            code_set = CustomCodeSet.objects.get(id=code_set_id)
            added_count = 0
            errors = []
            
            for code_data in codes:
                try:
                    CustomCode.objects.create(
                        code_set=code_set,
                        code=code_data['code'],
                        description=code_data['description'],
                        sort_order=code_data.get('sort_order', 0),
                        created_by=user
                    )
                    added_count += 1
                    
                except Exception as e:
                    errors.append(f"Code {code_data.get('code', 'unknown')}: {str(e)}")
            
            return {
                'success': len(errors) == 0,
                'added_count': added_count,
                'error_count': len(errors),
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error adding codes to set: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'added_count': 0
            }


class CodeValidationService:
    """Service for validating codes"""

    def __init__(self, version_id: str = None):
        """
        Initialize the service.

        Args:
            version_id: Optional UUID of a specific CodeSystemVersion to validate against.
        """
        self.version = None
        if version_id:
            try:
                self.version = CodeSystemVersion.objects.get(id=version_id)
            except CodeSystemVersion.DoesNotExist:
                raise ValueError("Invalid CodeSystemVersion ID")

    @staticmethod
    def validate_code(system: str, code: str) -> bool:
        """
        Validate if a code exists in the specified system
        
        Args:
            system: Code system ('icd10', 'cpt', 'snomed', etc.)
            code: Code to validate
            
        Returns:
            True if code exists and is active, False otherwise
        """
        try:
            if system == 'icd10':
                return ICD10Code.objects.filter(code=code, is_active=True).exists()
            elif system == 'cpt':
                return CPTCode.objects.filter(code=code, is_active=True).exists()
            elif system == 'snomed':
                return SNOMEDConcept.objects.filter(concept_id=code, is_active=True).exists()
            elif system == 'rxnorm':
                return RxNormConcept.objects.filter(rxcui=code, is_active=True).exists()
            elif system == 'loinc':
                return LOINCCode.objects.filter(loinc_num=code, is_active=True).exists()
            else:
                return False
        except Exception as e:
            logger.error(f"Error validating code {code} in system {system}: {str(e)}")
            return False
    
    @staticmethod
    def validate_code_static(system: str, code: str) -> bool:
        """
        Static method to validate if a code exists in the specified system
        
        Args:
            system: Code system ('icd10', 'cpt', 'snomed', etc.)
            code: Code to validate
            
        Returns:
            True if code exists and is active, False otherwise
        """
        try:
            if system == 'icd10':
                return ICD10Code.objects.filter(code=code, is_active=True).exists()
            elif system == 'cpt':
                return CPTCode.objects.filter(code=code, is_active=True).exists()
            elif system == 'snomed':
                return SNOMEDConcept.objects.filter(concept_id=code, is_active=True).exists()
            elif system == 'rxnorm':
                return RxNormConcept.objects.filter(rxcui=code, is_active=True).exists()
            elif system == 'loinc':
                return LOINCCode.objects.filter(loinc_num=code, is_active=True).exists()
            else:
                return False
        except Exception as e:
            logger.error(f"Error validating code {code} in system {system}: {str(e)}")
            return False
    
    @staticmethod
    def validate_codes_batch(system: str, codes: List[str]) -> Dict[str, bool]:
        """
        Validate multiple codes in batch
        
        Args:
            system: Code system
            codes: List of codes to validate
            
        Returns:
            Dictionary mapping codes to validation results
        """
        results = {}
        
        try:
            if system == 'icd10':
                existing_codes = set(
                    ICD10Code.objects.filter(
                        code__in=codes, 
                        is_active=True
                    ).values_list('code', flat=True)
                )
            elif system == 'cpt':
                existing_codes = set(
                    CPTCode.objects.filter(
                        code__in=codes, 
                        is_active=True
                    ).values_list('code', flat=True)
                )
            elif system == 'snomed':
                existing_codes = set(
                    SNOMEDConcept.objects.filter(
                        concept_id__in=codes, 
                        is_active=True
                    ).values_list('concept_id', flat=True)
                )
            elif system == 'rxnorm':
                existing_codes = set(
                    RxNormConcept.objects.filter(
                        rxcui__in=codes, 
                        is_active=True
                    ).values_list('rxcui', flat=True)
                )
            elif system == 'loinc':
                existing_codes = set(
                    LOINCCode.objects.filter(
                        loinc_num__in=codes, 
                        is_active=True
                    ).values_list('loinc_num', flat=True)
                )
            else:
                existing_codes = set()
            
            for code in codes:
                results[code] = code in existing_codes
            
        except Exception as e:
            logger.error(f"Error validating codes batch in system {system}: {str(e)}")
            # Return False for all codes if there's an error
            for code in codes:
                results[code] = False
        
        return results
    
    @staticmethod
    def get_validation_details(system: str, code: str) -> Dict[str, Any]:
        """
        Get detailed validation information for a code
        
        Args:
            system: Code system
            code: Code to validate
            
        Returns:
            Dictionary with validation details
        """
        try:
            if system == 'icd10':
                code_obj = ICD10Code.objects.filter(code=code).first()
                if code_obj:
                    return {
                        'valid': code_obj.is_active,
                        'code': code_obj.code,
                        'description': code_obj.short_description,
                        'billable': code_obj.billable,
                        'category': code_obj.category,
                        'system': 'icd10',
                        'active': code_obj.is_active
                    }
            elif system == 'cpt':
                code_obj = CPTCode.objects.filter(code=code).first()
                if code_obj:
                    return {
                        'valid': code_obj.is_active,
                        'code': code_obj.code,
                        'description': code_obj.short_description,
                        'category': code_obj.category,
                        'modifier_allowed': code_obj.modifier_allowed,
                        'system': 'cpt',
                        'active': code_obj.is_active
                    }
            elif system == 'snomed':
                code_obj = SNOMEDConcept.objects.filter(concept_id=code).first()
                if code_obj:
                    return {
                        'valid': code_obj.is_active,
                        'concept_id': code_obj.concept_id,
                        'preferred_term': code_obj.preferred_term,
                        'semantic_tag': code_obj.semantic_tag,
                        'system': 'snomed',
                        'active': code_obj.is_active
                    }
            elif system == 'rxnorm':
                code_obj = RxNormConcept.objects.filter(rxcui=code).first()
                if code_obj:
                    return {
                        'valid': code_obj.is_active,
                        'rxcui': code_obj.rxcui,
                        'name': code_obj.name,
                        'tty': code_obj.tty,
                        'system': 'rxnorm',
                        'active': code_obj.is_active
                    }
            elif system == 'loinc':
                code_obj = LOINCCode.objects.filter(loinc_num=code).first()
                if code_obj:
                    return {
                        'valid': code_obj.is_active,
                        'loinc_num': code_obj.loinc_num,
                        'short_name': code_obj.short_name,
                        'component': code_obj.component,
                        'property': code_obj.property,
                        'system': 'loinc',
                        'active': code_obj.is_active
                    }
            
            return {
                'valid': False,
                'code': code,
                'system': system,
                'error': 'Code not found'
            }
        
        except Exception as e:
            logger.error(f"Error getting validation details for {code} in {system}: {str(e)}")
            return {
                'valid': False,
                'code': code,
                'system': system,
                'error': str(e)
            }

# Add alias for backward compatibility with tests
CodeValidationService.validate_code = staticmethod(CodeValidationService.validate_code_static)
