"""Explicit four-tier provisioning for administrator-initiated role changes.

No role receives global patient-read permission. Public registration never calls
this service and cannot request an elevated tier.
"""
from django.contrib.auth.models import Group, Permission
from django.db import transaction

WORKSPACE_ROLE_PERMISSIONS = {
    'viewer': (),
    'researcher': ('health_screening.view_research_aggregates',),
    'manager': ('health_screening.view_research_aggregates',
                'health_screening.approve_research_aggregates',
                'health_screening.import_clinical_records',
                'patients.create_patient_records'),
    'admanager': ('health_screening.view_research_aggregates',
                  'health_screening.approve_research_aggregates',
                  'health_screening.import_clinical_records',
                  'patients.create_patient_records',
                  'authentication.view_productuser',
                  'authentication.change_productuser',
                  'auth.view_user'),
}


@transaction.atomic
def provision_workspace_role(product_user):
    """Bind only the managed tier group; preserve separately assigned grants."""
    role = product_user.role
    if role not in WORKSPACE_ROLE_PERMISSIONS:
        return  # Preserve legacy roles until explicitly reassigned.
    user = product_user.auth_user
    managed_names = ['workspace:' + name for name in WORKSPACE_ROLE_PERMISSIONS]
    previously_admin = user.groups.filter(name='workspace:admanager').exists()
    group, _ = Group.objects.get_or_create(name='workspace:' + role)
    permissions = []
    for qualified_name in WORKSPACE_ROLE_PERMISSIONS[role]:
        app_label, codename = qualified_name.split('.', 1)
        permissions.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
    group.permissions.set(permissions)
    user.groups.remove(*user.groups.filter(name__in=managed_names).exclude(pk=group.pk))
    user.groups.add(group)
    if role == 'admanager' or previously_admin:
        desired_staff = role == 'admanager'
        if user.is_staff != desired_staff:
            user.is_staff = desired_staff
            user.save(update_fields=['is_staff'])
