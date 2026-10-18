from django.contrib import admin
from django import forms

from .models import AuthSecurityState, ProductUser
from .services import approve_user, suspend_user
from .workspace_roles import provision_workspace_role


class ProductUserRoleForm(forms.ModelForm):
    class Meta:
        model = ProductUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('viewer', 'Viewer'), ('researcher', 'Researcher'),
                   ('manager', 'Manager'), ('admanager', 'Admanager')]
        current = self.instance.role if self.instance.pk else None
        if current and current not in {value for value, _ in choices}:
            choices.append((current, f'{current} (existing role)'))
        self.fields['role'] = forms.ChoiceField(choices=choices, initial=current or 'viewer')


@admin.register(ProductUser)
class ProductUserAdmin(admin.ModelAdmin):
    form = ProductUserRoleForm
    list_display = ('display_name', 'auth_user', 'role', 'status', 'organization_name')
    list_filter = ('status', 'role', 'organization_name')
    search_fields = ('display_name', 'auth_user__username', 'auth_user__email')
    actions = ('approve_selected_users', 'suspend_selected_users')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change or 'role' in form.changed_data:
            provision_workspace_role(obj)

    @admin.action(description='Approve selected user accounts')
    def approve_selected_users(self, request, queryset):
        for product_user in queryset.exclude(status='active'):
            approve_user(product_user)

    @admin.action(description='Suspend selected user accounts and revoke credentials')
    def suspend_selected_users(self, request, queryset):
        for product_user in queryset.exclude(status='suspended'):
            suspend_user(product_user)


@admin.register(AuthSecurityState)
class AuthSecurityStateAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_version', 'last_revoked_at', 'updated_at')
    readonly_fields = ('user', 'token_version', 'last_revoked_at', 'updated_at')
    search_fields = ('user__username', 'user__email')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Deleting/recreating this row could resurrect tokens with version 1.
        return False
