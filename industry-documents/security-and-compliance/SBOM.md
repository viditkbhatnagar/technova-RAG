# TechNova RAG — Software Bill of Materials (CycloneDX-style)

| Field | Value |
|---|---|
| Owner | TechNova Trust & Security |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |
| SBOM format | CycloneDX 1.5 (text representation below; machine-readable JSON generated on demand via `syft . -o cyclonedx-json`) |
| Snapshot date | 2026-04-16 |

## 1. Components — Python (backend/requirements.txt)

All components below are direct dependencies of the backend runtime unless marked transitive. PURLs follow the `pkg:pypi/` scheme.

| Name | Version | Type | License | PURL | Direct / Transitive |
|---|---|---|---|---|---|
| fastapi | 0.115.0 | library | MIT | pkg:pypi/fastapi@0.115.0 | Direct |
| uvicorn | 0.30.6 | library | BSD-3-Clause | pkg:pypi/uvicorn@0.30.6 | Direct |
| pydantic | 2.9.2 | library | MIT | pkg:pypi/pydantic@2.9.2 | Direct |
| pydantic-settings | 2.5.2 | library | MIT | pkg:pypi/pydantic-settings@2.5.2 | Direct |
| python-dotenv | 1.0.1 | library | BSD-3-Clause | pkg:pypi/python-dotenv@1.0.1 | Direct |
| pypdf | 4.3.1 | library | BSD-3-Clause | pkg:pypi/pypdf@4.3.1 | Direct |
| langchain-text-splitters | 0.3.0 | library | MIT | pkg:pypi/langchain-text-splitters@0.3.0 | Direct |
| sentence-transformers | 3.1.1 | library | Apache-2.0 | pkg:pypi/sentence-transformers@3.1.1 | Direct |
| qdrant-client | 1.12.0 | library | Apache-2.0 | pkg:pypi/qdrant-client@1.12.0 | Direct |
| rank-bm25 | 0.2.2 | library | Apache-2.0 | pkg:pypi/rank-bm25@0.2.2 | Direct |
| openai | >=1.55.3,<2.0.0 | library | Apache-2.0 | pkg:pypi/openai@1.55.3 | Direct |
| spacy | 3.8.0 | library | MIT | pkg:pypi/spacy@3.8.0 | Direct |
| torch | >=2.2.0 | library | BSD-3-Clause | pkg:pypi/torch@2.2.0 | Direct |
| numpy | <2.0 | library | BSD-3-Clause | pkg:pypi/numpy@1.26.4 | Direct (pinned below 2.x for sentence-transformers + spaCy compatibility) |
| asyncpg | 0.30.0 | library | Apache-2.0 | pkg:pypi/asyncpg@0.30.0 | Direct |
| starlette | 0.38.6 | library | BSD-3-Clause | pkg:pypi/starlette@0.38.6 | Transitive (via fastapi) |
| httpx | 0.27.2 | library | BSD-3-Clause | pkg:pypi/httpx@0.27.2 | Transitive (via openai) |
| h11 | 0.14.0 | library | MIT | pkg:pypi/h11@0.14.0 | Transitive |
| anyio | 4.4.0 | library | MIT | pkg:pypi/anyio@4.4.0 | Transitive |
| tokenizers | 0.19.1 | library | Apache-2.0 | pkg:pypi/tokenizers@0.19.1 | Transitive (via sentence-transformers) |
| transformers | 4.44.2 | library | Apache-2.0 | pkg:pypi/transformers@4.44.2 | Transitive (via sentence-transformers) |
| huggingface-hub | 0.25.0 | library | Apache-2.0 | pkg:pypi/huggingface-hub@0.25.0 | Transitive |
| regex | 2024.9.11 | library | Apache-2.0 | pkg:pypi/regex@2024.9.11 | Transitive |
| safetensors | 0.4.5 | library | Apache-2.0 | pkg:pypi/safetensors@0.4.5 | Transitive |
| grpcio | 1.66.1 | library | Apache-2.0 | pkg:pypi/grpcio@1.66.1 | Transitive (via qdrant-client) |
| portalocker | 2.10.1 | library | BSD-3-Clause | pkg:pypi/portalocker@2.10.1 | Transitive |
| thinc | 8.2.5 | library | MIT | pkg:pypi/thinc@8.2.5 | Transitive (via spacy) |
| en_core_web_sm | 3.8.0 | spaCy model | MIT | pkg:pypi/en-core-web-sm@3.8.0 | Direct (downloaded at install time) |

Environmental requirement: **Python 3.12**.

## 2. Components — Node (frontend/package.json)

PURLs follow `pkg:npm/` scheme. Versions reflect `package.json` entries for direct deps; transitive closure is excluded for brevity — generate with `syft frontend -o cyclonedx-json` for full closure.

### Direct runtime dependencies

| Name | Version | Type | License | PURL | Direct / Transitive |
|---|---|---|---|---|---|
| next | 16.2.3 | framework | MIT | pkg:npm/next@16.2.3 | Direct |
| react | 19.2.4 | library | MIT | pkg:npm/react@19.2.4 | Direct |
| react-dom | 19.2.4 | library | MIT | pkg:npm/react-dom@19.2.4 | Direct |
| @base-ui/react | 1.4.0 | library | MIT | pkg:npm/%40base-ui/react@1.4.0 | Direct |
| class-variance-authority | 0.7.1 | library | Apache-2.0 | pkg:npm/class-variance-authority@0.7.1 | Direct |
| clsx | 2.1.1 | library | MIT | pkg:npm/clsx@2.1.1 | Direct |
| lucide-react | 1.8.0 | library | ISC | pkg:npm/lucide-react@1.8.0 | Direct |
| react-force-graph-3d | 1.29.1 | library | MIT | pkg:npm/react-force-graph-3d@1.29.1 | Direct |
| react-markdown | 10.1.0 | library | MIT | pkg:npm/react-markdown@10.1.0 | Direct |
| shadcn | 4.2.0 | tool/library | MIT | pkg:npm/shadcn@4.2.0 | Direct |
| tailwind-merge | 3.5.0 | library | MIT | pkg:npm/tailwind-merge@3.5.0 | Direct |
| three | 0.183.2 | library | MIT | pkg:npm/three@0.183.2 | Direct |
| tw-animate-css | 1.4.0 | library | MIT | pkg:npm/tw-animate-css@1.4.0 | Direct |

### Direct dev dependencies

| Name | Version | Type | License | PURL |
|---|---|---|---|---|
| @types/three | 0.183.1 | types | MIT | pkg:npm/%40types/three@0.183.1 |
| @types/node | 22.x | types | MIT | pkg:npm/%40types/node |
| @types/react | 19.x | types | MIT | pkg:npm/%40types/react |
| @types/react-dom | 19.x | types | MIT | pkg:npm/%40types/react-dom |
| typescript | 5.x | compiler | Apache-2.0 | pkg:npm/typescript |
| eslint | 9.x | linter | MIT | pkg:npm/eslint |
| eslint-config-next | 16.2.3 | config | MIT | pkg:npm/eslint-config-next@16.2.3 |
| tailwindcss | 4.x | styles | MIT | pkg:npm/tailwindcss |

Environmental requirement: **Node 20 LTS or 22 LTS**.

## 3. Components — Model Artefacts

| Artefact | Version / Revision | License | PURL (conceptual) | Purpose |
|---|---|---|---|---|
| BAAI/bge-base-en-v1.5 | Revision as of 2026-04-16 | MIT | pkg:huggingface/BAAI/bge-base-en-v1.5 | Dense embedder, 768-dim. Loaded via sentence-transformers. |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | Revision as of 2026-04-16 | Apache-2.0 | pkg:huggingface/cross-encoder/ms-marco-MiniLM-L-6-v2 | Reranker stage. |
| spaCy en_core_web_sm | 3.8.0 | MIT | pkg:pypi/en-core-web-sm@3.8.0 | NER for knowledge graph build. |

Models are downloaded at first run from HuggingFace Hub (TB-6 in `DATA_FLOW_DIAGRAM.md`). No runtime data is exchanged with the Hub. Model files are cached on the host filesystem.

## 4. Components — Container Images

| Image | Tag | Purpose | Recommendation |
|---|---|---|---|
| qdrant/qdrant | latest | Vector store | Pin to a digest in `docker-compose.yml` (e.g. `qdrant/qdrant:v1.12.4@sha256:…`) — `latest` is discouraged for supply-chain integrity. Roadmap v1.1. |
| python | 3.12-slim | Backend base | Pinned in Dockerfile. Rebuild weekly to pick up CVE fixes. |
| node | 22-alpine | Frontend build (Vercel uses its own builder) | N/A for prod; Vercel manages. |

## 5. License Summary

| License | Components | Notes |
|---|---|---|
| MIT | fastapi, pydantic, pydantic-settings, langchain-text-splitters, spacy, thinc, next, react, react-dom, @base-ui/react, clsx, react-force-graph-3d, react-markdown, shadcn, tailwind-merge, three, tw-animate-css, @types/*, BAAI/bge-base-en-v1.5, spaCy en_core_web_sm | Permissive |
| Apache-2.0 | sentence-transformers, qdrant-client, rank-bm25, openai, asyncpg, tokenizers, transformers, huggingface-hub, regex, safetensors, grpcio, class-variance-authority, typescript, cross-encoder/ms-marco-MiniLM-L-6-v2 | Permissive, includes NOTICE requirement |
| BSD-3-Clause | uvicorn, python-dotenv, pypdf, torch, numpy, starlette, httpx, portalocker | Permissive |
| ISC | lucide-react | Permissive |

No copyleft (GPL / AGPL / LGPL) dependencies are present.

## 6. Known Vulnerabilities Snapshot — 2026-04-16

A full scan was executed on 2026-04-16 using the commands in section 7. No open CVEs of Medium or higher severity were identified.

| Scan | Status | Findings summary |
|---|---|---|
| `pip-audit` (backend) | Clean | 0 high, 0 medium (advisory-level informational: torch 2.2.0 minimum recommended) |
| `npm audit --omit=dev --audit-level=moderate` (frontend) | Clean | 0 high, 0 medium |
| `syft` SBOM generation | Succeeded | CycloneDX 1.5 JSON produced |
| `grype` (cross-check) | Clean | 0 high, 0 medium |
| `docker scout` (qdrant/qdrant:latest) | Advisory | Recommends pinning — see §4 |

## 7. Regeneration Commands

```bash
# Python
pip-audit -r backend/requirements.txt --strict

# Node
cd frontend && npm audit --omit=dev --audit-level=moderate

# Full CycloneDX SBOM for the repo
syft . -o cyclonedx-json > sbom.cdx.json
grype sbom:sbom.cdx.json --fail-on medium

# Container image audit (once qdrant tag is pinned)
docker scout cves qdrant/qdrant:v1.12.4
```

CI schedule: run the first two on every pull request; the `syft` + `grype` pair nightly; publish the resulting CycloneDX JSON as a build artefact.

## 8. Attestation

This SBOM is published alongside each TechNova RAG release. The CycloneDX JSON artefact is the machine-readable source of record; this Markdown document is the human-readable companion. On discovery of a new vulnerability affecting any listed component, the Trust & Security team will trigger the vulnerability disclosure workflow described in `VULNERABILITY_DISCLOSURE_POLICY.md` and will update this file in the next bi-annual review cycle, or sooner for High/Critical severity.

## 9. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Trust & Security | Initial release |
