import hashlib
import logging

logger = logging.getLogger("uvicorn")

# E5 utilise des préfixes distincts pour les questions et les passages
# Sans préfixe, la qualité de retrieval baisse significativement
EMBED_MODEL     = "intfloat/multilingual-e5-small"
_QUERY_PREFIX   = "query: "
_PASSAGE_PREFIX = "passage: "

_CACHE_MAX_SIZE = 512
_query_cache: dict[str, list[float]] = {}
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Chargement du modèle d'embedding : {EMBED_MODEL}")
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed_text(text: str) -> list[float]:
    """Encode un passage (chunk de document) avec le préfixe 'passage: '."""
    text = (_PASSAGE_PREFIX + text)[:8000]
    return _get_model().encode(text, convert_to_numpy=True).tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Encode un batch de passages (chunks) avec le préfixe 'passage: '."""
    prefixed = [(_PASSAGE_PREFIX + t)[:8000] for t in texts]
    return _get_model().encode(prefixed, batch_size=32, convert_to_numpy=True).tolist()


def embed_query(text: str) -> list[float]:
    """Encode une question avec le préfixe 'query: ' et cache in-memory."""
    key = hashlib.md5(text.strip().lower().encode()).hexdigest()
    if key in _query_cache:
        return _query_cache[key]
    prefixed = (_QUERY_PREFIX + text)[:8000]
    embedding = _get_model().encode(prefixed, convert_to_numpy=True).tolist()
    if len(_query_cache) >= _CACHE_MAX_SIZE:
        _query_cache.pop(next(iter(_query_cache)))
    _query_cache[key] = embedding
    return embedding
