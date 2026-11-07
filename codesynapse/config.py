import os
from dotenv import load_dotenv

load_dotenv()

# SQLite needs no setup for local runs. Docker and CI use Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///codesynapse_local.db")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODELS = "gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite"
GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", DEFAULT_MODELS).split(",")]

GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

# Optional: raises GitHub's hourly rate limit
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# How many indexing and analysis jobs run at once
WORKERS = int(os.getenv("WORKERS", "2"))

# Encrypts the browser's copy of the user token. Set a real value when deployed.
UI_SECRET = os.getenv("UI_SECRET", "local-dev-only")
