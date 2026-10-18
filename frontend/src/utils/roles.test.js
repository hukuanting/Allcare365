import { hasAnyRole, RESEARCH_ACCESS_ROLES, RESEARCH_APPROVAL_ROLES, CLINICAL_WRITE_ROLES, getAccessLevel } from './roles';

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

test.each([
  ['viewer', 'Viewer', false, false], ['researcher', 'Researcher', true, false],
  ['manager', 'Manager', true, true], ['admanager', 'Admanager', true, true],
])('exposes tier %s with matching research and write navigation', (role, label, research, write) => {
  expect(getAccessLevel({role})).toBe(label);
  expect(hasAnyRole({role}, RESEARCH_ACCESS_ROLES)).toBe(research);
  expect(hasAnyRole({role}, CLINICAL_WRITE_ROLES)).toBe(write);
});
