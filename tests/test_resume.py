import io
import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from codesynapse.db.models import Analysis, JobDescription
from codesynapse.db.session import SessionLocal
from codesynapse.services import analyses, llm, resume, users

RESUME_LINES = [
    "Alex Example - alex@example.com - +91 90000 00000",
    "Implemented HMAC-based signing of tokens in Python",
    "Wrote automated tests with pytest",
    "Built caching layers with Redis",
]

def make_pdf(lines=RESUME_LINES, pages=1):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for _ in range(pages):
        for i, line in enumerate(lines):
            pdf.drawString(72, 750 - 18 * i, line)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()

def claim(skill, quote, category="tool"):
    return resume.ResumeClaim(skill=skill, category=category, quote=quote)

def fake_reply(claims):
    def generate_json(prompt, schema, usage=None, temperature=0.0):
        return resume.ParsedResume(claims=claims)
    return generate_json

TEXT = "\n".join(RESUME_LINES)
GOOD_CLAIMS = [claim("HMAC signing", "HMAC-based signing of tokens", "concept"),
               claim("pytest", "automated tests with pytest", "framework"),
               claim("Redis", "caching layers with Redis")]

# --- READING FILES ---

def test_reads_the_text_of_a_pdf():
    text = resume.pdf_text(make_pdf())
    assert "HMAC-based signing" in text and "pytest" in text

@pytest.mark.parametrize("data,message", [
    (b"not a pdf at all" * 20, "doesn't look like a PDF"),
    (b"%PDF" + b"0" * (resume.MAX_BYTES + 1), "larger than 5 MB"),
    (b"%PDF-1.7 broken", "couldn't be read"),
])
def test_unusable_files_get_a_clear_reason(data, message):
    with pytest.raises(resume.ResumeError, match=message):
        resume.pdf_text(data)

def test_a_locked_pdf_is_refused():
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(make_pdf())))
    writer.encrypt("secret")
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(resume.ResumeError, match="password-protected"):
        resume.pdf_text(buffer.getvalue())

def test_a_very_long_pdf_is_refused():
    with pytest.raises(resume.ResumeError, match="more than"):
        resume.pdf_text(make_pdf(pages=resume.MAX_PAGES + 1))

def test_a_scanned_resume_asks_for_pasted_text():
    with pytest.raises(resume.ResumeError, match="paste its text"):
        resume.pdf_text(make_pdf(lines=[]))

# --- FINDING CLAIMS ---

def test_only_claims_quoted_from_the_resume_are_kept():
    parsed = resume.ParsedResume(claims=[*GOOD_CLAIMS, claim("Kubernetes", "ran Kubernetes clusters"),
                                         claim("pytest", "automated tests with pytest")])
    kept = resume.verified_claims(parsed, TEXT)
    assert [c.skill for c in kept] == ["HMAC signing", "pytest", "Redis"]

def test_claims_are_capped_at_what_the_agent_checks():
    many = [claim(f"skill {i}", "Wrote automated tests") for i in range(30)]
    assert len(resume.verified_claims(resume.ParsedResume(claims=many), TEXT)) == resume.MAX_CLAIMS

def test_only_the_claims_are_stored_never_the_whole_resume(monkeypatch):
    monkeypatch.setattr(llm, "generate_json", fake_reply(GOOD_CLAIMS))
    with SessionLocal() as db:
        user, _ = users.create_user(db)
        record = resume.create_resume(db, user, TEXT, "cv.pdf")
        assert record.kind == "resume" and record.title == "Resume: cv.pdf"
        assert "alex@example.com" not in record.raw_text and "+91" not in record.raw_text
        assert [s["name"] for s in record.skills] == ["HMAC signing", "pytest", "Redis"]
        assert all(s["importance"] == "required" for s in record.skills)

def test_a_resume_without_technical_claims_is_explained(monkeypatch):
    monkeypatch.setattr(llm, "generate_json", fake_reply([]))
    with SessionLocal() as db:
        user, _ = users.create_user(db)
        with pytest.raises(resume.ResumeError, match="No technical claims"):
            resume.create_resume(db, user, TEXT)

def test_an_ai_outage_is_reported_separately(monkeypatch):
    def broken(*args, **kwargs):
        raise llm.LLMError("AI Service Error (503).")
    monkeypatch.setattr(llm, "generate_json", broken)
    with SessionLocal() as db:
        user, _ = users.create_user(db)
        with pytest.raises(resume.ResumeUnavailable):
            resume.create_resume(db, user, TEXT)

def test_the_latest_report_is_kept_apart_for_jobs_and_resumes():
    with SessionLocal() as db:
        user, _ = users.create_user(db)
        job = JobDescription(user_id=user.id, title="Job", raw_text="t", skills=[])
        cv = JobDescription(user_id=user.id, kind="resume", title="Resume", raw_text="t", skills=[])
        db.add_all([job, cv])
        db.flush()
        db.add_all([Analysis(user_id=user.id, job_id=job.id, repo_ids=[], status="draft"),
                    Analysis(user_id=user.id, job_id=cv.id, repo_ids=[], status="draft")])
        db.commit()
        assert analyses.latest_report(db, user).job_id == job.id
        assert analyses.latest_report(db, user, "resume").job_id == cv.id

# --- API ---

def test_upload_a_resume_pdf(client, auth, monkeypatch):
    monkeypatch.setattr(llm, "generate_json", fake_reply(GOOD_CLAIMS))
    response = client.post("/api/resumes", headers=auth(),
                           files={"file": ("cv.pdf", make_pdf(), "application/pdf")})
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "resume" and len(body["skills"]) == 3

def test_paste_resume_text(client, auth, monkeypatch):
    monkeypatch.setattr(llm, "generate_json", fake_reply(GOOD_CLAIMS))
    response = client.post("/api/resumes", headers=auth(), data={"text": TEXT})
    assert response.status_code == 201 and response.json()["title"] == "Resume: pasted text"

def test_resume_api_errors(client, auth, monkeypatch):
    headers = auth()
    assert client.post("/api/resumes", headers=headers).status_code == 422
    bad = client.post("/api/resumes", headers=headers, files={"file": ("cv.pdf", b"nope" * 50, "application/pdf")})
    assert bad.status_code == 422 and "PDF" in bad.json()["detail"]
    def broken(*args, **kwargs):
        raise llm.LLMError("AI Service Error (503).")
    monkeypatch.setattr(llm, "generate_json", broken)
    assert client.post("/api/resumes", headers=headers, data={"text": TEXT}).status_code == 503
    assert client.post("/api/resumes", data={"text": TEXT}).status_code == 401

# --- AGENT AND REPORT WORDING ---

def test_the_agent_is_told_it_is_checking_a_resume_claim():
    from codesynapse.agents import gap_analysis
    skill = {"name": "Redis", "quote": "caching layers with Redis"}
    assert "The resume claims" in gap_analysis.assess_prompt(skill, {}, "", "resume")
    assert "The job asks for" in gap_analysis.assess_prompt(skill, {}, "")
    results = {"Redis": {"level": "none", "missing": []}}
    prompt = gap_analysis.recommend_prompt({"kind": "resume", "title": "Resume"}, [skill], results)
    assert "resume" in prompt and "never that the" in prompt

def test_resume_report_wording():
    from codesynapse.ui import components
    report = {"kind": "resume", "job_title": "Resume: cv.pdf", "summary": "s", "recommendations": [],
              "skills": [{"name": "Redis", "importance": "required", "level": "none", "citations": [],
                          "missing": ["No Redis"], "job_quote": "caching layers with <Redis>"}]}
    html = components.report_html(report, "draft")
    assert "resume claims backed by code" in html and "Your resume says" in html
    assert "&lt;Redis&gt;" in html and "<Redis>" not in html
    assert "Resume claims checked" in html
    assert "claims on your resume" in components.empty_report("resume")
    assert "Check each claim" in components.stage_tracker(2, components.RESUME_STAGES)

def test_repository_list_parsing():
    from codesynapse.ui import app
    assert app.parse_repo_list("a/b, c/d\n a/b \n\n e/f") == ["a/b", "c/d", "e/f"]
    assert app.parse_repo_list("") == []
