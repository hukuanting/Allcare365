"""
Code Systems API Views

This module provides REST API views for managing medical coding systems.
"""

from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
import logging
from typing import Dict, Any, Optional

from .models import (
    CodeSystemVersion, ICD10Code, CPTCode, SNOMEDConcept,
    RxNormConcept, LOINCCode, CodeMapping, CustomCodeSet, CustomCode
)
from .serializers import (
    CodeSystemVersionSerializer, ICD10CodeSerializer, CPTCodeSerializer,
    SNOMEDConceptSerializer, RxNormConceptSerializer, LOINCCodeSerializer,
    CodeMappingSerializer, CustomCodeSetSerializer, CustomCodeSerializer
)
from .services import CodeSystemService, CodeImportService, CodeValidationService

logger = logging.getLogger(__name__)


class CodeSystemPagination(PageNumberPagination):
    """Custom pagination for code systems"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class BaseCodeViewSet(viewsets.ModelViewSet):
    """Base viewset for code models"""
    permission_classes = [IsAuthenticated]
    pagination_class = CodeSystemPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CodeSystemVersionViewSet(BaseCodeViewSet):
    """ViewSet for code system versions"""
    queryset = CodeSystemVersion.objects.all()
    serializer_class = CodeSystemVersionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['system_name', 'status']
    ordering_fields = ['system_name', 'revision_date', 'status']
    search_fields = ['system_name', 'description']

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        """Get statistics for a specific code system version"""
        version = self.get_object()
        
        # Count related codes safely
        stats = {
            'total_codes': 0,
            'icd10_codes': 0,
            'cpt_codes': 0,
            'snomed_concepts': 0,
            'rxnorm_concepts': 0,
            'loinc_codes': 0,
        }
        
        try:
            stats['icd10_codes'] = ICD10Code.objects.filter(version=version).count()
            stats['cpt_codes'] = CPTCode.objects.filter(version=version).count()
            stats['snomed_concepts'] = SNOMEDConcept.objects.filter(version=version).count()
            stats['rxnorm_concepts'] = RxNormConcept.objects.filter(version=version).count()
            stats['loinc_codes'] = LOINCCode.objects.filter(version=version).count()
            
            stats['total_codes'] = sum([
                stats['icd10_codes'], stats['cpt_codes'], stats['snomed_concepts'],
                stats['rxnorm_concepts'], stats['loinc_codes']
            ])
        except Exception as e:
            logger.error(f"Error calculating stats for version {pk}: {e}")
        
        return Response(stats)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats_all(self, request):
        """Get statistics for all code system versions"""
        stats = {}
        try:
            for version in CodeSystemVersion.objects.all():
                icd10_count = ICD10Code.objects.filter(version=version).count()
                cpt_count = CPTCode.objects.filter(version=version).count()
                snomed_count = SNOMEDConcept.objects.filter(version=version).count()
                rxnorm_count = RxNormConcept.objects.filter(version=version).count()
                loinc_count = LOINCCode.objects.filter(version=version).count()
                
                stats[version.system_name] = {
                    'version_id': str(version.id),
                    'version': version.version,
                    'total_codes': icd10_count + cpt_count + snomed_count + rxnorm_count + loinc_count,
                    'icd10_codes': icd10_count,
                    'cpt_codes': cpt_count,
                    'snomed_concepts': snomed_count,
                    'rxnorm_concepts': rxnorm_count,
                    'loinc_codes': loinc_count,
                }
        except Exception as e:
            logger.error(f"Error calculating stats for all versions: {e}")
            
        return Response(stats)

    @action(detail=False, methods=['get'], url_path='overall_stats')
    def overall_stats(self, request):
        """Get overall statistics for all code system versions"""
        try:
            stats = {
                'total_versions': CodeSystemVersion.objects.count(),
                'active_versions': CodeSystemVersion.objects.filter(status='active').count(),
                'total_icd10_codes': ICD10Code.objects.count(),
                'total_cpt_codes': CPTCode.objects.count(),
                'total_snomed_concepts': SNOMEDConcept.objects.count(),
                'total_rxnorm_concepts': RxNormConcept.objects.count(),
                'total_loinc_codes': LOINCCode.objects.count(),
            }
            stats['total_codes'] = sum([
                stats['total_icd10_codes'], stats['total_cpt_codes'], 
                stats['total_snomed_concepts'], stats['total_rxnorm_concepts'],
                stats['total_loinc_codes']
            ])
            return Response(stats)
        except Exception as e:
            logger.error(f"Error calculating overall stats: {e}")
            return Response({'error': 'Unable to calculate statistics'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='current')
    def current_versions(self, request):
        """Get current active versions for all systems"""
        try:
            current_versions = {}
            for system in ['icd10', 'cpt', 'snomed', 'rxnorm', 'loinc']:
                version = CodeSystemVersion.objects.filter(
                    system_name=system, 
                    status='active'
                ).first()
                if version:
                    current_versions[system] = CodeSystemVersionSerializer(version).data
                else:
                    current_versions[system] = None
            return Response(current_versions)
        except Exception as e:
            logger.error(f"Error getting current versions: {e}")
            return Response({'error': 'Unable to get current versions'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ICD10CodeViewSet(BaseCodeViewSet):
    """ViewSet for ICD-10 codes"""
    queryset = ICD10Code.objects.all()
    serializer_class = ICD10CodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['category', 'billable', 'version']
    ordering_fields = ['code', 'short_description', 'category', 'billable']
    search_fields = ['code', 'short_description', 'long_description']

    @action(detail=False, methods=['post'])
    def validate_code(self, request):
        code = request.data.get('code')
        version_id = request.data.get('version_id')
        try:
            is_valid = CodeValidationService(version_id=version_id).validate_code('icd10', code)
            return Response({'is_valid': is_valid})
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class CPTCodeViewSet(BaseCodeViewSet):
    """ViewSet for CPT codes"""
    queryset = CPTCode.objects.all()
    serializer_class = CPTCodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['category', 'modifier_allowed', 'version']
    ordering_fields = ['code', 'short_description', 'category']
    search_fields = ['code', 'short_description', 'long_description']


class SNOMEDConceptViewSet(BaseCodeViewSet):
    """ViewSet for SNOMED CT concepts"""
    queryset = SNOMEDConcept.objects.all()
    serializer_class = SNOMEDConceptSerializer
    permission_classes = [IsAuthenticated]


class RxNormConceptViewSet(BaseCodeViewSet):
    """ViewSet for RxNorm concepts"""
    queryset = RxNormConcept.objects.all()
    serializer_class = RxNormConceptSerializer
    permission_classes = [IsAuthenticated]


class LOINCCodeViewSet(BaseCodeViewSet):
    """ViewSet for LOINC codes"""
    queryset = LOINCCode.objects.all()
    serializer_class = LOINCCodeSerializer
    permission_classes = [IsAuthenticated]


class CodeMappingViewSet(BaseCodeViewSet):
    """ViewSet for code mappings"""
    queryset = CodeMapping.objects.all()
    serializer_class = CodeMappingSerializer
    permission_classes = [IsAuthenticated]


class CustomCodeSetViewSet(BaseCodeViewSet):
    """ViewSet for custom code sets"""
    queryset = CustomCodeSet.objects.all()
    serializer_class = CustomCodeSetSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def codes(self, request, pk=None):
        """Get all codes in this custom code set"""
        code_set = self.get_object()
        codes = code_set.codes.filter(is_active=True)
        
        # Use pagination
        page = self.paginate_queryset(codes)
        if page is not None:
            serializer = CustomCodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CustomCodeSerializer(codes, many=True)
        return Response(serializer.data)


class CustomCodeViewSet(BaseCodeViewSet):
    """ViewSet for custom codes"""
    queryset = CustomCode.objects.all()
    serializer_class = CustomCodeSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_codes(request):
    """Search codes across all code systems"""
    query = request.GET.get('q', '')
    system = request.GET.get('system', 'all')
    limit = int(request.GET.get('limit', 50))
    
    if not query:
        return Response({
            'results': [],
            'count': 0,
            'message': 'Query parameter "q" is required'
        })
    
    results = []
    
    try:
        if system in ['all', 'icd10']:
            icd_codes = ICD10Code.objects.filter(
                Q(code__icontains=query) | Q(short_description__icontains=query)
            ).values('code', 'short_description')[:limit//5 if system == 'all' else limit]
            results.extend([{'system': 'icd10', **code} for code in icd_codes])
        
        if system in ['all', 'cpt']:
            cpt_codes = CPTCode.objects.filter(
                Q(code__icontains=query) | Q(short_description__icontains=query)
            ).values('code', 'short_description')[:limit//5 if system == 'all' else limit]
            results.extend([{'system': 'cpt', **code} for code in cpt_codes])
        
        if system in ['all', 'snomed']:
            snomed_codes = SNOMEDConcept.objects.filter(
                Q(concept_id__icontains=query) | Q(preferred_term__icontains=query)
            ).values('concept_id', 'preferred_term')[:limit//5 if system == 'all' else limit]
            results.extend([{'system': 'snomed', 'code': code['concept_id'], 'short_description': code['preferred_term']} for code in snomed_codes])
        
        if system in ['all', 'rxnorm']:
            rxnorm_codes = RxNormConcept.objects.filter(
                Q(rxcui__icontains=query) | Q(preferred_term__icontains=query)
            ).values('rxcui', 'preferred_term')[:limit//5 if system == 'all' else limit]
            results.extend([{'system': 'rxnorm', 'code': code['rxcui'], 'short_description': code['preferred_term']} for code in rxnorm_codes])
        
        if system in ['all', 'loinc']:
            loinc_codes = LOINCCode.objects.filter(
                Q(loinc_num__icontains=query) | Q(short_name__icontains=query)
            ).values('loinc_num', 'short_name')[:limit//5 if system == 'all' else limit]
            results.extend([{'system': 'loinc', 'code': code['loinc_num'], 'short_description': code['short_name']} for code in loinc_codes])
    
    except Exception as e:
        logger.error(f"Error searching codes: {e}")
        return Response({
            'error': 'An error occurred while searching codes',
            'details': str(e)
        }, status=500)
    
    return Response({
        'results': results[:limit],
        'count': len(results[:limit]),
        'total_found': len(results),
        'query': query,
        'system': system
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_code(request):
    """Validate a code"""
    data = request.data
    
    # Handle both old format (single code) and new format (multiple codes)
    if 'codes' in data:
        codes = data.get('codes', [])
    else:
        # Support legacy format for single code validation
        codes = [{
            'code': data.get('code'),
            'system': data.get('system', 'icd10')
        }]
    
    if not codes:
        return Response({
            'error': 'codes field is required and must be a list'
        }, status=400)
    
    results = []
    
    try:
        for code_data in codes:
            # Handle string format (just the code) vs dict format
            if isinstance(code_data, str):
                code = code_data
                system = 'icd10'  # default system
            else:
                code = code_data.get('code')
                system = code_data.get('system', 'icd10')
            
            if not code:
                results.append({
                    'code': code,
                    'system': system,
                    'is_valid': False,
                    'error': 'Code is required'
                })
                continue
            
            is_valid = False
            error = None
            
            try:
                if system == 'icd10':
                    is_valid = ICD10Code.objects.filter(code=code).exists()
                elif system == 'cpt':
                    is_valid = CPTCode.objects.filter(code=code).exists()
                elif system == 'snomed':
                    is_valid = SNOMEDConcept.objects.filter(concept_id=code).exists()
                elif system == 'rxnorm':
                    is_valid = RxNormConcept.objects.filter(rxcui=code).exists()
                elif system == 'loinc':
                    is_valid = LOINCCode.objects.filter(loinc_num=code).exists()
                else:
                    error = f"Unsupported system: {system}"
            except Exception as e:
                error = str(e)
            
            results.append({
                'code': code,
                'system': system,
                'valid': is_valid,  # Changed from 'is_valid' to 'valid'
                'error': error
            })
    
    except Exception as e:
        logger.error(f"Error validating codes: {e}")
        return Response({
            'error': 'An error occurred while validating codes',
            'details': str(e)
        }, status=500)
    
    return Response({
        'results': results,
        'count': len(results)
    })
