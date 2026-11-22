"""Routes for "Sign in with GitHub". See services/github_auth.py for the flow."""
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from codesynapse import config
from codesynapse.services import github_auth

router = APIRouter(prefix="/auth/github", include_in_schema=False)

def back_to_app(**query):
    return RedirectResponse(f"{config.PUBLIC_URL}/?{urlencode(query)}", status_code=303)

@router.get("/login")
def start_login():
    if not github_auth.is_configured():
        raise HTTPException(404, "GitHub sign-in is not set up on this server.")
    state = github_auth.new_state()
    response = RedirectResponse(github_auth.authorize_url(state), status_code=303)
    # Ties GitHub's reply to this browser, so another site can't complete a sign-in here
    response.set_cookie(github_auth.STATE_COOKIE, state, max_age=github_auth.STATE_SECONDS, httponly=True,
                        secure=config.PUBLIC_URL.startswith("https://"), samesite="lax", path="/auth/github")
    return response

@router.get("/callback")
def finish_login(request: Request, code: str = "", state: str = "", error: str = ""):
    if not github_auth.is_configured():
        raise HTTPException(404, "GitHub sign-in is not set up on this server.")
    if error:
        response = back_to_app(login_error="cancelled")
    elif not github_auth.states_match(request.cookies.get(github_auth.STATE_COOKIE), state) or not code:
        response = back_to_app(login_error="expired")
    else:
        try:
            identity = github_auth.fetch_identity(code)
        except github_auth.LoginError:
            response = back_to_app(login_error="github")
        else:
            response = back_to_app(login=github_auth.create_login_code(identity))
    response.delete_cookie(github_auth.STATE_COOKIE, path="/auth/github")
    return response
