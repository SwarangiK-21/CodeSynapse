from types import SimpleNamespace
import pytest
import respx
from pydantic import BaseModel
from codesynapse.db.models import Analysis, JobDescription, Repo
from codesynapse.db.session import SessionLocal
from codesynapse.services import cache, coach, embeddings, limits, llm, repos, tasks, users
from tests.test_repos import REPO, mock_github

# --- BACKGROUND JOBS ---

@pytest.fixture
def github():
    with respx.mock(assert_all_called=False) as m:
        mock_github(m)
        yield m

def test_indexing_returns_at_once_and_finishes_in_the_background(client, auth, github, monkeypatch):
    monkeypatch.setattr(tasks, "RUN_INLINE", False)
    submitted = []
    monkeypatch.setattr(tasks.executor, "submit", lambda fn, *args: submitted.append((fn, args)) or SimpleNamespace(
        add_done_callback=lambda cb: None))
    headers = auth()

    response = client.post("/api/repos", json={"repo": REPO}, headers=headers)
    assert response.status_code == 202 and response.json()["status"] == "indexing"
    assert response.json()["chunks"] == 0

    fn, args = submitted[0]
    fn(*args)
    repo = client.get("/api/repos", headers=headers).json()["repos"][0]
    assert repo["status"] == "ready" and repo["chunks"] == 2

def test_starting_twice_does_not_queue_a_second_job(client, auth, github, monkeypatch):
    monkeypatch.setattr(tasks, "RUN_INLINE", False)
    submitted = []
    monkeypatch.setattr(tasks.executor, "submit", lambda fn, *args: submitted.append(fn) or SimpleNamespace(
        add_done_callback=lambda cb: None))
    headers = auth()
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    assert len(submitted) == 1

def test_failed_indexing_records_the_reason(client, auth, monkeypatch):
    def broken(full_name, sha=None):
        raise repos.RepoError("That repository is too large to analyse.")
    monkeypatch.setattr(repos, "check_exists", lambda name: None)
    monkeypatch.setattr(repos, "download_archive", broken)
    headers = auth()
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    repo = client.get("/api/repos", headers=headers).json()["repos"][0]
    assert repo["status"] == "failed" and "too large" in repo["error"]

def test_unexpected_indexing_errors_are_hidden(client, auth, monkeypatch):
    def broken(full_name, sha=None):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(repos, "check_exists", lambda name: None)
    monkeypatch.setattr(repos, "download_archive", broken)
    headers = auth()
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    repo = client.get("/api/repos", headers=headers).json()["repos"][0]
    assert repo["status"] == "failed" and "secret" not in repo["error"]

def seed(token, status):
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        repo = Repo(user_id=user.id, full_name="octocat/demo", commit_sha="a" * 40, status=status)
        job = JobDescription(user_id=user.id, title="Engineer", raw_text="text", skills=[
            {"name": "Retries", "category": "practice", "importance": "required", "quote": "Retries"}])
        db.add_all([repo, job])
        db.commit()
        return repo.id, job.id

def test_analysis_waits_for_indexing_to_finish(client):
    token = client.post("/api/users").json()["token"]
    repo_id, job_id = seed(token, "indexing")
    response = client.post("/api/analyses", json={"job_id": job_id, "repo_ids": [repo_id]},
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422 and "isn't ready" in response.json()["detail"]

def test_restart_marks_stuck_jobs_as_failed(client):
    token = client.post("/api/users").json()["token"]
    repo_id, job_id = seed(token, "indexing")
    with SessionLocal() as db:
        user = users.get_user_by_token(db, token)
        db.add(Analysis(user_id=user.id, job_id=job_id, repo_ids=[repo_id], status="running"))
        db.commit()
        tasks.recover_interrupted(db)
        assert db.get(Repo, repo_id).status == "failed"
        analysis = db.query(Analysis).one()
        assert analysis.status == "failed" and "restart" in analysis.error and analysis.finished_at

def test_a_crashed_job_is_logged(capsys):
    future = SimpleNamespace(exception=lambda: RuntimeError("boom"))
    tasks.report_failure(future)
    assert "boom" in capsys.readouterr().out

# --- RATE LIMITS ---

def test_limit_blocks_then_explains_when_to_retry(monkeypatch):
    monkeypatch.setitem(limits.LIMITS, "chat", (2, 3600))
    limits.check("chat", "u1")
    limits.check("chat", "u1")
    with pytest.raises(limits.Limited) as error:
        limits.check("chat", "u1")
    assert 3500 < error.value.retry_after <= 3601 and "minutes" in str(error.value)

def test_limits_are_per_user(monkeypatch):
    monkeypatch.setitem(limits.LIMITS, "chat", (1, 3600))
    limits.check("chat", "u1")
    limits.check("chat", "u2")

def test_old_requests_stop_counting(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(limits.time, "monotonic", lambda: clock[0])
    monkeypatch.setitem(limits.LIMITS, "chat", (1, 60))
    limits.check("chat", "u1")
    clock[0] += 61
    limits.check("chat", "u1")

def test_api_returns_429_with_retry_after(client, auth, fake_ai, monkeypatch):
    monkeypatch.setitem(limits.LIMITS, "chat", (1, 3600))
    headers = auth()
    assert client.post("/api/chat", json={"message": "hi"}, headers=headers).status_code == 200
    response = client.post("/api/chat", json={"message": "hi"}, headers=headers)
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0

def test_new_users_are_limited_per_address(client, monkeypatch):
    monkeypatch.setitem(limits.LIMITS, "signup", (2, 3600))
    assert client.post("/api/users").status_code == 201
    assert client.post("/api/users").status_code == 201
    assert client.post("/api/users").status_code == 429

@pytest.mark.parametrize("path,body,action", [
    ("/api/repos", {"repo": REPO}, "index"),
    ("/api/jobs", {"text": "A long enough job description here."}, "job"),
    ("/api/analyses", {"job_id": 1, "repo_ids": [1]}, "analysis"),
])
def test_expensive_routes_are_limited(client, auth, monkeypatch, path, body, action):
    monkeypatch.setitem(limits.LIMITS, action, (0, 3600))
    assert client.post(path, json=body, headers=auth()).status_code == 429

# --- CACHE ---

class Reply(BaseModel):
    answer: str

@pytest.fixture
def counting_ai(monkeypatch):
    calls = []
    def generate_content(model, contents, config):
        calls.append(contents)
        return SimpleNamespace(text='{"answer": "yes"}', usage_metadata=None)
    def embed_content(model, contents, config):
        calls.append(contents)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.5]) for _ in contents])
    monkeypatch.setattr(coach, "client", SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content, embed_content=embed_content)))
    return calls

def test_identical_requests_are_answered_from_cache(counting_ai):
    usage = llm.Usage()
    assert llm.generate_json("same prompt", Reply, usage).answer == "yes"
    assert llm.generate_json("same prompt", Reply, usage).answer == "yes"
    assert len(counting_ai) == 1 and (usage.calls, usage.cached) == (1, 1)

def test_different_prompts_are_not_shared(counting_ai):
    llm.generate_json("prompt one", Reply)
    llm.generate_json("prompt two", Reply)
    assert len(counting_ai) == 2

def test_creative_requests_are_never_cached(counting_ai):
    llm.generate_json("p", Reply, temperature=0.7)
    llm.generate_json("p", Reply, temperature=0.7)
    assert len(counting_ai) == 2

def test_a_corrupt_cache_entry_is_ignored(counting_ai):
    cache.put("llm", ["Reply", "p"], "not json")
    assert llm.generate_json("p", Reply).answer == "yes"
    assert len(counting_ai) == 1

def test_embeddings_only_request_uncached_texts(counting_ai):
    embeddings.embed_documents(["a", "b"])
    counting_ai.clear()
    assert embeddings.embed_documents(["a", "b", "c"]) == [[0.5], [0.5], [0.5]]
    assert len(counting_ai) == 1 and len(counting_ai[0]) == 1

def test_storing_the_same_result_twice_is_harmless():
    cache.put("llm", ["x"], "1")
    cache.put("llm", ["x"], "2")
    assert cache.get("llm", ["x"]) == "1"
