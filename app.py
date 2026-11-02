import gradio as gr
import asyncio
import json
import pandas as pd
import plotly.express as px
from logic import fetchers, ai_coach, database
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import tempfile

# --- INITIALIZE DB ---
database.init_db()

# --- HELPER FUNCTIONS ---

async def fetch_data_logic(gh, lc):
    """Fetches data and returns the stats text + the score chart"""
    database.save_profile(gh, lc)

    inputs = { "github": gh, "leetcode": lc }
    results = await fetchers.get_all_stats(inputs)

    # 1. Format Stats
    stats_output = []
    chart_data = []

    for p in results:
        stats_text = f"### {p['platform'].upper()}\n"
        for k, v in p['stats'].items():
            stats_text += f"- **{k}**: {v}\n"
        stats_output.append(stats_text)
        
        # Platforms without real data stay off the chart
        if p['score_norm'] is not None:
            chart_data.append({
                "Platform": p['platform'],
                "Score": p['score_norm']
            })

    final_text = "\n\n".join(stats_output)

    # 2. Build Score Chart (Cyberpunk Style)
    if chart_data:
        df = pd.DataFrame(chart_data)
        fig = px.bar(
            df, x='Score', y='Platform', orientation='h',
            title="COMPETENCY SCORES", template="plotly_dark", range_x=[0, 100]
        )
        fig.update_traces(marker_color='rgba(0, 229, 255, 0.6)')
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#00e5ff",
            title_font_size=20
        )
    else:
        fig = None
        
    return final_text, fig, results

def generate_pdf_logic(results_cache):
    """Generates PDF (No Password)"""
    if not results_cache: return None 
    # Unique file per download so users can't overwrite each other's reports
    fd, filename = tempfile.mkstemp(prefix="Career_Report_", suffix=".pdf")
    os.close(fd)
    c = canvas.Canvas(filename, pagesize=letter)
    try:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "CodeSynapse: Career Report")
        y = 700
        for p in results_cache:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, y, f"Platform: {p['platform']}")
            y -= 20
            c.setFont("Helvetica", 12)
            for k, v in p['stats'].items():
                c.drawString(120, y, f"- {k}: {v}")
                y -= 15
            y -= 15
        c.save()
        return filename
    except Exception as e:
        print(f"PDF Error: {e}")
        return None

async def chat_logic(message, history, context_data):
    """AI Coach Logic"""
    database.save_chat_message("user", message)
    response_json_str = await asyncio.to_thread(ai_coach.ask_gemini, message, context_data)
    try:
        data = json.loads(response_json_str)
        clean_text = data.get("advice", "No advice")
        actions = data.get("actions", [])
        final_response = clean_text + "\n\n" + "\n".join([f"• {a['step']}" for a in actions])
    except (json.JSONDecodeError, AttributeError, KeyError, TypeError) as e:
        print(f"AI Reply Error: {e}")
        final_response = "Sorry, the AI sent back an unreadable reply. Please try again."
    database.save_chat_message("ai", final_response)
    return final_response

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
    fetched_data_state = gr.State(value=[])
    
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
            chatbot = gr.ChatInterface(
                fn=chat_logic,
                additional_inputs=[fetched_data_state],
                title="AI Nexus Coach",
                description="SYSTEM ONLINE. Ask about your stats, resume tips, or coding roadmaps."
            )

    # --- WIRING ---
    sync_btn.click(fetch_data_logic, [gh_in, lc_in], [stats_display, score_plot, fetched_data_state])
    pdf_btn.click(generate_pdf_logic, [fetched_data_state], [pdf_out])

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, theme=theme, css=custom_css)