import json
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from codesynapse.db.models import ChatMessage, User
from codesynapse.services import coach, profiles

# How many earlier messages the AI sees
HISTORY_LIMIT = 10

def get_history(db: Session, user: User):
    rows = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.id))
    return [{"role": m.role, "content": m.content} for m in rows]

def clear_history(db: Session, user: User):
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    db.commit()

def format_reply(raw):
    try:
        data = json.loads(raw)
        lines = [data.get("advice", "No advice")]
        steps = [f"• {a['step']}" for a in data.get("actions", [])]
        return "\n\n".join(lines + ["\n".join(steps)]) if steps else lines[0]
    except (json.JSONDecodeError, AttributeError, KeyError, TypeError) as e:
        print(f"AI Reply Error: {e}")
        return "Sorry, the AI sent back an unreadable reply. Please try again."

def send_message(db: Session, user: User, message):
    history = get_history(db, user)[-HISTORY_LIMIT:]
    reply = format_reply(coach.ask_gemini(message, profiles.get_stats(db, user), history))

    db.add(ChatMessage(user_id=user.id, role="user", content=message))
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply))
    db.commit()
    return reply
