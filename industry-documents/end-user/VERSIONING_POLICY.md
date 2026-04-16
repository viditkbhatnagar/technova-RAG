# Versioning Policy

Audience: TechNova RAG administrators, integrators, and engineers building against the platform | Version: 1.0 | Last Updated: 2026-04-16

This document states the rules TechNova RAG follows for versioning the product, the HTTP API, the data schema, the embedding and reranking models, and the Python and Node dependency graphs. It also defines breaking-change and deprecation policy, support windows, release cadence, and tagging conventions.

If you are writing code that calls TechNova RAG from outside the repo, read sections 3 and 4 carefully — they describe what we promise to keep stable and for how long.

## 1. Scheme

TechNova RAG uses [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) with the form `MAJOR.MINOR.PATCH`.

| Component | Bumped when |
|---|---|
| MAJOR | An incompatible change to a public API, a chunk payload change requiring re-ingest with a new `chunk_id` format, or a role-model change |
| MINOR | Backward-compatible new features, model upgrades that require re-ingest (see §6), and additive API fields |
| PATCH | Backward-compatible bug fixes, dependency security patches, and documentation updates |

Pre-release suffixes (`-rc.1`, `-beta.2`) are allowed for pilot-only releases and are never promoted to `latest` container tags.

### 1.1 Current state

- Product version: **1.0.0**, released 2026-04-15.
- API prefix: `/api/` (unversioned) in v1.0. Migrates to `/api/v1/` in the v1.1 release per §3.
- Payload schema: `v1` — `chunk_id = {org}_{doc_slug}_c{index}` with the field set enumerated in `CONVENTIONS.md`.

## 2. Product version source

The canonical product version is declared in two places that must match on every release:

1. `version=` passed to `FastAPI(...)` in `backend/main.py`.
2. `"version"` in `frontend/package.json`.

CI gates verify that both match the git tag at release time. If they drift, the release is blocked.

The product version is also returned by `GET /api/status` in the `version` field and by `GET /` in the service banner.

## 3. API versioning

Starting with v1.1, the HTTP API uses **URL-based versioning** with a major-version prefix:

```
/api/v1/ingest
/api/v1/query
/api/v1/status
/api/v1/graph
/api/v1/sessions
/api/v1/documents
/api/v1/pipeline/trace
```

### 3.1 Transition plan (v1.0 → v1.1)

- v1.0 exposes unversioned routes only: `/api/ingest`, `/api/query`, etc.
- v1.1 introduces `/api/v1/*` as the canonical path.
- The old unversioned routes remain as **aliases** to `/api/v1/*` for **90 days** after the v1.1 release, emitting `Deprecation` and `Sunset` response headers on every call.
- After 90 days, the unversioned routes return `410 Gone` with a migration hint in the response body.
- v2 of the API, when needed, appears under `/api/v2/*` alongside `/api/v1/*` with its own support window.

### 3.2 Additive vs breaking

Within a single API version (e.g. `/api/v1`), we guarantee:

- New optional request fields may be added at any time.
- New response fields may be added at any time; clients must ignore unknown fields.
- New endpoints may be added at any time.
- Existing field names, types, and enum values will not change.
- Required request fields will not be added.
- Fields will not be removed without first deprecating them.

Anything that violates these guarantees requires a new API major version (`/api/v2/...`).

## 4. Breaking change policy

### 4.1 Deprecation windows

| API surface | Minimum deprecation window |
|---|---|
| Public API routes (`/api/v*/*`) | **90 days** |
| Internal API routes (not documented in `API_CONTRACT.md`) | **30 days** |
| Response fields | 90 days (same as public API) |
| Request fields | 90 days to become optional; never silently removed |

### 4.2 Deprecation signals

Every deprecated response carries HTTP headers per [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594.html) and [draft-ietf-httpapi-deprecation-header](https://datatracker.ietf.org/doc/draft-ietf-httpapi-deprecation-header/):

```
Deprecation: true
Sunset: 2026-07-14T00:00:00Z
Link: <https://docs.technova.example/versioning>; rel="deprecation"
```

The `Sunset` date is an RFC 3339 timestamp. After `Sunset`, the endpoint returns `410 Gone`.

### 4.3 Announcement channels

Breaking changes and deprecations are announced through all of the following, simultaneously:

- An entry in `CHANGELOG.md` under the appropriate version.
- A post in the customer portal release notes.
- An email to every registered admin contact on the deployment.

The rule is simple: if a customer can't hear about it from at least two of the three channels, the deprecation hasn't happened.

## 5. Data schema versioning

The chunk payload is the most fragile contract in the system. Changing it is always a coordinated event.

Versioned elements:

- **`chunk_id` format** — today: `{org}_{doc_slug}_c{index}`. Any change is MAJOR and requires a full re-ingest.
- **Qdrant payload field set** — the named fields on every vector point. Adding an optional field is MINOR; renaming or removing a field is MAJOR.
- **BM25 pickle schema** — the shape of `backend/bm25_index.pkl`. Changes are MINOR if compatible, MAJOR otherwise.
- **Graph JSON schema** — `backend/graph_data.json`. Changes are MINOR.

Every MAJOR payload change ships with:

1. A migration note in `CHANGELOG.md` under the release.
2. A `RUNNING.md` update documenting the re-ingest requirement.
3. A script or endpoint parameter to force re-ingest without touching metadata.

Never mutate a payload field's meaning without bumping MAJOR. Silent schema drift is the single fastest way to corrupt retrieval quality.

## 6. Model version policy

TechNova RAG uses three model families: the embedder (BGE), the cross-encoder reranker, and the generator LLM (default `gpt-4o-mini`). Each has a different versioning rule because each has a different blast radius.

### 6.1 Embedder

Changing the embedder model **alters the embedding space**, which invalidates every vector in Qdrant. This is a MINOR bump with an explicit migration note, plus a forced re-ingest.

Process:

1. Propose the new embedder in an engineering review; quantify retrieval quality on the golden-query suite.
2. Pin the new model version in `backend/config.py`.
3. Release a MINOR version with a prominent **Migration** section in `CHANGELOG.md`.
4. On upgrade, admins must run `POST /api/ingest` with `force_reingest: true`.

Rollback means pinning the prior embedder and re-ingesting again.

### 6.2 Cross-encoder reranker

Same rule as the embedder: a reranker change is MINOR, with explicit migration. Re-ingest is not required, but an acceptance re-run is — reranker changes can shift which chunks surface.

### 6.3 Generator LLM

The generator model is a config key, not a code change. Swapping `gpt-4o-mini` for a different model is a configuration change on the deployment; it does not bump SemVer by itself.

However, if the swap is accompanied by a **prompt template change** (in `backend/services/generator.py`), that is a code change that bumps MINOR at least, because users will see different phrasing and potentially different answer shape.

## 7. Dependency policy

### 7.1 Pinning

- **Python direct dependencies** in `backend/requirements.txt` are pinned to exact versions (`==`).
- **Python transitive dependencies** float within the constraints imposed by direct pins.
- **Node direct dependencies** in `frontend/package.json` are pinned to exact versions; `package-lock.json` is committed and authoritative.

### 7.2 Updates

| Change class | Process |
|---|---|
| Security patch (CVE, high/critical) | Auto-bump via Dependabot; ship as PATCH within 72 hours of advisory |
| Minor dependency bump | Reviewed in weekly dependency-update PR; ship as PATCH |
| Major dependency bump | Engineering review; usually ships as MINOR; may ship as MAJOR if it forces an API change |
| Model provider SDK (e.g. `openai`) bump | Reviewed for wire-format changes; today we require `openai>=1.55.3` per the v0.4.0 release |

### 7.3 Lock file discipline

`requirements.txt` and `package-lock.json` are committed. CI rebuilds against the lock file; any drift fails the build.

## 8. Support windows

We support the current MAJOR fully: security, bug, and feature releases. We support the immediately preceding MAJOR with **critical security fixes only** for **12 months** after its successor's release.

Example: when v2.0.0 ships, v1.x receives security fixes for 12 months. After that, v1.x is end-of-life; customers must upgrade.

Historical MAJOR versions older than the preceding one are not supported at all. Customers on unsupported versions should upgrade; migration playbooks accompany every MAJOR release.

## 9. Release cadence

| Class | Cadence | Trigger |
|---|---|---|
| PATCH | As needed | Bug fixes, security patches, doc fixes |
| MINOR | Monthly | Bundle of new features, model changes, observability improvements |
| MAJOR | Annually (target) | Breaking API, breaking payload schema, breaking role-model change |

MINOR releases cut on the first Tuesday of the month. PATCH releases cut whenever there is something worth shipping. MAJOR releases are announced 4 weeks in advance, with a preview branch available for at least 2 weeks before GA.

Releases are cut from `main`. There are no long-lived release branches unless a security backport requires one.

## 10. Commit style

Commits follow the conventional style documented in `CONVENTIONS.md`:

```
feat:      a new user-visible feature
fix:       a bug fix
docs:      documentation only
refactor:  code change without behaviour change
chore:     build, tooling, or dependency change
```

Release notes in `CHANGELOG.md` are authored by hand from the commit log. The commit-prefix discipline is what makes that authoring fast.

## 11. Tagging and artefacts

Every release is tagged in git as `v<MAJOR>.<MINOR>.<PATCH>`:

```bash
git tag -a v1.0.0 -m "TechNova RAG v1.0.0"
git push origin v1.0.0
```

Container images follow the same tag. For the backend:

```
technova/rag-backend:1.0.0
technova/rag-backend:1.0          # floating minor
technova/rag-backend:1            # floating major
technova/rag-backend:latest       # points at the most recent stable MAJOR
```

`latest` is only updated after a MINOR or PATCH passes the post-release smoke suite. Pre-release images (`1.1.0-rc.1`) are pushed but never tagged `latest`.

The frontend is tagged analogously as `technova/rag-frontend`.

### 11.1 Provenance

Every image carries OCI metadata pointing at the git commit and the CI build:

```
org.opencontainers.image.revision=<git sha>
org.opencontainers.image.version=<semver>
org.opencontainers.image.source=<repo url>
```

Customers pinning against TechNova images should pin against the full `MAJOR.MINOR.PATCH` tag, not `latest`, and not a floating minor tag.

## 12. When in doubt

If a change straddles two of the classes above, pick the **higher-impact class** and document why. A PATCH that could plausibly be called MINOR is a better choice than a MINOR that was actually a PATCH — customers read the version number and set expectations accordingly.

When a change is ambiguous and the blast radius is unknown, ship it behind a configuration flag (`FEATURES_*` in `backend/config.py`) default-off, and promote to default-on in a subsequent release. That lets customers opt in during a pilot window.

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Documentation | Initial release |
