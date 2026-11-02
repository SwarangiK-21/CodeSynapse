import os
import tempfile
import gradio as gr
import pandas as pd
import plotly.express as px
from codesynapse import config
from codesynapse.db.session import SessionLocal
from codesynapse.services import chat, profiles, reports, users

# --- HELPER FUNCTIONS ---

def format_stats(stats):
    sections = []
    for p in stats:
        text = f"### {p['platform'].upper()}\n"
        for k, v in p['stats'].items():
            text += f"- **{k}**: {v}\n"
        sections.append(text)
    return "\n\n".join(sections)

def build_chart(stats):
    # Platforms without real data stay off the chart
    rows = [{"Platform": p['platform'], "Score": p['score_norm']} for p in stats if p['score_norm'] is not None]
    if not rows:
        return None
    fig = px.bar(
        pd.DataFrame(rows), x='Score', y='Platform', orientation='h',
        title="COMPETENCY SCORES", template="plotly_dark", range_x=[0, 100]
    )
    fig.update_traces(marker_color='rgba(0, 229, 255, 0.6)')
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#00e5ff",
        title_font_size=20
    )
    return fig

def require_user(db, token):
    user = users.get_user_by_token(db, token)
    if not user:
        raise gr.Error("Your session has expired. Please reload the page.")
    return user

def load_session(token):
    """Restores this browser's data, creating a user on the first visit."""
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        if not user:
            user, token = users.create_user(db)
        profile = profiles.get_profile(db, user)
        stats = profile.stats if profile else []
        return (
            token,
            profile.github if profile else "",
            profile.leetcode if profile else "",
            format_stats(stats) or "Waiting for Uplink...",
            build_chart(stats),
            chat.get_history(db, user),
        )

def fetch_data_logic(token, gh, lc):
    """Fetches data and returns the stats text + the score chart"""
    with SessionLocal() as db:
        user = require_user(db, token)
        try:
            stats = profiles.sync_profile(db, user, gh, lc).stats
        except profiles.InvalidUsername as e:
            raise gr.Error(str(e))
    return format_stats(stats), build_chart(stats)

def generate_pdf_logic(token):
    """Generates PDF"""
    with SessionLocal() as db:
        stats = profiles.get_stats(db, require_user(db, token))
    if not stats:
        return None
    # Unique file per download so users can't overwrite each other's reports
    fd, filename = tempfile.mkstemp(prefix="Career_Report_", suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(reports.build_pdf(stats))
    return filename

def chat_logic(message, history, token):
    """AI Coach Logic"""
    with SessionLocal() as db:
        return chat.send_message(db, require_user(db, token), message)

# --- CUSTOM THEME (Cyberpunk/Techie) ---
theme = gr.themes.Soft(
    primary_hue="cyan",
    secondary_hue="cyan",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_950",
    block_background_fill="*neutral_900",
    block_border_width="1px",
    block_border_color="*primary_500",
    input_background_fill="*neutral_800",
    button_primary_background_fill="*primary_600",
    button_primary_text_color="white",
)

# --- CUSTOM CSS ---
custom_css = """
body { background-color: #0b0f19; }
h1 { color: #00e5ff; font-family: 'Courier New', monospace; text-align: center; text-shadow: 0 0 10px #00e5ff; }
gradio-app { background-color: #0b0f19 !important; }
.contain { background-color: #0b0f19 !important; }
"""

# --- BUILD UI ---
with gr.Blocks(title="CodeSynapse") as demo:
    # The user's private token, kept in this browser so data survives a reload
    user_token = gr.BrowserState(None, storage_key="codesynapse_token", secret=config.UI_SECRET)

    gr.Markdown("# 🎮 CodeSynapse \n *// CAREER ARCHITECTURE PROTOCOL_INITIALIZED*")

    with gr.Tabs():
        # TAB 1: DASHBOARD
        with gr.TabItem("DASHBOARD"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 1. IDENTITY UPLINK")
                    gh_in = gr.Textbox(label="GitHub ID", value="", placeholder="Enter GitHub ID...")
                    lc_in = gr.Textbox(label="LeetCode ID", value="", placeholder="Enter LeetCode ID...")

                    sync_btn = gr.Button("⚡ INITIALIZE SYNC", variant="primary")

                with gr.Column(scale=2):
                    gr.Markdown("### 2. ANALYTICS MATRIX")
                    score_plot = gr.Plot(label="Competency Scores")
                    stats_display = gr.Markdown("Waiting for Uplink...")

            with gr.Row():
                pdf_btn = gr.Button("📄 DOWNLOAD REPORT")
                pdf_out = gr.File(label="Download Report")

        # TAB 2: AI COACH
        with gr.TabItem("AI NEXUS"):
            chatbot = gr.Chatbot(label="AI Nexus Coach")
            gr.ChatInterface(
                fn=chat_logic,
                chatbot=chatbot,
                additional_inputs=[user_token],
                title="AI Nexus Coach",
                description="SYSTEM ONLINE. Ask about your stats, resume tips, or coding roadmaps."
            )

    # --- WIRING ---
    demo.load(load_session, [user_token], [user_token, gh_in, lc_in, stats_display, score_plot, chatbot])
    sync_btn.click(fetch_data_logic, [user_token, gh_in, lc_in], [stats_display, score_plot])
    pdf_btn.click(generate_pdf_logic, [user_token], [pdf_out])
