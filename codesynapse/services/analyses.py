from sqlalchemy import select
from sqlalchemy.orm import Session
from codesynapse.agents import gap_analysis
from codesynapse.db.models import Analysis, JobDescription, Repo, User, utcnow
from codesynapse.db.session import SessionLocal
from codesynapse.services import llm, tasks

class AnalysisError(ValueError):
    pass

def create_analysis(db: Session, user: User, job_id, repo_ids):
    """Saves a pending analysis after checking this user owns the job and repositories."""
    job = db.scalar(select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id))
    if not job:
        raise AnalysisError("Job description not found.")
    if not job.skills:
        raise AnalysisError("No skills were found in that job description.")

    owned = {r.id: r for r in db.scalars(select(Repo).where(Repo.user_id == user.id, Repo.id.in_(repo_ids)))}
    if not repo_ids or set(owned) != set(repo_ids):
        raise AnalysisError("Repository not found.")
    if any(r.status != "ready" for r in owned.values()):
        raise AnalysisError("That repository isn't ready yet. Wait for indexing to finish.")

    analysis = Analysis(user_id=user.id, job_id=job.id, repo_ids=list(repo_ids))
    db.add(analysis)
    db.commit()
    return analysis

def execute(analysis_id):
    """Runs the agent. Uses its own session because it can outlive the web request."""
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        user = db.get(User, analysis.user_id)
        job = db.get(JobDescription, analysis.job_id)
        try:
            analysis.report, analysis.trace, analysis.usage = gap_analysis.run(
                db, user, {"title": job.title, "skills": job.skills}, analysis.repo_ids)
            analysis.status = "draft"
        except llm.LLMError as e:
            analysis.status, analysis.error = "failed", str(e)
        except Exception as e:
            print(f"Analysis Error: {e}")
            analysis.status, analysis.error = "failed", "The analysis stopped unexpectedly. Please try again."
        analysis.finished_at = utcnow()
        db.commit()

def start(analysis):
    tasks.submit(execute, analysis.id)

def get_analysis(db: Session, user: User, analysis_id):
    return db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id))

def latest_report(db: Session, user: User):
    """Returns this user's newest analysis that produced a report."""
    return db.scalar(
        select(Analysis).where(Analysis.user_id == user.id, Analysis.status.in_(("draft", "approved")))
        .order_by(Analysis.id.desc()).limit(1)
    )

def approve(db: Session, analysis):
    """A person signs off on the draft before it counts as a final report."""
    if analysis.status != "draft":
        raise AnalysisError("Only a finished draft can be approved.")
    analysis.status = "approved"
    db.commit()
    return analysis

def to_markdown(analysis):
    report = analysis.report
    lines = [f"# Skill gap report: {report['job_title']}", "", report["summary"], "", "## Skills", ""]
    for skill in report["skills"]:
        lines.append(f"### {skill['name']} ({skill['importance']}): {skill['level']}")
        lines.extend(f"- {c['claim']} ([{c['path']}:{c['start_line']}]({c['url']}))" for c in skill["citations"])
        if skill["missing"]:
            lines.append(f"- **Not found in the code searched:** {'; '.join(skill['missing'])}")
        lines.append("")
    if report["recommendations"]:
        lines.extend(["## Recommended next steps", ""])
        lines.extend(f"- **{r['skill']}** ({r['priority']}): {r['action']}" for r in report["recommendations"])
    return "\n".join(lines) + "\n"
