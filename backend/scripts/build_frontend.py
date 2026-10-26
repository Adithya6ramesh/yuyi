"""
Build the React frontend and copy it into backend/frontend_dist/.

Vercel runs this during deployment (see [tool.vercel.scripts] in pyproject.toml). The
FastAPI app then serves the built site itself, so the website and the API share one
address and the frontend can keep calling "/api/...".

You can also run it locally (from the backend/ folder) to try that one-address setup:
    .venv\\Scripts\\python.exe scripts\\build_frontend.py
    .venv\\Scripts\\python.exe -m uvicorn app.main:app
then open http://127.0.0.1:8000 (delete frontend_dist/ to go back to normal).
"""

import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
TARGET_DIR = BACKEND_DIR / "frontend_dist"


def main():
    npm = shutil.which("npm")
    if npm is None:
        sys.exit("npm was not found: Node.js is needed to build the frontend.")
    if not FRONTEND_DIR.is_dir():
        sys.exit(f"The frontend folder was not found at {FRONTEND_DIR}.")

    print(f"Building the frontend in {FRONTEND_DIR} ...", flush=True)
    subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)

    shutil.rmtree(TARGET_DIR, ignore_errors=True)
    shutil.copytree(FRONTEND_DIR / "dist", TARGET_DIR)
    print(f"Copied the built site to {TARGET_DIR}", flush=True)


if __name__ == "__main__":
    main()
