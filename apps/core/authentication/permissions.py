from __future__ import annotations

from typing import Iterable, Set

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission


ADMIN_ROLES = {"admin", "administrator", "system_admin"}
CLINICAL_ROLES = {"clinician", "doctor", "physician", "nurse", "provider"}
RESEARCH_ROLES = {"researcher", "research", "data_scientist", "analyst"}
LEGACY_PROFESSIONAL_ROLES = {"professional"}


def normalized_user_roles(user) -> Set[str]:
    """Return product roles for DRF permission checks without creating records."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    roles = set()
    if getattr(user, "is_superuser", False):
        roles.add("admin")
    if getattr(user, "is_staff", False):
        roles.add("staff")

    try:
        product_user = getattr(user, "product_user", None)
    except ObjectDoesNotExist:
        product_user = None
    if product_user is not None and getattr(product_user, "status", "active") == "active":
        role = getattr(product_user, "role", "")
        if role:
            roles.add(str(role).strip().lower())

    try:
        auth_profile = getattr(user, "auth_profile", None)
    except ObjectDoesNotExist:
        auth_profile = None
    if auth_profile is not None:
        role = getattr(auth_profile, "role", "")
        if role:
            roles.add(str(role).strip().lower())

    for group in getattr(user, "groups", []).all():
        roles.add(str(group.name).strip().lower())

    return {role for role in roles if role}


def user_has_any_role(user, allowed_roles: Iterable[str]) -> bool:
    roles = normalized_user_roles(user)
    allowed = {str(role).strip().lower() for role in allowed_roles}
    return bool(roles & allowed)


class HasResearchAccess(BasePermission):
    """Allow aggregate research discovery for approved product roles only."""

    allowed_roles = ADMIN_ROLES | CLINICAL_ROLES | RESEARCH_ROLES | LEGACY_PROFESSIONAL_ROLES

    def has_permission(self, request, view) -> bool:
        return user_has_any_role(request.user, self.allowed_roles)


class HasResearchApprovalAccess(BasePermission):
    """Allow approval/rejection of governed research outputs."""

    allowed_roles = ADMIN_ROLES | CLINICAL_ROLES

    def has_permission(self, request, view) -> bool:
        return user_has_any_role(request.user, self.allowed_roles)
