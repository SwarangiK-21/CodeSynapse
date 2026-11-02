import uvicorn
from codesynapse.db.migrate import upgrade

if __name__ == "__main__":
    upgrade()
    uvicorn.run("codesynapse.main:app", host="0.0.0.0", port=7860)
