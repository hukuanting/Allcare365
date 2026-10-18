import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient, APIRequestFactory
from apps.core.authentication.models import ProductUser
from apps.core.authentication.permissions import HasResearchAccess, HasResearchApprovalAccess
from apps.core.authentication.services import requires_mfa
from apps.clinical.patients.access_policy import PatientCareAccessPolicy
from django.test import override_settings


@pytest.mark.django_db
def test_public_registration_ignores_privilege_fields_and_can_login():
    client = APIClient()
    payload = {'username': 'public-viewer', 'email': 'viewer@example.test',
               'password': 'Synthetic-password-123!', 'password2': 'Synthetic-password-123!',
               'role': 'admanager', 'is_staff': True, 'is_superuser': True,
               'status': 'active', 'groups': ['admanager']}
    response = client.post('/api/auth/register/', payload, format='json')
    assert response.status_code == 201
    assert response.data['status'] == 'active'
    assert response.data['user']['role'] == 'viewer'
    assert 'access' not in response.data
    user = User.objects.get(username='public-viewer')
    assert user.is_active and not user.is_staff and not user.is_superuser
    assert not user.groups.exists() and not user.user_permissions.exists()
    assert user.check_password(payload['password'])
    login = client.post('/api/auth/login/', {'username': payload['username'], 'password': payload['password']}, format='json')
    assert login.status_code == 200
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + login.data['access'])
    assert client.get('/api/auth/profile/').status_code == 200
    patients = client.get('/api/patients/')
    assert patients.status_code == 200 and patients.data['count'] == 0
    assert client.post('/api/patients/', {'first_name': 'Synthetic', 'last_name': 'Viewer', 'date_of_birth': '2000-01-01', 'sex': 'male'}, format='json').status_code == 403
    assert client.get('/api/health-screening/cohorts/summary/').status_code == 403
    assert not PatientCareAccessPolicy().queryset(user).exists()


@pytest.mark.django_db
@pytest.mark.parametrize('role,research,approval,mfa', [
    ('viewer', False, False, False), ('researcher', True, False, True),
    ('manager', True, True, True), ('admanager', True, True, True),
])
@override_settings(MFA_REQUIRED_FOR_PRIVILEGED=True)
def test_four_role_boundaries(role, research, approval, mfa):
    user = User.objects.create_user('tier-' + role, password='Synthetic-password-123!')
    ProductUser.objects.create(auth_user=user, display_name=role, role=role, status='active')
    request = APIRequestFactory().get('/')
    request.user = user
    assert HasResearchAccess().has_permission(request, None) is research
    assert HasResearchApprovalAccess().has_permission(request, None) is approval
    assert requires_mfa(user) is mfa
    # A role name alone never confers global patient or Django admin access.
    assert not PatientCareAccessPolicy().queryset(user).exists()
    assert not user.is_staff and not user.is_superuser


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['viewer', 'researcher', 'manager', 'admanager'])
def test_explicit_tier_provisioning_grants_only_its_permission_set(role):
    from apps.core.authentication.workspace_roles import provision_workspace_role, WORKSPACE_ROLE_PERMISSIONS
    user = User.objects.create_user('provision-' + role, password='Synthetic-password-123!')
    product = ProductUser.objects.create(auth_user=user, display_name=role, role=role, status='active')
    provision_workspace_role(product)
    user = User.objects.get(pk=user.pk)
    assert user.get_all_permissions() == set(WORKSPACE_ROLE_PERMISSIONS[role])
    assert user.is_staff is (role == 'admanager')
    assert not user.is_superuser
    assert not PatientCareAccessPolicy().queryset(user).exists()


@pytest.mark.django_db
def test_tier_downgrade_removes_managed_permissions_and_admin_access():
    from apps.core.authentication.workspace_roles import provision_workspace_role
    user = User.objects.create_user('downgrade-tier', password='Synthetic-password-123!')
    product = ProductUser.objects.create(auth_user=user, display_name='Synthetic', role='admanager', status='active')
    provision_workspace_role(product)
    product.role = 'viewer'
    product.save(update_fields=['role'])
    provision_workspace_role(product)
    user = User.objects.get(pk=user.pk)
    assert not user.is_staff and not user.is_superuser
    assert not user.get_all_permissions()
    assert list(user.groups.values_list('name', flat=True)) == ['workspace:viewer']
