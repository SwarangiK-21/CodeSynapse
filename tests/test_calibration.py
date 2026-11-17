import json
import numpy as np
import pytest
from codesynapse.agents import confidence
from evals import calibration
from evals import calibration_metrics as cm

# --- METRICS ---

def test_perfectly_calibrated_predictions_have_no_error():
    probs = [0.1] * 10 + [0.9] * 10
    labels = [1] + [0] * 9 + [1] * 9 + [0]
    assert cm.ece(probs, labels) == pytest.approx(0)

def test_overconfidence_shows_up_as_calibration_error():
    # Always 95% sure, right only half the time
    assert cm.ece([0.95] * 10, [1, 0] * 5) == pytest.approx(0.45)

def test_brier_score():
    assert cm.brier([1, 0], [1, 0]) == 0 and cm.brier([0.5, 0.5], [1, 0]) == 0.25

def test_auroc_measures_ranking():
    assert cm.auroc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]) == 1
    assert cm.auroc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == 0
    assert cm.auroc([0.5, 0.5], [1, 0]) == 0.5
    assert cm.auroc([0.5], [1]) is None

def test_reliability_bins_count_every_prediction():
    bins = cm.reliability_bins([0.0, 0.3, 0.55, 1.0], [0, 0, 1, 1])
    assert sum(b["count"] for b in bins) == 4

def test_logistic_regression_learns_the_direction():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 1))
    y = (x[:, 0] + rng.normal(scale=0.5, size=200) > 0).astype(float)
    intercept, weights = cm.fit_logistic(x, y, l2=0.1)
    assert weights[0] > 1
    assert cm.predict_logistic(intercept, weights, [[2.0]])[0] > 0.9

def test_grouped_predictions_never_use_the_held_out_group():
    seen = []
    def fit(x, y):
        seen.append(len(x))
        return None
    cm.grouped_predictions([[0]] * 5, [0, 1, 0, 1, 0], ["a", "a", "b", "b", "b"], fit, lambda m, x: np.zeros(len(x)))
    assert sorted(seen) == [2, 3]

# --- APP-SIDE MODEL ---

RESULT = {"level": "strong", "citations": [{}, {}], "rejected_claims": 1, "stated_confidence": 0.8}

def test_features_from_a_verified_result():
    values = confidence.features(RESULT)
    assert values["strong"] == 1 and values["partial"] == 0 and values["any_rejected"] == 1
    assert values["verified_citations"] == pytest.approx(np.log1p(2))

def test_a_missing_or_odd_stated_confidence_is_neutral_or_clamped():
    assert confidence.features({**RESULT, "stated_confidence": None})["stated_confidence"] == 0.5
    assert confidence.clamp(1.7) == 1 and confidence.clamp(-3) == 0 and confidence.clamp(float("nan")) is None

def test_prediction_is_a_probability():
    model = {"intercept": -1.0, "weights": dict.fromkeys(confidence.FEATURES, 1.0)}
    assert 0 < confidence.confidence(RESULT, model) < 1

def test_no_model_means_no_confidence(monkeypatch, tmp_path):
    monkeypatch.setattr(confidence, "MODEL_FILE", tmp_path / "missing.json")
    assert confidence.confidence(RESULT) is None

# --- END TO END ON SYNTHETIC RECORDS ---

def synthetic_records():
    records = []
    for repo in range(4):
        for i in range(10):
            present = i % 2 == 0
            records.append({"suite": "core", "repo": f"r{repo}", "skill": f"s{i}", "type": "plain",
                            "present": present, "level": "strong" if present else "none",
                            "citations": 2 if present else 0, "rejected_claims": 0,
                            # Overconfident: always says 0.9
                            "stated_confidence": 0.9})
    return records

def test_analyze_scores_methods_and_writes_a_usable_model(monkeypatch, tmp_path):
    records_file = tmp_path / "calibration.jsonl"
    records_file.write_text("\n".join(json.dumps(r) for r in synthetic_records()), encoding="utf-8")
    monkeypatch.setattr(calibration, "RECORDS", records_file)
    monkeypatch.setattr(calibration, "SUMMARY", tmp_path / "calibration.json")
    monkeypatch.setattr(calibration, "CHART", tmp_path / "calibration.svg")
    monkeypatch.setattr(confidence, "MODEL_FILE", tmp_path / "model.json")

    assert calibration.analyze() == 0
    methods = json.loads((tmp_path / "calibration.json").read_text())["methods"]
    # The always-0.9 self-report is badly calibrated; the learned model fixes it
    assert methods["AI's own confidence"]["ece"] > 0.3
    assert methods["Learned model (all features)"]["ece"] < methods["AI's own confidence"]["ece"]
    assert (tmp_path / "calibration.svg").read_text().startswith("<svg")
    model = confidence.load_model()
    assert confidence.confidence({"level": "strong", "citations": [{}], "stated_confidence": 0.9}, model) > 0.5
    assert confidence.confidence({"level": "none", "citations": [], "stated_confidence": 0.9}, model) < 0.5

def test_analyze_without_records(monkeypatch, tmp_path):
    monkeypatch.setattr(calibration, "RECORDS", tmp_path / "none.jsonl")
    assert calibration.analyze() == 1
