# AI Career Portfolio and Resume RAG Assistant

A recruiter-facing single-page portfolio with an AI career assistant that answers questions
strictly from approved career materials, with clickable citations.

**Current status: Phase 2 complete (offline).** The frontend is fully built and the FastAPI backend
serves **deterministic mock answers**. The approved résumé is converted to Markdown and an offline
ingestion pipeline validates, chunks, and plans indexing. No live OpenAI or Pinecone call has been
made yet, and the backend is not connected to retrieval.

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
│   ├── adapters/             OpenAI embedder and Pinecone store (live mode only)
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
Pinecone index whose dimension matches the embedding model, and these environment variables:

```powershell
$env:ENABLE_LIVE_MODEL_CALLS = "true"
$env:OPENAI_API_KEY = "..."; $env:OPENAI_EMBEDDING_MODEL = "..."
$env:PINECONE_API_KEY = "..."; $env:PINECONE_INDEX = "career-portfolio"; $env:PINECONE_NAMESPACE = "production"
python -m ingestion.cli ingest --apply                  # Upsert new/changed chunks
python -m ingestion.cli ingest --apply --delete-stale   # Also delete removed chunks
```

---

## API (Phase 1)

| Method | Path           | Description                                    |
| ------ | -------------- | ---------------------------------------------- |
| GET    | `/health`      | Liveness. Calls no paid dependency.            |
| GET    | `/ready`       | Configuration checks, no secret values.        |
| GET    | `/version`     | Application, corpus, and build identifiers.    |
| POST   | `/api/v1/chat` | Deterministic mock answer with mock citations. |

The `/api/v1/chat` request and response shapes already match the final contract, so Phase 3 can
replace the mock service without changing the frontend.

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
| 2     | Knowledge base and ingestion        | Complete (offline; live upsert not yet run) |
| 3     | Live RAG pipeline                   | Not started |
| 4     | Guardrails and cost controls        | Not started |
| 5     | Evaluation framework                | Not started |
| 6     | Deployment                          | Not started |
| 7     | Content and polish                  | Not started |
