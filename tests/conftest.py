import os
import tempfile
from pathlib import Path

# Must be set before codesynapse is imported. CI supplies a Postgres DATABASE_URL.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.mkdtemp()) / 'test.db'}")
os.environ["GEMINI_API_KEY"] = ""
os.environ["GITHUB_TOKEN"] = ""

import pytest
from fastapi.testclient import TestClient
from codesynapse.db.migrate import upgrade
from codesynapse.db.models import Base
from codesynapse.db.session import SessionLocal
from codesynapse.main import app

@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    upgrade()

@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with SessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth(client):
    """Creates a user and returns their Authorization header."""
    def make():
        token = client.post("/api/users").json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return make

@pytest.fixture
def fake_stats(monkeypatch):
    """Replaces live fetching. Each username gets its own stats."""
    async def get_all_stats(usernames):
        return [{"platform": "GitHub", "stats": {"Public Repos": len(usernames["github"])}, "score_norm": 10}]
    monkeypatch.setattr("codesynapse.services.fetchers.get_all_stats", get_all_stats)

@pytest.fixture
def fake_ai(monkeypatch):
    """Replaces Gemini and records what it was given."""
    calls = []
    def ask_gemini(question, stats, history=()):
        calls.append({"question": question, "stats": stats, "history": list(history)})
        return '{"advice": "Keep going", "actions": [{"step": "Build a project"}]}'
    monkeypatch.setattr("codesynapse.services.coach.ask_gemini", ask_gemini)
    return calls
