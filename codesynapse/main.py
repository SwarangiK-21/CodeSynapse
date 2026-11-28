import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from codesynapse.api import auth
from codesynapse.api.routes import router
from codesynapse.db.session import engine
from codesynapse.services import limits
from codesynapse.ui.app import demo
from codesynapse.ui.style import custom_css, theme

app = FastAPI(title="CodeSynapse")
app.include_router(router)
app.include_router(auth.router)

@app.exception_handler(limits.Limited)
def rate_limited(request: Request, error: limits.Limited):
    return JSONResponse({"detail": str(error)}, status_code=429, headers={"Retry-After": str(error.retry_after)})

@app.get("/health")
def health():
    """Checks the database too, so a monitor sees a broken connection, and the daily check
    counts as activity for hosted databases that pause when idle."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "error", "database": "unreachable"}, status_code=503)
    return {"status": "ok", "database": "ok"}

# Mounted last: the UI owns every path the API doesn't
app = gr.mount_gradio_app(app, demo.queue(), path="/", theme=theme, css=custom_css)
