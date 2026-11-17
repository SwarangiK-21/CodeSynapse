"""Calibration metrics and a small logistic regression, in plain numpy.

probs are predicted probabilities that a skill is present; labels are 1 (present) or 0.
"""
import numpy as np

def brier(probs, labels):
    """Mean squared error of the probabilities: 0 is perfect, 0.25 is always guessing 0.5."""
    probs, labels = np.asarray(probs, float), np.asarray(labels, float)
    return float(np.mean((probs - labels) ** 2))

def reliability_bins(probs, labels, bins=5):
    """For each confidence band: how many predictions, their average confidence, and how often they were right."""
    probs, labels = np.asarray(probs, float), np.asarray(labels, float)
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for i in range(bins):
        last = i == bins - 1
        inside = (probs >= edges[i]) & ((probs <= edges[i + 1]) if last else (probs < edges[i + 1]))
        if inside.any():
            rows.append({"low": float(edges[i]), "high": float(edges[i + 1]), "count": int(inside.sum()),
                         "confidence": float(probs[inside].mean()), "accuracy": float(labels[inside].mean())})
    return rows

def ece(probs, labels, bins=5):
    """Expected calibration error: the average gap between confidence and accuracy, weighted by band size."""
    total = len(probs)
    return float(sum(r["count"] / total * abs(r["confidence"] - r["accuracy"])
                     for r in reliability_bins(probs, labels, bins))) if total else 0.0

def auroc(probs, labels):
    """How often a present skill scores above an absent one (0.5 is chance, 1 is perfect ranking)."""
    probs, labels = np.asarray(probs, float), np.asarray(labels, int)
    positives, negatives = probs[labels == 1], probs[labels == 0]
    if not len(positives) or not len(negatives):
        return None
    wins = (positives[:, None] > negatives[None, :]).sum() + 0.5 * (positives[:, None] == negatives[None, :]).sum()
    return float(wins / (len(positives) * len(negatives)))

def fit_logistic(x, y, l2=1.0, steps=50):
    """Logistic regression by Newton's method, with an L2 penalty that keeps weights small on little data.

    Returns (intercept, weights). The intercept is not penalised.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    design = np.hstack([np.ones((len(x), 1)), x])
    beta = np.zeros(design.shape[1])
    penalty = np.eye(design.shape[1]) * l2
    penalty[0, 0] = 0
    for _ in range(steps):
        p = 1 / (1 + np.exp(-design @ beta))
        gradient = design.T @ (p - y) + penalty @ beta
        hessian = design.T @ (design * (p * (1 - p))[:, None]) + penalty
        step = np.linalg.solve(hessian + 1e-9 * np.eye(len(beta)), gradient)
        beta -= step
        if np.abs(step).max() < 1e-8:
            break
    return float(beta[0]), beta[1:].tolist()

def predict_logistic(intercept, weights, x):
    x = np.asarray(x, float)
    return 1 / (1 + np.exp(-(intercept + x @ np.asarray(weights, float))))

def grouped_predictions(x, y, groups, fit, predict):
    """Leave-one-group-out: each group is scored by a model trained on all the others."""
    x, y, groups = np.asarray(x, float), np.asarray(y, float), np.asarray(groups)
    out = np.zeros(len(y))
    for group in np.unique(groups):
        held = groups == group
        model = fit(x[~held], y[~held])
        out[held] = predict(model, x[held])
    return out

def summary(probs, labels):
    probs = np.asarray(probs, float)
    return {"ece": round(ece(probs, labels), 3), "brier": round(brier(probs, labels), 3),
            "auroc": None if auroc(probs, labels) is None else round(auroc(probs, labels), 3),
            "accuracy@0.5": round(float(np.mean((probs >= 0.5) == np.asarray(labels, bool))), 3)}
