"""
FHIR Utilities for Resource Name Normalization and Path Parsing.
Eliminates the need for regex-based resource detection.
"""

class FHIRUtils:
    # Mapping of lowercase resource names to their canonical PascalCase FHIR names.
    # This acts as an allowlist and a normalizer.
    KNOWN_RESOURCES = {
        'patient': 'Patient',
        'observation': 'Observation',
        'encounter': 'Encounter',
        'practitioner': 'Practitioner',
        'medicationrequest': 'MedicationRequest',
        'allergyintolerance': 'AllergyIntolerance',
        'careplan': 'CarePlan',
        'careteam': 'CareTeam',
        'condition': 'Condition',
        'device': 'Device',
        'diagnosticreport': 'DiagnosticReport',
        'documentreference': 'DocumentReference',
        'goal': 'Goal',
        'immunization': 'Immunization',
        'location': 'Location',
        'medication': 'Medication',
        'organization': 'Organization',
        'procedure': 'Procedure',
        'provenance': 'Provenance',
        'riskassessment': 'RiskAssessment',
        'practitionerrole': 'PractitionerRole',
        'servicerequest': 'ServiceRequest',
        'coverage': 'Coverage',
        'medicationdispense': 'MedicationDispense',
        'specimen': 'Specimen',
        'media': 'Media',
        'endpoint': 'Endpoint',
        'binary': 'Binary',
        'bundle': 'Bundle',
        'communication': 'Communication',
        'searchparameter': 'SearchParameter',
        'group': 'Group',
        'uscdidataelement': 'USCDIDataElement',
        'relatedperson': 'RelatedPerson',
        'questionnaireresponse': 'QuestionnaireResponse',
    }

    @classmethod
    def get_resource_type_from_view(cls, view):
        """
        Determines the FHIR Resource type from the ViewSet's basename.
        """
        if hasattr(view, 'basename') and view.basename:
            return cls.normalize_resource_name(view.basename)
        return None

    @classmethod
    def get_resource_type_from_path(cls, path):
        """
        Parses the URL path to identify a FHIR Resource.
        Logic: Scans path segments and checks against the known resource allowlist.
        Returns the first matching canonical resource name.
        """
        # Split path by '/' and filter empty strings
        parts = [p for p in path.strip('/').split('/') if p]
        
        # Iterate through parts to find a valid resource name.
        # We prioritize the part immediately following 'fhir' if it exists,
        # otherwise we scan all parts.
        
        # Optimization: Check if 'fhir' is in the path
        start_index = 0
        if 'fhir' in parts:
            try:
                start_index = parts.index('fhir') + 1
            except ValueError:
                pass
        
        # Check parts starting from the likely position
        for i in range(start_index, len(parts)):
            normalized = cls.normalize_resource_name(parts[i])
            if normalized:
                # Ensure we don't accidentally match metadata/jwks if they were in the map (they aren't)
                return normalized
                
        return None

    @classmethod
    def normalize_resource_name(cls, name):
        """
        Converts a case-insensitive name to Canonical PascalCase.
        Returns None if not a known resource.
        """
        return cls.KNOWN_RESOURCES.get(name.lower())
