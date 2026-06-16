"""
Code Systems Admin Configuration

This module provides Django admin interface for managing medical coding systems.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import (
    CodeSystemVersion, ICD10Code, CPTCode, SNOMEDConcept,
    RxNormConcept, LOINCCode, CodeMapping, CustomCodeSet, CustomCode
)
from .services import CodeSystemService, CodeImportService


class BaseCodeAdmin(admin.ModelAdmin):
    """Base admin class for code models"""
    list_per_page = 50
    search_fields = ['code', 'short_description', 'long_description']
    list_filter = ['is_active', 'created_at', 'updated_at']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CodeSystemVersion)
class CodeSystemVersionAdmin(BaseCodeAdmin):
    """Admin for code system versions"""
    list_display = ['system_name', 'version', 'revision_date', 'status', 'is_active']
    list_filter = ['system_name', 'status', 'is_active', 'revision_date']
    search_fields = ['system_name', 'version', 'description']
    ordering = ['-revision_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            code_count=Count('icd10codes') + Count('cptcodes') + Count('snomedconcepts')
        )


@admin.register(ICD10Code)
class ICD10CodeAdmin(BaseCodeAdmin):
    """Admin for ICD-10 codes"""
    list_display = ['code', 'short_description', 'category', 'billable', 'is_active']
    list_filter = ['category', 'billable', 'is_active', 'created_at']
    search_fields = ['code', 'short_description', 'long_description']
    ordering = ['code']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('code', 'short_description', 'long_description')
        }),
        (_('Classification'), {
            'fields': ('category', 'billable', 'valid_for_coding')
        }),
        (_('Metadata'), {
            'fields': ('version', 'effective_date', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(CPTCode)
class CPTCodeAdmin(BaseCodeAdmin):
    """Admin for CPT codes"""
    list_display = ['code', 'short_description', 'category', 'modifier_allowed', 'is_active']
    list_filter = ['category', 'modifier_allowed', 'is_active', 'created_at']
    search_fields = ['code', 'short_description', 'long_description']
    ordering = ['code']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('code', 'short_description', 'long_description')
        }),
        (_('Classification'), {
            'fields': ('category', 'modifier_allowed')
        }),
        (_('Metadata'), {
            'fields': ('version', 'effective_date', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(SNOMEDConcept)
class SNOMEDConceptAdmin(BaseCodeAdmin):
    """Admin for SNOMED CT concepts"""
    list_display = ['concept_id', 'preferred_term', 'semantic_tag', 'is_active']
    list_filter = ['semantic_tag', 'is_active', 'created_at']
    search_fields = ['concept_id', 'preferred_term', 'fully_specified_name']
    ordering = ['concept_id']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('concept_id', 'preferred_term', 'fully_specified_name')
        }),
        (_('Classification'), {
            'fields': ('semantic_tag', 'module_id', 'definition_status')
        }),
        (_('Metadata'), {
            'fields': ('version', 'effective_date', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(RxNormConcept)
class RxNormConceptAdmin(BaseCodeAdmin):
    """Admin for RxNorm concepts"""
    list_display = ['rxcui', 'preferred_term', 'tty', 'is_active']
    list_filter = ['tty', 'is_active', 'created_at']
    search_fields = ['rxcui', 'preferred_term']
    ordering = ['rxcui']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('rxcui', 'preferred_term', 'tty')
        }),
        (_('Metadata'), {
            'fields': ('version', 'source', 'suppress', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(LOINCCode)
class LOINCCodeAdmin(BaseCodeAdmin):
    """Admin for LOINC codes"""
    list_display = ['loinc_num', 'short_name', 'component', 'property', 'is_active']
    list_filter = ['property', 'time_aspct', 'system', 'is_active', 'created_at']
    search_fields = ['loinc_num', 'short_name', 'long_common_name', 'component']
    ordering = ['loinc_num']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('loinc_num', 'short_name', 'long_common_name')
        }),
        (_('Classification'), {
            'fields': ('component', 'property', 'time_aspct', 'system', 'scale_typ', 'method_typ')
        }),
        (_('Metadata'), {
            'fields': ('version', 'status', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(CodeMapping)
class CodeMappingAdmin(BaseCodeAdmin):
    """Admin for code mappings"""
    list_display = ['source_system', 'source_code', 'target_system', 'target_code', 'mapping_type', 'is_active']
    list_filter = ['source_system', 'target_system', 'mapping_type', 'is_active', 'created_at']
    search_fields = ['source_code', 'target_code', 'description']
    ordering = ['source_system', 'source_code']
    
    fieldsets = (
        (_('Source'), {
            'fields': ('source_system', 'source_code', 'source_description')
        }),
        (_('Target'), {
            'fields': ('target_system', 'target_code', 'target_description')
        }),
        (_('Mapping Details'), {
            'fields': ('mapping_type', 'equivalence', 'description')
        }),
        (_('Metadata'), {
            'fields': ('version', 'effective_date', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(CustomCodeSet)
class CustomCodeSetAdmin(BaseCodeAdmin):
    """Admin for custom code sets"""
    list_display = ['name', 'prefix', 'code_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            code_count=Count('codes')
        )
    
    def code_count(self, obj):
        return obj.code_count
    code_count.short_description = _('Code Count')
    code_count.admin_order_field = 'code_count'


@admin.register(CustomCode)
class CustomCodeAdmin(BaseCodeAdmin):
    """Admin for custom codes"""
    list_display = ['code', 'description', 'code_set', 'is_active']
    list_filter = ['code_set', 'is_active', 'created_at']
    search_fields = ['code', 'description']
    ordering = ['code_set', 'code']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('code_set', 'code', 'description')
        }),
        (_('Metadata'), {
            'fields': ('is_active',)
        }),
        (_('System Information'), {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
