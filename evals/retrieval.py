"""Measures how well code search finds evidence for a skill. Uses no generative AI.

    python -m evals.retrieval

Queries are the skills labelled present in cases.json and cases_hard.json. A chunk counts
as relevant when it matches that skill's proof pattern, the same check check_labels.py runs
against the real files, so the labels need no AI and no hand-marking.

Each search method ranks the chunks of one repository. Query vectors are saved to
evals/.cache, so re-runs cost no quota. New methods, such as a reranker, are added to METHODS.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / ".cache"
RESULTS = ROOT / "results"
# Reuses the evaluation index built by evals.run
os.environ["DATABASE_URL"] = f"sqlite:///{(CACHE / 'eval.db').as_posix()}"

from sqlalchemy import select  # noqa: E402
from codesynapse.db.migrate import upgrade  # noqa: E402
from codesynapse.db.models import CodeChunk, Repo  # noqa: E402
from codesynapse.db.session import SessionLocal  # noqa: E402
from codesynapse.services import embeddings, search  # noqa: E402
from evals import check_labels, ranking_metrics  # noqa: E402

QUERY_VECTORS = CACHE / "query_vectors.json"

def load_query_vectors():
    return json.loads(QUERY_VECTORS.read_text(encoding="utf-8")) if QUERY_VECTORS.exists() else {}

def query_vector(text, saved):
    if text not in saved:
        vector = embeddings.embed_query(text)
        if vector is None:
            raise SystemExit("Could not embed the query. Check GEMINI_API_KEY, or try again after the quota resets.")
        saved[text] = vector
        QUERY_VECTORS.write_text(json.dumps(saved), encoding="utf-8")
    return saved[text]

def relevant_ids(chunks, proof):
    """Chunks that contain the proof, using the same rule as the label check."""
    return {c.id for c in chunks if not c.path.endswith(".md") and re.search(proof, c.content, re.MULTILINE)}

# Each method takes (db, chunks, query, vector) and returns chunk ids, best first
def keyword(db, chunks, query, vector):
    return search.keyword_ranking(chunks, query)

def semantic(db, chunks, query, vector):
    return search.vector_ranking_python(chunks, vector)

def hybrid(db, chunks, query, vector):
    return [chunk_id for chunk_id, _ in search.fuse([keyword(db, chunks, query, vector),
                                                     semantic(db, chunks, query, vector)])]

# Tuned on the standard set only (keyword weight 0, 0.1, 0.25, 0.5, 1 x k 10, 60), so the
# hard set's paraphrased queries stay a fair held-out check
TUNED_KEYWORD_WEIGHT = 0.25
TUNED_K = 10

def tuned_hybrid(db, chunks, query, vector):
    rankings = [keyword(db, chunks, query, vector), semantic(db, chunks, query, vector)]
    fused = search.fuse(rankings, weights=[TUNED_KEYWORD_WEIGHT, 1.0], k=TUNED_K)
    return [chunk_id for chunk_id, _ in fused]

METHODS = {"keyword (BM25)": keyword, "vector": semantic, "hybrid (RRF)": hybrid,
           "hybrid, tuned": tuned_hybrid}

def build_queries(db):
    """Returns one entry per present skill whose repository is in the evaluation index."""
    indexed = {r.full_name: r for r in db.scalars(select(Repo))}
    queries, skipped = [], []
    for suite in ("core", "hard"):
        for case in check_labels.load_cases(suite):
            repo = indexed.get(case["repo"])
            if not repo or repo.commit_sha != case["commit"]:
                skipped.extend(f"{case['repo']}: {s['name']} (not indexed)" for s in case["skills"] if s["present"])
                continue
            chunks = list(db.scalars(select(CodeChunk).where(CodeChunk.repo_id == repo.id)))
            for skill in case["skills"]:
                if not skill["present"]:
                    continue
                relevant = relevant_ids(chunks, skill["proof"])
                if not relevant:
                    skipped.append(f"{case['repo']}: {skill['name']} (no chunk holds the proof)")
                    continue
                queries.append({"suite": suite, "type": skill.get("type", "plain"), "repo": case["repo"],
                                "query": skill["name"], "chunks": chunks, "relevant": relevant})
    return queries, skipped

def evaluate(db, queries, methods=METHODS):
    saved = load_query_vectors()
    scores = {name: [] for name in methods}
    for q in queries:
        vector = query_vector(q["query"], saved)
        for name, method in methods.items():
            ranking = method(db, q["chunks"], q["query"], vector)
            row = {metric: fn(ranking, q["relevant"]) for metric, fn in ranking_metrics.METRICS.items()}
            scores[name].append(row | {"suite": q["suite"], "type": q["type"], "query": q["query"], "repo": q["repo"]})
    return scores

def report(scores):
    def group(rows, keep):
        return ranking_metrics.summarize([r for r in rows if keep(r)])
    return {name: {"all": group(rows, lambda r: True),
                   "standard": group(rows, lambda r: r["suite"] == "core"),
                   "hard: paraphrased": group(rows, lambda r: r["type"] == "paraphrase"),
                   "per_query": rows}
            for name, rows in scores.items()}

def print_table(summary):
    print(f"{'method':<16} {'set':<18} {'n':>3} {'S@1':>6} {'S@5':>6} {'MRR':>6} {'nDCG':>6}")
    for name, groups in summary.items():
        for label in ("all", "standard", "hard: paraphrased"):
            g = groups[label]
            print(f"{name:<16} {label:<18} {g['queries']:>3} {g['success@1']:>6} {g['success@5']:>6} "
                  f"{g['mrr@10']:>6} {g['ndcg@10']:>6}")

def main():
    upgrade()
    with SessionLocal() as db:
        queries, skipped = build_queries(db)
        summary = report(evaluate(db, queries))
    for line in skipped:
        print("skipped", line)
    print_table(summary)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "retrieval.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"Saved {RESULTS / 'retrieval.json'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
