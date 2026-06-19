'''Reranker pour les résultats de recherche, basé sur un modèle de type cross-encoder
de sentence-transformers.'''
import logging

logger = logging.getLogger("uvicorn")

_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_model = None
_load_attempted = False


def _get_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    try:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(_MODEL_NAME)
        logger.info(f"[Reranker] Modèle chargé : {_MODEL_NAME}")
    except Exception as e:
        logger.warning(f"[Reranker] Chargement échoué, fallback cosinus : {e}")
        _model = None
    return _model


def rerank(question: str, rows: list, top_k: int) -> list[tuple[float, any]]:
    """Retourne les top_k sous forme (reranker_score, row) triés par pertinence.
    Fallback sur la distance cosine si sentence-transformers n'est pas installé."""
    if not rows:
        return []
    model = _get_model()
    if model is None:
        # Fallback : utilise la distance cosine existante (score = 1 - distance)
        scored = [(1 - float(row.distance), row) for row in rows]
        return sorted(scored, key=lambda x: x[0], reverse=True)[:top_k]
    pairs = [(question, row.contenu) for row in rows]
    scores = model.predict(pairs)
    ranked = sorted(zip(scores, rows), key=lambda x: x[0], reverse=True)
    return ranked[:top_k]
