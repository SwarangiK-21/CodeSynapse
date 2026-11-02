import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("🔍 Checking available models for you...")

try:
    for m in client.models.list():
        # We only care about models that can generate text
        if 'generateContent' in (m.supported_actions or []):
            print(f"✅ Found: {m.name}")
except Exception as e:
    print(f"❌ Error: {e}")
