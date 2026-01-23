import google.generativeai as genai

# --- PASTE YOUR REAL KEY HERE ---
api_key = "AIzaSyAmggF5Y2jIKcESWZSadaM4CsjjMwmwOB0" 

genai.configure(api_key=api_key)

print("🔍 Checking available models for you...")

try:
    for m in genai.list_models():
        # We only care about models that can generate text
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Found: {m.name}")
except Exception as e:
    print(f"❌ Error: {e}")