"""Runs the evaluation. Finished repositories are skipped, so it can resume after a quota stop.

    python -m evals.run agent
    python -m evals.run baseline
    python -m evals.run injection
    python -m evals.run report
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / ".cache"
RESULTS = ROOT / "results"
CACHE.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)
# The index is slow to build, so it is kept apart from the app's data and reused
os.environ["DATABASE_URL"] = f"sqlite:///{(CACHE / 'eval.db').as_posix()}"

from sqlalchemy import select
from codesynapse.db.migrate import upgrade
from codesynapse.db.models import User
from codesynapse.db.session import SessionLocal
from codesynapse.services import llm, repos, users
from codesynapse.agents import gap_analysis
from evals import baseline, check_labels, injection, metrics

def result_file(system):
    return RESULTS / f"{system}.jsonl"

def finished(system):
    path = result_file(system)
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return {row["repo"]: row for row in rows}

def save(system, row):
    with result_file(system).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

def eval_user(db):
    user = db.scalar(select(User))
    return user or users.create_user(db)[0]

def indexed_repo(db, user, case):
    """Reuses the index when its vectors are complete. Rate limits can leave some unfinished."""
    existing = next((r for r in repos.list_repos(db, user) if r["full_name"] == case["repo"]), None)
    if existing and existing["commit_sha"] == case["commit"] and existing["embedded_chunks"] == existing["chunks"]:
        return existing["id"]
    started = time.time()
    repo = repos.index_repo(db, user, case["repo"], case["commit"])
    print(f"indexed {case['repo']} in {round(time.time() - started)}s", flush=True)
    return repo.id

def job_for(case):
    skills = [{"name": s["name"], "category": "tool", "importance": "required", "quote": s["name"]} for s in case["skills"]]
    return {"title": "Evaluation", "skills": skills}

def run_agent(db, user, case, repo_id):
    report, trace, usage = gap_analysis.run(db, user, job_for(case), [repo_id])
    return {
        "levels": {s["name"]: s["level"] for s in report["skills"]},
        "citations": [c for s in report["skills"] for c in s["citations"]],
        "rejected_claims": sum(s["rejected_claims"] for s in report["skills"]),
        "retried": [t["step"] for t in trace].count("assess") - 1,
        "usage": usage,
    }

def run_baseline(db, user, case, repo_id):
    levels, usage = baseline.run(db, user, repo_id, job_for(case)["skills"])
    return {"levels": levels, "citations": [], "rejected_claims": 0, "retried": 0,
            "usage": {"llm_calls": usage.calls, "prompt_tokens": usage.prompt_tokens, "output_tokens": usage.output_tokens}}

def run_system(system):
    runner = {"agent": run_agent, "baseline": run_baseline}[system]
    upgrade()
    done = finished(system)
    with SessionLocal() as db:
        user = eval_user(db)
        for case in check_labels.load_cases():
            if case["repo"] in done:
                continue
            repo_id = indexed_repo(db, user, case)
            started = time.time()
            try:
                row = runner(db, user, case, repo_id)
            except llm.LLMError as e:
                print(f"stopped at {case['repo']}: {e}. Run again to resume.")
                return 1
            row.update(repo=case["repo"], seconds=round(time.time() - started))
            save(system, row)
            print(f"finished {case['repo']} in {row['seconds']}s", flush=True)
    return 0

def rows_for(system):
    done = finished(system)
    rows = []
    for case in check_labels.load_cases():
        if case["repo"] in done:
            for skill in case["skills"]:
                rows.append({"repo": case["repo"], "skill": skill["name"], "expected": skill["present"],
                             "level": done[case["repo"]]["levels"].get(skill["name"], "none")})
    return rows

def system_report(system):
    rows = rows_for(system)
    done = finished(system)
    files = {}
    citations = []
    for case in check_labels.load_cases():
        if case["repo"] in done and done[case["repo"]]["citations"]:
            repo_files = check_labels.load_files(case["repo"], case["commit"])
            for citation in done[case["repo"]]["citations"]:
                files[citation["path"]] = repo_files.get(citation["path"])
                citations.append(citation)
    usage = [r["usage"] for r in done.values()]
    return {
        "repos": len(done),
        "presence": metrics.score(rows),
        "citations": metrics.citation_score(citations, {k: v for k, v in files.items() if v is not None}),
        "rejected_claims": sum(r["rejected_claims"] for r in done.values()),
        "retried_repos": sum(1 for r in done.values() if r["retried"] > 0),
        "llm_calls": sum(u["llm_calls"] for u in usage),
        "tokens": sum(u["prompt_tokens"] + u["output_tokens"] for u in usage),
        "seconds_per_repo": round(sum(r["seconds"] for r in done.values()) / len(done)) if done else 0,
        "errors": [{k: r[k] for k in ("repo", "skill", "expected", "level")} for r in metrics.errors(rows)],
    }

def report():
    summary = {system: system_report(system) for system in ("agent", "baseline")}
    path = result_file("injection")
    if path.exists():
        attacks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        summary["injection"] = {"attacks": len(attacks), "blocked": sum(a["blocked"] for a in attacks), "rows": attacks}
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0

def run_injection():
    result_file("injection").unlink(missing_ok=True)
    for row in injection.run():
        save("injection", row)
    return 0

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command in ("agent", "baseline"):
        sys.exit(run_system(command))
    if command == "injection":
        sys.exit(run_injection())
    if command == "report":
        sys.exit(report())
    sys.exit(__doc__)
