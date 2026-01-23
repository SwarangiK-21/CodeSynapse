import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Load keys
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# 2. List of models to try (Priority: Free/Exp -> Lite -> Standard)
# This list is based exactly on the screenshot you shared.
MODEL_FALLBACKS = [
    "gemini-2.0-flash-exp",           # often unlimited free preview
    "gemini-2.0-flash-lite-preview-02-05", # 'Lite' models consume less quota
    "gemini-2.0-flash",               # Standard (what you were using)
    "gemini-2.5-flash"                # Newest (might have strict limits)
]

generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 1024,
}

def ask_gemini(user_question, user_stats):
    if not api_key:
        return '{"advice": "Error: API Key Missing. Check .env file.", "actions": []}'

    last_error = ""

    # 3. The Self-Healing Loop 🔄
    for model_name in MODEL_FALLBACKS:
        try:
            # print(f"Trying model: {model_name}...") # Uncomment for debugging
            
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )

            prompt = f"""
            Role: Expert Career Coach.
            User Stats: {str(user_stats)}
            User Question: {user_question}
            
            CRITICAL OUTPUT RULES:
            1. Respond ONLY in raw JSON.
            2. Do not use Markdown (no ```json blocks).
            3. Structure:
            {{
                "advice": "Short, specific advice string.",
                "actions": [
                    {{"step": "Action 1"}},
                    {{"step": "Action 2"}}
                ]
            }}
            """
            
            response = model.generate_content(prompt)
            
            # Clean up response
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            return text.strip()

        except Exception as e:
            # If we hit a 429 (Quota) or 404 (Not Found), we catch it and try the next model.
            last_error = str(e)
            continue 

    # If ALL models fail
    print(f"❌ ALL AI MODELS FAILED. Last error: {last_error}")
    return f'{{"advice": "AI Quota Exceeded (Error 429). Please wait 1 minute and try again.", "actions": []}}'