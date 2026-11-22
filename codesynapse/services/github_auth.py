"""Sign in with GitHub, so a user's data follows them across browsers and devices.

The OAuth flow asks for no permissions: it only learns the GitHub account's id and login.
GitHub's access token is used once for that and never stored.

The browser never sees a CodeSynapse token in a URL. After GitHub sends the user back, the
callback hands the page a one-time code that expires in a few minutes; the page swaps it
for the token through complete_login, which also links an anonymous browser's existing
data to the GitHub account.
"""
import secrets
import threading
import time
from urllib.parse import urlencode
import httpx
from sqlalchemy.orm import Session
from codesynapse import config
from codesynapse.db.models import Profile
from codesynapse.services import users

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
STATE_COOKIE = "cs_oauth_state"
STATE_SECONDS = 10 * 60
CODE_SECONDS = 5 * 60

class LoginError(Exception):
    """A message to show the user when sign-in can't finish."""

def is_configured():
    return bool(config.GITHUB_CLIENT_ID and config.GITHUB_CLIENT_SECRET and config.PUBLIC_URL)

def callback_url():
    return f"{config.PUBLIC_URL}/auth/github/callback"

def authorize_url(state):
    query = {"client_id": config.GITHUB_CLIENT_ID, "redirect_uri": callback_url(), "state": state,
             "allow_signup": "true"}
    return f"{AUTHORIZE_URL}?{urlencode(query)}"

def new_state():
    return secrets.token_urlsafe(24)

def states_match(cookie_value, query_value):
    return bool(cookie_value and query_value) and secrets.compare_digest(cookie_value, query_value)

def fetch_identity(code):
    """Exchanges GitHub's code for the account's id and login. The access token is discarded."""
    try:
        return _fetch_identity(code)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        raise LoginError("Couldn't reach GitHub to finish signing in. Please try again.") from e

def _fetch_identity(code):
    with httpx.Client(timeout=15) as client:
        response = client.post(TOKEN_URL, headers={"Accept": "application/json"}, data={
            "client_id": config.GITHUB_CLIENT_ID, "client_secret": config.GITHUB_CLIENT_SECRET,
            "code": code, "redirect_uri": callback_url(),
        })
        access_token = response.json().get("access_token") if response.status_code == 200 else None
        if not access_token:
            raise LoginError("GitHub didn't confirm the sign-in. Please try again.")
        user = client.get(USER_URL, headers={"Authorization": f"Bearer {access_token}",
                                             "Accept": "application/vnd.github+json"})
    if user.status_code != 200:
        raise LoginError("Couldn't read your GitHub account. Please try again.")
    data = user.json()
    return {"id": int(data["id"]), "login": data["login"]}

# One-time codes waiting to be swapped for a token. In memory, like the rate limits:
# they only need to survive the few seconds between GitHub's redirect and the page load.
_codes = {}
_lock = threading.Lock()

def create_login_code(identity):
    code = secrets.token_urlsafe(32)
    with _lock:
        now = time.monotonic()
        for stale in [c for c, (_, expires) in _codes.items() if expires < now]:
            del _codes[stale]
        _codes[code] = (identity, now + CODE_SECONDS)
    return code

def take_login_code(code):
    """Returns the identity for a code once; a used or expired code gives None."""
    with _lock:
        entry = _codes.pop(code or "", None)
    if not entry or entry[1] < time.monotonic():
        return None
    return entry[0]

def complete_login(db: Session, current_token, code):
    """Finishes sign-in for this browser. Returns (token, user) for the browser to keep.

    A GitHub account already linked to a user signs this browser in as that user, with a
    token of its own. Otherwise this browser's user, with any work it has, becomes linked.
    """
    identity = take_login_code(code)
    if not identity:
        raise LoginError("That sign-in link has expired. Please sign in again.")
    current = users.get_user_by_token(db, current_token)
    linked = users.get_user_by_github_id(db, identity["id"])
    if linked:
        linked.github_login = identity["login"]
        db.commit()
        if current and current.id == linked.id:
            return current_token, linked
        return users.issue_token(db, linked), linked

    token = current_token
    if not current:
        current, token = users.create_user(db)
    current.github_id, current.github_login = identity["id"], identity["login"]
    # Saves typing: the Profile tab can sync this account straight away
    profile = db.get(Profile, current.id)
    if profile is None:
        db.add(Profile(user_id=current.id, github=identity["login"], leetcode=""))
    elif not profile.github:
        profile.github = identity["login"]
    db.commit()
    return token, current
