from rest_framework import serializers

from .models import (
    ClinicalTestResult,
    DiagnosticImagingResult,
    HealthScreening,
    HealthStatusAssessment,
    Immunization,
    LaboratoryResults,
    Problem,
    Procedure,
    ResearchAggregateReport,
    VitalSigns,
)


class VitalSignsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSigns
        exclude = ["health_screening"]


class LaboratoryResultsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaboratoryResults
        exclude = ["health_screening"]


class HealthStatusAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthStatusAssessment
        exclude = ["health_screening"]


class ClinicalTestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalTestResult
        exclude = ["health_screening"]


class DiagnosticImagingResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticImagingResult
        exclude = ["health_screening"]


class ImmunizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Immunization
        fields = "__all__"


class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = "__all__"


class ProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = "__all__"


class HealthScreeningSerializer(serializers.ModelSerializer):
    vital_signs = VitalSignsSerializer(read_only=True)
    laboratory_results = LaboratoryResultsSerializer(source="lab_results", many=True, read_only=True)
    assessments = HealthStatusAssessmentSerializer(read_only=True)
    clinical_tests = ClinicalTestResultSerializer(many=True, read_only=True)
    imaging_results = DiagnosticImagingResultSerializer(many=True, read_only=True)

    patient_name = serializers.SerializerMethodField()
    patient_medical_record_number = serializers.CharField(source="patient.medical_record_number", read_only=True)

    class Meta:
        model = HealthScreening
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_patient_name(self, obj):
        return f"{obj.patient.last_name}{obj.patient.first_name}"


class HealthScreeningListSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = HealthScreening
        fields = ["id", "patient", "patient_name", "screening_date", "encounter_type"]

    def get_patient_name(self, obj):
        return f"{obj.patient.last_name}{obj.patient.first_name}"


class BulkHealthScreeningSerializer(serializers.Serializer):
    screenings = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class ResearchAggregateReportSerializer(serializers.ModelSerializer):
    requested_by_username = serializers.CharField(source="requested_by_user.username", read_only=True)
    approved_by_username = serializers.CharField(source="approved_by_user.username", read_only=True)
    artifact_available = serializers.SerializerMethodField()

    class Meta:
        model = ResearchAggregateReport
        fields = [
            "id",
            "title",
            "report_type",
            "status",
            "dataset",
            "query_params_json",
            "privacy_json",
            "requested_at",
            "approved_at",
            "rejected_at",
            "approval_note",
            "requested_by_username",
            "approved_by_username",
            "artifact_available",
        ]
        read_only_fields = fields

    def get_artifact_available(self, obj):
        return obj.status == "approved"
