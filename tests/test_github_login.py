from urllib.parse import parse_qs, urlparse
import httpx
import pytest
import respx
from codesynapse import config
from codesynapse.db.models import ChatMessage, Profile, User
from codesynapse.db.session import SessionLocal
from codesynapse.services import github_auth, users
from codesynapse.ui import app as ui
from codesynapse.ui import components

PUBLIC = "https://codesynapse.test"
GITHUB_USER = {"id": 4242, "login": "octocat"}

@pytest.fixture
def client():
    """Over https: the state cookie is Secure, so a browser only sends it back over https."""
    from fastapi.testclient import TestClient
    from codesynapse.main import app
    return TestClient(app, base_url="https://testserver")

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(config, "PUBLIC_URL", PUBLIC)
    github_auth._codes.clear()

@pytest.fixture
def github():
    with respx.mock(assert_all_called=False) as mock:
        mock.post(github_auth.TOKEN_URL).respond(200, json={"access_token": "gho_temporary"})
        mock.get(github_auth.USER_URL).respond(200, json=GITHUB_USER)
        yield mock

def query_of(response):
    return parse_qs(urlparse(response.headers["location"]).query)

def start(client):
    response = client.get("/auth/github/login", follow_redirects=False)
    return response, query_of(response)["state"][0]

# --- THE OAUTH ROUTES ---

def test_sign_in_is_off_until_configured(client):
    assert client.get("/auth/github/login", follow_redirects=False).status_code == 404
    assert client.get("/auth/github/callback?code=x&state=y", follow_redirects=False).status_code == 404
    assert components.account_html(None, configured=False) == ""

def test_sign_in_sends_the_browser_to_github_with_a_state_cookie(client, configured):
    response, state = start(client)
    assert response.status_code == 303 and response.headers["location"].startswith(github_auth.AUTHORIZE_URL)
    query = query_of(response)
    assert query["client_id"] == ["client-id"] and query["redirect_uri"] == [f"{PUBLIC}/auth/github/callback"]
    # No permissions are requested: only the public identity is read
    assert "scope" not in query
    cookie = response.headers["set-cookie"]
    assert state in cookie and "HttpOnly" in cookie and "Secure" in cookie

def test_a_callback_without_the_matching_state_is_refused(client, configured, github):
    start(client)
    response = client.get("/auth/github/callback?code=abc&state=forged", follow_redirects=False)
    assert query_of(response) == {"login_error": ["expired"]}
    assert not github.calls

def test_a_cancelled_sign_in_is_explained(client, configured):
    start(client)
    response = client.get("/auth/github/callback?error=access_denied&state=x", follow_redirects=False)
    assert query_of(response) == {"login_error": ["cancelled"]}

def test_a_failed_token_exchange_is_explained(client, configured, github):
    github.post(github_auth.TOKEN_URL).respond(200, json={"error": "bad_verification_code"})
    _, state = start(client)
    response = client.get(f"/auth/github/callback?code=abc&state={state}", follow_redirects=False)
    assert query_of(response) == {"login_error": ["github"]}

def test_a_successful_callback_returns_a_one_time_code_not_a_token(client, configured, github):
    _, state = start(client)
    response = client.get(f"/auth/github/callback?code=abc&state={state}", follow_redirects=False)
    assert response.headers["location"].startswith(f"{PUBLIC}/?login=")
    code = query_of(response)["login"][0]
    assert github_auth.take_login_code(code) == GITHUB_USER
    assert github_auth.take_login_code(code) is None
    # GitHub's access token was only used to read the identity
    assert github.calls.last.request.headers["authorization"] == "Bearer gho_temporary"

# --- LINKING ACCOUNTS ---

def anonymous_user_with_data():
    with SessionLocal() as db:
        user, token = users.create_user(db)
        db.add(ChatMessage(user_id=user.id, role="user", content="hello"))
        db.commit()
        return user.id, token

def test_signing_in_keeps_the_work_of_this_browser(configured):
    user_id, token = anonymous_user_with_data()
    code = github_auth.create_login_code(GITHUB_USER)
    with SessionLocal() as db:
        kept_token, user = github_auth.complete_login(db, token, code)
        assert kept_token == token and user.id == user_id
        assert (user.github_id, user.github_login) == (4242, "octocat")
        assert db.get(Profile, user_id).github == "octocat"
        assert db.query(ChatMessage).filter_by(user_id=user_id).count() == 1

def test_another_device_gets_its_own_token_for_the_same_account(configured):
    first_id, first_token = anonymous_user_with_data()
    with SessionLocal() as db:
        github_auth.complete_login(db, first_token, github_auth.create_login_code(GITHUB_USER))
        _, phone_token = users.create_user(db)
        token, user = github_auth.complete_login(db, phone_token, github_auth.create_login_code(GITHUB_USER))
        assert user.id == first_id and token != first_token
        # Both devices stay signed in
        assert users.get_user_by_token(db, token).id == first_id
        assert users.get_user_by_token(db, first_token).id == first_id

def test_signing_in_again_on_the_same_browser_changes_nothing(configured):
    _, token = anonymous_user_with_data()
    with SessionLocal() as db:
        github_auth.complete_login(db, token, github_auth.create_login_code(GITHUB_USER))
        again, _ = github_auth.complete_login(db, token, github_auth.create_login_code(GITHUB_USER))
        assert again == token

def test_a_used_or_expired_code_is_refused(configured, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(github_auth.time, "monotonic", lambda: clock[0])
    code = github_auth.create_login_code(GITHUB_USER)
    clock[0] += github_auth.CODE_SECONDS + 1
    with SessionLocal() as db:
        with pytest.raises(github_auth.LoginError, match="expired"):
            github_auth.complete_login(db, None, code)

def test_a_new_visitor_signing_in_gets_an_account(configured):
    with SessionLocal() as db:
        token, user = github_auth.complete_login(db, None, github_auth.create_login_code(GITHUB_USER))
        assert users.get_user_by_token(db, token).id == user.id and user.github_login == "octocat"
        assert db.query(User).count() == 1

# --- THE INTERFACE ---

def test_the_page_finishes_sign_in_from_its_one_time_code(configured):
    _, token = anonymous_user_with_data()
    code = github_auth.create_login_code(GITHUB_USER)
    assert ui.complete_login_logic(token, code, "") == token
    with SessionLocal() as db:
        assert users.get_user_by_token(db, token).github_login == "octocat"

def test_the_page_keeps_its_token_when_sign_in_fails(configured):
    assert ui.complete_login_logic("tok", "", "cancelled") == "tok"
    assert ui.complete_login_logic("tok", "no-such-code", "") == "tok"
    assert ui.complete_login_logic("tok", "", "") == "tok"

def test_the_account_area():
    signed_in = components.account_html("octo<cat>", configured=True)
    assert "@octo&lt;cat&gt;" in signed_in and "Sign in" not in signed_in
    button = components.account_html(None, configured=True)
    assert 'href="/auth/github/login"' in button and 'target="_top"' in button

def test_an_unreachable_github_sends_the_user_back_with_a_reason(client, configured):
    with respx.mock() as mock:
        mock.post(github_auth.TOKEN_URL).mock(side_effect=httpx.ConnectError("down"))
        _, state = start(client)
        response = client.get(f"/auth/github/callback?code=abc&state={state}", follow_redirects=False)
    assert query_of(response) == {"login_error": ["github"]}
