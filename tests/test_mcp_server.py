import asyncio
import json
import httpx
import pytest
import respx
from codesynapse import mcp_server as ms

URL = "https://codesynapse.test"
REPO = {"id": 1, "full_name": "pallets/itsdangerous", "commit_sha": "a" * 40, "status": "ready", "error": "",
        "chunks": 169, "embedded_chunks": 169}
REPORT = {
    "kind": "resume", "job_title": "Resume: pasted text", "summary": "Two of three claims are backed by code.",
    "recommendations": [{"skill": "Redis", "priority": "high", "action": "Add a Redis cache."}],
    "skills": [
        {"name": "HMAC", "importance": "required", "level": "strong", "confidence": 0.93, "missing": [],
         "citations": [{"claim": f"c{i}", "path": "signer.py", "start_line": i, "url": f"https://github.com/x#L{i}"}
                       for i in range(5)]},
        {"name": "Redis", "importance": "required", "level": "none", "confidence": 0.07,
         "missing": ["No Redis usage"], "citations": []},
    ],
}

@pytest.fixture
def api(tmp_path, monkeypatch):
    """A mocked CodeSynapse, and a client that keeps its token in a temporary file."""
    monkeypatch.delenv("CODESYNAPSE_TOKEN", raising=False)
    monkeypatch.setattr(ms, "POLL_SECONDS", 0)
    with respx.mock(base_url=URL, assert_all_called=False) as mock:
        mock.post("/api/users", name="create_user").respond(201, json={"user_id": "u", "token": "tok-1"})
        mock.get("/api/repos").respond(200, json={"repos": [REPO]})
        client = ms.Client(URL, token_file=tmp_path / "token")
        monkeypatch.setattr(ms, "_client", client)
        yield mock

def call(name, **arguments):
    """Calls a tool the way an assistant would, through the MCP server."""
    return asyncio.run(ms.server.call_tool(name, arguments))

# --- THE SERVER ---

def test_the_server_offers_every_tool_with_a_description():
    tools = {t.name: t for t in asyncio.run(ms.server.list_tools())}
    assert set(tools) == {"index_repository", "list_repositories", "search_code", "start_skill_check",
                          "start_resume_check", "get_report"}
    assert all(t.description for t in tools.values())
    assert tools["search_code"].annotations.read_only_hint
    assert tools["get_report"].annotations.read_only_hint
    assert not tools["index_repository"].annotations.destructive_hint

# --- TOKEN HANDLING ---

def test_a_token_is_created_once_and_saved_privately(api, tmp_path):
    client = ms.client()
    assert client.token() == "tok-1"
    saved = tmp_path / "token"
    assert saved.read_text() == "tok-1"
    # A second client reuses the saved token instead of creating another user
    assert ms.Client(URL, token_file=saved).token() == "tok-1"
    assert api.routes["create_user"].call_count == 1

def test_a_given_token_is_used_and_never_replaced(api, tmp_path):
    client = ms.Client(URL, token="mine", token_file=tmp_path / "token")
    api.get("/api/profile").respond(401, json={"detail": "Invalid or missing token"})
    with pytest.raises(ms.ToolError, match="401"):
        client.request("GET", "/api/profile")
    assert not (tmp_path / "token").exists()

def test_a_stale_saved_token_is_replaced(api, tmp_path):
    (tmp_path / "token").write_text("old")
    client = ms.Client(URL, token_file=tmp_path / "token")
    route = api.get("/api/profile")
    route.side_effect = [httpx.Response(401, json={"detail": "x"}), httpx.Response(200, json={"github": ""})]
    assert client.request("GET", "/api/profile") == {"github": ""}
    assert (tmp_path / "token").read_text() == "tok-1"

def test_errors_carry_the_api_explanation(api):
    api.get("/api/search").respond(429, json={"detail": "Please try again in about 3 minutes."})
    with pytest.raises(ms.ToolError, match="Rate limited: Please try again"):
        ms.client().request("GET", "/api/search")

def test_an_unreachable_server_is_explained(api):
    api.get("/api/chat").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(ms.ToolError, match="Could not reach CodeSynapse"):
        ms.client().request("GET", "/api/chat")

# --- TOOLS ---

def test_index_repository_waits_until_ready(api):
    start = api.post("/api/repos").respond(202, json={**REPO, "status": "indexing", "chunks": 0})
    result = ms.index_repository("https://github.com/pallets/itsdangerous.git", wait_seconds=5)
    assert result["status"] == "ready" and result["code_chunks"] == 169
    assert json.loads(start.calls.last.request.content) == {"repo": "pallets/itsdangerous"}

def test_search_links_each_result_to_its_lines(api):
    api.get("/api/search").respond(200, json={"results": [
        {"repo": "pallets/itsdangerous", "path": "src/signer.py", "start_line": 10, "end_line": 20,
         "symbol": "Signer.sign", "snippet": "def sign(self):"}]})
    [hit] = ms.search_code("signing", repo="pallets/itsdangerous")
    assert hit["url"] == f"https://github.com/pallets/itsdangerous/blob/{'a' * 40}/src/signer.py#L10-L20"
    assert dict(api.calls.last.request.url.params) == {"q": "signing", "limit": "8", "repo_id": "1"}

def test_checks_need_indexed_repositories(api):
    with pytest.raises(ms.ToolError, match="isn't indexed yet"):
        ms.start_skill_check("A job description long enough.", ["octocat/unknown"])

def test_a_repository_still_indexing_is_explained(api):
    api.get("/api/repos").respond(200, json={"repos": [{**REPO, "status": "indexing"}]})
    with pytest.raises(ms.ToolError, match="is indexing"):
        ms.start_skill_check("A job description long enough.", ["pallets/itsdangerous"])

def test_start_skill_check_returns_an_id_to_collect_later(api):
    api.post("/api/jobs").respond(201, json={"id": 4, "skills": [{"name": "HMAC"}]})
    api.post("/api/analyses").respond(202, json={"id": 9, "status": "running"})
    result = ms.start_skill_check("Python developer with HMAC experience.", ["pallets/itsdangerous"])
    assert result["analysis_id"] == 9 and result["checking"] == ["HMAC"] and "get_report" in result["next"]
    assert json.loads(api.calls.last.request.content) == {"job_id": 4, "repo_ids": [1]}

def test_start_resume_check_sends_the_text_as_a_form(api):
    resumes = api.post("/api/resumes").respond(201, json={"id": 5, "skills": [{"name": "Redis"}]})
    api.post("/api/analyses").respond(202, json={"id": 10, "status": "running"})
    assert ms.start_resume_check("I built caching layers with Redis.", ["pallets/itsdangerous"])["analysis_id"] == 10
    assert b"text=" in resumes.calls.last.request.content

def test_get_report_while_running_and_after_failing(api):
    api.get("/api/analyses/1").respond(200, json={"status": "running", "error": "", "report": {}})
    api.get("/api/analyses/2").respond(200, json={"status": "failed", "error": "Quota used up", "report": {}})
    assert ms.get_report(1)["status"] == "running"
    assert ms.get_report(2) == {"status": "failed", "error": "Quota used up"}

def test_get_report_is_compact_and_keeps_the_evidence_links(api):
    api.get("/api/analyses/3").respond(200, json={"status": "draft", "error": "", "report": REPORT})
    report = ms.get_report(3)
    assert report["kind"] == "resume" and report["recommendations"][0]["skill"] == "Redis"
    hmac, redis = report["skills"]
    assert len(hmac["evidence"]) == ms.MAX_CITATIONS and hmac["evidence"][0]["url"].startswith("https://github.com/")
    assert hmac["likely_present"] == 0.93 and redis["not_found"] == ["No Redis usage"]

def test_tool_errors_reach_the_assistant_with_their_explanation(api):
    from mcp.server.mcpserver.exceptions import UnexpectedToolError
    with pytest.raises(ms.ToolError, match="isn't indexed yet") as error:
        call("start_skill_check", job_description="A job description long enough.", repos=["octocat/unknown"])
    # An unexpected error would reach the assistant only as "Error executing tool"
    assert not isinstance(error.value, UnexpectedToolError)

def test_short_names_from_links():
    assert ms.short_name("https://github.com/pallets/itsdangerous.git/") == "pallets/itsdangerous"
    assert ms.short_name("pallets/itsdangerous/tree/main") == "pallets/itsdangerous"
