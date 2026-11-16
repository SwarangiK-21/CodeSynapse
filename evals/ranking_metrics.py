"""Ranking metrics for the retrieval evaluation.

Each takes a ranked list of ids and the set of relevant ids. The task is finding evidence
for a skill, where one good chunk is enough, so success@k and reciprocal rank matter most.
"""
import math

def success_at(ranking, relevant, k):
    """1 if any of the top k results is relevant."""
    return float(any(item in relevant for item in ranking[:k]))

def reciprocal_rank(ranking, relevant, k=10):
    """1 / position of the first relevant result within the top k, else 0."""
    for position, item in enumerate(ranking[:k], start=1):
        if item in relevant:
            return 1 / position
    return 0.0

def ndcg_at(ranking, relevant, k=10):
    """Rewards relevant results near the top, compared with the best possible order."""
    gain = sum(1 / math.log2(position + 1)
               for position, item in enumerate(ranking[:k], start=1) if item in relevant)
    ideal = sum(1 / math.log2(position + 1) for position in range(1, min(len(relevant), k) + 1))
    return gain / ideal if ideal else 0.0

METRICS = {
    "success@1": lambda r, rel: success_at(r, rel, 1),
    "success@5": lambda r, rel: success_at(r, rel, 5),
    "mrr@10": lambda r, rel: reciprocal_rank(r, rel, 10),
    "ndcg@10": lambda r, rel: ndcg_at(r, rel, 10),
}

def summarize(per_query):
    """Averages each metric over queries. per_query is a list of {metric: value}."""
    if not per_query:
        return {name: None for name in METRICS} | {"queries": 0}
    averages = {name: round(sum(q[name] for q in per_query) / len(per_query), 3) for name in METRICS}
    return averages | {"queries": len(per_query)}
