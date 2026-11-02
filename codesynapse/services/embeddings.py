import re
import time
import httpx
from google.genai import errors, types
from codesynapse import config
from codesynapse.db.models import EMBEDDING_DIM
from codesynapse.services import coach

BATCH_SIZE = 50
# Indexing can wait out a rate limit. A live search falls back to keywords instead.
INDEX_RETRIES = 5
MAX_WAIT_SECONDS = 65

def retry_delay(error):
    match = re.search(r"retry in ([\d.]+)s", str(error.message), re.IGNORECASE)
    return min(float(match.group(1)) + 1, MAX_WAIT_SECONDS) if match else 30

def is_daily_limit(error):
    """A daily quota lasts for hours, so waiting and retrying is pointless."""
    return "per day" in str(error.message).lower()

def embed_batch(batch, embed_config, retries):
    for attempt in range(retries + 1):
        try:
            response = coach.client.models.embed_content(
                model=config.GEMINI_EMBEDDING_MODEL,
                contents=batch,
                config=embed_config,
            )
            return [e.values for e in response.embeddings]
        except errors.APIError as e:
            if e.code != 429 or attempt == retries or is_daily_limit(e):
                print(f"Embedding Error: {e.code} {e.message}")
                return None
            time.sleep(retry_delay(e))
        except (httpx.TransportError, OSError) as e:
            print(f"Embedding Network Error: {e}")
            return None

def embed_texts(texts, task_type, retries=0):
    """Returns one vector per text, with None for any that failed, or None without a key.

    Search still works without vectors, using keywords only.
    """
    if not coach.client:
        return None

    embed_config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIM)
    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        # A plain list of strings is merged into one vector by gemini-embedding-2
        batch = [types.Content(parts=[types.Part(text=t)]) for t in texts[start:start + BATCH_SIZE]]
        result = embed_batch(batch, embed_config, retries)
        if result is None or len(result) != len(batch):
            print(f"Embedding stopped after {len(vectors)} of {len(texts)} texts")
            break
        vectors.extend(result)
    return vectors + [None] * (len(texts) - len(vectors))

def embed_documents(texts):
    return embed_texts(texts, "RETRIEVAL_DOCUMENT", retries=INDEX_RETRIES)

def embed_query(text):
    vectors = embed_texts([text], "RETRIEVAL_QUERY")
    return vectors[0] if vectors else None
