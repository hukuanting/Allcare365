"""Regression coverage for browser consent, CORS and cache boundaries."""
import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=['testserver'])
def test_oauth_consent_post_without_csrf_is_rejected():
    response = Client(enforce_csrf_checks=True).post('/o/authorize/', {'allow': 'true'})
    assert response.status_code == 403


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOWED_ORIGINS=['https://allowed.example'],
)
def test_cors_rejects_unlisted_origin_and_allows_configured_origin():
    client = Client()
    rejected = client.options('/api/auth/login/', HTTP_ORIGIN='https://attacker.example')
    assert 'Access-Control-Allow-Origin' not in rejected
    allowed = client.options('/api/auth/login/', HTTP_ORIGIN='https://allowed.example')
    assert allowed['Access-Control-Allow-Origin'] == 'https://allowed.example'


@override_settings(ALLOWED_HOSTS=['testserver'])
def test_auth_responses_are_never_cacheable():
    response = Client().get('/api/auth/login/')
    assert response['Cache-Control'] == 'no-store'


@override_settings(ALLOWED_HOSTS=['testserver'])
def test_root_level_fhir_routes_are_never_cacheable():
    response = Client().get('/Patient')
    assert response['Cache-Control'] == 'no-store'
