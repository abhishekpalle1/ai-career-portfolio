.PHONY: help install-frontend install-backend dev-frontend dev-backend test-frontend test-backend lint-frontend lint-backend typecheck build test lint

help:
	@echo "install-frontend  Install frontend dependencies"
	@echo "install-backend   Install backend dependencies (editable, with dev extras)"
	@echo "dev-frontend      Run the Vite dev server on http://localhost:5173"
	@echo "dev-backend       Run the FastAPI dev server on http://localhost:8000"
	@echo "test              Run frontend and backend tests"
	@echo "lint              Run frontend and backend linters"
	@echo "build             Produce the frontend production build"

install-frontend:
	cd frontend && npm ci

install-backend:
	cd backend && python -m pip install -e ".[dev]"

dev-frontend:
	cd frontend && npm run dev

dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

test-frontend:
	cd frontend && npm run test

test-backend:
	cd backend && python -m pytest

lint-frontend:
	cd frontend && npm run lint && npm run format:check

lint-backend:
	cd backend && python -m ruff check . && python -m mypy

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

test: test-frontend test-backend

lint: lint-frontend lint-backend
