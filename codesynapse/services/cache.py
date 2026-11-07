"""Stores AI results so an identical request is never paid for twice."""
import hashlib
import json
from sqlalchemy.exc import IntegrityError
from codesynapse.db.models import CacheEntry
from codesynapse.db.session import SessionLocal

def make_key(parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode("utf-8")).hexdigest()

def get(kind, parts):
    with SessionLocal() as db:
        entry = db.get(CacheEntry, make_key([kind, *parts]))
        return entry.value if entry else None

def put(kind, parts, value):
    with SessionLocal() as db:
        db.add(CacheEntry(key=make_key([kind, *parts]), kind=kind, value=value))
        try:
            db.commit()
        except IntegrityError:
            # Another job stored the same result first
            db.rollback()
