from types import SimpleNamespace
import pytest
from google.genai import errors, types
from codesynapse.services import coach, embeddings

def use_ai(monkeypatch, embed_content):
    monkeypatch.setattr(coach, "client", SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)))

def reply(count):
    return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1]) for _ in range(count)])

def test_no_key_means_no_vectors(monkeypatch):
    monkeypatch.setattr(coach, "client", None)
    assert embeddings.embed_documents(["a"]) is None

def test_each_text_is_sent_as_separate_content(monkeypatch):
    seen = []
    def embed_content(model, contents, config):
        seen.append(contents)
        return reply(len(contents))
    use_ai(monkeypatch, embed_content)

    assert len(embeddings.embed_documents(["a", "b"])) == 2
    assert all(isinstance(item, types.Content) for item in seen[0])

def test_large_inputs_are_batched(monkeypatch):
    sizes = []
    def embed_content(model, contents, config):
        sizes.append(len(contents))
        return reply(len(contents))
    use_ai(monkeypatch, embed_content)

    assert len(embeddings.embed_documents(["x"] * 120)) == 120
    assert sizes == [50, 50, 20]

def test_wrong_vector_count_is_rejected(monkeypatch):
    use_ai(monkeypatch, lambda model, contents, config: reply(1))
    assert embeddings.embed_documents(["a", "b", "c"]) == [None, None, None]

def rate_limit():
    message = "Quota exceeded. Please retry in 7.5s."
    return errors.ClientError(429, {"error": {"code": 429, "message": message, "status": "S"}})

def test_indexing_waits_out_a_rate_limit(monkeypatch):
    waits, calls = [], []
    def embed_content(model, contents, config):
        calls.append(1)
        if len(calls) == 1:
            raise rate_limit()
        return reply(len(contents))
    use_ai(monkeypatch, embed_content)
    monkeypatch.setattr(embeddings.time, "sleep", waits.append)

    assert len(embeddings.embed_documents(["a"])) == 1
    assert waits == [8.5]

def test_finished_batches_are_kept_when_quota_runs_out(monkeypatch):
    calls = []
    def embed_content(model, contents, config):
        calls.append(1)
        if len(calls) > 1:
            raise rate_limit()
        return reply(len(contents))
    use_ai(monkeypatch, embed_content)
    monkeypatch.setattr(embeddings.time, "sleep", lambda seconds: None)

    vectors = embeddings.embed_documents(["x"] * 60)
    assert vectors[49] == [0.1] and vectors[50] is None and len(vectors) == 60

def test_dropped_connection_falls_back_to_keywords(monkeypatch):
    def embed_content(model, contents, config):
        raise ConnectionResetError("reset")
    use_ai(monkeypatch, embed_content)
    assert embeddings.embed_query("a") is None

def test_live_search_does_not_wait(monkeypatch):
    use_ai(monkeypatch, lambda model, contents, config: (_ for _ in ()).throw(rate_limit()))
    monkeypatch.setattr(embeddings.time, "sleep", lambda seconds: pytest.fail("search must not wait"))
    assert embeddings.embed_query("a") is None

def test_api_failure_falls_back_to_keywords(monkeypatch):
    def embed_content(model, contents, config):
        raise errors.ClientError(403, {"error": {"code": 403, "message": "m", "status": "S"}})
    use_ai(monkeypatch, embed_content)
    assert embeddings.embed_documents(["a"]) == [None]
