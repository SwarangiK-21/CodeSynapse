"""Checks whether the agent's confidence can be trusted, and trains the confidence model.

    python -m evals.calibration collect   # runs the agent on every labelled skill (uses Gemini)
    python -m evals.calibration analyze   # scores and fits, no AI

collect saves one record per skill to evals/results/calibration.jsonl and resumes where it
stopped, like evals.run. analyze compares four ways of turning a result into a probability,
each scored by leave-one-repository-out cross-validation, so a repository is never scored by
a model that saw it. It writes the scores, a reliability chart, and the final model fitted
on all the data to codesynapse/agents/confidence_model.json.

Unlike evals.run, this uses the app's own model list: the confidence model scores the live
app's answers, so it learns from the models the app really calls.
"""
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
if __name__ == "__main__":
    # Before any app code reads its settings: keep the search index in evals/.cache, which
    # is reused between runs (and cached by the Evals workflow) so it isn't embedded again
    os.environ["DATABASE_URL"] = f"sqlite:///{(ROOT / '.cache' / 'eval.db').as_posix()}"

import numpy as np  # noqa: E402
from evals import calibration_metrics as cm  # noqa: E402
from evals import check_labels  # noqa: E402
from codesynapse.agents import confidence  # noqa: E402

RECORDS = ROOT / "results" / "calibration.jsonl"
SUMMARY = ROOT / "results" / "calibration.json"
CHART = ROOT.parent / "docs" / "images" / "calibration.svg"
L2 = 1.0

# --- COLLECT ---

def load_records():
    if not RECORDS.exists():
        return []
    return [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]

def collect():
    # Imported here so analyze works without the agent
    from evals import run
    from codesynapse.db.migrate import upgrade
    from codesynapse.db.session import SessionLocal
    from codesynapse.services import llm
    upgrade()
    done = {(r["suite"], r["repo"]) for r in load_records()}
    waiting = []
    with SessionLocal() as db:
        user = run.eval_user(db)
        for suite in ("core", "hard"):
            for case in check_labels.load_cases(suite):
                if (suite, case["repo"]) in done:
                    continue
                repo_id = run.indexed_repo(db, user, case)
                if repo_id is None:
                    # Out of embedding quota: skip it, so repositories already indexed still run today
                    waiting.append(f"{suite}/{case['repo']}")
                    continue
                started = time.time()
                try:
                    report, _, _ = run.gap_analysis.run(db, user, run.job_for(case), [repo_id])
                except llm.LLMError as e:
                    print(f"stopped at {suite}/{case['repo']}: {e}. Run again to resume.")
                    return 1
                found = {s["name"]: s for s in report["skills"]}
                with RECORDS.open("a", encoding="utf-8") as f:
                    for skill in case["skills"]:
                        result = found.get(skill["name"], {})
                        f.write(json.dumps({
                            "suite": suite, "repo": case["repo"], "skill": skill["name"],
                            "type": skill.get("type", "plain"), "present": skill["present"],
                            "level": result.get("level", "none"),
                            "citations": len(result.get("citations", [])),
                            "rejected_claims": result.get("rejected_claims", 0),
                            "stated_confidence": result.get("stated_confidence"),
                        }) + "\n")
                print(f"finished {suite}/{case['repo']} in {round(time.time() - started)}s", flush=True)
    if waiting:
        print(f"Embedding quota used up for today. Waiting for: {', '.join(waiting)}. Run again tomorrow to resume.")
        return 1
    return 0

# --- ANALYZE ---

def feature_matrix(records, names):
    rows = []
    for r in records:
        values = confidence.features({**r, "citations": [None] * r["citations"]})
        rows.append([values[n] for n in names])
    return np.array(rows, float)

def logistic(names):
    """A method that fits a logistic regression on the given features."""
    def method(records, labels, groups):
        x = feature_matrix(records, names)
        return cm.grouped_predictions(
            x, labels, groups,
            fit=lambda xs, ys: cm.fit_logistic(xs, ys, l2=L2),
            predict=lambda model, xs: cm.predict_logistic(model[0], model[1], xs))
    return method

def stated(records, labels, groups):
    return feature_matrix(records, ["stated_confidence"])[:, 0]

METHODS = {
    "AI's own confidence": stated,
    "Verified level only": logistic(["strong", "partial"]),
    "AI's confidence, rescaled": logistic(["stated_confidence"]),
    "Learned model (all features)": logistic(confidence.FEATURES),
}

def chart(results):
    """A reliability diagram as SVG: a calibrated method follows the diagonal."""
    size, pad = 320, 44
    colors = ["#e07a5f", "#8d99ae", "#f2a541", "#2b7a78"]
    def xy(conf, acc):
        return pad + conf * size, pad + (1 - acc) * size
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size + pad + 230} {size + 2 * pad}" '
             'font-family="system-ui, sans-serif" font-size="12">',
             f'<rect x="{pad}" y="{pad}" width="{size}" height="{size}" fill="none" stroke="#8b949e"/>',
             f'<line x1="{pad}" y1="{pad + size}" x2="{pad + size}" y2="{pad}" stroke="#8b949e" stroke-dasharray="4 4"/>',
             f'<text x="{pad + size / 2}" y="{size + pad + 32}" text-anchor="middle" fill="#8b949e">Confidence</text>',
             f'<text x="14" y="{pad + size / 2}" text-anchor="middle" fill="#8b949e" '
             f'transform="rotate(-90 14 {pad + size / 2})">How often it was right</text>']
    for tick in (0, 0.5, 1):
        parts.append(f'<text x="{pad + tick * size}" y="{size + pad + 15}" text-anchor="middle" fill="#8b949e">{tick}</text>')
        parts.append(f'<text x="{pad - 6}" y="{pad + (1 - tick) * size + 4}" text-anchor="end" fill="#8b949e">{tick}</text>')
    for (name, result), color, row in zip(results.items(), colors, range(len(results))):
        points = [xy(b["confidence"], b["accuracy"]) for b in result["bins"]]
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="'
                     + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '"/>')
        parts.extend(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>' for x, y in points)
        ly = pad + 10 + row * 22
        parts.append(f'<rect x="{pad + size + 16}" y="{ly - 9}" width="12" height="12" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{pad + size + 34}" y="{ly + 1}" fill="#8b949e">{name} (ECE {result["ece"]})</text>')
    parts.append("</svg>")
    return "\n".join(parts)

def analyze():
    records = load_records()
    if not records:
        print("No records yet. Run: python -m evals.calibration collect")
        return 1
    labels = np.array([r["present"] for r in records], float)
    groups = np.array([r["repo"] for r in records])
    results = {}
    for name, method in METHODS.items():
        probs = method(records, labels, groups)
        results[name] = cm.summary(probs, labels) | {"bins": cm.reliability_bins(probs, labels)}

    x = feature_matrix(records, confidence.FEATURES)
    intercept, weights = cm.fit_logistic(x, labels, l2=L2)
    model = {"intercept": round(intercept, 4),
             "weights": {n: round(w, 4) for n, w in zip(confidence.FEATURES, weights)},
             "trained_on": len(records), "repositories": len(set(groups)), "l2": L2,
             "cross_validated": {k: v for k, v in results["Learned model (all features)"].items() if k != "bins"},
             "date": date.today().isoformat()}
    confidence.MODEL_FILE.write_text(json.dumps(model, indent=1), encoding="utf-8")
    SUMMARY.write_text(json.dumps({"records": len(records), "repositories": len(set(groups)),
                                   "methods": results}, indent=1), encoding="utf-8")
    CHART.write_text(chart(results), encoding="utf-8")

    print(f"{len(records)} skills from {len(set(groups))} repositories, leave-one-repository-out")
    print(f"{'method':<32} {'ECE':>6} {'Brier':>6} {'AUROC':>6} {'Acc':>6}")
    for name, r in results.items():
        print(f"{name:<32} {r['ece']:>6} {r['brier']:>6} {str(r['auroc']):>6} {r['accuracy@0.5']:>6}")
    print(f"Saved {SUMMARY}, {CHART} and {confidence.MODEL_FILE}")
    return 0

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"collect": collect, "analyze": analyze}.get(command, lambda: print(__doc__) or 1)())
