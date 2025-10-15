from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EncounterViewSet, EncounterFormViewSet, EncounterDiagnosisViewSet

app_name = 'encounters'

router = DefaultRouter()
router.register(r'encounters', EncounterViewSet)
router.register(r'forms', EncounterFormViewSet)
router.register(r'diagnoses', EncounterDiagnosisViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
