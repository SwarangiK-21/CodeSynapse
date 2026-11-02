import re
import numpy as np
from rank_bm25 import BM25Plus
from sqlalchemy import select
from sqlalchemy.orm import Session
from codesynapse.db.models import CodeChunk, Repo, User
from codesynapse.services import embeddings

# Standard constant for reciprocal rank fusion
RRF_K = 60
CANDIDATES = 50
SNIPPET_CHARS = 600

def tokenize(text):
    """Splits identifiers, so `getUserName` and `get_user_name` both match "user"."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [t for t in re.split(r"[^A-Za-z0-9]+", text.lower()) if t]

def searchable_text(chunk):
    return f"{chunk.path} {chunk.symbol} {chunk.content}"

def keyword_ranking(chunks, query):
    """Returns chunk ids, best first. Only chunks containing a query term count."""
    terms = set(tokenize(query))
    corpus = [tokenize(searchable_text(c)) for c in chunks]
    scores = BM25Plus(corpus).get_scores(list(terms))
    matches = [i for i, tokens in enumerate(corpus) if terms & set(tokens)]
    matches.sort(key=lambda i: scores[i], reverse=True)
    return [chunks[i].id for i in matches[:CANDIDATES]]

def vector_ranking_python(chunks, query_vector):
    """SQLite has no vector index, so similarity is computed here."""
    embedded = [c for c in chunks if c.embedding is not None]
    if not embedded:
        return []
    matrix = np.array([c.embedding for c in embedded], dtype=float)
    query = np.array(query_vector, dtype=float)
    scores = matrix @ query / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query) + 1e-10)
    best = np.argsort(-scores)[:CANDIDATES]
    return [embedded[i].id for i in best]

def vector_ranking(db: Session, chunks, query_vector):
    if db.get_bind().dialect.name != "postgresql":
        return vector_ranking_python(chunks, query_vector)
    ids = [c.id for c in chunks]
    return list(db.scalars(
        select(CodeChunk.id).where(CodeChunk.id.in_(ids), CodeChunk.embedding.is_not(None))
        .order_by(CodeChunk.embedding.cosine_distance(query_vector)).limit(CANDIDATES)
    ))

def fuse(rankings):
    """Reciprocal rank fusion: rewards results that rank well in either list."""
    scores = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)

def search_code(db: Session, user: User, query, repo_id=None, limit=10):
    """Finds code in this user's repositories using keywords and meaning."""
    statement = select(CodeChunk, Repo.full_name).join(Repo).where(Repo.user_id == user.id)
    if repo_id:
        statement = statement.where(Repo.id == repo_id)
    rows = db.execute(statement).all()
    if not rows:
        return []

    chunks = [chunk for chunk, _ in rows]
    repo_names = {chunk.id: name for chunk, name in rows}
    by_id = {c.id: c for c in chunks}

    keyword = keyword_ranking(chunks, query)
    query_vector = embeddings.embed_query(query)
    vector = vector_ranking(db, chunks, query_vector) if query_vector else []

    results = []
    for chunk_id, score in fuse([keyword, vector])[:limit]:
        c = by_id[chunk_id]
        results.append({
            "repo": repo_names[chunk_id], "path": c.path, "symbol": c.symbol, "kind": c.kind,
            "language": c.language, "start_line": c.start_line, "end_line": c.end_line,
            "score": round(score, 5), "snippet": c.content[:SNIPPET_CHARS],
            "matched_by": [name for name, ranking in (("keyword", keyword), ("vector", vector)) if chunk_id in ranking],
        })
    return results
