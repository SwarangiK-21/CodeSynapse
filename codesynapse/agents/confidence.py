"""Turns an assessed skill into a calibrated probability that the developer really has it.

A small logistic regression over facts the verifier has already checked. It is trained
and evaluated by evals/calibration.py, which writes the coefficients to confidence_model.json.
Without that file the report simply shows no confidence.
"""
import json
import math
from pathlib import Path

MODEL_FILE = Path(__file__).with_name("confidence_model.json")
# Used when the model gives no confidence of its own
NEUTRAL = 0.5

FEATURES = ["stated_confidence", "strong", "partial", "verified_citations", "any_rejected"]

def clamp(value):
    if value is None or not isinstance(value, (int, float)) or math.isnan(value):
        return None
    return min(max(float(value), 0.0), 1.0)

def features(result):
    """The numbers the model sees for one skill. result is the agent's verified result."""
    stated = clamp(result.get("stated_confidence"))
    return {
        "stated_confidence": NEUTRAL if stated is None else stated,
        "strong": float(result["level"] == "strong"),
        "partial": float(result["level"] == "partial"),
        # Diminishing returns: a third citation adds less than the first
        "verified_citations": math.log1p(len(result["citations"])),
        "any_rejected": float(result.get("rejected_claims", 0) > 0),
    }

def predict(model, feature_values):
    """Logistic regression: the probability the skill is really present."""
    z = model["intercept"] + sum(model["weights"][name] * feature_values[name] for name in FEATURES)
    return 1 / (1 + math.exp(-z))

def load_model():
    if not MODEL_FILE.exists():
        return None
    model = json.loads(MODEL_FILE.read_text(encoding="utf-8"))
    return model if set(model.get("weights", {})) == set(FEATURES) else None

def confidence(result, model=None):
    """A calibrated probability between 0 and 1, or None when no trained model is available."""
    model = model or load_model()
    return round(predict(model, features(result)), 3) if model else None
