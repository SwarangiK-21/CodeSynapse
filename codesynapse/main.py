import gradio as gr
from fastapi import FastAPI
from codesynapse.api.routes import router
from codesynapse.ui.app import demo
from codesynapse.ui.style import custom_css, theme

app = FastAPI(title="CodeSynapse")
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}

# Mounted last: the UI owns every path the API doesn't
app = gr.mount_gradio_app(app, demo.queue(), path="/", theme=theme, css=custom_css)
