from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"screenings", views.HealthScreeningViewSet, basename="health-screening")
router.register(r"immunizations", views.ImmunizationViewSet, basename="immunizations")
router.register(r"problems", views.ProblemViewSet, basename="problems")
router.register(r"procedures", views.ProcedureViewSet, basename="procedures")

app_name = "apps.clinical.health_screening"

urlpatterns = [
    path("parse-file/", views.parse_file, name="parse_file"),
    path("bulk-import/", views.bulk_import, name="bulk_import"),
    path("fhir-import/", views.fhir_import, name="fhir_import"),
    path("risk-analysis/", views.risk_analysis, name="risk_analysis"),
    path("risk-algorithms/", views.risk_algorithm_catalog, name="risk_algorithm_catalog"),
    path("disease-risk/", views.disease_risk_assessment, name="disease_risk_assessment"),
    path("cohorts/summary/", views.cohort_summary, name="cohort_summary"),
    path("cohorts/summary/fhir/", views.cohort_summary_fhir, name="cohort_summary_fhir"),
    path("cohorts/patients-like-this/", views.patients_like_this, name="patients_like_this"),
    path("data-quality/summary/", views.data_quality_summary, name="data_quality_summary"),
    path("research-reports/", views.research_reports, name="research_reports"),
    path("research-reports/<uuid:report_id>/", views.research_report_detail, name="research_report_detail"),
    path("research-reports/<uuid:report_id>/approve/", views.approve_research_report, name="approve_research_report"),
    path("research-reports/<uuid:report_id>/reject/", views.reject_research_report, name="reject_research_report"),
    path("research-reports/<uuid:report_id>/artifact/", views.research_report_artifact, name="research_report_artifact"),
    path("", include(router.urls)),
    path("list/", views.screening_list_view, name="list"),
]
