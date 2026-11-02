import io
import re
import tarfile
import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from codesynapse import config
from codesynapse.db.models import CodeChunk, Repo, User, utcnow
from codesynapse.services import chunker, embeddings

REPO_NAME = re.compile(r"^(?:https?://github\.com/)?([A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$")

# Repository contents are untrusted. They are read from memory, never unpacked or run.
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_UNPACKED_BYTES = 200 * 1024 * 1024
MAX_FILE_BYTES = 200 * 1024
MAX_FILES = 2000
MAX_CHUNKS = 3000

SKIPPED_DIRS = {"node_modules", "vendor", "dist", "build", "venv", ".venv", "__pycache__", "target",
                ".git", ".next", "coverage", "site-packages"}

class RepoError(ValueError):
    pass

def parse_name(value):
    match = REPO_NAME.match(value.strip())
    if not match:
        raise RepoError("Use the form owner/repo or a github.com link.")
    return match.group(1)

def github_headers():
    return {"Authorization": f"Bearer {config.GITHUB_TOKEN}"} if config.GITHUB_TOKEN else {}

def get_github_json(client, url):
    resp = client.get(url, headers=github_headers())
    if resp.status_code == 404:
        raise RepoError("That public repository was not found.")
    if resp.status_code != 200:
        raise RepoError(f"GitHub is unavailable (HTTP {resp.status_code}).")
    return resp.json()

def download_archive(full_name, sha=None):
    """Returns the commit sha and its source archive. Without a sha, uses the latest commit."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        if not sha:
            info = get_github_json(client, f"https://api.github.com/repos/{full_name}")
            branch = info["default_branch"]
            sha = get_github_json(client, f"https://api.github.com/repos/{full_name}/commits/{branch}")["sha"]

        data = bytearray()
        with client.stream("GET", f"https://codeload.github.com/{full_name}/tar.gz/{sha}") as resp:
            if resp.status_code != 200:
                raise RepoError(f"Could not download the repository (HTTP {resp.status_code}).")
            for block in resp.iter_bytes():
                data += block
                if len(data) > MAX_ARCHIVE_BYTES:
                    raise RepoError("That repository is too large to analyse.")
    return sha, bytes(data)

def is_generated(path):
    return path.endswith((".min.js", ".lock", "package-lock.json")) or "/migrations/versions/" in path

def read_source_files(archive):
    """Yields (path, text) for source files. Only regular files are read, and nothing touches the disk."""
    seen = unpacked = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r|gz") as tar:
        for member in tar:
            unpacked += member.size
            if unpacked > MAX_UNPACKED_BYTES:
                raise RepoError("That repository is too large to analyse.")
            if not member.isreg() or member.size > MAX_FILE_BYTES:
                continue

            # GitHub puts everything under a single top-level folder
            path = member.name.split("/", 1)[-1]
            if set(path.split("/")[:-1]) & SKIPPED_DIRS or is_generated(path) or not chunker.is_supported(path):
                continue

            raw = tar.extractfile(member).read()
            if b"\0" in raw:
                continue
            seen += 1
            if seen > MAX_FILES:
                raise RepoError("That repository has too many files to analyse.")
            yield path, raw.decode("utf-8", "replace")

def embedding_text(chunk):
    return f"{chunk.path} {chunk.symbol}\n{chunk.content}"

def index_repo(db: Session, user: User, value, sha=None):
    """Downloads a public repository and makes its code searchable for this user."""
    full_name = parse_name(value)
    sha, archive = download_archive(full_name, sha)

    chunks = [c for path, text in read_source_files(archive) for c in chunker.chunk_file(path, text)]
    if not chunks:
        raise RepoError("No supported source files were found.")
    chunks = chunks[:MAX_CHUNKS]
    vectors = embeddings.embed_documents([embedding_text(c) for c in chunks])

    repo = db.scalar(select(Repo).where(Repo.user_id == user.id, Repo.full_name == full_name))
    if repo:
        db.execute(delete(CodeChunk).where(CodeChunk.repo_id == repo.id))
    else:
        repo = Repo(user_id=user.id, full_name=full_name, commit_sha=sha)
        db.add(repo)
        db.flush()
    repo.commit_sha, repo.indexed_at = sha, utcnow()

    db.add_all(CodeChunk(
        repo_id=repo.id, path=c.path, language=c.language, kind=c.kind, symbol=c.symbol,
        start_line=c.start_line, end_line=c.end_line, content=c.content,
        embedding=vectors[i] if vectors else None,
    ) for i, c in enumerate(chunks))
    db.commit()
    return repo

def list_repos(db: Session, user: User):
    rows = db.execute(
        select(Repo, func.count(CodeChunk.id), func.count(CodeChunk.embedding))
        .outerjoin(CodeChunk, CodeChunk.repo_id == Repo.id)
        .where(Repo.user_id == user.id).group_by(Repo.id).order_by(Repo.full_name)
    )
    return [{"id": r.id, "full_name": r.full_name, "commit_sha": r.commit_sha, "indexed_at": r.indexed_at,
             "chunks": total, "embedded_chunks": embedded} for r, total, embedded in rows]

def delete_repo(db: Session, user: User, repo_id):
    repo = db.scalar(select(Repo).where(Repo.id == repo_id, Repo.user_id == user.id))
    if not repo:
        return False
    db.execute(delete(CodeChunk).where(CodeChunk.repo_id == repo.id))
    db.delete(repo)
    db.commit()
    return True
