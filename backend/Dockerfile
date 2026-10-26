# The backend image: Python + our FastAPI app + the clean January data.
#
# Three stages (each "FROM" starts one):
#   base    - Python, the libraries the app needs, the app code and the processed data
#   test    - base + pytest and the tests (only built when you ask for it)
#   runtime - base, run as a normal user, with a health check   <- the default image
#
# Build and run on its own:   docker build -t windhedge-backend backend
#                             docker run -p 8000:8000 windhedge-backend
# Run the tests in Docker:    docker compose --profile test run --rm backend-tests

# ---------- base ----------
FROM python:3.11-slim AS base

# Don't write .pyc files, print logs straight away, keep pip quiet and small.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Libraries first: Docker re-uses this step until requirements.txt changes,
# so rebuilding after a code change is fast.
COPY requirements.txt .
RUN pip install -r requirements.txt

# The app and the clean data it reads. No internet or Elexon download needed.
COPY app/ app/
COPY data/processed/ data/processed/

# A normal (non-admin) user to run the app as.
RUN useradd --create-home --uid 10001 appuser

# ---------- test ----------
FROM base AS test
COPY requirements-dev.txt pytest.ini ./
RUN pip install -r requirements-dev.txt
COPY tests/ tests/
USER appuser
# -p no:cacheprovider: pytest doesn't try to save its cache in the read-only app folder
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

# ---------- runtime (the default, used by docker compose) ----------
FROM base AS runtime

# Not root: if someone ever broke into the app, they wouldn't get admin rights here.
USER appuser

EXPOSE 8000

# Docker asks /api/health every 30 s; after 3 failures the container is "unhealthy".
# (The slim image has no curl, so we use Python itself.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status != 200)"

# 0.0.0.0 = accept connections from outside this container (from nginx and from you).
# 127.0.0.1 would mean "only from inside this same container".
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
