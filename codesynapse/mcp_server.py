"""CodeSynapse as an MCP server, so AI assistants can check code evidence for you.

Assistants such as Claude Desktop, Claude Code or Cursor start this as a local process and
call its tools in plain conversation ("check my repo against this job post"). It talks to
a running CodeSynapse over its REST API, the live demo by default:

    python -m codesynapse.mcp_server

Settings, all optional:
    CODESYNAPSE_URL    the CodeSynapse to use (default: the live demo)
    CODESYNAPSE_TOKEN  an existing user token; otherwise one is created on first use and
                       kept in ~/.codesynapse/token, readable only by you

Analyses take minutes, longer than an assistant waits for one call, so they are started by
one tool and collected by another.
"""
import logging
import os
import time
from pathlib import Path
import httpx
from mcp.server.mcpserver import MCPServer
# Raising this sends its message to the assistant; other exceptions are hidden as "unexpected"
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

DEFAULT_URL = "https://swarangik-21-codesynapse.hf.space"
# httpx logs every request URL, search text included, which clutters the assistant's server log
logging.getLogger("httpx").setLevel(logging.WARNING)
TOKEN_FILE = Path.home() / ".codesynapse" / "token"
POLL_SECONDS = 3
MAX_CITATIONS = 3

class Client:
    """A small CodeSynapse REST client that looks after the user token."""

    def __init__(self, base_url=None, token=None, token_file=TOKEN_FILE, http=None):
        self.base_url = (base_url or os.getenv("CODESYNAPSE_URL") or DEFAULT_URL).rstrip("/")
        self.fixed_token = token or os.getenv("CODESYNAPSE_TOKEN")
        self.token_file = token_file
        # Waking a sleeping demo can take a while
        self.http = http or httpx.Client(timeout=120)
        self._token = None

    def token(self):
        if self.fixed_token:
            return self.fixed_token
        if self._token:
            return self._token
        if self.token_file.exists():
            self._token = self.token_file.read_text(encoding="utf-8").strip()
            return self._token
        return self.new_token()

    def new_token(self):
        response = self.http.post(f"{self.base_url}/api/users")
        self.check(response)
        self._token = response.json()["token"]
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(self._token, encoding="utf-8")
        # The token is a password for this user's data
        self.token_file.chmod(0o600)
        return self._token

    def request(self, method, path, **kwargs):
        response = self.send(method, path, **kwargs)
        if response.status_code == 401 and not self.fixed_token:
            # A saved token can belong to a database that was reset: start a fresh user
            self.new_token()
            response = self.send(method, path, **kwargs)
        self.check(response)
        return response.json() if response.content else None

    def send(self, method, path, **kwargs):
        headers = {"Authorization": f"Bearer {self.token()}"}
        try:
            return self.http.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        except httpx.TransportError as e:
            raise ToolError(f"Could not reach CodeSynapse at {self.base_url}: {e}") from e

    @staticmethod
    def check(response):
        if response.status_code < 400:
            return
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        if response.status_code == 429:
            raise ToolError(f"Rate limited: {detail or 'too many requests'}")
        raise ToolError(f"CodeSynapse error {response.status_code}: {detail or response.text[:200]}")

_client = None

def client():
    global _client
    _client = _client or Client()
    return _client

# --- HELPERS ---

def repos_by_name():
    return {r["full_name"].lower(): r for r in client().request("GET", "/api/repos")["repos"]}

def short_name(value):
    """Accepts owner/repo or a github.com link."""
    value = value.strip().removesuffix("/").removesuffix(".git")
    if "github.com/" in value:
        value = value.split("github.com/", 1)[1]
    return "/".join(value.split("/")[:2])

def ready_repo_ids(repos):
    """Ids of the named repositories, which must already be indexed."""
    known = repos_by_name()
    ids = []
    for name in repos:
        repo = known.get(short_name(name).lower())
        if not repo:
            raise ToolError(f"{name} isn't indexed yet. Call index_repository first.")
        if repo["status"] != "ready":
            raise ToolError(f"{name} is {repo['status']}{': ' + repo['error'] if repo['error'] else ''}. "
                            "Wait for indexing to finish, or index it again.")
        ids.append(repo["id"])
    return ids

def start_analysis(job, repo_ids):
    analysis = client().request("POST", "/api/analyses", json={"job_id": job["id"], "repo_ids": repo_ids})
    return {
        "analysis_id": analysis["id"],
        "checking": [s["name"] for s in job["skills"]],
        "next": "This takes a few minutes. Call get_report with this analysis_id to see progress and the result.",
    }

def compact_skill(skill):
    citations = [{"claim": c["claim"], "code": f"{c['path']}:{c['start_line']}", "url": c["url"]}
                 for c in skill["citations"][:MAX_CITATIONS]]
    return {
        "name": skill["name"], "importance": skill["importance"], "level": skill["level"],
        "likely_present": skill.get("confidence"),
        "evidence": citations, "not_found": skill["missing"],
    }

# --- TOOLS ---

server = MCPServer(
    "CodeSynapse",
    instructions=(
        "CodeSynapse checks real code for evidence of skills. Index public GitHub repositories first, "
        "then search them, or start a skill check against a job description or resume and collect it "
        "with get_report. Every piece of evidence links to exact lines on GitHub; 'none' means no "
        "evidence was found in the code searched, not that the person lacks the skill."
    ),
)

@server.tool(annotations=ToolAnnotations(title="Index a repository", read_only_hint=False,
                                         destructive_hint=False, idempotent_hint=True, open_world_hint=True))
def index_repository(repo: str, wait_seconds: int = 120) -> dict:
    """Adds a public GitHub repository (owner/repo or a link) to CodeSynapse so it can be searched.

    Waits up to wait_seconds for indexing to finish; large repositories may still be indexing
    when it returns, so call it again to check.
    """
    name = short_name(repo)
    record = client().request("POST", "/api/repos", json={"repo": name})
    deadline = time.monotonic() + max(0, min(wait_seconds, 600))
    while record["status"] == "indexing" and time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        record = repos_by_name().get(name.lower(), record)
    return {"repo": record["full_name"], "status": record["status"], "error": record["error"] or None,
            "code_chunks": record["chunks"], "with_vectors": record["embedded_chunks"]}

@server.tool(annotations=ToolAnnotations(title="List indexed repositories", read_only_hint=True))
def list_repositories() -> list[dict]:
    """Lists the repositories indexed for you, with their status and commit."""
    return [{"repo": r["full_name"], "status": r["status"], "commit": r["commit_sha"][:7], "code_chunks": r["chunks"]}
            for r in repos_by_name().values()]

@server.tool(annotations=ToolAnnotations(title="Search code", read_only_hint=True))
def search_code(query: str, repo: str | None = None, limit: int = 8) -> list[dict]:
    """Searches indexed code by keywords and meaning, for example "retry with backoff" or "JWT validation".

    Optionally limit it to one indexed repository. Each result links to the exact lines on GitHub.
    """
    known = repos_by_name()
    params = {"q": query, "limit": max(1, min(limit, 20))}
    if repo:
        params["repo_id"] = ready_repo_ids([repo])[0]
    results = client().request("GET", "/api/search", params=params)["results"]
    shas = {r["full_name"]: r["commit_sha"] for r in known.values()}
    return [{
        "repo": r["repo"], "code": f"{r['path']}:{r['start_line']}-{r['end_line']}", "symbol": r["symbol"],
        "url": f"https://github.com/{r['repo']}/blob/{shas.get(r['repo'], 'HEAD')}/{r['path']}"
               f"#L{r['start_line']}-L{r['end_line']}",
        "snippet": r["snippet"][:400],
    } for r in results]

@server.tool(annotations=ToolAnnotations(title="Start a skill check", read_only_hint=False,
                                         destructive_hint=False, open_world_hint=True))
def start_skill_check(job_description: str, repos: list[str]) -> dict:
    """Starts checking indexed repositories against a job description's skills.

    Returns an analysis_id at once; the check takes a few minutes, so collect it with get_report.
    """
    repo_ids = ready_repo_ids(repos)
    job = client().request("POST", "/api/jobs", json={"text": job_description})
    if not job["skills"]:
        raise ToolError("No skills were found in that job description.")
    return start_analysis(job, repo_ids)

@server.tool(annotations=ToolAnnotations(title="Start a resume check", read_only_hint=False,
                                         destructive_hint=False, open_world_hint=True))
def start_resume_check(resume_text: str, repos: list[str]) -> dict:
    """Starts checking each technical claim on a resume against indexed repositories.

    Only the extracted claims are stored, not the resume. Returns an analysis_id at once;
    collect the result with get_report.
    """
    repo_ids = ready_repo_ids(repos)
    record = client().request("POST", "/api/resumes", data={"text": resume_text})
    return start_analysis(record, repo_ids)

@server.tool(annotations=ToolAnnotations(title="Get a report", read_only_hint=True))
def get_report(analysis_id: int) -> dict:
    """Returns a skill or resume check: still running, failed, or the finished report.

    Each skill has a level (strong, partial or none), a calibrated likelihood when available,
    and evidence linking to exact lines. "none" means nothing was found in the code searched.
    """
    analysis = client().request("GET", f"/api/analyses/{analysis_id}")
    if analysis["status"] == "running":
        return {"status": "running", "next": "Still working. Call get_report again in a minute."}
    if analysis["status"] == "failed":
        return {"status": "failed", "error": analysis["error"]}
    report = analysis["report"]
    return {
        "status": analysis["status"],
        "kind": report.get("kind", "job"),
        "title": report["job_title"],
        "summary": report["summary"],
        "skills": [compact_skill(s) for s in report["skills"]],
        "recommendations": report["recommendations"],
    }

if __name__ == "__main__":
    server.run()
