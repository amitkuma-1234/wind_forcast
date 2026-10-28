"""Vercel serverless entrypoint: exposes the FastAPI app from backend/main.py."""
import os
import sys

BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
os.environ.setdefault("ALLOW_LIVE", "0")  # serverless: use bundled CSV cache, never fetch in a request

from main import app  # noqa: E402,F401
