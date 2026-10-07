"""Central configuration, read from environment variables (.env supported)."""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

POLICY_DIR = BASE_DIR / "policies"
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "cases.db"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:5173")

# Assessment date; individual cases may override it.
DEFAULT_CASE_DATE = date.fromisoformat(os.getenv("CASE_DATE", "2026-10-07"))

GROQ_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")