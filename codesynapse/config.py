import os
from dotenv import load_dotenv

load_dotenv()

# SQLite needs no setup for local runs. Docker and CI use Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///codesynapse_local.db")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-3.8-flash,gemini-3.5-flash-lite").split(",")]

# Optional: raises GitHub's hourly rate limit
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Encrypts the browser's copy of the user token. Set a real value when deployed.
UI_SECRET = os.getenv("UI_SECRET", "local-dev-only")
