# TechNova RAG — Open Source Software License Inventory

| Field            | Value                                  |
|------------------|----------------------------------------|
| Owner            | TechNova Engineering / Legal           |
| Classification   | Public — Customer Shareable            |
| Last Reviewed    | 2026-04-16                             |
| Next Review      | 2026-10-16                             |
| Version          | 1.0                                    |

## (a) Scope and Methodology

This inventory enumerates all open-source software (**"OSS"**) components distributed with or used at runtime by the TechNova RAG platform, together with their license terms and a compliance assessment.

**Scope.**
1. Backend Python packages declared in `backend/requirements.txt`.
2. Frontend Node packages declared in `frontend/package.json` (production and development dependencies).
3. Container images referenced in `docker-compose.yml`.
4. Pre-trained models and linguistic assets downloaded from Hugging Face Hub at backend startup.

Not in scope:
- Proprietary third-party services invoked over API (e.g., OpenAI `gpt-4o-mini`) — these are governed by the vendor's commercial terms, not OSS licenses, and TechNova does not redistribute them. They are addressed separately in Section (d).
- Transitive dependencies of transitive dependencies are surveyed via automated tooling (see Section (h)) but not individually listed here; the top-level declarations capture the license obligations that flow through.
- Build-only tooling that never ships in a release artifact (e.g., local IDE plugins).

**Methodology.**
- Direct dependencies are read from `backend/requirements.txt` and `frontend/package.json`.
- Licenses are confirmed against each package's published metadata (PyPI `classifier` / `License-Expression` fields; npm `license` field; Hugging Face model cards).
- The inventory is regenerated on every release using:
  - Python: `pip-licenses --format=markdown --with-urls --with-license-file` (or `pip-licenses --format=json`) against the pinned virtual environment.
  - Node: `npx license-checker --production --json` and `npx license-checker --json` for the full tree.
  - Container images: `syft packages <image> -o spdx-json` or equivalent SBOM tooling.
  - Output is reconciled against this document; deltas are surfaced in the Change History.

## (b) Python Packages (backend/requirements.txt)

| Package                   | Version    | License       | License Type | Usage in TechNova                                                             | Compliance Notes                                                                                   |
|---------------------------|------------|---------------|--------------|-------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| fastapi                   | 0.115.0    | MIT           | Permissive   | HTTP framework (`backend/main.py`, all routers)                               | Preserve copyright notice in NOTICE.txt if redistributed.                                           |
| uvicorn                   | 0.30.6     | BSD-3-Clause  | Permissive   | ASGI server for FastAPI                                                       | Preserve copyright notice and disclaimer if redistributed.                                          |
| pydantic                  | 2.9.2      | MIT           | Permissive   | Request/response schemas in `backend/models.py`                               | Preserve copyright notice.                                                                          |
| pydantic-settings         | 2.5.2      | MIT           | Permissive   | `Settings` class in `backend/config.py`                                       | Preserve copyright notice.                                                                          |
| python-dotenv             | 1.0.1      | BSD-3-Clause  | Permissive   | Loads `.env` / `backend/.env`                                                  | Preserve copyright notice and disclaimer.                                                           |
| pypdf                     | 4.3.1      | BSD-3-Clause  | Permissive   | PDF loader (`backend/services/loader.py`)                                     | Preserve copyright notice and disclaimer.                                                           |
| langchain-text-splitters  | 0.3.0      | MIT           | Permissive   | Chunker (500/100) in `backend/services/chunker.py`                            | Preserve copyright notice.                                                                          |
| sentence-transformers     | 3.1.1      | Apache-2.0    | Permissive   | Embedder (BGE) and cross-encoder reranker                                     | Must include LICENSE + NOTICE in distribution if redistributed (Apache-2.0 §4).                     |
| qdrant-client             | 1.12.0     | Apache-2.0    | Permissive   | Qdrant client for dense store                                                 | Apache-2.0 NOTICE-file obligation.                                                                  |
| rank-bm25                 | 0.2.2      | Apache-2.0    | Permissive   | BM25 indexer, pickled to `backend/bm25_index.pkl`                             | Apache-2.0 NOTICE-file obligation.                                                                  |
| openai                    | >=1.55.3,<2| Apache-2.0    | Permissive   | OpenAI SDK for `gpt-4o-mini` inference                                         | Apache-2.0 NOTICE-file obligation. Use of OpenAI service itself governed by OpenAI terms.           |
| spacy                     | 3.8.0      | MIT           | Permissive   | NER for knowledge-graph construction                                          | Preserve copyright notice.                                                                          |
| torch                     | >=2.2.0    | BSD-3-Clause  | Permissive   | Deep-learning runtime underlying embedder and reranker                        | Preserve copyright notice and disclaimer. Includes third-party notices within its own distribution. |
| numpy                     | <2.0       | BSD-3-Clause  | Permissive   | Numerical backend for embeddings and BM25                                     | Preserve copyright notice and disclaimer.                                                           |
| asyncpg                   | 0.30.0     | Apache-2.0    | Permissive   | Async Postgres driver for Neon corpus mirror                                  | Apache-2.0 NOTICE-file obligation.                                                                  |

## (c) Node Packages (frontend/package.json)

### Production Dependencies

| Package                       | Version  | License    | License Type | Usage in TechNova                                                         | Compliance Notes                                                  |
|-------------------------------|----------|------------|--------------|---------------------------------------------------------------------------|-------------------------------------------------------------------|
| next                          | 16.2.3   | MIT        | Permissive   | Next.js App Router for all frontend surfaces                              | Preserve copyright notice.                                        |
| react                         | 19.2.4   | MIT        | Permissive   | Core UI framework                                                         | Preserve copyright notice.                                        |
| react-dom                     | 19.2.4   | MIT        | Permissive   | React DOM renderer                                                        | Preserve copyright notice.                                        |
| @base-ui/react                | 1.4.0    | MIT        | Permissive   | Accessible primitive components                                           | Preserve copyright notice.                                        |
| class-variance-authority      | 0.7.1    | Apache-2.0 | Permissive   | Component variant utility                                                 | Apache-2.0 NOTICE-file obligation.                                |
| clsx                          | 2.1.1    | MIT        | Permissive   | Conditional className utility                                             | Preserve copyright notice.                                        |
| lucide-react                  | 1.8.0    | ISC        | Permissive   | Icon set used across surfaces                                             | Preserve copyright notice.                                        |
| react-force-graph-3d          | 1.29.1   | MIT        | Permissive   | 3D force-directed graph on `/knowledge-graph`                              | Preserve copyright notice.                                        |
| react-markdown                | 10.1.0   | MIT        | Permissive   | Rendering model outputs with markdown                                     | Preserve copyright notice.                                        |
| shadcn                        | 4.2.0    | MIT        | Permissive   | Component scaffolding                                                     | Preserve copyright notice.                                        |
| tailwind-merge                | 3.5.0    | MIT        | Permissive   | Tailwind class-deduplication utility                                      | Preserve copyright notice.                                        |
| three                         | 0.183.2  | MIT        | Permissive   | 3D graphics library backing `react-force-graph-3d`                        | Preserve copyright notice.                                        |
| tw-animate-css                | 1.4.0    | MIT        | Permissive   | Tailwind animation utilities                                              | Preserve copyright notice.                                        |
| @types/three                  | 0.183.1  | MIT        | Permissive   | TypeScript types for `three`                                              | Preserve copyright notice.                                        |

### Development Dependencies

| Package                       | Version  | License    | License Type | Usage in TechNova                                                         | Compliance Notes                                                  |
|-------------------------------|----------|------------|--------------|---------------------------------------------------------------------------|-------------------------------------------------------------------|
| eslint                        | 9        | MIT        | Permissive   | Linting                                                                   | Preserve copyright notice.                                        |
| tailwindcss                   | 4        | MIT        | Permissive   | Utility-first CSS                                                         | Preserve copyright notice.                                        |
| typescript                    | 5        | Apache-2.0 | Permissive   | Type-checking                                                             | Apache-2.0 NOTICE-file obligation if redistributed.               |
| @tailwindcss/postcss          | 4        | MIT        | Permissive   | Tailwind PostCSS plugin                                                   | Preserve copyright notice.                                        |
| @types/node                   | 20       | MIT        | Permissive   | TypeScript types for Node                                                 | Preserve copyright notice.                                        |
| @types/react                  | 19       | MIT        | Permissive   | TypeScript types for React                                                | Preserve copyright notice.                                        |
| @types/react-dom              | 19       | MIT        | Permissive   | TypeScript types for React DOM                                            | Preserve copyright notice.                                        |
| eslint-config-next            | 16.2.3   | MIT        | Permissive   | ESLint ruleset tuned for Next.js                                          | Preserve copyright notice.                                        |

## (d) Models and Linguistic Assets

| Asset                                             | License    | License Type | Usage in TechNova                                         | Compliance Notes                                                                                       |
|---------------------------------------------------|------------|--------------|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `BAAI/bge-base-en-v1.5`                           | MIT        | Permissive   | Dense embeddings (768-d) for retrieval                     | Preserve MIT notice if the model files are redistributed in a release artifact.                        |
| `cross-encoder/ms-marco-MiniLM-L-6-v2`            | Apache-2.0 | Permissive   | Cross-encoder reranker on top-N fused results              | Apache-2.0 NOTICE-file obligation if redistributed.                                                    |
| spaCy `en_core_web_sm`                            | MIT        | Permissive   | Named-entity recognition for the knowledge graph           | Preserve MIT notice if redistributed.                                                                  |
| OpenAI `gpt-4o-mini` (**proprietary — not OSS**)  | Proprietary| N/A          | LLM inference via OpenAI API                               | Not distributed with TechNova; access governed by OpenAI's commercial terms. **Not subject to OSS review.** |

## (e) Container Images

| Image                 | License    | License Type | Usage in TechNova                                              | Compliance Notes                                                       |
|-----------------------|------------|--------------|----------------------------------------------------------------|------------------------------------------------------------------------|
| `qdrant/qdrant`       | Apache-2.0 | Permissive   | Vector database (self-hosted default; Qdrant Cloud optional)   | Apache-2.0 NOTICE-file obligation. Image is run unmodified.            |

## (f) License Compatibility Analysis

All OSS components in scope are distributed under permissive licenses: **MIT**, **Apache-2.0**, **BSD-3-Clause**, or **ISC**. None of these licenses imposes source-disclosure obligations on downstream distributors of combined or derivative works.

| License Family     | Count in Scope | Compatibility with TechNova's Proprietary Code                                                       |
|--------------------|----------------|------------------------------------------------------------------------------------------------------|
| MIT                | Majority       | Compatible — attribution-only.                                                                        |
| Apache-2.0         | Several        | Compatible — attribution + NOTICE preservation + explicit patent grant.                               |
| BSD-3-Clause       | Several        | Compatible — attribution + no-endorsement clause.                                                     |
| ISC                | 1              | Compatible — functionally equivalent to simplified BSD.                                               |
| GPL / AGPL / LGPL  | **0**          | None detected. TechNova does not currently accept strong-copyleft runtime dependencies.               |

No strong-copyleft (GPL, AGPL, LGPL, SSPL) or non-commercial licenses have been detected. The platform is therefore **safe for commercial distribution and SaaS use** from an OSS-compliance standpoint.

## (g) NOTICE File Obligations (Apache-2.0)

Apache-2.0 §4(d) requires that, when redistributing Apache-2.0-licensed works in source or object form, any NOTICE file from the original work be preserved and passed on. The following dependencies are Apache-2.0 and trigger this obligation when TechNova distributes binaries or container images containing them:

- `sentence-transformers` 3.1.1
- `qdrant-client` 1.12.0
- `rank-bm25` 0.2.2
- `openai` (Python SDK)
- `asyncpg` 0.30.0
- `class-variance-authority` 0.7.1
- `typescript` 5 (dev-only, but reproduced in source releases)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (if the model file is redistributed)
- `qdrant/qdrant` (container image)

### Generated `NOTICE.txt` Template

The following template is produced as part of every release artifact and is included alongside the LICENSE file. TechNova's build pipeline substitutes the bracketed placeholders with metadata read from each dependency's own NOTICE file at build time.

```
TechNova RAG
Copyright (c) 2026 TechNova, Inc.

This product includes software developed by third parties under permissive
open-source licenses. Attribution and notices required by those licenses
are reproduced below.

-------------------------------------------------------------------------------
sentence-transformers
  Copyright (c) [year] [copyright holders]
  Licensed under the Apache License, Version 2.0.
  Upstream NOTICE: [verbatim contents of the sentence-transformers NOTICE file]
-------------------------------------------------------------------------------
qdrant-client
  Copyright (c) [year] Qdrant
  Licensed under the Apache License, Version 2.0.
  Upstream NOTICE: [verbatim contents of qdrant-client NOTICE file, if any]
-------------------------------------------------------------------------------
rank-bm25
  Copyright (c) [year] [copyright holders]
  Licensed under the Apache License, Version 2.0.
  Upstream NOTICE: [verbatim contents or "no NOTICE file present upstream"]
-------------------------------------------------------------------------------
openai (Python SDK)
  Copyright (c) OpenAI
  Licensed under the Apache License, Version 2.0.
  Upstream NOTICE: [verbatim contents of openai-python NOTICE file]
-------------------------------------------------------------------------------
asyncpg
  Copyright (c) MagicStack, Inc.
  Licensed under the Apache License, Version 2.0.
  Upstream NOTICE: [verbatim contents or "no NOTICE file present upstream"]
-------------------------------------------------------------------------------
class-variance-authority
  Copyright (c) [year] [copyright holders]
  Licensed under the Apache License, Version 2.0.
-------------------------------------------------------------------------------
typescript
  Copyright (c) Microsoft Corporation
  Licensed under the Apache License, Version 2.0.
-------------------------------------------------------------------------------
cross-encoder/ms-marco-MiniLM-L-6-v2
  Copyright (c) UKPLab / Hugging Face authors
  Licensed under the Apache License, Version 2.0.
-------------------------------------------------------------------------------
qdrant/qdrant container image
  Copyright (c) Qdrant Solutions GmbH
  Licensed under the Apache License, Version 2.0.
-------------------------------------------------------------------------------

A full copy of the Apache License, Version 2.0 is available at:
    https://www.apache.org/licenses/LICENSE-2.0

Permissive MIT / BSD / ISC licensed components are also included. The
LICENSES/ directory of this distribution reproduces the full text of each
license and the applicable copyright notices.
```

## (h) Audit Commands

The following commands regenerate the inventory and should be run on every release. Output is reconciled against this document and stored alongside the release artifact.

```bash
# Python — from an activated venv in the repository root
pip install pip-licenses
pip-licenses --format=markdown --with-urls --with-license-file > licenses/python.md
pip-licenses --format=json --with-urls --with-license-file > licenses/python.json

# Node — from frontend/
cd frontend
npx --yes license-checker --production --json > ../licenses/node-production.json
npx --yes license-checker --json > ../licenses/node-all.json

# Container SBOM — syft produces SPDX; optional but recommended
syft packages qdrant/qdrant:latest -o spdx-json > licenses/qdrant-image.spdx.json

# Fail the release on detection of disallowed licenses
pip-licenses --fail-on "GPL;AGPL;LGPL;SSPL"
```

## (i) Known Issues

None as of 2026-04-16. No GPL/AGPL/LGPL/SSPL dependencies detected; no license conflicts; no unresolved attribution obligations.

## (j) Refresh Cadence

- **Every release.** Inventory regenerated, reconciled, and committed with the release tag.
- **Ad-hoc.** Upon adoption of any new dependency or upgrade of a major-version dependency; upon any change to a license classifier in PyPI or npm metadata.
- **Semi-annual.** Full re-review by TechNova Legal (Next Review: 2026-10-16).

## Revision History

| Version | Date       | Author         | Summary         |
|---------|------------|----------------|-----------------|
| 1.0     | 2026-04-16 | TechNova Legal | Initial release |
