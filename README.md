# AI Career Portfolio and Resume RAG Assistant

A recruiter-facing single-page portfolio with an AI career assistant that answers questions
strictly from approved career materials, with clickable citations.

**Current status: Phase 1 complete.** The frontend is fully built and the FastAPI backend serves
**deterministic mock answers**. No OpenAI, Pinecone, GCP, or deployment integration exists yet.

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
├── .github/workflows/        Frontend and backend CI
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
| 2     | Knowledge base and ingestion        | Not started |
| 3     | Live RAG pipeline                   | Not started |
| 4     | Guardrails and cost controls        | Not started |
| 5     | Evaluation framework                | Not started |
| 6     | Deployment                          | Not started |
| 7     | Content and polish                  | Not started |
