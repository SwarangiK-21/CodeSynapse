import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from codesynapse.api.routes import router
from codesynapse.services import limits
from codesynapse.ui.app import demo
from codesynapse.ui.style import custom_css, theme

app = FastAPI(title="CodeSynapse")
app.include_router(router)

@app.exception_handler(limits.Limited)
def rate_limited(request: Request, error: limits.Limited):
    return JSONResponse({"detail": str(error)}, status_code=429, headers={"Retry-After": str(error.retry_after)})

@app.get("/health")
def health():
    return {"status": "ok"}

# Mounted last: the UI owns every path the API doesn't
app = gr.mount_gradio_app(app, demo.queue(), path="/", theme=theme, css=custom_css)
