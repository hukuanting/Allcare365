# ONC g10 - 9 Visual Inspection and Attestation

This document records the SMART App Launch setup for Inferno g10 section 9.

## Scope

Section 9 validates remaining SMART App Launch and OAuth/OIDC behavior:

- Public standalone launch with OpenID Connect
- Token revocation
- Invalid `aud`
- Invalid token request
- Invalid PKCE verifier
- EHR launch with patient scopes
- Token introspection
- Asymmetric standalone launch
- SMART v1 scopes
- Fine-grained and granular scope selection

## Local Preparation

```powershell
.\venv\Scripts\python.exe manage.py setup_ehr_app
.\venv\Scripts\python.exe manage.py setup_smart_visual_inspection_clients
```

Local guard:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_onc_visual_inspection.ps1
```

## Common URLs

Replace `<current-cloudflare-host>` with the active Cloudflare tunnel host shown by `start_cloudflare_quick_tunnel.ps1`. Do not reuse saved Inferno `smart_auth_info` after a tunnel URL changes.

| Field | Value |
| --- | --- |
| FHIR Base URL / AUD | `https://<current-cloudflare-host>/fhir/R4` |
| Authorization URL | `https://<current-cloudflare-host>/o/authorize/` |
| Token URL | `https://<current-cloudflare-host>/o/token/` |
| Revocation URL | `https://<current-cloudflare-host>/o/revoke/` |
| Introspection URL | `https://<current-cloudflare-host>/o/introspect/` |
| SMART configuration | `https://<current-cloudflare-host>/fhir/R4/.well-known/smart-configuration` |
| JWKS URL | `https://<current-cloudflare-host>/fhir/R4/jwks` |
| EHR launch helper | `https://<current-cloudflare-host>/smart-launch-test/` |

## Registered Test Clients

| Use | Client ID | Type |
| --- | --- | --- |
| Public standalone/OIDC/PKCE | `inferno_public_client` | public authorization-code client |
| EHR launch patient scopes | `inferno_ehr_client` | confidential symmetric authorization-code client |
| Asymmetric standalone | `inferno_asymmetric_client` | confidential authorization-code client using `private_key_jwt` |
| Bulk Data | `inferno_bulk_client` | Backend Services client |

## Scenario Mapping

| Scenario | Expected System Behavior |
| --- | --- |
| 9.16 Public Client Standalone Launch with OpenID Connect | Use `inferno_public_client`, PKCE `S256`, scopes include `openid fhirUser launch/patient`. Token response includes `id_token`, `patient`, and SMART context. |
| 9.3 Token Revocation | Use `/o/revoke/`. Revocation returns `200` for valid or unknown tokens, revokes the app's active access/refresh grant, revoked access tokens introspect as inactive, and refresh token reuse fails. |
| 9.4 Invalid AUD Parameter | Authorization requests with `aud` not equal to the FHIR base URL are rejected with `400 invalid_request`. |
| 9.17 Invalid Access Token Request | Invalid token requests are rejected by the OAuth token endpoint. |
| 9.18 Invalid PKCE Code Verifier | `PKCE_REQUIRED=true`; incorrect verifier is rejected during code exchange. |
| 9.19 EHR Launch with Patient Scopes | Use `/fhir/R4/launch` or `/smart-launch-test/`; patient scopes are preserved and token response includes patient context. |
| 9.20 Token Introspection | Use `/o/introspect/`; active tokens return `active=true`, scope, client id, token type, and expiration. |
| 9.21 Asymmetric Client Standalone Launch | Use `inferno_asymmetric_client`; token endpoint accepts `private_key_jwt` signed with Inferno JWKS keys. |
| 9.22 SMART App Launch with SMART v1 scopes | `.read` scopes are supported alongside `.rs` scopes. |
| 9.25 Fine-grained scopes | Requested patient/user resource scopes are shown individually and minted as selected. |
| 9.28 SMART Granular Scope Selection | Consent page exposes checkbox-level scope selection and select/deselect all behavior. |

## Maintenance Rules

- Keep `/o/revoke/` and `/o/introspect/` aligned with SMART discovery.
- Keep authorization `aud` validation aligned to the public FHIR base URL.
- Keep `PUBLIC_BASE_URL` empty for tunnel-based certification runs unless a stable public host is intentionally configured.
- Do not hide requested SMART scopes on the consent page; Inferno needs granular visual inspection.
- Keep `openid` token responses able to include `id_token` and `fhirUser`.
- Preserve `.read` and `.rs` scope support during authorization and token issuance.

## 9.3 Token Revocation Form

| Field | Value |
| --- | --- |
| Token Revocation Attestation | `true` |
| Token Revocation Notes | `Tester demonstrated patient-directed app access revocation through the SMART revocation endpoint. The module revokes the app authorization grant immediately: active access tokens become inactive and paired refresh tokens cannot mint new access tokens.` |

Run 9.3 with freshly generated `smart_auth_info` for the current tunnel. If Inferno shows `getaddrinfo` for an older `trycloudflare.com` hostname, rerun the SMART launch/discovery setup in Inferno so `auth_url`, `token_url`, and saved tokens point at the current host.

## References

- SMART App Launch Backend Services: https://www.hl7.org/fhir/smart-app-launch/backend-services.html
- SMART App Launch: https://www.hl7.org/fhir/smart-app-launch/
- USCDI v4: https://isp.healthit.gov/united-states-core-data-interoperability-uscdi#uscdi-v4

## Live Smoke Check

Verified against the Cloudflare endpoint without printing bearer tokens:

- SMART discovery returns `/o/authorize/`, `/o/token/`, `/o/revoke/`, `/o/introspect/`, and `/fhir/R4/jwks`
- `private_key_jwt` token request returns `200`
- `/o/introspect/` returns `active=true` for a live access token
- `/o/revoke/` returns `200`
- `/o/introspect/` returns `active=false` after revocation
