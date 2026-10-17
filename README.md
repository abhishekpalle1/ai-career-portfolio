# AI Career Portfolio and Resume RAG Assistant

A recruiter-facing single-page portfolio with an AI career assistant that answers questions
strictly from approved career materials, with clickable citations.

**Current status: Phase 4 complete.** The live Gemini + Pinecone RAG path is verified against the 13
indexed résumé chunks and now runs behind deterministic input, retrieval, and output guardrails
with rate limits and caching. The backend serves **deterministic mock answers** unless the live
flags are enabled.

---

## Repository layout

```
.
├── frontend/                 React + TypeScript + Vite single-page site
│   ├── src/
│   │   ├── api/              Backend client with defensive response normalization
│   │   ├── components/       Presentational and interactive components
│   │   ├── data/             Typed, editable professional content
│   │   ├── hooks/            useCareerAssistant chat state
│   │   ├── sections/         Hero, Metrics, Featured Work, Assistant, Contact, Footer
│   │   ├── styles/           Design tokens and global stylesheet
│   │   └── types/            Portfolio and chat type definitions
│   └── tests/                Vitest + React Testing Library
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── api/              Chat and system routers
│   │   ├── core/             Environment-driven settings
│   │   ├── models/           Pydantic request/response schemas
│   │   └── services/         Deterministic mock assistant (replaced in Phase 3)
│   └── tests/                Pytest
├── knowledge-base/           Approved Markdown sources with YAML front matter
│   └── resume/resume.md
├── ingestion/                Offline ingestion CLI (run from the repository root)
│   ├── parsers/              Front matter + heading-aware Markdown parsing
│   ├── validation/           Metadata validation and sensitive-content scanning
│   ├── chunking/             Section-aware chunking, stable IDs, SHA-256 hashes
│   ├── adapters/             Gemini embedder and Pinecone store (live mode only)
│   ├── pipelines/            Planning, apply, manifest, reports
│   ├── state/                manifest.json, written only after a successful --apply
│   ├── tests/                Pytest (no network)
│   └── cli.py
├── .github/workflows/        Frontend, backend, and ingestion CI
├── Makefile
└── README.md
```

---

## Setup

### Frontend

Requires Node >= 20.19.

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
```

> Regenerating `package-lock.json` from scratch (deleting it and running `npm install`) requires
> **npm >= 11**. npm 10 crashes with `Cannot read properties of null (reading 'edgesOut')` while
> resolving Vitest's optional browser peer dependencies — an npm bug, not a dependency conflict.
> Use `npx npm@11 install` if you need to rebuild the lockfile. `npm ci` and `npm install` against
> the committed lockfile work on npm 10.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

> `FRONTEND_ORIGINS` is a **comma-separated** list, not JSON — for example
> `FRONTEND_ORIGINS=http://localhost:5173,https://user.github.io`. Leave it unset to fall back to
> `http://localhost:5173`.

---

## Run locally

| Target   | Command                                                        | URL                     |
| -------- | -------------------------------------------------------------- | ----------------------- |
| Frontend | `cd frontend; npm run dev`                                      | <http://localhost:5173> |
| Backend  | `cd backend; python -m uvicorn app.main:app --reload --port 8000` | <http://localhost:8000> |

The site works without the backend running — the assistant shows a graceful unavailable message
while the rest of the page stays fully functional.

---

## Verification commands

```powershell
cd frontend; npm run test          # Vitest
cd frontend; npm run lint          # ESLint
cd frontend; npm run format:check  # Prettier
cd frontend; npm run typecheck     # tsc --noEmit
cd frontend; npm run build         # Production build

cd backend; python -m pytest       # Pytest
cd backend; python -m ruff check . # Ruff
cd backend; python -m mypy         # MyPy (strict)

# Ingestion (from the repository root)
python -m pytest ingestion
python -m ruff check ingestion
python -m mypy --config-file ingestion/pyproject.toml ingestion
```

---

## Knowledge base and ingestion

Every file in `knowledge-base/` is Markdown with YAML front matter (`source_id`, `source_type`,
`source_name`, `section`, `project_id`, `experience_type`, `visibility`, `approved`, `source_url`,
`document_version`, `updated_at`, and optional `section_experience_types`, which maps `##`
headings to `PROFESSIONAL`, `PORTFOLIO`, `EDUCATION`, or `GENERAL`).

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -r ingestion/requirements-dev.txt

python -m ingestion.cli validate   # Metadata, sensitive content, chunking. No outputs, no network.
python -m ingestion.cli ingest     # Dry run: plan + reports in ingestion/output/ (gitignored)

# Offline stateful check: writes a local manifest so a second run reports UNCHANGED.
# Makes no embedding or Pinecone calls. Refuses the production manifest path.
python -m ingestion.cli --manifest $env:TEMP\kb-state\manifest.json ingest --persist-manifest
```

Pipeline behavior:

- Files with `approved: false` or `visibility: PRIVATE` are reported as skipped, never indexed
- Any error (invalid metadata, phone number, email outside `PUBLIC_CONTACT`, secret, internal URL,
  redaction placeholder, confidentiality marker, embedded instruction) fails the whole run.
  Findings report the category and line, never the matched value
- Chunks follow heading sections; each chunk is prefixed with its heading path, so a role, its
  projects, and their metrics stay together. Long sections split only between whole bullets
- `CHUNK_SIZE_TOKENS` (450) and `CHUNK_OVERLAP_TOKENS` (60) use an approximate offline token count
- Chunk IDs derive from `source_id` + heading path; hashes cover chunk text and metadata
- `ingestion/state/manifest.json` records what was upserted (IDs and hashes only, no text), so
  re-runs embed only new or changed chunks. A different embedding model forces a full re-index

Live indexing (not yet run) requires `pip install -r ingestion/requirements-live.txt`, an existing
Pinecone index whose dimension equals `GEMINI_EMBEDDING_DIMENSIONS` (1536 for `career-portfolio`),
and both `ENABLE_LIVE_MODEL_CALLS=true` and `ENABLE_LIVE_VECTOR_UPSERTS=true`. Settings can be
read from `backend/.env` with `--env-file`; values are never printed.

Model provider: Google Gemini Developer API (`google-genai`). Documents and queries are embedded
with `GEMINI_EMBEDDING_MODEL` (`gemini-embedding-2`) using its retrieval text format
(`title: none | text: …` for documents, `task: search result | query: …` for questions).
Changing the embedding model or dimensions forces a full re-index.

```powershell
python -m ingestion.cli --env-file backend/.env preflight                # No network, no writes
python -m ingestion.cli --env-file backend/.env ingest --apply           # Upsert new/changed chunks
python -m ingestion.cli --env-file backend/.env ingest --apply --delete-stale
```

---

## Live RAG (Phase 3)

`POST /api/v1/chat` serves the deterministic mock unless **both** `ENABLE_LIVE_RAG` and
`ENABLE_LIVE_MODEL_CALLS` are true. When live, each question makes at most one query embedding,
one Pinecone query, and one generation call:

- Deterministic intent classification; out-of-scope, contact, and resume requests make no paid calls
- Pinecone query always filtered on `visibility=PUBLIC`, `approved=true`, `ingestion_status=VERIFIED`
  in backend code, then re-verified per match along with provenance and safe `source_url`
- Context: score-ordered, de-duplicated, capped by `FINAL_CONTEXT_CHUNKS` and optional
  `MIN_RETRIEVAL_SCORE` / `MAX_CONTEXT_TOKENS` (left unset until Phase 5 evaluation)
- Evidence is wrapped in `<retrieved_evidence>` as untrusted data; structured JSON output from
  `GEMINI_GENERATION_MODEL` (`gemini-3.5-flash-lite`), validated against the response schema
- Gemini clients are built with retries disabled; a failed call surfaces as an abstention or `503`
- Unknown citations, uncited or unsupported claims, and professional/portfolio attribution
  mismatches become a safe abstention. Dependency failures return a generic `503`
- Logs record trace ID, intent, counts, outcome, and latency, never question text or secrets

```powershell
cd backend; python -m app.preflight   # No network, no writes; prints names and booleans only
```

---

## Guardrails and cost controls (Phase 4)

All guardrails are deterministic application code in `backend/app/guardrails/`; none adds a model call.

| Stage | Control |
| --- | --- |
| Input | Blocks prompt injection and jailbreaks (including leetspeak, spaced, zero-width, URL/HTML-entity, and base64/hex-encoded forms), credential and prompt requests, vector-store dumps, fabrication requests, sensitive personal data, confidential employer data, HTML/script/file content, and off-topic tasks. Blocked requests get the scope message and make **no** paid call |
| Retrieval | Drops retrieved chunks containing instructions aimed at the assistant before generation |
| Prompt | `grounded-answer-v2`: absence of evidence is reported as "not documented", false premises are corrected from evidence, portfolio projects are never placed at an employer |
| Output | `PASS` / `REPAIRABLE` / `FAIL`. Fails on secrets, prompt or metadata leakage, URLs/HTML, unsupported negative assertions ("has not worked at X"), and portfolio-at-employer attribution. Repairable: uncited numbers or bullets, over-long answers. Stray emails and phone numbers are redacted |
| Retries | `MAX_GENERATION_RETRIES` (default `0`) applies only to repairable failures |
| Limits | `MAX_QUESTIONS_PER_SESSION` and `MAX_QUESTIONS_PER_IP_PER_DAY` return `429` with `Retry-After`. `X-Forwarded-For` is ignored unless `TRUSTED_PROXY_HOPS` > 0 |
| Cache | Bounded TTL LRU cache keyed by normalized question + corpus, models, dimensions, namespace, and prompt version. Only grounded, validated answers are cached |

The frontend already treats `429` and `503` as "temporarily unavailable"; the static page keeps
working.

---

## API

| Method | Path           | Description                                                  |
| ------ | -------------- | ------------------------------------------------------------ |
| GET    | `/health`      | Liveness. Calls no paid dependency.                          |
| GET    | `/ready`       | Configuration checks, no secret values.                      |
| GET    | `/version`     | Application, corpus, and build identifiers.                  |
| POST   | `/api/v1/chat` | Mock answer, or live grounded answer when live flags are on. |

The request and response shapes are unchanged from Phase 1, so the frontend needs no changes.

---

## Section anchors

`#home` · `#work` · `#assistant` · `#contact`

---

## Content placeholders

All editable content lives in `frontend/src/data/`. Values wrapped in square brackets are
**unverified placeholders** and must be replaced with approved content or removed:

- `profile.ts` — confirm or clear `availabilityStatement`; supply `photoUrl` if a real photo exists
- `metrics.ts` — every metric is a placeholder; publish only metrics backed by approved sources,
  or empty the array to hide the band
- `featuredWork.ts` — the two professional cards are placeholders; the portfolio card is accurate
- `contacts.ts` — driven by `VITE_PUBLIC_EMAIL`, `VITE_LINKEDIN_URL`, `VITE_GITHUB_URL`
- `backend/app/services/mock_assistant.py` — all mock answers are placeholder text

No employer, role, metric, degree, certification, or contact detail is asserted anywhere until
approved source content is supplied.

---

## Security notes

- No secrets in frontend code or `VITE_` variables
- Explicit, environment-driven CORS allowlist (no wildcards)
- Request-size limit, input-length limit, and security headers on the backend
- Backend errors are logged internally and returned as a generic message
- Model output is rendered as text, never as HTML
- Citation URLs using `javascript:`, `data:`, or `file:` schemes are dropped

---

## Roadmap

| Phase | Scope                               | Status      |
| ----- | ----------------------------------- | ----------- |
| 1     | Frontend + backend skeleton + mocks | Complete    |
| 2     | Knowledge base and ingestion        | Complete    |
| 3     | Live RAG pipeline                   | Complete (Gemini + Pinecone, 13 chunks in `development`) |
| 4     | Guardrails and cost controls        | Complete    |
| 5     | Evaluation framework                | Not started |
| 6     | Deployment                          | Not started |
| 7     | Content and polish                  | Not started |
