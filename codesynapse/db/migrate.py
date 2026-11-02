from pathlib import Path
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[2]

def upgrade():
    """Brings the database up to the latest migration."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")
