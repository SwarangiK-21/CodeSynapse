import os
import tempfile
import gradio as gr
import pandas as pd
import plotly.express as px
from codesynapse import config
from codesynapse.db.session import SessionLocal
from codesynapse.services import analyses, chat, jobs, profiles, reports, repos, users
from codesynapse.ui import components

SAMPLE_REPO = "pallets/itsdangerous"
SAMPLE_JOB = """Python Developer. You must have strong Python and experience with cryptographic signing.
You will write automated tests with pytest and maintain GitHub Actions pipelines.
Experience with Redis caching is a bonus."""

# The finished report appears below the form, where it is easy to miss
SCROLL_TO_REPORT = "() => document.querySelector('.cs-report')?.scrollIntoView({block: 'start'})"

# --- HELPER FUNCTIONS ---

def build_chart(stats):
    # Platforms without real data stay off the chart
    rows = [{"Platform": p['platform'], "Score": p['score_norm']} for p in stats if p['score_norm'] is not None]
    if not rows:
        return None
    fig = px.bar(pd.DataFrame(rows), x='Score', y='Platform', orientation='h', range_x=[0, 100], height=220)
    fig.update_traces(marker_color='#14b8a6', width=0.5)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#64748b",
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title=None,
        xaxis_title="Score out of 100",
        xaxis_gridcolor="rgba(148,163,184,0.25)",
    )
    return fig

def require_user(db, token):
    user = users.get_user_by_token(db, token)
    if not user:
        raise gr.Error("Your session has expired. Please reload the page.")
    return user

def write_temp_file(prefix, suffix, data):
    # Unique file per download so users can't overwrite each other's reports
    fd, filename = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return filename

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
            components.profile_html(stats),
            build_chart(stats),
            chat.get_history(db, user),
        )

def fetch_data_logic(token, gh, lc):
    """Fetches data and returns the stats + the score chart"""
    with SessionLocal() as db:
        user = require_user(db, token)
        try:
            stats = profiles.sync_profile(db, user, gh, lc).stats
        except profiles.InvalidUsername as e:
            raise gr.Error(str(e))
    return components.profile_html(stats), build_chart(stats)

def generate_pdf_logic(token):
    """Generates PDF"""
    with SessionLocal() as db:
        stats = profiles.get_stats(db, require_user(db, token))
    if not stats:
        return None
    return write_temp_file("Career_Report_", ".pdf", reports.build_pdf(stats))

def chat_logic(message, history, token):
    """AI Coach Logic"""
    with SessionLocal() as db:
        return chat.send_message(db, require_user(db, token), message)

def clear_chat_logic(token):
    with SessionLocal() as db:
        chat.clear_history(db, require_user(db, token))

def report_view(analysis):
    """Returns the report, its id and the state of the buttons under it."""
    download = write_temp_file("Skill_Gap_Report_", ".md", analyses.to_markdown(analysis).encode("utf-8"))
    return (
        components.report_html(analysis.report, analysis.status),
        analysis.id,
        gr.update(visible=analysis.status == "draft"),
        gr.update(visible=True, value=download),
    )

def hidden_view(html):
    return html, None, gr.update(visible=False), gr.update(visible=False)

def load_latest_report(token):
    """Brings back this browser's most recent report after a reload."""
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        analysis = analyses.latest_report(db, user) if user else None
        return report_view(analysis) if analysis else hidden_view(components.empty_report())

def run_agent_logic(token, repo, job_text):
    """Indexes the repository, reads the job description and runs the agent, reporting each stage."""
    if not repo.strip() or len(job_text.strip()) < 20:
        yield hidden_view(components.message_box("Enter a repository and paste a job description.", "error"))
        return
    with SessionLocal() as db:
        user = require_user(db, token)
        try:
            yield hidden_view(components.stage_tracker(0))
            indexed = repos.index_repo(db, user, repo)
            yield hidden_view(components.stage_tracker(1))
            job = jobs.create_job(db, user, job_text)
            yield hidden_view(components.stage_tracker(2))
            analysis = analyses.create_analysis(db, user, job.id, [indexed.id])
        except (repos.RepoError, jobs.JobError, analyses.AnalysisError) as e:
            yield hidden_view(components.message_box(str(e), "error"))
            return

        analyses.execute(analysis.id)
        db.refresh(analysis)
        if analysis.status == "failed":
            yield hidden_view(components.message_box(analysis.error, "error"))
            return
        yield report_view(analysis)

def approve_logic(token, analysis_id):
    with SessionLocal() as db:
        analysis = analyses.get_analysis(db, require_user(db, token), analysis_id)
        if not analysis:
            raise gr.Error("Run an analysis first.")
        try:
            analyses.approve(db, analysis)
        except analyses.AnalysisError as e:
            raise gr.Error(str(e))
        return report_view(analysis)

# --- BUILD UI ---
with gr.Blocks(title="CodeSynapse") as demo:
    # The user's private token, kept in this browser so data survives a reload
    user_token = gr.BrowserState(None, storage_key="codesynapse_token", secret=config.UI_SECRET)

    gr.HTML("""<header class="cs-header">
      <h1>CodeSynapse</h1>
      <p>See how your real code matches the job you want.</p>
    </header>""")

    with gr.Tabs():
        # TAB 1: SKILL GAP ANALYSIS
        with gr.TabItem("Skill Gap"):
            gr.HTML('<p class="cs-intro">Compare a public GitHub repository with a job description.</p>')
            repo_in = gr.Textbox(label="GitHub repository", placeholder="owner/repo or a github.com link")
            job_in = gr.Textbox(label="Job description", lines=7, placeholder="Paste the job description here")
            with gr.Row():
                sample_btn = gr.Button("Try an example")
                run_btn = gr.Button("Analyse my code", variant="primary")
            agent_output = gr.HTML(components.empty_report())
            with gr.Row():
                approve_btn = gr.Button("Approve report", variant="primary", visible=False)
                download_btn = gr.DownloadButton("Download report", visible=False)
            analysis_id = gr.State(None)

        # TAB 2: CODING PROFILE
        with gr.TabItem("Profile"):
            gr.HTML('<p class="cs-intro">See your public GitHub and LeetCode stats in one place.</p>')
            with gr.Row():
                gh_in = gr.Textbox(label="GitHub username", value="", placeholder="octocat")
                lc_in = gr.Textbox(label="LeetCode username", value="", placeholder="your_username")
            sync_btn = gr.Button("Sync profiles", variant="primary")
            stats_display = gr.HTML(components.profile_html([]))
            score_plot = gr.Plot(label="Activity scores")
            with gr.Row():
                pdf_btn = gr.Button("Create PDF summary")
                pdf_out = gr.File(label="PDF summary")

        # TAB 3: CAREER COACH
        with gr.TabItem("Coach"):
            gr.HTML('<p class="cs-intro">Ask about your stats, your resume or what to learn next. '
                    'Sync your profiles first for advice based on your numbers.</p>')
            chatbot = gr.Chatbot(label="Career Coach", show_label=False, height=420,
                                 placeholder="Try: What should I focus on next?")
            gr.ChatInterface(fn=chat_logic, chatbot=chatbot, additional_inputs=[user_token])

    # --- WIRING ---
    demo.load(load_session, [user_token], [user_token, gh_in, lc_in, stats_display, score_plot, chatbot]).then(
        load_latest_report, [user_token], [agent_output, analysis_id, approve_btn, download_btn])
    sync_btn.click(fetch_data_logic, [user_token, gh_in, lc_in], [stats_display, score_plot])
    pdf_btn.click(generate_pdf_logic, [user_token], [pdf_out])
    sample_btn.click(lambda: (SAMPLE_REPO, SAMPLE_JOB), None, [repo_in, job_in])
    run_btn.click(run_agent_logic, [user_token, repo_in, job_in], [agent_output, analysis_id, approve_btn, download_btn]).then(
        None, None, None, js=SCROLL_TO_REPORT)
    approve_btn.click(approve_logic, [user_token, analysis_id], [agent_output, analysis_id, approve_btn, download_btn])
    chatbot.clear(clear_chat_logic, [user_token])
