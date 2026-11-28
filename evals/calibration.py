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
    """A reliability diagram as SVG: a calibrated method follows the diagonal.

    Each point is a confidence band; its area shows how many records fell in it, so bands
    holding one or two records, which swing the most, read as the small dots they are.
    Drawn on its own light card so it is legible in light and dark READMEs.
    """
    import math
    size, left, top = 360, 64, 28
    legend_top = top + size + 58
    width, height = left + size + 40, legend_top + 26 * len(results) + 34
    ink, muted, grid = "#1f2933", "#52606d", "#d9e2ec"
    colors = ["#e07a5f", "#7b8794", "#d9a12b", "#2b7a78"]
    def xy(conf, acc):
        return left + conf * size, top + (1 - acc) * size
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             'font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="14">',
             f'<rect width="{width}" height="{height}" rx="14" fill="#ffffff"/>',
             f'<rect x="{left}" y="{top}" width="{size}" height="{size}" fill="none" stroke="{grid}"/>']
    for tick in (0.25, 0.5, 0.75):
        x, y = xy(tick, tick)
        parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + size}" stroke="{grid}"/>')
        parts.append(f'<line x1="{left}" y1="{y}" x2="{left + size}" y2="{y}" stroke="{grid}"/>')
    parts.append(f'<line x1="{left}" y1="{top + size}" x2="{left + size}" y2="{top}" stroke="{muted}" '
                 'stroke-dasharray="5 5"/>')
    lx, ly = xy(0.68, 0.6)
    parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{muted}" font-size="12" '
                 f'transform="rotate(-45 {lx:.1f} {ly:.1f})">perfectly calibrated</text>')
    for tick in (0, 0.5, 1):
        x, y = xy(tick, tick)
        parts.append(f'<text x="{x}" y="{top + size + 20}" text-anchor="middle" fill="{muted}">{tick:g}</text>')
        parts.append(f'<text x="{left - 10}" y="{y + 5}" text-anchor="end" fill="{muted}">{tick:g}</text>')
    parts.append(f'<text x="{left + size / 2}" y="{top + size + 42}" text-anchor="middle" fill="{ink}">'
                 'Stated confidence</text>')
    parts.append(f'<text x="18" y="{top + size / 2}" text-anchor="middle" fill="{ink}" '
                 f'transform="rotate(-90 18 {top + size / 2})">How often it was right</text>')
    for (name, result), color, row in zip(results.items(), colors, range(len(results))):
        bins = result["bins"]
        points = [xy(b["confidence"], b["accuracy"]) for b in bins]
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" stroke-opacity="0.55" points="'
                     + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '"/>')
        parts.extend(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3 + 1.6 * math.sqrt(b["count"]):.1f}" '
                     f'fill="{color}" fill-opacity="0.8" stroke="#ffffff"/>' for (x, y), b in zip(points, bins))
        ly = legend_top + row * 26
        parts.append(f'<circle cx="{left + 6}" cy="{ly - 5}" r="6" fill="{color}"/>')
        parts.append(f'<text x="{left + 20}" y="{ly}" fill="{ink}">{name}</text>')
        parts.append(f'<text x="{left + size}" y="{ly}" text-anchor="end" fill="{muted}">'
                     f'ECE {result["ece"]} · Brier {result["brier"]}</text>')
    parts.append(f'<text x="{left}" y="{legend_top + 26 * len(results) + 8}" fill="{muted}" font-size="12">'
                 'Dot size: how many skills fell in that confidence band</text>')
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
