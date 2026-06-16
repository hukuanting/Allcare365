import { hasAnyRole, RESEARCH_ACCESS_ROLES, RESEARCH_APPROVAL_ROLES } from './roles';

test('allows research workspace for product researcher role', () => {
  expect(hasAnyRole({ role: 'researcher', roles: ['patient', 'researcher'] }, RESEARCH_ACCESS_ROLES)).toBe(true);
});

test('rejects research workspace for patient role', () => {
  expect(hasAnyRole({ role: 'patient', roles: ['patient'] }, RESEARCH_ACCESS_ROLES)).toBe(false);
});

test('limits research report approvals to clinical or admin roles', () => {
  expect(hasAnyRole({ role: 'researcher', roles: ['researcher'] }, RESEARCH_APPROVAL_ROLES)).toBe(false);
  expect(hasAnyRole({ role: 'doctor', roles: ['doctor'] }, RESEARCH_APPROVAL_ROLES)).toBe(true);
});
