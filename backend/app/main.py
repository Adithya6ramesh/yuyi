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
"""

from contextlib import asynccontextmanager

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
# address unless that server says "this page is allowed" - here we allow the React
# development server (Vite runs on port 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

errors.register(app)
app.include_router(router, prefix="/api")


@app.get("/", include_in_schema=False)
def home():
    """Opening the bare address sends you to the interactive docs page."""
    return RedirectResponse("/docs")
