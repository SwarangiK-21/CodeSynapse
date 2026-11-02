import pytest
from sqlalchemy import select
from codesynapse.db.models import User
from codesynapse.db.session import SessionLocal

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

@pytest.mark.parametrize("method,path", [
    ("get", "/api/profile"), ("put", "/api/profile"), ("get", "/api/chat"),
    ("post", "/api/chat"), ("delete", "/api/chat"), ("get", "/api/report"),
])
def test_routes_require_a_token(client, method, path):
    assert client.request(method, path).status_code == 401

def test_wrong_token_is_rejected(client):
    assert client.get("/api/profile", headers={"Authorization": "Bearer nope"}).status_code == 401

def test_raw_token_is_not_stored(client):
    token = client.post("/api/users").json()["token"]
    with SessionLocal() as db:
        assert db.scalar(select(User)).token_hash != token

def test_profile_sync_and_read(client, auth, fake_stats):
    headers = auth()
    assert client.put("/api/profile", json={"github": "octocat"}, headers=headers).status_code == 200
    body = client.get("/api/profile", headers=headers).json()
    assert body["github"] == "octocat"
    assert body["stats"][0]["stats"]["Public Repos"] == 7

def test_resync_updates_rather_than_duplicates(client, auth, fake_stats):
    headers = auth()
    client.put("/api/profile", json={"github": "first"}, headers=headers)
    client.put("/api/profile", json={"github": "second"}, headers=headers)
    assert client.get("/api/profile", headers=headers).json()["github"] == "second"

@pytest.mark.parametrize("body", [
    {"github": "../rate_limit"}, {"github": "a/b"}, {"github": "x" * 40},
    {"leetcode": "bad name"}, {"leetcode": "a?b"},
])
def test_invalid_usernames_never_reach_a_fetcher(client, auth, monkeypatch, body):
    async def fail(usernames):
        raise AssertionError("fetcher should not be called")
    monkeypatch.setattr("codesynapse.services.fetchers.get_all_stats", fail)
    assert client.put("/api/profile", json=body, headers=auth()).status_code == 422

def test_chat_sends_stats_and_history_to_ai(client, auth, fake_stats, fake_ai):
    headers = auth()
    client.put("/api/profile", json={"github": "octocat"}, headers=headers)
    reply = client.post("/api/chat", json={"message": "first"}, headers=headers).json()["reply"]
    client.post("/api/chat", json={"message": "second"}, headers=headers)

    assert reply == "Keep going\n\n• Build a project"
    assert fake_ai[0]["stats"][0]["platform"] == "GitHub"
    assert [m["content"] for m in fake_ai[1]["history"]] == ["first", reply]

def test_chat_rejects_empty_and_huge_messages(client, auth, fake_ai):
    headers = auth()
    assert client.post("/api/chat", json={"message": ""}, headers=headers).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 2001}, headers=headers).status_code == 422
    assert fake_ai == []

def test_clear_chat(client, auth, fake_ai):
    headers = auth()
    client.post("/api/chat", json={"message": "hi"}, headers=headers)
    assert client.delete("/api/chat", headers=headers).status_code == 204
    assert client.get("/api/chat", headers=headers).json() == {"messages": []}

def test_report_needs_a_profile(client, auth):
    assert client.get("/api/report", headers=auth()).status_code == 404

def test_report_is_a_pdf(client, auth, fake_stats):
    headers = auth()
    client.put("/api/profile", json={"github": "octocat"}, headers=headers)
    response = client.get("/api/report", headers=headers)
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

def test_two_users_cannot_see_each_others_data(client, auth, fake_stats, fake_ai):
    alice, bob = auth(), auth()
    client.put("/api/profile", json={"github": "alice"}, headers=alice)
    client.put("/api/profile", json={"github": "bobby-long-name"}, headers=bob)
    client.post("/api/chat", json={"message": "alice secret"}, headers=alice)
    client.post("/api/chat", json={"message": "bob question"}, headers=bob)

    assert client.get("/api/profile", headers=alice).json()["github"] == "alice"
    assert client.get("/api/profile", headers=bob).json()["github"] == "bobby-long-name"

    bob_messages = str(client.get("/api/chat", headers=bob).json())
    assert "alice secret" not in bob_messages
    assert fake_ai[1]["history"] == []
    assert fake_ai[1]["stats"][0]["stats"]["Public Repos"] == len("bobby-long-name")

    client.delete("/api/chat", headers=bob)
    assert "alice secret" in str(client.get("/api/chat", headers=alice).json())
