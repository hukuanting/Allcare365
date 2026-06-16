import os
import sys
import pytest

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_system.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.core.authentication.models import ProductUser, UserProfile

@pytest.mark.django_db
def test_user_profile_has_role():
    """
    Test that UserProfile has a role field and it can be set to 'professional' or 'patient'.
    """
    user = User.objects.create_user(username='testuser', password='password123')
    profile = user.auth_profile
    
    # This should fail initially because 'role' field doesn't exist
    profile.role = 'professional'
    profile.save()
    
    updated_profile = UserProfile.objects.get(user=user)
    assert updated_profile.role == 'professional'

@pytest.mark.django_db
def test_login_returns_role():
    """
    Test that login API returns the user's role.
    """
    client = APIClient()
    user = User.objects.create_user(username='pro_user', password='password123')
    profile = user.auth_profile
    profile.role = 'professional'
    profile.save()
    
    response = client.post('/api/auth/login/', {'username': 'pro_user', 'password': 'password123'})
    assert response.status_code == 200
    assert response.data['user']['role'] == 'professional'


@pytest.mark.django_db
def test_login_prefers_active_product_role():
    client = APIClient()
    user = User.objects.create_user(username='research_user', password='password123')
    profile = user.auth_profile
    profile.role = 'patient'
    profile.save()
    ProductUser.objects.create(
        auth_user=user,
        display_name='Research User',
        role='researcher',
        status='active',
    )

    response = client.post('/api/auth/login/', {'username': 'research_user', 'password': 'password123'})

    assert response.status_code == 200
    assert response.data['user']['role'] == 'researcher'
    assert 'researcher' in response.data['user']['roles']
    assert response.data['user']['product_role'] == 'researcher'
    assert response.data['user']['legacy_role'] == 'patient'


@pytest.mark.django_db
def test_seed_demo_role_accounts_creates_login_users():
    call_command('seed_demo_role_accounts')

    expected = {
        'admin': ('admin123456', 'admin'),
        'patient': ('patient123456', 'patient'),
        'researcher': ('researcher123456', 'researcher'),
        'analyst': ('analyst123456', 'analyst'),
        'clinician': ('clinician123456', 'clinician'),
        'doctor': ('doctor123456', 'doctor'),
        'physician': ('physician123456', 'physician'),
        'nurse': ('nurse123456', 'nurse'),
        'provider': ('provider123456', 'provider'),
        'staff': ('staff123456', 'staff'),
        'device_client': ('device_client123456', 'device_client'),
        'system_service': ('system_service123456', 'system_service'),
    }
    client = APIClient()

    for username, (password, role) in expected.items():
        response = client.post('/api/auth/login/', {'username': username, 'password': password})
        assert response.status_code == 200
        assert response.data['user']['role'] == role
        assert role in response.data['user']['roles']

    assert User.objects.get(username='admin').is_superuser is True
