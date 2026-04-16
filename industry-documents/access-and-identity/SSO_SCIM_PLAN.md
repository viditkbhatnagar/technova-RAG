# SSO and SCIM Integration Plan (v1.1)

| Field | Value |
|---|---|
| Owner | TechNova Identity and Access |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

---

## 1. Purpose

This document describes the target state for authentication and lifecycle management in TechNova RAG v1.1. It covers the protocol surfaces (OIDC, SAML, SCIM 2.0), the supported identity providers, the session model, the claim-to-role mapping, and the migration path from v1.0's client-supplied role model.

The v1.0 release ships without authentication - the `role` field in Project B requests is client-supplied. This is a known limitation and is documented in `RBAC_DESIGN.md` section 6.1. The v1.1 scope closes that gap.

---

## 2. Requirements

### 2.1 Functional

- **Authentication protocols**: SAML 2.0 and OIDC must both be supported. Enterprise customers differ in which protocol their IdP prefers; TechNova will not force migration.
- **Lifecycle**: SCIM 2.0 for user and group provisioning, updates, and deactivation.
- **Role extraction**: configurable claim path with a deterministic fallback to group membership.
- **Tenancy**: multi-tenant by design; each tenant has an independent IdP configuration, signing key set, and claim-to-role mapping table.
- **Deprovisioning SLA**: session terminated within five minutes of SCIM delete or SCIM `active=false`.

### 2.2 Non-functional

- **Availability**: auth flow must degrade gracefully if the IdP is slow. A cached JWKS with a two-hour stale-while-revalidate window prevents a transient IdP outage from bricking the application.
- **Security**: all tokens signed (RS256 or ES256); no shared-secret HS256. TLS 1.2 minimum, 1.3 preferred on ingress.
- **Compliance**: SOC 2 CC6.1, CC6.2, CC6.3 auditable. Access reviews supported via SCIM read APIs.

---

## 3. Supported Identity Providers

The integration is protocol-first, so any compliant IdP works. The providers below are explicitly tested as part of the v1.1 release gate.

| IdP | Protocol tested | SCIM tested | Priority |
|---|---|---|---|
| Okta | OIDC + SAML | Yes | Primary reference |
| Microsoft Entra ID (Azure AD) | OIDC + SAML | Yes | High - large install base |
| Google Workspace | OIDC | Yes | Medium |
| Generic SAML 2.0 IdP | SAML | No (manual provisioning) | Catch-all for self-hosted |
| Ping Identity | OIDC + SAML | Yes | Roadmap v1.2 |
| JumpCloud | OIDC + SCIM | Yes | Roadmap v1.2 |

Each supported IdP ships with a configuration profile (JSON) that bakes in metadata URLs, expected claims, and group patterns. The profiles live in `backend/auth/idp_profiles/`.

---

## 4. OIDC Flow

OIDC is the preferred protocol. The flow is Authorization Code with PKCE, suitable for both the Next.js frontend and a future native CLI.

### 4.1 Sequence

1. Unauthenticated user hits `/project-b`.
2. Frontend redirects to `GET /api/auth/login` which constructs an authorization URL with `response_type=code`, `code_challenge` (S256), and `state`.
3. Browser redirects to IdP; user authenticates.
4. IdP redirects back to `GET /api/auth/callback?code=...&state=...`.
5. Backend exchanges code for tokens at the IdP token endpoint using `code_verifier`. Verifies ID token against JWKS: signature (RS256), `iss`, `aud`, `exp`, `iat`, `nonce`.
6. Backend mints its own short-lived session JWT (see section 7) and sets it as an HttpOnly, Secure, SameSite=Lax cookie.
7. Subsequent `/api/query` requests carry the session JWT; the backend re-verifies on every call.

### 4.2 Claim extraction

Role is read from the claim at path `technova_role` by default. The path is configurable per tenant. Fallback order:

1. Direct claim: `id_token.technova_role` if present and in `{employee, manager, admin}`.
2. Group mapping: iterate `id_token.groups` and match against the tenant's group-to-role table (section 6).
3. Deny: if neither yields a known role, the session is refused with HTTP 403 and an audit event `AUTH_FAIL` with reason `no_role_resolvable`.

Note the deliberate absence of a default role. Unknown users get nothing.

---

## 5. SAML Flow

SAML is supported for tenants who mandate it. The flow is SP-initiated.

### 5.1 Sequence

1. Unauthenticated user hits `/project-b`.
2. Frontend redirects to `GET /api/auth/saml/login` which constructs a signed `AuthnRequest` (HTTP-Redirect binding preferred, HTTP-POST supported).
3. IdP authenticates user and returns a signed `Response` with assertion via HTTP-POST to `/api/auth/saml/acs`.
4. Backend validates assertion signature against the IdP's certificate, checks `NotBefore`, `NotOnOrAfter`, `Audience`, `Recipient`, `InResponseTo`, and assertion freshness.
5. Role extracted from attribute `http://schemas.technova.com/claims/role` (configurable). Group fallback identical to OIDC.
6. Session JWT minted; same cookie as OIDC path.

### 5.2 Metadata

TechNova's SP metadata is published at `/api/auth/saml/metadata` with a one-year validity window and a rotating signing key. IdP metadata is consumed either by URL (auto-refreshed every twenty-four hours) or by static XML upload through the admin UI.

---

## 6. Claim to Role Mapping

The following table shows the default mapping for the Okta reference tenant. Each mapping is tenant-scoped and lives in the Postgres `tenants.role_mappings` JSONB column.

| IdP group / claim value | TechNova role | Rationale |
|---|---|---|
| `TN-Admins` | admin | Pre-agreed admin cohort; membership attested quarterly. |
| `TN-Managers` | manager | People managers and finance partners. |
| `TN-Employees` | employee | Default cohort for all staff. |
| `TN-Contractors` | employee | Contractors granted employee clearance after CDA signature. |
| `TN-External-Board` | admin | Board members with active seats; expire on term end. |
| (no match) | deny | Explicit deny, not fallback. |

A YAML snippet for a tenant configuration:

```yaml
tenant_id: acme
protocol: oidc
issuer: https://acme.okta.com
audience: https://rag.technova.com
role_claim_path: technova_role
group_claim_path: groups
role_mappings:
  TN-Admins: admin
  TN-Managers: manager
  TN-Employees: employee
  TN-Contractors: employee
```

Mappings are evaluated in order; first match wins. Unlisted groups are ignored (not denied) so a user can carry arbitrary additional groups without blocking access.

---

## 7. Session Management

v1.1 session tokens are minted by TechNova, not by the IdP. This keeps the IdP decoupled from request-level enforcement and avoids sending opaque IdP tokens on every query.

| Token | TTL | Storage | Verification |
|---|---|---|---|
| Access JWT | 15 minutes | HttpOnly cookie, SameSite=Lax, Secure | Every request; signature via local key pair. |
| Refresh token | 8 hours | HttpOnly cookie, Path=/api/auth/refresh | Rotating; one-time use, family tracked. |
| IdP ID token | IdP-defined (typically 1h) | Not stored after session JWT mint | N/A - consumed once. |

Role is re-read from the access JWT on every request. There is no server-side role cache. This is intentional: a cache would create a window where a revocation has happened at the IdP but not yet propagated, and the invariant from `RBAC_DESIGN.md` cannot tolerate such a window.

Refresh rotation follows the pattern: on each refresh, the old token is invalidated and a new token is issued; reuse of an invalidated refresh token triggers a family-level revocation and an `AUTH_FAIL` audit event with reason `refresh_reuse_detected`.

Logout invalidates the refresh token family and clears the cookies. Optional single-logout propagates to the IdP via the SAML SLO or OIDC `end_session_endpoint` when present.

---

## 8. SCIM 2.0 Endpoints

SCIM is the control plane for user lifecycle. Endpoints live under `/scim/v2/` and are authenticated with a bearer token issued per tenant.

| Endpoint | Method | Purpose |
|---|---|---|
| `/scim/v2/Users` | POST | Create user (JIT also supported, see 8.2). |
| `/scim/v2/Users/{id}` | GET | Read user. |
| `/scim/v2/Users/{id}` | PUT / PATCH | Update (including `active=false` for deactivate). |
| `/scim/v2/Users/{id}` | DELETE | Hard delete (session revoked within 5 minutes). |
| `/scim/v2/Groups` | POST / GET | Manage group definitions. |
| `/scim/v2/Groups/{id}` | PATCH | Add or remove members. |
| `/scim/v2/ServiceProviderConfig` | GET | Standard SCIM discovery. |
| `/scim/v2/Schemas` | GET | Schema advertisement. |

### 8.1 Deactivation and deletion

`active=false` is a soft disable: user cannot authenticate but history is retained. Existing session JWTs are not revoked instantly - the cookie remains valid until its fifteen-minute expiry. To enforce a tighter window, a per-user `disabled_at` timestamp is consulted on every request; any JWT with `iat < disabled_at` is rejected. This mechanism is what enforces the five-minute deprovisioning SLA (worst case is JWT lifetime, fifteen minutes; typical case is sub-minute on next refresh).

Hard DELETE purges the user and triggers an immediate revocation event; the SLA here is five minutes end-to-end.

### 8.2 JIT provisioning

If a user authenticates via SSO with a known tenant but no SCIM record, a user record is created just-in-time using claims from the ID token or assertion. JIT provisioning can be disabled per tenant for environments that require explicit pre-provisioning (common in regulated industries).

### 8.3 Compliance suite

The SCIM 2.0 DynamicLoader compliance suite (RFC 7643 and RFC 7644) is part of the v1.1 release gate. All happy-path and error-path tests must pass for Okta and Entra ID before release; Google Workspace is allowed a documented subset because of their known SCIM deviations.

---

## 9. Migration from v1.0

The v1.0 release uses a client-supplied `role` in the request body. v1.1 deprecates that field but does not delete it, to allow a controlled migration.

### 9.1 Feature flag

A single environment variable `AUTH_MODE` controls behaviour:

- `AUTH_MODE=legacy` - read `role` from request body; no authentication. v1.0 behaviour. Default for existing deployments at v1.1 launch.
- `AUTH_MODE=sso` - require a valid session JWT; ignore the body `role` entirely. If both are present, the JWT wins and a deprecation warning is logged.
- `AUTH_MODE=dual` - read JWT if present, fall back to body `role` if not. Transitional only; disabled after the overlap window.

### 9.2 Timeline

| Phase | Duration | AUTH_MODE | Notes |
|---|---|---|---|
| Announcement | 14 days pre-launch | `legacy` | Customer communication, IdP metadata exchange. |
| Overlap | 60 days post-launch | `dual` | Both paths live; telemetry tracks per-tenant JWT adoption. |
| Cutover | date + 74 days | `sso` | Body `role` returns 410 Gone. |

The overlap window is sized to accommodate enterprise change cycles. Customers who fail to migrate within the overlap receive a two-week extension on request; after that, the endpoint returns 410 and integration support is required.

### 9.3 Data migration

No data migration is required. The Qdrant payload schema does not change. The Postgres `messages` table gains a nullable `actor_sub` column that is NULL for v1.0 records and populated from the JWT for v1.1 records.

---

## 10. Implementation Tasks and Effort

The following table is the release planning estimate, in engineer-weeks. Estimates include test and documentation effort.

| Task | Effort | Owner |
|---|---|---|
| OIDC Authorization Code + PKCE flow, JWKS cache | 2.0 | Platform Eng |
| SAML 2.0 SP, ACS, metadata endpoint | 2.5 | Platform Eng |
| Session JWT mint, refresh rotation | 1.0 | Platform Eng |
| SCIM 2.0 server (Users, Groups, lifecycle) | 3.0 | Platform Eng |
| Tenant config and role mapping storage | 1.0 | Platform Eng |
| `AUTH_MODE` feature flag and migration shim | 0.5 | Platform Eng |
| Okta reference integration and certification | 1.0 | Partner Eng |
| Entra ID and Google Workspace certifications | 1.5 | Partner Eng |
| Admin API for role grants with audit | 1.0 | Platform Eng |
| Adversarial test harness for auth (token tampering, replay) | 1.0 | Security |
| Documentation, customer onboarding guides | 1.0 | Tech Writing |
| **Total** | **14.5** | |

The plan assumes two engineers working in parallel, yielding a nine-week calendar delivery, plus a two-week hardening window before GA.

---

## 11. Testing

### 11.1 SAML

- Replay of captured SAML `Response` must fail on second use (`InResponseTo` tracking).
- Signature stripping, signature wrapping, and comment-based XPath attacks tested against the chosen SAML library.
- Clock skew tolerance bounded to sixty seconds; assertions outside that window rejected.

### 11.2 OIDC

- Missing `nonce` rejection.
- `none` algorithm rejection (explicit allow-list: RS256, ES256, EdDSA).
- JWKS rotation: mid-session key rotation must not invalidate unexpired tokens signed with the prior key (kid-based lookup).

### 11.3 SCIM

- DynamicLoader compliance suite.
- JIT provisioning under OIDC and SAML.
- Deactivation-and-reactivate cycle preserves `id`.
- Delete followed by Create with the same externalId yields a new `id`.
- Five-minute deprovisioning SLA measured end-to-end by a synthetic drill.

### 11.4 Adversarial

- Role escalation via tampered JWT (signature invalidation).
- Token substitution across tenants (audience mismatch rejection).
- Refresh token reuse detection.
- Session fixation via cookie injection rejection.

All four suites must pass for release. A single failure in adversarial testing blocks GA.

---

## 12. Revision History

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Identity & Access | Initial release |
