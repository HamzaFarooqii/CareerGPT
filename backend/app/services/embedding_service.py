# ============================================================
# Embedding Service — Multi-Provider with Local Fallback
# ============================================================
# PROVIDER OPTIONS:
#   "local"  → sentence-transformers (FREE, offline, no quota)
#   "gemini" → Google embedding API (1500/day free)  
#   "cohere" → Cohere API (1000/month free)
#
# "local" is RECOMMENDED — runs on your machine, no API calls,
# no quota limits, downloads model once (~90MB).
# ============================================================

from __future__ import annotations
from app.config.settings import settings

# Cache the local model so we only load it once
_local_model = None


def _get_local_model():
    """Load sentence-transformers model (cached after first load)."""
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = settings.EMBEDDING_MODEL or "all-MiniLM-L6-v2"
            print(f"📦 Loading local embedding model: {model_name} (first time downloads ~90MB)")
            _local_model = SentenceTransformer(model_name)
            print(f"✅ Embedding model loaded: {model_name}")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed!\n"
                "Run: pip install sentence-transformers"
            )
    return _local_model


async def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for the given text.
    Uses the provider configured in .env (EMBEDDING_PROVIDER).

    Args:
        text: Text to embed (resume content, job description, etc.)

    Returns:
        List of floats (the embedding vector)
    """
    text = text.strip()[:4000]  # Truncate for model context limits
    provider = settings.EMBEDDING_PROVIDER

    # ── Local (sentence-transformers) ────────────────────────
    if provider == "local":
        model = _get_local_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    # ── Google Gemini ────────────────────────────────────────
    elif provider == "gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            result = genai.embed_content(
                model=f"models/{settings.EMBEDDING_MODEL}",
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            print(f"⚠️ Gemini embedding failed: {e}, falling back to local")
            model = _get_local_model()
            return model.encode(text, normalize_embeddings=True).tolist()

    # ── Cohere ───────────────────────────────────────────────
    elif provider == "cohere":
        try:
            import cohere
            co = cohere.Client(settings.COHERE_API_KEY)
            result = co.embed(
                texts=[text],
                model="embed-english-v3.0",
                input_type="search_document",
            )
            return result.embeddings[0]
        except Exception as e:
            print(f"⚠️ Cohere embedding failed: {e}, falling back to local")
            model = _get_local_model()
            return model.encode(text, normalize_embeddings=True).tolist()

    # ── Default fallback: local ──────────────────────────────
    else:
        model = _get_local_model()
        return model.encode(text, normalize_embeddings=True).tolist()


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts efficiently (batch processing).
    Much faster than calling generate_embedding() in a loop for local models.
    """
    if not texts:
        return []

    provider = settings.EMBEDDING_PROVIDER

    if provider == "local":
        model = _get_local_model()
        clean_texts = [t.strip()[:4000] for t in texts]
        embeddings = model.encode(clean_texts, normalize_embeddings=True, batch_size=32)
        return [e.tolist() for e in embeddings]

    # For API providers, fall back to individual calls
    results = []
    for text in texts:
        emb = await generate_embedding(text)
        results.append(emb)
    return results
