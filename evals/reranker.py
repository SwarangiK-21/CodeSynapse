"""Distils Gemini's relevance judgements into a small cross-encoder that reranks code search.

    python -m evals.reranker label   # Gemini scores the top candidates for each query (uses AI)
    python -m evals.reranker train   # fine-tunes the student and evaluates it (no AI; needs
                                     # requirements-reranker.txt)

Candidates are the top 20 chunks from the tuned hybrid search for each labelled query. Gemini,
the teacher, scores each 0-3. A small pretrained cross-encoder, the student, is fine-tuned on
those scores from five repositories and tested on the other three.

The test is judged by the proof-pattern labels, the same ones the retrieval evaluation uses,
not by the teacher, so the student can't score well just by copying the teacher's mistakes.
It is compared with the search order itself and with the same cross-encoder before training.
"""
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
if __name__ == "__main__":
    # Before any app code reads its settings, as in evals/calibration.py
    os.environ["DATABASE_URL"] = f"sqlite:///{(ROOT / '.cache' / 'eval.db').as_posix()}"

from evals import ranking_metrics  # noqa: E402
from evals import reranker_data as rd  # noqa: E402

LABELS = ROOT / "results" / "reranker_labels.jsonl"
RESULTS = ROOT / "results" / "reranker.json"
MODEL_DIR = ROOT / ".cache" / "reranker-model"
BASE_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
EPOCHS = 3
BATCH = 16
LEARNING_RATE = 2e-5
MAX_TOKENS = 256
SEED = 0

def load_labels():
    if not LABELS.exists():
        return []
    return [json.loads(line) for line in LABELS.read_text(encoding="utf-8").splitlines() if line.strip()]

def candidate_rows(db):
    """For every labelled query: its top candidates from the tuned search and which are relevant."""
    from evals import retrieval
    queries, _ = retrieval.build_queries(db)
    saved = retrieval.load_query_vectors()
    for q in queries:
        vector = retrieval.query_vector(q["query"], saved)
        ranking = retrieval.tuned_hybrid(db, q["chunks"], q["query"], vector)[:rd.CANDIDATES]
        yield {"suite": q["suite"], "type": q["type"], "repo": q["repo"], "query": q["query"],
               "candidates": ranking, "relevant": [c for c in ranking if c in q["relevant"]],
               "all_relevant": len(q["relevant"])}, {c.id: c for c in q["chunks"]}

# --- LABEL ---

def label():
    from codesynapse.db.migrate import upgrade
    from codesynapse.db.session import SessionLocal
    from codesynapse.services import llm
    upgrade()
    done = {(r["repo"], r["query"]) for r in load_labels()}
    added = 0
    with SessionLocal() as db:
        for row, chunks in candidate_rows(db):
            if (row["repo"], row["query"]) in done:
                continue
            ordered = [chunks[c] for c in row["candidates"]]
            try:
                reply = llm.generate_json(rd.teacher_prompt(row["query"], ordered), rd.TeacherReply)
            except llm.LLMError as e:
                print(f"stopped at {row['repo']} / {row['query']}: {e}. Run again to resume.")
                return 1
            row["scores"] = {str(k): v for k, v in rd.parse_scores(reply, row["candidates"]).items()}
            with LABELS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            added += 1
            print(f"scored {row['repo']} / {row['query']}", flush=True)
    print(f"{added} queries scored, {len(load_labels())} in total")
    return 0

# --- TRAIN AND EVALUATE ---

def cross_encoder(source):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    return AutoTokenizer.from_pretrained(source), AutoModelForSequenceClassification.from_pretrained(source)

def scores_for(tokenizer, model, query, texts):
    import torch
    model.eval()
    with torch.no_grad():
        encoded = tokenizer([query] * len(texts), texts, truncation=True, max_length=MAX_TOKENS,
                            padding=True, return_tensors="pt")
        return model(**encoded).logits.squeeze(-1).tolist()

def fine_tune(tokenizer, model, pairs):
    import torch
    torch.manual_seed(SEED)
    random.seed(SEED)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    for epoch in range(EPOCHS):
        model.train()
        random.shuffle(pairs)
        total = 0.0
        for start in range(0, len(pairs), BATCH):
            batch = pairs[start:start + BATCH]
            encoded = tokenizer([p[0] for p in batch], [p[1] for p in batch], truncation=True,
                                max_length=MAX_TOKENS, padding=True, return_tensors="pt")
            targets = torch.tensor([p[2] for p in batch], dtype=torch.float)
            loss = loss_fn(model(**encoded).logits.squeeze(-1), targets)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item() * len(batch)
        print(f"epoch {epoch + 1}: loss {total / len(pairs):.4f}", flush=True)

def rerank(row, texts, tokenizer, model):
    candidates = [c for c in row["candidates"] if c in texts]
    scores = scores_for(tokenizer, model, row["query"], [texts[c] for c in candidates])
    return [c for _, c in sorted(zip(scores, candidates), key=lambda pair: -pair[0])]

def evaluate(rows, rankings):
    per_query = []
    for row in rows:
        ranking = rankings(row)
        values = {m: fn(ranking, set(row["relevant"])) for m, fn in ranking_metrics.METRICS.items()}
        per_query.append(values | {"type": row["type"]})
    return {"all": ranking_metrics.summarize(per_query),
            "paraphrased": ranking_metrics.summarize([q for q in per_query if q["type"] == "paraphrase"])}

def train():
    from codesynapse.db.migrate import upgrade
    from codesynapse.db.session import SessionLocal
    rows = load_labels()
    if not rows:
        print("No teacher labels yet. Run: python -m evals.reranker label")
        return 1
    upgrade()
    with SessionLocal() as db:
        from codesynapse.db.models import CodeChunk
        wanted = {int(c) for r in rows for c in r["candidates"]}
        texts = {c.id: rd.chunk_text(c) for c in db.query(CodeChunk).filter(CodeChunk.id.in_(wanted))}
    train_rows, test_rows = rd.split(rows)
    pairs = rd.training_pairs(train_rows, texts)
    print(f"{len(train_rows)} training queries ({len(pairs)} pairs), {len(test_rows)} test queries")

    started = time.time()
    tokenizer, base = cross_encoder(BASE_MODEL)
    results = {"search order (tuned hybrid)": evaluate(test_rows, lambda r: r["candidates"]),
               "cross-encoder, not trained": evaluate(test_rows, lambda r: rerank(r, texts, tokenizer, base))}
    tokenizer, student = cross_encoder(BASE_MODEL)
    fine_tune(tokenizer, student, pairs)
    results["cross-encoder, distilled"] = evaluate(test_rows, lambda r: rerank(r, texts, tokenizer, student))
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    student.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)

    ceiling = ranking_metrics.summarize([{m: float(bool(r["relevant"])) for m in ranking_metrics.METRICS}
                                         for r in test_rows])["success@1"]
    summary = {
        "base_model": BASE_MODEL, "epochs": EPOCHS, "learning_rate": LEARNING_RATE, "seed": SEED,
        "train_repos": sorted({r["repo"] for r in train_rows}), "test_repos": sorted(rd.TEST_REPOS),
        "train_queries": len(train_rows), "train_pairs": len(pairs), "test_queries": len(test_rows),
        "test_queries_with_a_relevant_candidate": ceiling,
        "teacher_agreement_with_labels": rd.teacher_agreement(rows),
        "seconds": round(time.time() - started), "methods": results,
    }
    RESULTS.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "methods"}, indent=1))
    for name, groups in results.items():
        g = groups["all"]
        print(f"{name:<30} S@1 {g['success@1']}  S@5 {g['success@5']}  MRR {g['mrr@10']}  nDCG {g['ndcg@10']}")
    return 0

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"label": label, "train": train}.get(command, lambda: print(__doc__) or 1)())
