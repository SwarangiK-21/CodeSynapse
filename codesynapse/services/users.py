import hashlib
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session
from codesynapse.db.models import User

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def create_user(db: Session):
    """Creates a user. The raw token is returned once and never stored."""
    token = secrets.token_urlsafe(32)
    user = User(token_hash=hash_token(token))
    db.add(user)
    db.commit()
    return user, token

def get_user_by_token(db: Session, token):
    if not token:
        return None
    return db.scalar(select(User).where(User.token_hash == hash_token(token)))
