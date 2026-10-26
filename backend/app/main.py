"""
THE WEB SERVER - where the app starts.

Start it from the backend/ folder:
    .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
then open http://127.0.0.1:8000/docs

This file only wires things together:
    - load the data once at start-up           (store.py)
    - allow the React dev server to call us    (CORS, below)
    - friendly error messages                  (errors.py)
    - the endpoints, all under /api            (routes.py)
    - the built React app, when it exists      (on Vercel; see FRONTEND_DIR below)
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import errors, store
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before 'yield') - load the data into memory."""
    store.load()
    yield


app = FastAPI(
    title="UK Wind Forecast Accuracy API",
    description="How accurate were national wind forecasts (Elexon WINDFOR) against "
    "actual wind (Elexon FUELHH) for day-ahead purchases in January 2026? "
    "All times are UTC.",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS in one sentence: browsers block a web page from calling a server on a different
# address unless that server says "this page is allowed".
# Which addresses are allowed comes from the ALLOWED_ORIGINS environment variable
# (comma-separated, e.g. "https://windhedge.vercel.app,http://localhost:5173").
# Default: the React development server (Vite, port 5173), except on Vercel, where the
# site and the API share one address, so no other site needs to be allowed.
# (In Docker it isn't needed: nginx serves the page AND forwards /api, so it's one address.)
DEFAULT_ORIGINS = "" if os.environ.get("VERCEL") else "http://localhost:5173,http://127.0.0.1:5173"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

errors.register(app)
app.include_router(router, prefix="/api")

# The built React app, if there is one (on Vercel, scripts/build_frontend.py puts it here).
# With it, this one app serves the whole site: the API routes above (/api/..., /docs)
# always win, and every other page address gets the React app's index.html, so /desk
# works on refresh and unknown addresses show the app's own 404 screen.
# Without it (local development, Docker), the frontend runs separately, as before.
FRONTEND_DIR = Path(
    os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[1] / "frontend_dist")
)

if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR, fallback="index.html")
elif not os.environ.get("VERCEL"):  # Vercel sets VERCEL=1; there "/" is the landing page

    @app.get("/", include_in_schema=False)
    def home():
        """Opening the bare address sends you to the interactive docs page."""
        return RedirectResponse("/docs")
