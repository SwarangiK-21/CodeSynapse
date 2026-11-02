import json
from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from codesynapse import config

client = genai.Client(api_key=config.GEMINI_API_KEY) if config.GEMINI_API_KEY else None

# Errors worth retrying on another model: not found, quota, overloaded
FALLBACK_CODES = {404, 429, 500, 503}

class Action(BaseModel):
    step: str

class CoachReply(BaseModel):
    advice: str
    actions: list[Action]

generation_config = types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=1024,
    response_mime_type="application/json",
    response_schema=CoachReply,
)

def error_reply(message):
    return json.dumps({"advice": message, "actions": []})

def describe_error(code):
    if code in (400, 401, 403):
        return "AI Error: the API key was rejected. Check GEMINI_API_KEY in .env."
    if code == 404:
        return "AI Error: none of the configured models exist. Check GEMINI_MODELS."
    if code == 429:
        return "AI Quota Exceeded (Error 429). Please wait 1 minute and try again."
    return f"AI Service Error ({code}). Please try again later."

def build_prompt(user_question, user_stats, history):
    earlier = "\n".join(f"{m['role']}: {m['content']}" for m in history) or "None."
    return f"""
    Role: Expert Career Coach.
    User Stats: {str(user_stats) if user_stats else "None yet. The user has not synced any profiles."}
    Earlier Conversation:
    {earlier}
    User Question: {user_question}

    Give short, specific advice and a list of actions. Only refer to stats listed above.
    Never invent stats for a platform marked as not found or unavailable.
    """

def ask_gemini(user_question, user_stats, history=()):
    if not client:
        return error_reply("Error: API Key Missing. Check .env file.")

    prompt = build_prompt(user_question, user_stats, history)
    last_code = None

    # The Self-Healing Loop 🔄
    for model_name in config.GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=generation_config,
            )
            return response.text.strip()

        except errors.APIError as e:
            print(f"Gemini Error on {model_name}: {e.code} {e.message}")
            last_code = e.code
            if e.code not in FALLBACK_CODES:
                break

        except Exception as e:
            print(f"Gemini Error on {model_name}: {e}")
            return error_reply("AI Error: could not reach the AI service. Please try again.")

    # If ALL models fail
    return error_reply(describe_error(last_code))
