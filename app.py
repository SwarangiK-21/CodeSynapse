import gradio as gr
import asyncio
import json
import pandas as pd
import plotly.express as px
from logic import fetchers, ai_coach, database
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# --- INITIALIZE DB ---
database.init_db()

# --- HELPER FUNCTIONS ---

async def fetch_data_logic(gh, lc, hr, gfg):
    """Fetches data and returns the stats text + the radar chart plot"""
    database.save_profile(gh, lc, hr, gfg)
    
    inputs = { "github": gh, "leetcode": lc, "hackerrank": hr, "gfg": gfg }
    results = await fetchers.get_all_stats(inputs)
    
    # 1. Format Stats
    stats_output = []
    radar_data = []
    
    for p in results:
        stats_text = f"### {p['platform'].upper()}\n"
        for k, v in p['stats'].items():
            stats_text += f"- **{k}**: {v}\n"
        stats_output.append(stats_text)
        
        radar_data.append({
            "Platform": p['platform'],
            "Score": p.get('score_norm', 50)
        })
    
    final_text = "\n\n".join(stats_output)
    
    # 2. Build Radar Chart (Cyberpunk Style)
    if radar_data:
        df = pd.DataFrame(radar_data)
        fig = px.line_polar(
            df, r='Score', theta='Platform', line_close=True,
            title="COMPETENCY RADAR", template="plotly_dark", range_r=[0, 100]
        )
        fig.update_traces(fill='toself', line_color='#00e5ff', fillcolor='rgba(0, 229, 255, 0.3)')
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
    filename = "/tmp/Career_Roadmap.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    try:
        # Password removed as requested!
        
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
    except: return None

async def chat_logic(message, history, context_data):
    """AI Coach Logic"""
    database.save_chat_message("user", message)
    response_json_str = await asyncio.to_thread(ai_coach.ask_gemini, message, context_data)
    try:
        data = json.loads(response_json_str)
        clean_text = data.get("advice", "No advice")
        actions = data.get("actions", [])
        final_response = clean_text + "\n\n" + "\n".join([f"• {a['step']}" for a in actions])
    except:
        final_response = response_json_str
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
with gr.Blocks(theme=theme, css=custom_css, title="CodeSynapse") as demo:
    fetched_data_state = gr.State(value=[])
    
    gr.Markdown("# 🎮 CodeSynapse \n *// CAREER ARCHITECTURE PROTOCOL_INITIALIZED*")
    
    with gr.Tabs():
        # TAB 1: DASHBOARD
        with gr.TabItem("DASHBOARD"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 1. IDENTITY UPLINK")
                    # HERE IS THE CHANGE: value="" makes them empty!
                    gh_in = gr.Textbox(label="GitHub ID", value="", placeholder="Enter GitHub ID...")
                    lc_in = gr.Textbox(label="LeetCode ID", value="", placeholder="Enter LeetCode ID...")
                    hr_in = gr.Textbox(label="HackerRank ID", value="", placeholder="Enter HackerRank ID...")
                    gfg_in = gr.Textbox(label="GeeksForGeeks ID", value="", placeholder="Enter GFG ID...")
                    
                    sync_btn = gr.Button("⚡ INITIALIZE SYNC", variant="primary")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 2. ANALYTICS MATRIX")
                    radar_plot = gr.Plot(label="Competency Radar")
                    stats_display = gr.Markdown("Waiting for Uplink...")
            
            with gr.Row():
                pdf_btn = gr.Button("📄 DOWNLOAD REPORT")
                pdf_out = gr.File(label="Download Report")

        # TAB 2: AI COACH
        with gr.TabItem("AI NEXUS"):
            chatbot = gr.ChatInterface(
                fn=lambda msg, hist: asyncio.run(chat_logic(msg, hist, fetched_data_state.value)),
                title="AI Nexus Coach",
                description="SYSTEM ONLINE. Ask about your stats, resume tips, or coding roadmaps."
            )

    # --- WIRING ---
    sync_btn.click(fetch_data_logic, [gh_in, lc_in, hr_in, gfg_in], [stats_display, radar_plot, fetched_data_state])
    pdf_btn.click(generate_pdf_logic, [fetched_data_state], [pdf_out])

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)