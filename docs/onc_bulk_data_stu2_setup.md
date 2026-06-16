# ONC g10 - 8 Multi-Patient Authorization and API STU2

This document records the Allcare 365 Bulk Data Access STU2 setup used for Inferno g10 Multi-Patient Authorization and API tests.

## Scope

- Scenario: `8 Multi-Patient Authorization and API STU2`
- Authorization: SMART Backend Services, `client_credentials`, `private_key_jwt`
- Export operation: `GET [Bulk Data FHIR URL]/Group/example-group/$export`
- Status operation: `GET [Bulk Data FHIR URL]/bulk-status/{job_id}`
- Cancel operation: `DELETE [Bulk Data FHIR URL]/bulk-status/{job_id}`
- Download operation: exported NDJSON URLs returned by the status manifest

## Local Preparation

Run these before Inferno:

```powershell
.\venv\Scripts\python.exe manage.py setup_bulk_inferno_client
.\venv\Scripts\python.exe manage.py seed_bulk_group
```

Optional local guard:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_onc_bulk_data_stu2.ps1 -Seed
```

## Inferno Registration

Register Inferno as a bulk data client with this JWK Set URL:

```text
https://inferno.healthit.gov/suites/custom/g10_certification/.well-known/jwks.json
```

Server-side client id:

```text
inferno_bulk_client
```

Do not store Inferno private JWKS in this repository.

## Inferno Form Values

Replace the host if the Cloudflare tunnel changes.

| Field | Value |
| --- | --- |
| Bulk Data FHIR URL | `https://intention-present-manga-packs.trycloudflare.com/fhir/R4` |
| Group ID | `example-group` |
| Patient IDs in exported Group | `10000000-0000-4000-a000-000000000001,10000000-0000-4000-a000-000000000002,10000000-0000-4000-a000-000000000003` |
| Implantable Device Type Codes in exported Group | `14106009` |
| Limit validation to a maximum resource count | blank |
| Export Times Out after | `180` |
| Auth Type | `Backend Services` |
| Populate fields from discovery | use it if Inferno offers it |
| Token URL | `https://intention-present-manga-packs.trycloudflare.com/o/token/` |
| Scopes | `system/*.read` |
| Client ID | `inferno_bulk_client` |
| Encryption Algorithm | `ES384` or `RS384` |
| Key ID for ES384 | blank, or `4b49a739d1eb115b3225f4cf9beb6d1b` |
| Key ID for RS384 | `b41528b6f37a9500edb8a905a595bdd7` |
| JWKS | blank; let Inferno use its default JWKS |
| Timestamp for `_since` | `2026-05-14T21:23:36+00:00` |

Recommended algorithm: `ES384` with blank `kid`, because Inferno can select its default ES384 signing key. `RS384` is also supported.

## Code Ownership

- Bulk endpoint routing: `apps/integration/fhir_integration/urls.py`
- Bulk export/status/download/cancel behavior: `apps/integration/fhir_integration/views.py::BulkExportViewSet`
- Backend Services JWT validation: `apps/integration/fhir_integration/views.py::SMARTv2Validator`
- Token issuance: `apps/core/authentication/views.py::CustomTokenView`
- SMART discovery: `apps/integration/fhir_integration/smart_config.py`
- OAuth client registration: `apps/integration/fhir_integration/management/commands/setup_bulk_inferno_client.py`
- Group seed data: `apps/integration/fhir_integration/management/commands/seed_bulk_group.py`
- Local guard: `verify_onc_bulk_data_stu2.ps1`

## Maintenance Rules

- Keep `Group/example-group` members identical to exported Patient NDJSON resources.
- Keep status/download URLs under the same FHIR base path used by Inferno, especially `/fhir/R4`.
- Leave `PUBLIC_BASE_URL` empty for Cloudflare/ngrok test runs unless a stable public host is intentionally configured; endpoint URLs should derive from the incoming request.
- Keep `requiresAccessToken` as `true`; Inferno downloads NDJSON with the Backend Services access token.
- Preserve `system/*.read` support in discovery, token issuance, and FHIR scope checks.
- Bulk endpoints must reject anonymous requests even if `FHIR_ALLOW_ANONYMOUS_READ=true`.
- Do not log full `client_assertion` JWT values.
- Keep `Group` `$export` declared in `/fhir/R4/metadata`.
- Keep the bundled Inferno public JWKS fallback public-only; never commit Inferno private JWKS.
- `INFERNO_BULK_ALLOW_DYNAMIC_CLIENT_REGISTRATION=true` is certification-test behavior: a client id is auto-provisioned only after the client assertion verifies against the registered Inferno JWKS.
- If a resource includes a reference to a contextual resource, include that referenced resource in the export or make it resolvable by the FHIR API.

## Live Smoke Check

After backend reload, these were verified against the Cloudflare endpoint without printing bearer tokens:

- `POST /o/token/` with `client_credentials` + `private_key_jwt`: `200`
- anonymous `GET /fhir/R4/Group/example-group/$export`: `401`
- authorized Group export kickoff: `202`
- status polling manifest: `200`, `requiresAccessToken=true`, output entries contain `type` and `url`

## References

- HL7 Bulk Data Access IG STU2: https://hl7.org/fhir/uv/bulkdata/STU2/export.html
- SMART Backend Services Authorization profile: https://www.hl7.org/fhir/uv/bulkdata/STU1/authorization/index.html
