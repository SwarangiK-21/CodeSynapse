import re

def is_present(level):
    return level in ("strong", "partial")

def score(rows):
    """Scores presence detection. Each row has expected (bool) and level (str)."""
    tp = sum(1 for r in rows if r["expected"] and is_present(r["level"]))
    fp = sum(1 for r in rows if not r["expected"] and is_present(r["level"]))
    fn = sum(1 for r in rows if r["expected"] and not is_present(r["level"]))
    tn = len(rows) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "pairs": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
        "accuracy": round((tp + tn) / len(rows), 3) if rows else 0.0,
    }

def errors(rows):
    return [r for r in rows if r["expected"] != is_present(r["level"])]

def normalize(text):
    return re.sub(r"\s+", " ", text).strip().lower()

def citation_is_real(citation, files):
    """Rechecks a citation against the raw file, independently of the agent's verifier."""
    text = files.get(citation["path"])
    if text is None:
        return False
    lines = text.split("\n")[citation["start_line"] - 1:citation["end_line"]]
    return normalize(citation["quote"]) in normalize("\n".join(lines))

def citation_score(citations, files):
    real = sum(1 for c in citations if citation_is_real(c, files))
    return {"citations": len(citations), "real": real,
            "accuracy": round(real / len(citations), 3) if citations else None}
