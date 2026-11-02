from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from codesynapse.db.models import User
from codesynapse.db.session import get_db
from codesynapse.services import chat, jobs, profiles, reports, repos, search, users

router = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)

class ProfileIn(BaseModel):
    github: str = ""
    leetcode: str = ""

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class RepoIn(BaseModel):
    repo: str = Field(min_length=3, max_length=200)

class JobIn(BaseModel):
    text: str = Field(min_length=20, max_length=20000)

def job_out(job):
    return {"id": job.id, "title": job.title, "skills": job.skills, "created_at": job.created_at}

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    user = users.get_user_by_token(db, credentials.credentials) if credentials else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")
    return user

def profile_out(profile):
    if not profile:
        return {"github": "", "leetcode": "", "stats": [], "synced_at": None}
    return {"github": profile.github, "leetcode": profile.leetcode, "stats": profile.stats, "synced_at": profile.synced_at}

# Plain `def` routes: FastAPI runs them in a thread pool, so slow calls don't block the server
@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(db: Session = Depends(get_db)):
    user, token = users.create_user(db)
    return {"user_id": user.id, "token": token}

@router.get("/profile")
def read_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return profile_out(profiles.get_profile(db, user))

@router.put("/profile")
def sync_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return profile_out(profiles.sync_profile(db, user, body.github, body.leetcode))
    except profiles.InvalidUsername as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e))

@router.get("/chat")
def read_chat(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"messages": chat.get_history(db, user)}

@router.post("/chat")
def send_chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"reply": chat.send_message(db, user, body.message)}

@router.delete("/chat", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat(user: User = Depends(current_user), db: Session = Depends(get_db)):
    chat.clear_history(db, user)

@router.post("/repos", status_code=status.HTTP_201_CREATED)
def index_repo(body: RepoIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        repo = repos.index_repo(db, user, body.repo)
    except repos.RepoError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e))
    return next(r for r in repos.list_repos(db, user) if r["id"] == repo.id)

@router.get("/repos")
def list_repos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"repos": repos.list_repos(db, user)}

@router.delete("/repos/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repo(repo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not repos.delete_repo(db, user, repo_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Repository not found")

@router.get("/search")
def search_code(q: str = Query(min_length=2, max_length=200), repo_id: int | None = None,
                limit: int = Query(10, ge=1, le=50), user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"results": search.search_code(db, user, q, repo_id, limit)}

@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(body: JobIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return job_out(jobs.create_job(db, user, body.text))
    except jobs.JobError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))

@router.get("/jobs/{job_id}")
def read_job(job_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = jobs.get_job(db, user, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job description not found")
    return job_out(job)

@router.get("/report")
def download_report(user: User = Depends(current_user), db: Session = Depends(get_db)):
    stats = profiles.get_stats(db, user)
    if not stats:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sync a profile first")
    return Response(reports.build_pdf(stats), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Career_Report.pdf"'})
