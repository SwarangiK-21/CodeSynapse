from types import SimpleNamespace
import pytest
from codesynapse.db.models import Analysis, JobDescription
from codesynapse.db.session import SessionLocal
from codesynapse.services import analyses, jobs, repos, users
from codesynapse.ui import app as ui
from codesynapse.ui import components

ATTACK = '<script>alert(1)</script>'

def citation(**overrides):
    return {"claim": "Retries on failure", "quote": "except TimeoutError:", "path": "src/retry.py", "start_line": 5,
            "url": "https://github.com/octocat/demo/blob/abc/src/retry.py#L5-L5", **overrides}

def skill(name="Retries", level="strong", importance="required", citations=None, missing=()):
    return {"name": name, "level": level, "importance": importance,
            "citations": [citation()] if citations is None else citations, "missing": list(missing)}

def report(**overrides):
    return {"job_title": "Engineer", "summary": "A summary.", "recommendations": [], "skills": [
        skill(), skill("Redis", "none", citations=[], missing=["No Redis usage"]),
        skill("Docker", "partial", "preferred"),
    ], **overrides}

def test_counts_required_skills_with_evidence():
    html = components.report_html(report(), "draft")
    assert "1/2" in html and "required skills with evidence" in html

def test_levels_are_shown_in_words_not_only_colour():
    html = components.report_html(report(), "draft")
    assert all(text in html for text in ("Strong evidence", "Some evidence", "Not found"))

def test_required_skills_come_first():
    html = components.report_html(report(skills=[skill("Docker", importance="preferred"), skill("Python")]), "draft")
    assert html.index("Python") < html.index("Docker")

def test_gaps_are_open_and_strong_skills_are_collapsed():
    assert " open" in components.skill_card(skill(level="none", citations=[]))
    assert " open" not in components.skill_card(skill(level="strong"))

def test_status_is_clear():
    assert "Draft" in components.report_html(report(), "draft")
    assert "Approved report" in components.report_html(report(), "approved")

def test_high_priority_recommendations_come_first():
    html = components.recommendations_html([
        {"skill": "Later", "priority": "low", "action": "a"}, {"skill": "First", "priority": "high", "action": "b"}])
    assert html.index("First") < html.index("Later")

@pytest.mark.parametrize("build", [
    lambda: components.report_html(report(job_title=ATTACK), "draft"),
    lambda: components.report_html(report(summary=ATTACK), "draft"),
    lambda: components.skill_card(skill(name=ATTACK)),
    lambda: components.skill_card(skill(missing=[ATTACK])),
    lambda: components.citation_html(citation(claim=ATTACK)),
    lambda: components.citation_html(citation(quote=ATTACK)),
    lambda: components.citation_html(citation(path=ATTACK)),
    lambda: components.recommendations_html([{"skill": ATTACK, "priority": "high", "action": "a"}]),
    lambda: components.recommendations_html([{"skill": "a", "priority": ATTACK, "action": "a"}]),
    lambda: components.recommendations_html([{"skill": "a", "priority": "high", "action": ATTACK}]),
    lambda: components.profile_html([{"platform": ATTACK, "stats": {}}]),
    lambda: components.profile_html([{"platform": "a", "stats": {ATTACK: ATTACK}}]),
    lambda: components.message_box(ATTACK),
])
def test_untrusted_text_is_escaped(build):
    html = build()
    assert ATTACK not in html and "&lt;script&gt;" in html

@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://evil.example/x", None, 'https://github.com/"onclick="x'])
def test_only_safe_github_links_work(url):
    html = components.safe_link(url, "file.py")
    if url and url.startswith("https://github.com/"):
        assert 'onclick="x' not in html
    else:
        assert "<a" not in html

def test_stage_tracker_marks_progress():
    html = components.stage_tracker(1)
    assert html.count("cs-stage-done") == 1 and html.count('aria-current="step"') == 1

def test_empty_profile_explains_what_to_do():
    assert "Sync your profiles" in components.profile_html([])

# --- REPORT VIEWS ---

def seed_analysis(token, status="draft"):
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        job = JobDescription(user_id=user.id, title="Engineer", raw_text="text", skills=[])
        db.add(job)
        db.flush()
        analysis = Analysis(user_id=user.id, job_id=job.id, repo_ids=[1], status=status, report=report())
        db.add(analysis)
        db.commit()
        return analysis.id

def new_token():
    with SessionLocal() as db:
        return users.create_user(db)[1]

def test_latest_report_returns_after_reload():
    token = new_token()
    analysis_id = seed_analysis(token)
    html, loaded_id, approve_button, download_button = ui.load_latest_report(token)
    assert "Engineer" in html and loaded_id == analysis_id
    assert approve_button["visible"] is True and download_button["visible"] is True

def test_failed_analysis_is_not_restored():
    token = new_token()
    seed_analysis(token, "failed")
    html, loaded_id, approve_button, _ = ui.load_latest_report(token)
    assert loaded_id is None and "will appear here" in html and approve_button["visible"] is False

def test_reports_stay_private():
    seed_analysis(new_token())
    assert ui.load_latest_report(new_token())[1] is None

def test_approving_hides_the_button_and_keeps_download():
    token = new_token()
    analysis_id = seed_analysis(token)
    html, _, approve_button, download_button = ui.approve_logic(token, analysis_id)
    assert "Approved report" in html
    assert approve_button["visible"] is False and download_button["visible"] is True

def test_empty_form_shows_a_clear_message():
    html, *_ = list(ui.run_agent_logic(new_token(), "", ""))[-1]
    assert "Enter a repository" in html

def test_bad_repository_shows_a_clear_message():
    html, *_ = list(ui.run_agent_logic(new_token(), "not a repo", "A long enough job description here."))[-1]
    assert "owner/repo" in html

def test_full_run_shows_each_stage_then_the_report(monkeypatch):
    def fake_index(db, user, value):
        return SimpleNamespace(id=1)
    def fake_job(db, user, text):
        return SimpleNamespace(id=1)
    token = new_token()
    analysis_id = seed_analysis(token)
    with SessionLocal() as db:
        saved = analyses.get_analysis(db, users.get_user_by_token(db, token), analysis_id)
    monkeypatch.setattr(repos, "index_repo", fake_index)
    monkeypatch.setattr(jobs, "create_job", fake_job)
    monkeypatch.setattr(analyses, "create_analysis", lambda db, user, job, ids: db.merge(saved))
    monkeypatch.setattr(analyses, "execute", lambda analysis: None)

    views = list(ui.run_agent_logic(token, "octocat/demo", "A long enough job description here."))
    assert len(views) == 4 and "aria-current" in views[0][0]
    assert "Engineer" in views[-1][0] and views[-1][1] == analysis_id

def test_failed_run_shows_the_reason(monkeypatch):
    token = new_token()
    analysis_id = seed_analysis(token, "failed")
    with SessionLocal() as db:
        saved = db.get(Analysis, analysis_id)
        saved.error = "The daily AI quota is used up."
        db.commit()
    monkeypatch.setattr(repos, "index_repo", lambda db, user, value: SimpleNamespace(id=1))
    monkeypatch.setattr(jobs, "create_job", lambda db, user, text: SimpleNamespace(id=1))
    monkeypatch.setattr(analyses, "create_analysis", lambda db, user, job, ids: db.get(Analysis, analysis_id))
    monkeypatch.setattr(analyses, "execute", lambda analysis: None)

    html, *_ = list(ui.run_agent_logic(token, "octocat/demo", "A long enough job description here."))[-1]
    assert "daily AI quota" in html
