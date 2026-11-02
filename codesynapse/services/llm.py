import time
from dataclasses import dataclass
import httpx
from google.genai import errors, types
from pydantic import BaseModel, ValidationError
from codesynapse import config
from codesynapse.services import coach, embeddings

# Long-running work can wait for the service to recover
ROUNDS = 3
BACKOFF_SECONDS = 20

class LLMError(RuntimeError):
    pass

@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0

    def add(self, response):
        self.calls += 1
        metadata = response.usage_metadata
        if metadata:
            self.prompt_tokens += metadata.prompt_token_count or 0
            self.output_tokens += metadata.candidates_token_count or 0

def call_model(model_name, prompt, schema, generation, usage):
    response = coach.client.models.generate_content(model=model_name, contents=prompt, config=generation)
    if usage:
        usage.add(response)
    return schema.model_validate_json(response.text)

def generate_json(prompt, schema: type[BaseModel], usage: Usage | None = None, temperature=0.0):
    """Returns the model's reply as a validated schema object.

    Tries every configured model, then waits and tries again, because overloads usually pass.
    """
    if not coach.client:
        raise LLMError("AI is not configured. Check GEMINI_API_KEY in .env.")

    generation = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=schema,
    )
    last_code = None
    exhausted = set()
    for round_number in range(ROUNDS):
        wait = BACKOFF_SECONDS * (round_number + 1)
        for model_name in config.GEMINI_MODELS:
            if model_name in exhausted:
                continue
            try:
                return call_model(model_name, prompt, schema, generation, usage)
            except errors.APIError as e:
                print(f"LLM Error on {model_name}: {e.code} {e.message}")
                last_code = e.code
                if e.code not in coach.FALLBACK_CODES:
                    raise LLMError(coach.describe_error(e.code))
                if e.code == 429 and embeddings.is_daily_limit(e):
                    exhausted.add(model_name)
                elif e.code == 429:
                    wait = max(wait, embeddings.retry_delay(e))
            except (httpx.TransportError, OSError) as e:
                print(f"LLM Network Error on {model_name}: {e}")
                last_code = 504
            except (ValidationError, TypeError) as e:
                print(f"LLM Reply Error on {model_name}: {e}")
        if exhausted == set(config.GEMINI_MODELS):
            raise LLMError("The daily AI quota is used up. Please try again tomorrow.")
        if round_number < ROUNDS - 1:
            time.sleep(wait)
    raise LLMError(coach.describe_error(last_code) if last_code else "The AI sent back an unreadable reply.")
