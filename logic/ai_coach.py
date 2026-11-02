import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

# 1. Load keys
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key) if api_key else None

# 2. List of models to try, in order. Override with GEMINI_MODELS in .env
MODEL_FALLBACKS = os.getenv("GEMINI_MODELS", "gemini-3.8-flash,gemini-3.5-flash-lite").split(",")

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

def ask_gemini(user_question, user_stats):
    if not client:
        return error_reply("Error: API Key Missing. Check .env file.")

    prompt = f"""
    Role: Expert Career Coach.
    User Stats: {str(user_stats) if user_stats else "None yet. The user has not synced any profiles."}
    User Question: {user_question}

    Give short, specific advice and a list of actions. Only refer to stats listed above.
    Never invent stats for a platform marked as not found or unavailable.
    """

    last_code = None

    # 3. The Self-Healing Loop 🔄
    for model_name in MODEL_FALLBACKS:
        try:
            response = client.models.generate_content(
                model=model_name.strip(),
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
