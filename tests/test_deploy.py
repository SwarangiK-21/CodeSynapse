import importlib.util
from pathlib import Path
import pytest
from codesynapse import config

@pytest.mark.parametrize("given,expected", [
    ("postgresql://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
    ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("sqlite:///local.db", "sqlite:///local.db"),
])
def test_plain_postgres_urls_use_the_installed_driver(given, expected):
    assert config.database_url(given) == expected

def load_push_script():
    path = Path(__file__).parent.parent / "deploy" / "push_space.py"
    spec = importlib.util.spec_from_file_location("push_space", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError:
        pytest.skip("huggingface_hub is only installed by the deploy workflow")
    return module

def test_space_bundle_has_settings_and_no_secrets(tmp_path):
    push = load_push_script()
    push.build(tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("---\n") and "sdk: docker" in readme and "app_port: 7860" in readme
    assert (tmp_path / "Dockerfile").exists() and (tmp_path / "codesynapse" / "main.py").exists()
    names = {p.name for p in tmp_path.rglob("*")}
    assert ".env" not in names and "tests" not in names and "__pycache__" not in names

def test_tables_are_closed_to_hosted_data_apis():
    from sqlalchemy import text
    from codesynapse.db.session import engine
    if engine.dialect.name != "postgresql":
        pytest.skip("Row-level security is a Postgres feature")
    with engine.connect() as connection:
        open_tables = connection.execute(text(
            "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
            "AND relkind = 'r' AND NOT relrowsecurity")).scalars().all()
    assert open_tables == []
