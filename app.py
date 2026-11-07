import os
import sys
import uvicorn
from codesynapse import config
from codesynapse.db.migrate import upgrade

if __name__ == "__main__":
    # Hugging Face sets SPACE_ID. A public deployment must not use the shared development secret.
    if os.getenv("SPACE_ID") and config.UI_SECRET == "local-dev-only":
        sys.exit("Set the UI_SECRET secret in the Space settings before deploying.")
    if os.getenv("SPACE_ID") and config.DATABASE_URL.startswith("sqlite"):
        print("Warning: DATABASE_URL is not set, so data is lost whenever the Space restarts.", flush=True)
    upgrade()
    from codesynapse.db.session import SessionLocal
    from codesynapse.services import tasks
    with SessionLocal() as db:
        tasks.recover_interrupted(db)
    uvicorn.run("codesynapse.main:app", host="0.0.0.0", port=7860)
