"""
Code Systems Models

This module provides models for managing medical coding systems including
ICD-10, CPT, SNOMED CT, RxNorm, and other standardized medical vocabularies.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid


class BaseCodeModel(models.Model):
    """Base model for all code system models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='%(class)s_updated'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class CodeSystemVersion(BaseCodeModel):
    """Track versions of installed code systems"""
    
    SYSTEM_CHOICES = [
        ('icd10', 'ICD-10'),
        ('icd9', 'ICD-9'),
        ('cpt', 'CPT'),
        ('snomed', 'SNOMED CT'),
        ('rxnorm', 'RxNorm'),
        ('loinc', 'LOINC'),
        ('dsmv', 'DSM-V'),
        ('ndc', 'NDC'),
        ('hcpcs', 'HCPCS'),
        ('custom', 'Custom'),
    ]
    
    STATUS_CHOICES = [
        ('staged', 'Staged'),
        ('installing', 'Installing'),
        ('installed', 'Installed'),
        ('failed', 'Installation Failed'),
        ('deprecated', 'Deprecated'),
    ]
    
    system_name = models.CharField(
        max_length=50,
        choices=SYSTEM_CHOICES,
        help_text=_("Code system name")
    )
    
    version = models.CharField(
        max_length=50,
        help_text=_("Version of the code system")
    )
    
    revision_date = models.DateField(
        help_text=_("Official revision date of this version")
    )
    
    file_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("MD5 checksum of source file")
    )
    
    file_name = models.CharField(
        max_length=255,
        help_text=_("Source file name")
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='staged',
        help_text=_("Installation status")
    )
    
    imported_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date when import was completed")
    )
    
    import_log = models.TextField(
        blank=True,
        help_text=_("Import process log")
    )
    
    records_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of records imported")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Description of this code system version")
    )
    
    class Meta:
        db_table = 'code_system_versions'
        unique_together = ['system_name', 'version']
        ordering = ['-revision_date', '-imported_date']
        
    def __str__(self):
        return f"{self.system_name} ({self.revision_date})"

class ICD10Code(BaseCodeModel):
    """ICD-10 diagnosis codes"""
    
    code = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z][0-9]{2}(\.[0-9X]{1,4})?$',
            message='Invalid ICD-10 code format'
        )],
        help_text=_("ICD-10 code (e.g., F32.1)")
    )
    
    short_description = models.CharField(
        max_length=100,
        help_text=_("Short description")
    )
    
    long_description = models.TextField(
        help_text=_("Full description")
    )
    
    category = models.CharField(
        max_length=5,
        help_text=_("ICD-10 category (e.g., F32)")
    )
    
    billable = models.BooleanField(
        default=True,
        help_text=_("Whether this code is billable")
    )
    
    valid_for_coding = models.BooleanField(
        default=True,
        help_text=_("Whether this code is valid for coding")
    )
    
    version = models.ForeignKey(
        CodeSystemVersion,
        on_delete=models.CASCADE,
        related_name='icd10_codes',
        limit_choices_to={'system_name': 'icd10'}
    )
    
    class Meta:
        db_table = 'icd10_codes'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['category']),
            models.Index(fields=['billable']),
        ]
        
    def __str__(self):
        return f"{self.code} - {self.short_description}"


class CPTCode(BaseCodeModel):
    """CPT procedure codes"""
    
    code = models.CharField(
        max_length=5,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[0-9]{5}$',
            message='CPT code must be 5 digits'
        )],
        help_text=_("CPT code (5 digits)")
    )
    
    short_description = models.CharField(
        max_length=100,
        help_text=_("Short description")
    )
    
    long_description = models.TextField(
        help_text=_("Full description")
    )
    
    category = models.CharField(
        max_length=100,
        help_text=_("CPT category")
    )
    
    modifier_allowed = models.BooleanField(
        default=True,
        help_text=_("Whether modifiers are allowed")
    )
    
    bilateral = models.BooleanField(
        default=False,
        help_text=_("Whether procedure can be bilateral")
    )
    
    version = models.ForeignKey(
        CodeSystemVersion,
        on_delete=models.CASCADE,
        related_name='cpt_codes',
        limit_choices_to={'system_name': 'cpt'}
    )
    
    class Meta:
        db_table = 'cpt_codes'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['category']),
        ]
        
    def __str__(self):
        return f"{self.code} - {self.short_description}"


class SNOMEDConcept(BaseCodeModel):
    """SNOMED CT concepts"""
    
    concept_id = models.CharField(
        max_length=18,
        unique=True,
        help_text=_("SNOMED CT concept ID")
    )
    
    fully_specified_name = models.TextField(
        help_text=_("Fully specified name")
    )
    
    preferred_term = models.CharField(
        max_length=255,
        help_text=_("Preferred term")
    )
    
    definition = models.TextField(
        blank=True,
        help_text=_("Concept definition")
    )
    
    semantic_tag = models.CharField(
        max_length=100,
        help_text=_("Semantic tag")
    )
    
    module_id = models.CharField(
        max_length=18,
        help_text=_("Module ID")
    )
    
    version = models.ForeignKey(
        CodeSystemVersion,
        on_delete=models.CASCADE,
        related_name='snomed_concepts',
        limit_choices_to={'system_name': 'snomed'}
    )
    
    class Meta:
        db_table = 'snomed_concepts'
        indexes = [
            models.Index(fields=['concept_id']),
            models.Index(fields=['semantic_tag']),
        ]
        
    def __str__(self):
        return f"{self.concept_id} | {self.preferred_term}"


class RxNormConcept(BaseCodeModel):
    """RxNorm drug concepts"""
    
    rxcui = models.CharField(
        max_length=8,
        unique=True,
        help_text=_("RxNorm concept unique identifier")
    )
    
    preferred_term = models.CharField(
        max_length=255,
        help_text=_("Preferred term for the concept")
    )
    
    tty = models.CharField(
        max_length=20,
        help_text=_("Term type (e.g., SCD, SBD, GPCK)")
    )
    
    source = models.CharField(
        max_length=20,
        help_text=_("Source vocabulary")
    )
    
    suppress = models.CharField(
        max_length=1,
        default='N',
        help_text=_("Suppress flag")
    )
    
    version = models.ForeignKey(
        CodeSystemVersion,
        on_delete=models.CASCADE,
        related_name='rxnorm_concepts',
        limit_choices_to={'system_name': 'rxnorm'}
    )
    
    class Meta:
        db_table = 'rxnorm_concepts'
        indexes = [
            models.Index(fields=['rxcui']),
            models.Index(fields=['tty']),
            models.Index(fields=['suppress']),
        ]
        
    def __str__(self):
        return f"{self.rxcui} | {self.preferred_term}"


class LOINCCode(BaseCodeModel):
    """LOINC laboratory codes"""
    
    loinc_num = models.CharField(
        max_length=10,
        unique=True,
        help_text=_("LOINC number")
    )
    
    component = models.CharField(
        max_length=255,
        help_text=_("Component")
    )
    
    property = models.CharField(
        max_length=100,
        help_text=_("Property")
    )
    
    time_aspct = models.CharField(
        max_length=100,
        help_text=_("Time aspect")
    )
    
    system = models.CharField(
        max_length=100,
        help_text=_("System")
    )
    
    scale_typ = models.CharField(
        max_length=100,
        help_text=_("Scale type")
    )
    
    method_typ = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Method type")
    )
    
    short_name = models.CharField(
        max_length=255,
        help_text=_("Short name")
    )
    
    long_common_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Long common name")
    )
    
    status = models.CharField(
        max_length=20,
        help_text=_("Status")
    )
    
    version = models.ForeignKey(
        CodeSystemVersion,
        on_delete=models.CASCADE,
        related_name='loinc_codes',
        limit_choices_to={'system_name': 'loinc'}
    )
    
    class Meta:
        db_table = 'loinc_codes'
        indexes = [
            models.Index(fields=['loinc_num']),
            models.Index(fields=['component']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.loinc_num} | {self.short_name}"


class CodeMapping(BaseCodeModel):
    """Cross-references between different code systems"""
    
    MAPPING_TYPE_CHOICES = [
        ('exact', 'Exact Match'),
        ('equivalent', 'Equivalent'),
        ('broader', 'Broader'),
        ('narrower', 'Narrower'),
        ('related', 'Related'),
        ('inexact', 'Inexact'),
    ]
    
    source_system = models.CharField(
        max_length=50,
        help_text=_("Source code system")
    )
    
    source_code = models.CharField(
        max_length=50,
        help_text=_("Source code")
    )
    
    target_system = models.CharField(
        max_length=50,
        help_text=_("Target code system")
    )
    
    target_code = models.CharField(
        max_length=50,
        help_text=_("Target code")
    )
    
    mapping_type = models.CharField(
        max_length=20,
        choices=MAPPING_TYPE_CHOICES,
        default='equivalent',
        help_text=_("Type of mapping relationship")
    )
    
    confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.00,
        help_text=_("Mapping confidence (0.00-1.00)")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Mapping notes")
    )
    
    class Meta:
        db_table = 'code_mappings'
        unique_together = ['source_system', 'source_code', 'target_system', 'target_code']
        indexes = [
            models.Index(fields=['source_system', 'source_code']),
            models.Index(fields=['target_system', 'target_code']),
        ]
        
    def __str__(self):
        return f"{self.source_code} -> {self.target_code}"


class CustomCodeSet(BaseCodeModel):
    """Custom code sets defined by the organization"""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Code set name")
    )
    
    description = models.TextField(
        help_text=_("Code set description")
    )
    
    prefix = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Code prefix")
    )
    
    class Meta:
        db_table = 'custom_code_sets'
        
    def __str__(self):
        return self.name


class CustomCode(BaseCodeModel):
    """Codes within custom code sets"""
    
    code_set = models.ForeignKey(
        CustomCodeSet,
        on_delete=models.CASCADE,
        related_name='codes'
    )
    
    code = models.CharField(
        max_length=50,
        help_text=_("Code value")
    )
    
    description = models.CharField(
        max_length=255,
        help_text=_("Code description")
    )
    
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Sort order")
    )
    
    class Meta:
        db_table = 'custom_codes'
        unique_together = ['code_set', 'code']
        ordering = ['code_set', 'sort_order', 'code']
        
    def __str__(self):
        return f"{self.code} | {self.description}"
