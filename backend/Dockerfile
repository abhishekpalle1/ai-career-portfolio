# Cloud Run source deploy: gcloud run deploy --source backend
# Python 3.12 matches the backend CI test matrix (pyproject requires >=3.11).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Runtime dependencies only (no [dev] extra); the app package installs into site-packages.
COPY pyproject.toml ./
COPY app ./app
RUN pip install . && rm -rf build ./*.egg-info

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
