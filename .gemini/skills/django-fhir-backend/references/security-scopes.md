# SMART on FHIR Security Scopes

## Mandatory Scopes for ONC Certification
| Scope | Description |
| :--- | :--- |
| `openid` | Required for OIDC |
| `fhirUser` | User identity |
| `launch` | Required for EHR Launch |
| `launch/patient` | Context-specific launch |
| `patient/*.read` | Read access to all patient data |
| `user/*.read` | Practitioner access |

## Resource-Specific Patterns
Pattern: `[patient|user|system]/[ResourceType].[read|write|*]`

Examples:
- `patient/Observation.rs`: Read-only access to Observations for the current patient.
- `user/Patient.read`: Read-only access to all Patients the user is authorized to see.
