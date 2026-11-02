from google.genai import errors, types
from codesynapse import config
from codesynapse.db.models import EMBEDDING_DIM
from codesynapse.services import coach

BATCH_SIZE = 100

def embed_texts(texts, task_type):
    """Returns one vector per text, or None if embeddings are unavailable.

    Search still works without vectors, using keywords only.
    """
    if not coach.client:
        return None

    vectors = []
    embed_config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIM)
    try:
        for start in range(0, len(texts), BATCH_SIZE):
            response = coach.client.models.embed_content(
                model=config.GEMINI_EMBEDDING_MODEL,
                contents=texts[start:start + BATCH_SIZE],
                config=embed_config,
            )
            vectors.extend(e.values for e in response.embeddings)
    except errors.APIError as e:
        print(f"Embedding Error: {e.code} {e.message}")
        return None
    return vectors

def embed_documents(texts):
    return embed_texts(texts, "RETRIEVAL_DOCUMENT")

def embed_query(text):
    vectors = embed_texts([text], "RETRIEVAL_QUERY")
    return vectors[0] if vectors else None
