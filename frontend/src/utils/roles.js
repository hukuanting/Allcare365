export const RESEARCH_ACCESS_ROLES = [
  'admanager',
  'manager',
  'admin',
  'administrator',
  'system_admin',
  'researcher',
  'research',
  'data_scientist',
  'analyst',
  'clinician',
  'doctor',
  'physician',
  'nurse',
  'provider',
  'professional',
];

export const RESEARCH_APPROVAL_ROLES = [
  'admanager',
  'manager',
  'admin',
  'administrator',
  'system_admin',
  'clinician',
  'doctor',
  'physician',
  'nurse',
  'provider',
];

export const normalizeRole = (role) => String(role || '').trim().toLowerCase();

export const getUserRoles = (userInfo) => {
  if (!userInfo) return [];

  const roles = new Set();
  if (Array.isArray(userInfo.roles)) {
    userInfo.roles.forEach((role) => {
      const normalized = normalizeRole(role);
      if (normalized) roles.add(normalized);
    });
  }

  [userInfo.role, userInfo.product_role, userInfo.legacy_role].forEach((role) => {
    const normalized = normalizeRole(role);
    if (normalized) roles.add(normalized);
  });

  return Array.from(roles);
};

export const hasAnyRole = (userInfo, allowedRoles) => {
  if (!allowedRoles || allowedRoles.length === 0) return true;
  const userRoles = new Set(getUserRoles(userInfo));
  return allowedRoles.some((role) => userRoles.has(normalizeRole(role)));
};

export const CLINICAL_WRITE_ROLES = RESEARCH_APPROVAL_ROLES.concat('professional');

export const getAccessLevel = (userInfo) => {
  if (hasAnyRole(userInfo, ['admanager', 'admin', 'administrator', 'system_admin'])) return 'Admanager';
  if (hasAnyRole(userInfo, CLINICAL_WRITE_ROLES)) return 'Manager';
  if (hasAnyRole(userInfo, RESEARCH_ACCESS_ROLES)) return 'Researcher';
  return 'Viewer';
};
