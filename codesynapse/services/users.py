import hashlib
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session
from codesynapse.db.models import User, UserToken

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def new_token():
    return secrets.token_urlsafe(32)

def create_user(db: Session):
    """Creates a user. The raw token is returned once and never stored."""
    token = new_token()
    user = User(token_hash=hash_token(token))
    db.add(user)
    db.commit()
    return user, token

def get_user_by_token(db: Session, token):
    if not token:
        return None
    hashed = hash_token(token)
    user = db.scalar(select(User).where(User.token_hash == hashed))
    if user:
        return user
    extra = db.get(UserToken, hashed)
    return db.get(User, extra.user_id) if extra else None

def issue_token(db: Session, user: User):
    """Gives another device its own token for this user, without signing others out."""
    token = new_token()
    db.add(UserToken(token_hash=hash_token(token), user_id=user.id))
    db.commit()
    return token

def get_user_by_github_id(db: Session, github_id):
    return db.scalar(select(User).where(User.github_id == github_id))
