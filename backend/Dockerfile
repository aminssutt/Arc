# syntax=docker/dockerfile:1
# Arc backend — FastAPI on Python 3.12, run from the repo root as a package
# (`backend.app.main:app` imports both `agents.*` and `backend.app.*`), so the
# build context is the REPO ROOT (see docker-compose.yml: context ".").
# No secret is ever copied in: .env, .venv, keys and the frontend/ios trees are
# excluded by the root .dockerignore. Secrets arrive at run time via env_file.
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Pinned runtime deps first, for layer caching (covers agents/common too: httpx).
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Application code + the data/contracts the backend reads at boot.
COPY agents/ agents/
COPY backend/ backend/
COPY contracts/ contracts/
COPY data/ data/

# Non-root user; owns the app and the writable runtime dir (push-out + device
# registry) that docker-compose mounts as a named volume at /var/lib/arc.
RUN useradd --create-home --uid 10001 arc \
 && mkdir -p /var/lib/arc/push-out \
 && chown -R arc:arc /app /var/lib/arc
USER arc

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
