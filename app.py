import uvicorn
from codesynapse.db.migrate import upgrade

if __name__ == "__main__":
    upgrade()
    from codesynapse.db.session import SessionLocal
    from codesynapse.services import tasks
    with SessionLocal() as db:
        tasks.recover_interrupted(db)
    uvicorn.run("codesynapse.main:app", host="0.0.0.0", port=7860)
