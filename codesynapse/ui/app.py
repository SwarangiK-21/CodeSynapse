import os
import tempfile
import time
import gradio as gr
import pandas as pd
import plotly.express as px
from codesynapse import config
from codesynapse.db.session import SessionLocal
from codesynapse.services import analyses, chat, jobs, limits, profiles, reports, repos, resume, users
from codesynapse.ui import components
from codesynapse.ui.style import RESTORE_THEME, TOGGLE_THEME

# How often to check on a background job, and when to give up waiting
POLL_SECONDS = 2
MAX_WAIT_SECONDS = 30 * 60

SAMPLE_REPO = "pallets/itsdangerous"
SAMPLE_JOB = """Python Developer. You must have strong Python and experience with cryptographic signing.
You will write automated tests with pytest and maintain GitHub Actions pipelines.
Experience with Redis caching is a bonus."""

MAX_RESUME_REPOS = 3
SAMPLE_RESUME_REPO = "pallets/itsdangerous"
# A made-up resume: some claims the sample repository proves, some it doesn't
SAMPLE_RESUME = """Alex Example, Backend Developer
Skills
- Implemented HMAC-based signing of tokens and cookies in Python
- Wrote automated tests with pytest and kept CI green with GitHub Actions
- Used Python type hints across the codebase
- Built caching layers with Redis
- Deployed services on Kubernetes"""

# The finished report appears below the form, where it is easy to miss
SCROLL_TO_REPORT = "() => document.querySelector('.cs-report')?.scrollIntoView({block: 'start'})"

# --- HELPER FUNCTIONS ---

def build_chart(stats):
    # Platforms without real data stay off the chart
    rows = [{"Platform": p['platform'], "Score": p['score_norm']} for p in stats if p['score_norm'] is not None]
    if not rows:
        return None
    fig = px.bar(pd.DataFrame(rows), x='Score', y='Platform', orientation='h', range_x=[0, 100], height=220)
    fig.update_traces(marker_color='#a7d3e8', marker_line_color='#7fb8d4', marker_line_width=1.5, width=0.5)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#7d8c8d",
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title=None,
        xaxis_title="Score out of 100",
        xaxis_gridcolor="rgba(127,184,212,0.25)",
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

def load_session(token, request: gr.Request = None):
    """Restores this browser's data, creating a user on the first visit."""
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        if not user:
            address = request.client.host if request and request.client else "unknown"
            try:
                limits.check("signup", address)
            except limits.Limited as e:
                raise gr.Error(str(e))
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
        user = require_user(db, token)
        try:
            limits.check("chat", user.id)
        except limits.Limited as e:
            return str(e)
        return chat.send_message(db, user, message)

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

def wait_while(db, record, busy_status):
    """Waits for a background job to move on from busy_status."""
    started = time.monotonic()
    db.refresh(record)
    while record.status == busy_status:
        if time.monotonic() - started > MAX_WAIT_SECONDS:
            raise TimeoutError("This is taking longer than expected. Reload the page later to see the result.")
        time.sleep(POLL_SECONDS)
        db.refresh(record)

def run_agent_logic(token, repo, job_text):
    """Indexes the repository, reads the job description and runs the agent, reporting each stage."""
    if not repo.strip() or len(job_text.strip()) < 20:
        yield hidden_view(components.message_box("Enter a repository and paste a job description.", "error"))
        return
    with SessionLocal() as db:
        user = require_user(db, token)
        try:
            limits.check("analysis", user.id)
            yield hidden_view(components.stage_tracker(0))
            indexed = repos.start_index(db, user, repo)
            wait_while(db, indexed, "indexing")
            if indexed.status == "failed":
                yield hidden_view(components.message_box(indexed.error, "error"))
                return
            yield hidden_view(components.stage_tracker(1))
            job = jobs.create_job(db, user, job_text)
            yield hidden_view(components.stage_tracker(2))
            analysis = analyses.create_analysis(db, user, job.id, [indexed.id])
        except (repos.RepoError, jobs.JobError, analyses.AnalysisError, limits.Limited, TimeoutError) as e:
            yield hidden_view(components.message_box(str(e), "error"))
            return

        analyses.start(analysis)
        try:
            wait_while(db, analysis, "running")
        except TimeoutError as e:
            yield hidden_view(components.message_box(str(e), "error"))
            return
        if analysis.status == "failed":
            yield hidden_view(components.message_box(analysis.error, "error"))
            return
        yield report_view(analysis)

def parse_repo_list(text):
    """Splits repositories given one per line or separated by commas, keeping their order."""
    names = [part.strip() for part in (text or "").replace(",", "\n").split("\n")]
    return list(dict.fromkeys(name for name in names if name))

def read_resume(file_path, text):
    """Returns the resume's text and a name for it, from an uploaded PDF or pasted text."""
    if file_path:
        with open(file_path, "rb") as f:
            data = f.read(resume.MAX_BYTES + 1)
        return resume.pdf_text(data), os.path.basename(file_path)
    return resume.check_text(text), "pasted text"

def load_latest_resume_report(token):
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        analysis = analyses.latest_report(db, user, "resume") if user else None
        return report_view(analysis) if analysis else hidden_view(components.empty_report("resume"))

def run_resume_logic(token, file_path, text, repo_text):
    """Reads the resume, indexes the repositories, then checks every claim against the code."""
    names = parse_repo_list(repo_text)
    if not names or not (file_path or (text or "").strip()):
        yield hidden_view(components.message_box("Add your repositories and upload or paste your resume.", "error"))
        return
    if len(names) > MAX_RESUME_REPOS:
        yield hidden_view(components.message_box(f"Choose up to {MAX_RESUME_REPOS} repositories.", "error"))
        return
    stages = components.RESUME_STAGES
    with SessionLocal() as db:
        user = require_user(db, token)
        try:
            limits.check("analysis", user.id)
            # Read the file first: a bad PDF should fail before the slow indexing starts
            content, name = read_resume(file_path, text)
            yield hidden_view(components.stage_tracker(0, stages))
            indexed = [repos.start_index(db, user, repo) for repo in names]
            for repo in indexed:
                wait_while(db, repo, "indexing")
                if repo.status == "failed":
                    yield hidden_view(components.message_box(f"{repo.full_name}: {repo.error}", "error"))
                    return
            yield hidden_view(components.stage_tracker(1, stages))
            record = resume.create_resume(db, user, content, name)
            yield hidden_view(components.stage_tracker(2, stages))
            analysis = analyses.create_analysis(db, user, record.id, [r.id for r in indexed])
        except (repos.RepoError, resume.ResumeError, analyses.AnalysisError, limits.Limited, TimeoutError) as e:
            yield hidden_view(components.message_box(str(e), "error"))
            return

        analyses.start(analysis)
        try:
            wait_while(db, analysis, "running")
        except TimeoutError as e:
            yield hidden_view(components.message_box(str(e), "error"))
            return
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

    with gr.Row(elem_classes="cs-topbar"):
        gr.HTML("""<header class="cs-header">
          <div class="cs-logo"><span class="cs-logo-mark" aria-hidden="true">✦</span>CodeSynapse</div>
          <h1>Your code, your proof.</h1>
          <p>See how your real code matches the job you want, with every skill backed by the exact lines.</p>
          <div class="cs-chips">
            <span class="cs-chip cs-chip-blue">🤖 AI agent</span>
            <span class="cs-chip cs-chip-mint">🔗 Line-level proof</span>
            <span class="cs-chip cs-chip-sand">🛡️ No made-up claims</span>
          </div>
        </header>""")
        theme_btn = gr.Button("Switch light or dark mode", elem_id="cs-theme-toggle", scale=0, min_width=52)

    with gr.Tabs(elem_classes="cs-tabs"):
        # TAB 1: SKILL GAP ANALYSIS
        with gr.TabItem("🎯 Skill Gap"):
            gr.HTML('<p class="cs-intro"><span class="cs-intro-emoji" aria-hidden="true">🧩</span>'
                    'Compare a public GitHub repository with a job description.</p>')
            repo_in = gr.Textbox(label="GitHub repository", placeholder="owner/repo or a github.com link")
            job_in = gr.Textbox(label="Job description", lines=7, placeholder="Paste the job description here")
            with gr.Row():
                sample_btn = gr.Button("✨ Try an example")
                run_btn = gr.Button("Analyse my code 🚀", variant="primary")
            agent_output = gr.HTML(components.empty_report())
            with gr.Row():
                approve_btn = gr.Button("Approve report", variant="primary", visible=False)
                download_btn = gr.DownloadButton("Download report", visible=False)
            analysis_id = gr.State(None)

        # TAB 2: RESUME CHECK
        with gr.TabItem("📄 Resume Check"):
            gr.HTML('<p class="cs-intro"><span class="cs-intro-emoji" aria-hidden="true">🔎</span>'
                    'Check the technical claims on your resume against your public code.</p>')
            resume_file = gr.File(label="Resume (PDF)", file_types=[".pdf"], type="filepath")
            resume_text = gr.Textbox(label="Or paste your resume text", lines=5,
                                     placeholder="Paste the text if your resume is a scanned image")
            resume_repos = gr.Textbox(label=f"Your GitHub repositories (up to {MAX_RESUME_REPOS})", lines=2,
                                      placeholder="owner/repo, one per line or separated by commas")
            gr.HTML('<p class="cs-muted">Your resume is sent to the AI once to find its claims. Only the '
                    'claims are kept: not your name, contact details or the rest of the file.</p>')
            with gr.Row():
                resume_sample_btn = gr.Button("✨ Try an example")
                resume_run_btn = gr.Button("Check my claims 🔍", variant="primary")
            resume_output = gr.HTML(components.empty_report("resume"))
            with gr.Row():
                resume_approve_btn = gr.Button("Approve report", variant="primary", visible=False)
                resume_download_btn = gr.DownloadButton("Download report", visible=False)
            resume_analysis_id = gr.State(None)

        # TAB 3: CODING PROFILE
        with gr.TabItem("📊 Profile"):
            gr.HTML('<p class="cs-intro"><span class="cs-intro-emoji" aria-hidden="true">📈</span>'
                    'See your public GitHub and LeetCode stats in one place.</p>')
            with gr.Row():
                gh_in = gr.Textbox(label="GitHub username", value="", placeholder="octocat")
                lc_in = gr.Textbox(label="LeetCode username", value="", placeholder="your_username")
            sync_btn = gr.Button("Sync profiles 🔄", variant="primary")
            stats_display = gr.HTML(components.profile_html([]))
            score_plot = gr.Plot(label="Activity scores")
            with gr.Row():
                pdf_btn = gr.Button("Create PDF summary")
                pdf_out = gr.File(label="PDF summary")

        # TAB 4: CAREER COACH
        with gr.TabItem("💬 Coach"):
            gr.HTML('<p class="cs-intro"><span class="cs-intro-emoji" aria-hidden="true">💡</span>'
                    'Ask about your stats, your resume or what to learn next. '
                    'Sync your profiles first for advice based on your numbers.</p>')
            chatbot = gr.Chatbot(label="Career Coach", show_label=False, height=420,
                                 placeholder="Try: What should I focus on next?")
            gr.ChatInterface(fn=chat_logic, chatbot=chatbot, additional_inputs=[user_token])

    # --- WIRING ---
    demo.load(None, None, None, js=RESTORE_THEME)
    theme_btn.click(None, None, None, js=TOGGLE_THEME)
    demo.load(load_session, [user_token], [user_token, gh_in, lc_in, stats_display, score_plot, chatbot]).then(
        load_latest_report, [user_token], [agent_output, analysis_id, approve_btn, download_btn]).then(
        load_latest_resume_report, [user_token],
        [resume_output, resume_analysis_id, resume_approve_btn, resume_download_btn])
    sync_btn.click(fetch_data_logic, [user_token, gh_in, lc_in], [stats_display, score_plot])
    pdf_btn.click(generate_pdf_logic, [user_token], [pdf_out])
    sample_btn.click(lambda: (SAMPLE_REPO, SAMPLE_JOB), None, [repo_in, job_in])
    run_btn.click(run_agent_logic, [user_token, repo_in, job_in], [agent_output, analysis_id, approve_btn, download_btn]).then(
        None, None, None, js=SCROLL_TO_REPORT)
    approve_btn.click(approve_logic, [user_token, analysis_id], [agent_output, analysis_id, approve_btn, download_btn])
    resume_outputs = [resume_output, resume_analysis_id, resume_approve_btn, resume_download_btn]
    resume_sample_btn.click(lambda: (None, SAMPLE_RESUME, SAMPLE_RESUME_REPO), None,
                            [resume_file, resume_text, resume_repos])
    resume_run_btn.click(run_resume_logic, [user_token, resume_file, resume_text, resume_repos], resume_outputs).then(
        None, None, None, js=SCROLL_TO_REPORT)
    resume_approve_btn.click(approve_logic, [user_token, resume_analysis_id], resume_outputs)
    chatbot.clear(clear_chat_logic, [user_token])
