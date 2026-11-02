import asyncio
import re
from sqlalchemy.orm import Session
from codesynapse.db.models import Profile, User, utcnow
from codesynapse.services import fetchers

GITHUB_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
LEETCODE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,30}$")

class InvalidUsername(ValueError):
    pass

def get_profile(db: Session, user: User):
    return db.get(Profile, user.id)

def get_stats(db: Session, user: User):
    profile = get_profile(db, user)
    return profile.stats if profile else []

def sync_profile(db: Session, user: User, github, leetcode):
    """Validates usernames, fetches live stats and saves them for this user."""
    github, leetcode = github.strip(), leetcode.strip()
    if github and not GITHUB_NAME.match(github):
        raise InvalidUsername("That is not a valid GitHub username.")
    if leetcode and not LEETCODE_NAME.match(leetcode):
        raise InvalidUsername("That is not a valid LeetCode username.")

    results = asyncio.run(fetchers.get_all_stats({"github": github, "leetcode": leetcode}))

    profile = get_profile(db, user) or Profile(user_id=user.id)
    profile.github, profile.leetcode, profile.stats = github, leetcode, list(results)
    profile.synced_at = utcnow()
    db.add(profile)
    db.commit()
    return profile
