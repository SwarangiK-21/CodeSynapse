"""Builds the HTML shown in the UI.

Report text comes from repositories and the AI, so it is untrusted: everything passes
through esc() before reaching the page.
"""
from html import escape

LEVELS = {
    "strong": ("Strong evidence", "strong"),
    "partial": ("Some evidence", "partial"),
    "none": ("Not found", "none"),
}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
STAGES = ["Read the repository", "Read the job description", "Analyse and verify the evidence"]
RESUME_STAGES = ["Read your repositories", "Find the claims in your resume", "Check each claim against your code"]

def esc(value):
    return escape(str(value), quote=True)

def safe_link(url, label):
    """Only links to GitHub are rendered as links."""
    if isinstance(url, str) and url.startswith("https://github.com/"):
        return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'
    return esc(label)

def message_box(text, kind="info"):
    return f'<div class="cs-message cs-message-{esc(kind)}" role="status">{esc(text)}</div>'

def account_html(github_login, configured):
    """The GitHub sign-in area: who is signed in, or the button, or nothing when not set up."""
    if github_login:
        return (f'<div class="cs-account"><span>Signed in with GitHub as <strong>@{esc(github_login)}</strong></span>'
                '<span class="cs-muted">Your reports and profile follow you to any device you sign in on.</span></div>')
    if not configured:
        return ""
    # target=_top leaves the Hugging Face page frame, which GitHub's sign-in page refuses to load inside
    return ('<div class="cs-account"><span>Keep your reports and profile on every device.</span>'
            '<a class="cs-github-btn" href="/auth/github/login" target="_top">Sign in with GitHub</a></div>')

def empty_report(kind="job"):
    if kind == "resume":
        art, text = "📄🔍", "Each technical claim on your resume is checked against your code, with links to the exact lines."
    else:
        art, text = "🔍✨", "Each skill in the job description is checked against your code, with links to the exact lines."
    return f"""<div class="cs-empty">
      <div class="cs-empty-art" aria-hidden="true">{art}</div>
      <h3>Your report will appear here</h3>
      <p>{text}</p>
    </div>"""

def stage_tracker(active, stages=STAGES):
    """Shows which stage is running. Stages before `active` are finished."""
    items = []
    for index, label in enumerate(stages):
        state = "done" if index < active else "active" if index == active else "waiting"
        mark = "✓" if state == "done" else index + 1
        current =' aria-current="step"' if state == "active" else ""
        items.append(f'<li class="cs-stage cs-stage-{state}"{current}><span class="cs-stage-mark">{mark}</span>{esc(label)}</li>')
    note = "This usually takes a few minutes. Keep this page open."
    stages = f'<ol class="cs-stages">{"".join(items)}</ol>'
    return f'<div class="cs-progress" role="status">{stages}<p class="cs-muted">{note}</p></div>'

def citation_html(citation):
    label = f"{citation['path']}:{citation['start_line']}"
    return f"""<li class="cs-citation">
      <p>{esc(citation['claim'])}</p>
      <p class="cs-source">{safe_link(citation.get('url'), label)}</p>
      <pre><code>{esc(citation['quote'])}</code></pre>
    </li>"""

def confidence_tag(value):
    """How likely the skill is really present, from the calibrated confidence model."""
    if not isinstance(value, (int, float)):
        return ""
    percent = round(min(max(value, 0), 1) * 100)
    title = "Calibrated estimate that this skill is really present, from the evidence checks"
    return f'<span class="cs-confidence" title="{title}">{percent}% likely</span>'

def skill_card(skill, resume=False):
    text, css = LEVELS.get(skill["level"], LEVELS["none"])
    citations = "".join(citation_html(c) for c in skill["citations"])
    evidence = f'<ul class="cs-citations">{citations}</ul>' if citations else ""
    gaps = "".join(f"<li>{esc(item)}</li>" for item in skill["missing"])
    not_found = f'<div class="cs-gaps"><h5>Not found in the code searched</h5><ul>{gaps}</ul></div>' if gaps else ""
    count = len(skill["citations"])
    summary_note = f"{count} code reference{'' if count == 1 else 's'}" if count else ""
    said = f'<p class="cs-said">Your resume says: "{esc(skill["job_quote"])}"</p>' if resume and skill.get("job_quote") else ""
    opened = " open" if skill["level"] != "strong" else ""
    return f"""<details class="cs-skill"{opened}>
      <summary>
        <span class="cs-skill-name">{esc(skill['name'])}</span>
        <span class="cs-tag">{esc(skill['importance'])}</span>
        {confidence_tag(skill.get("confidence"))}
        <span class="cs-count">{summary_note}</span>
        <span class="cs-badge cs-badge-{css}">{text}</span>
      </summary>
      <div class="cs-skill-body">{said}{evidence}{not_found}</div>
    </details>"""

def stat(value, label, css=""):
    return f'<div class="cs-stat {css}"><span class="cs-stat-value">{value}</span><span>{esc(label)}</span></div>'

def recommendations_html(recommendations):
    if not recommendations:
        return ""
    ordered = sorted(recommendations, key=lambda r: PRIORITY_ORDER.get(r["priority"], 3))
    items = "".join(
        f"""<li><span class="cs-priority cs-priority-{esc(r['priority'])}">{esc(r['priority'])}</span>
        <div><strong>{esc(r['skill'])}</strong><p>{esc(r['action'])}</p></div></li>"""
        for r in ordered
    )
    return f'<h3>Recommended next steps</h3><ol class="cs-actions">{items}</ol>'

def report_html(report, status):
    resume = report.get("kind") == "resume"
    skills = sorted(report["skills"], key=lambda s: s["importance"] != "required")
    levels = [s["level"] for s in skills]
    required = [s for s in skills if s["importance"] == "required"]
    matched = sum(1 for s in required if s["level"] != "none")
    state = "Approved report" if status == "approved" else "Draft: review the evidence, then approve this report"
    heading = "Resume claims checked against your code" if resume else esc(report["job_title"])
    main_stat = "resume claims backed by code" if resume else "required skills with evidence"
    note = ("Findings come from searching these repositories, so \"not found\" means no proof was found in public code, "
            "not that the claim is untrue." if resume else
            "Findings come from searching this repository, so \"not found\" means no evidence was found, "
            "not that you lack the skill.")
    return f"""<article class="cs-report">
      <p class="cs-state cs-state-{esc(status)}">{state}</p>
      <h2>{heading}</h2>
      <p class="cs-summary">{esc(report['summary'])}</p>
      <div class="cs-stats">
        {stat(f"{matched}/{len(required)}", main_stat, "cs-stat-main")}
        {stat(levels.count("strong"), "strong")}
        {stat(levels.count("partial"), "some evidence")}
        {stat(levels.count("none"), "not found")}
      </div>
      <h3>{"Claims" if resume else "Skills"}</h3>
      {"".join(skill_card(s, resume) for s in skills)}
      {recommendations_html(report["recommendations"])}
      <p class="cs-muted">{note}</p>
    </article>"""

def profile_html(stats):
    if not stats:
        return '<p class="cs-muted">Sync your profiles to see your stats here.</p>'
    cards = []
    for platform in stats:
        rows = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in platform["stats"].items())
        cards.append(f'<section class="cs-profile"><h4>{esc(platform["platform"])}</h4><dl>{rows}</dl></section>')
    return f'<div class="cs-profiles">{"".join(cards)}</div>'
