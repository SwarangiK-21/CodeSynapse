import json
import re
from pathlib import Path
import pytest
from evals import check_labels, injection, metrics

def row(expected, level):
    return {"expected": expected, "level": level}

def test_score_counts_each_outcome():
    rows = [row(True, "strong"), row(True, "partial"), row(True, "none"), row(False, "strong"), row(False, "none")]
    result = metrics.score(rows)
    assert (result["tp"], result["fn"], result["fp"], result["tn"]) == (2, 1, 1, 1)
    assert result["precision"] == 0.667 and result["recall"] == 0.667 and result["accuracy"] == 0.6

def test_score_handles_empty_input():
    assert metrics.score([])["f1"] == 0.0

def test_always_yes_scores_badly_on_negatives():
    rows = [row(True, "strong"), row(False, "strong"), row(False, "strong"), row(False, "strong")]
    assert metrics.score(rows)["precision"] == 0.25

def test_errors_lists_wrong_rows():
    assert metrics.errors([row(True, "strong"), row(False, "partial")]) == [row(False, "partial")]

FILE = "line one\nexcept TimeoutError:\n    retry()\nlast line"

def citation(**overrides):
    return {"path": "a.py", "start_line": 2, "end_line": 3, "quote": "except TimeoutError: retry()", **overrides}

def test_real_citation_passes():
    assert metrics.citation_is_real(citation(), {"a.py": FILE})

@pytest.mark.parametrize("change", [{"path": "b.py"}, {"start_line": 1, "end_line": 1}, {"quote": "not in the file"}])
def test_wrong_citations_fail(change):
    assert not metrics.citation_is_real(citation(**change), {"a.py": FILE})

def test_citation_score():
    assert metrics.citation_score([citation(), citation(quote="fake")], {"a.py": FILE})["accuracy"] == 0.5
    assert metrics.citation_score([], {})["accuracy"] is None

def test_label_check_catches_a_wrong_present_label():
    files = {"a.py": "print(1)"}
    assert "matches nothing" in check_labels.label_problem({"present": True, "proof": "import redis"}, files)

def test_label_check_catches_a_wrong_absent_label():
    assert "labelled absent" in check_labels.label_problem({"present": False, "proof": "import redis"},
                                                           {"a.py": "import redis"})

def test_label_check_ignores_readmes():
    assert check_labels.label_problem({"present": False, "proof": "redis"}, {"README.md": "redis"}) is None

def test_label_file_is_valid_and_balanced():
    cases = json.loads(Path(check_labels.CASES).read_text(encoding="utf-8"))
    skills = [s for c in cases for s in c["skills"]]
    assert len(skills) >= 40
    assert all(re.compile(s["proof"]) for s in skills)
    assert all(len(c["commit"]) == 40 for c in cases)
    positives = sum(s["present"] for s in skills)
    assert 0.4 < positives / len(skills) < 0.65

def test_attacks_never_contain_the_real_skill():
    assert all("kubectl" not in injection.BASE for _ in injection.ATTACKS)
