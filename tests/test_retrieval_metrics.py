import pytest
from codesynapse.services import search
from evals import ranking_metrics as m

def test_success_at_k():
    assert m.success_at(["a", "b", "c"], {"c"}, 2) == 0 and m.success_at(["a", "b", "c"], {"c"}, 3) == 1

def test_reciprocal_rank_uses_the_first_relevant_result():
    assert m.reciprocal_rank(["a", "b", "c"], {"b", "c"}) == 0.5
    assert m.reciprocal_rank(["a"] * 10 + ["b"], {"b"}, k=10) == 0

def test_ndcg_is_one_for_a_perfect_order_and_lower_otherwise():
    assert m.ndcg_at(["a", "b", "x"], {"a", "b"}) == pytest.approx(1)
    assert 0 < m.ndcg_at(["x", "a", "b"], {"a", "b"}) < 1
    assert m.ndcg_at(["x"], set()) == 0

def test_summarize_averages_each_metric():
    rows = [dict.fromkeys(m.METRICS, 1.0), dict.fromkeys(m.METRICS, 0.0)]
    summary = m.summarize(rows)
    assert summary["success@1"] == 0.5 and summary["queries"] == 2
    assert m.summarize([])["queries"] == 0

def test_fusion_defaults_are_unchanged():
    assert [i for i, _ in search.fuse([["a", "b"], ["b", "c"]])] == ["b", "a", "c"]

def test_fusion_weights_shift_the_order():
    keyword, vector = ["k1", "v1"], ["v1", "v2"]
    plain = [i for i, _ in search.fuse([keyword, vector])]
    weighted = [i for i, _ in search.fuse([keyword, vector], weights=[0.1, 1.0], k=10)]
    assert plain[0] == "v1" and weighted.index("v2") < weighted.index("k1")
