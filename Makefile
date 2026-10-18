.PHONY: help install-frontend install-backend install-ingestion dev-frontend dev-backend test-frontend test-backend test-ingestion lint-frontend lint-backend lint-ingestion ingest-validate ingest-dry-run typecheck build test lint test-evaluations lint-evaluations eval-offline eval-rescore

help:
	@echo "install-frontend  Install frontend dependencies"
	@echo "install-backend   Install backend dependencies (editable, with dev extras)"
	@echo "install-ingestion Install ingestion pipeline dev dependencies"
	@echo "dev-frontend      Run the Vite dev server on http://localhost:5173"
	@echo "dev-backend       Run the FastAPI dev server on http://localhost:8000"
	@echo "test              Run frontend and backend tests"
	@echo "lint              Run frontend and backend linters"
	@echo "build             Produce the frontend production build"
	@echo "ingest-validate   Validate the knowledge base (no outputs, no network)"
	@echo "ingest-dry-run    Plan ingestion and write reports (no network)"
	@echo "eval-offline      Phase 5 offline evaluation and release gates (no network)"
	@echo "eval-rescore      Re-score saved observations, LABEL=baseline (no network)"

install-frontend:
	cd frontend && npm ci

install-backend:
	cd backend && python -m pip install -e ".[dev]"

install-ingestion:
	python -m pip install -r ingestion/requirements-dev.txt

dev-frontend:
	cd frontend && npm run dev

dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

test-frontend:
	cd frontend && npm run test

test-backend:
	cd backend && python -m pytest

test-ingestion:
	python -m pytest ingestion

lint-frontend:
	cd frontend && npm run lint && npm run format:check

lint-backend:
	cd backend && python -m ruff check . && python -m mypy

lint-ingestion:
	python -m ruff check ingestion && python -m ruff format --check ingestion && python -m mypy --config-file ingestion/pyproject.toml ingestion

ingest-validate:
	python -m ingestion.cli validate

ingest-dry-run:
	python -m ingestion.cli ingest

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

test-evaluations:
	python -m pytest evaluations

lint-evaluations:
	python -m ruff check evaluations && python -m ruff format --check evaluations && python -m mypy --config-file evaluations/pyproject.toml evaluations

eval-offline:
	python -m evaluations.run_evaluation offline --overwrite

LABEL ?= baseline
eval-rescore:
	python -m evaluations.run_evaluation rescore --observations evaluations/reports/$(LABEL)/observations.jsonl --label $(LABEL)-rescored --overwrite

test: test-frontend test-backend test-ingestion test-evaluations

lint: lint-frontend lint-backend lint-ingestion lint-evaluations
