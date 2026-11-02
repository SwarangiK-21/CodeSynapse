import io
import tarfile
import pytest
import respx
from codesynapse.db.models import EMBEDDING_DIM
from codesynapse.services import repos

REPO = "octocat/demo"
SHA = "a" * 40

def archive(files, links=()):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path, data in files.items():
            info = tarfile.TarInfo(f"demo-{SHA}/{path}")
            raw = data if isinstance(data, bytes) else data.encode()
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
        for path, target in links:
            info = tarfile.TarInfo(f"demo-{SHA}/{path}")
            info.type, info.linkname = tarfile.SYMTYPE, target
            tar.addfile(info)
    return buffer.getvalue()

FILES = {
    "src/retry.py": "def retry_request():\n    try:\n        call()\n    except TimeoutError:\n        pass\n",
    "src/payment.py": "def charge_card(amount):\n    return amount\n",
    "node_modules/dep/index.js": "function vendored() {}\n",
    "logo.png": b"\x89PNG\0binary",
    "lib/data.py": b"def x():\0 pass",
}

def mock_github(m, name=REPO, files=FILES):
    m.get(f"https://api.github.com/repos/{name}").respond(json={"default_branch": "main"})
    m.get(f"https://api.github.com/repos/{name}/commits/main").respond(json={"sha": SHA})
    m.get(f"https://codeload.github.com/{name}/tar.gz/{SHA}").respond(content=archive(files))

@pytest.fixture
def github():
    with respx.mock(assert_all_called=False) as m:
        mock_github(m)
        yield m

@pytest.mark.parametrize("value,expected", [
    ("octocat/demo", "octocat/demo"),
    ("https://github.com/octocat/demo", "octocat/demo"),
    ("https://github.com/octocat/demo.git", "octocat/demo"),
    ("https://github.com/octocat/demo/", "octocat/demo"),
])
def test_repo_names(value, expected):
    assert repos.parse_name(value) == expected

@pytest.mark.parametrize("value", ["octocat", "../../etc/passwd", "a/b/c", "https://evil.com/a/b", "a b/c"])
def test_bad_repo_names(value):
    with pytest.raises(repos.RepoError):
        repos.parse_name(value)

def test_reads_only_source_files():
    paths = [p for p, _ in repos.read_source_files(archive(FILES))]
    assert paths == ["src/retry.py", "src/payment.py"]

def test_ignores_links_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = [p for p, _ in repos.read_source_files(archive({"a.py": "x = 1\n"}, [("evil.py", "/etc/passwd")]))]
    assert paths == ["a.py"]
    assert list(tmp_path.iterdir()) == []

def test_skips_oversized_files():
    assert list(repos.read_source_files(archive({"big.py": "x" * (repos.MAX_FILE_BYTES + 1)}))) == []

def test_rejects_too_many_files(monkeypatch):
    monkeypatch.setattr(repos, "MAX_FILES", 1)
    with pytest.raises(repos.RepoError):
        list(repos.read_source_files(archive({"a.py": "1", "b.py": "2"})))

def test_rejects_decompression_bombs(monkeypatch):
    monkeypatch.setattr(repos, "MAX_UNPACKED_BYTES", 10)
    with pytest.raises(repos.RepoError):
        list(repos.read_source_files(archive({"a.py": "x" * 100})))

def test_index_and_list(client, auth, github):
    headers = auth()
    body = client.post("/api/repos", json={"repo": REPO}, headers=headers).json()
    assert body["full_name"] == REPO and body["commit_sha"] == SHA
    assert body["chunks"] == 2 and body["embedded_chunks"] == 0
    assert client.get("/api/repos", headers=headers).json()["repos"][0]["id"] == body["id"]

def test_unknown_repo_is_reported(client, auth):
    with respx.mock(assert_all_called=False) as m:
        m.get(f"https://api.github.com/repos/{REPO}").respond(404)
        response = client.post("/api/repos", json={"repo": REPO}, headers=auth())
    assert response.status_code == 422 and "not found" in response.json()["detail"]

def test_reindexing_replaces_chunks(client, auth, github):
    headers = auth()
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    body = client.post("/api/repos", json={"repo": REPO}, headers=headers).json()
    assert body["chunks"] == 2
    assert len(client.get("/api/repos", headers=headers).json()["repos"]) == 1

def test_keyword_search_finds_the_right_function(client, auth, github):
    headers = auth()
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    top = client.get("/api/search", params={"q": "retry timeout"}, headers=headers).json()["results"][0]
    assert (top["path"], top["symbol"], top["start_line"]) == ("src/retry.py", "retry_request", 1)
    assert top["matched_by"] == ["keyword"]

def test_search_with_no_match_is_empty(client, auth, github):
    headers = auth()
    client.post("/api/repos", json={"repo": REPO}, headers=headers)
    assert client.get("/api/search", params={"q": "kubernetes"}, headers=headers).json()["results"] == []

def test_search_before_indexing_is_empty(client, auth):
    assert client.get("/api/search", params={"q": "retry"}, headers=auth()).json()["results"] == []

def test_vector_search_finds_meaning_without_shared_words(client, auth, github, monkeypatch):
    def fake_embed(texts, task_type, retries=0):
        def vector(text):
            v = [0.0] * EMBEDDING_DIM
            v[0 if "retry" in text or "resilience" in text else 1] = 1.0
            return v
        return [vector(t) for t in texts]
    monkeypatch.setattr("codesynapse.services.embeddings.embed_texts", fake_embed)

    headers = auth()
    body = client.post("/api/repos", json={"repo": REPO}, headers=headers).json()
    assert body["embedded_chunks"] == 2
    top = client.get("/api/search", params={"q": "resilience"}, headers=headers).json()["results"][0]
    assert top["path"] == "src/retry.py" and top["matched_by"] == ["vector"]

def test_users_cannot_see_each_others_repos(client, auth, github):
    alice, bob = auth(), auth()
    repo_id = client.post("/api/repos", json={"repo": REPO}, headers=alice).json()["id"]

    assert client.get("/api/repos", headers=bob).json() == {"repos": []}
    assert client.get("/api/search", params={"q": "retry"}, headers=bob).json()["results"] == []
    assert client.get("/api/search", params={"q": "retry", "repo_id": repo_id}, headers=bob).json()["results"] == []
    assert client.delete(f"/api/repos/{repo_id}", headers=bob).status_code == 404
    assert client.get("/api/search", params={"q": "retry"}, headers=alice).json()["results"]

def test_delete_repo(client, auth, github):
    headers = auth()
    repo_id = client.post("/api/repos", json={"repo": REPO}, headers=headers).json()["id"]
    assert client.delete(f"/api/repos/{repo_id}", headers=headers).status_code == 204
    assert client.get("/api/search", params={"q": "retry"}, headers=headers).json()["results"] == []

def test_fusion_rewards_agreement():
    from codesynapse.services.search import fuse
    assert fuse([[1, 2], [2, 3]])[0][0] == 2

def test_tokenize_splits_identifiers():
    from codesynapse.services.search import tokenize
    assert tokenize("getUserName get_user_name") == ["get", "user", "name", "get", "user", "name"]
