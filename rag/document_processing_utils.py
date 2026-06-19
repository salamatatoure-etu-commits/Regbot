import re
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("uvicorn")


def _normalize_ws(text: str) -> str:
    """Réduit tout whitespace (espaces, \n, \t) à un espace simple pour comparaison."""
    return re.sub(r'\s+', ' ', text).strip()


# -----------------------------
# DEDUPLICATION CHUNKS (OPTIMISÉE)
# -----------------------------
def deduplicate_chunks(chunks, embeddings, threshold: float = 0.95):
    """
    Supprime les chunks trop similaires.
    Passe 1 : doublons textuels exacts après normalisation du whitespace.
    Passe 2 : quasi-doublons via cosine similarity (seuil 0.95).
    """

    if not chunks or not embeddings:
        return [], []

    # ── Passe 1 : doublons textuels (whitespace normalisé) ──────────────────
    n = len(chunks)
    to_keep = np.ones(n, dtype=bool)
    normalized = [_normalize_ws(c[1]) for c in chunks]

    # Ordre : plus long d'abord (on garde la version la plus complète)
    order = sorted(range(n), key=lambda idx: len(chunks[idx][1]), reverse=True)

    seen_texts: set[str] = set()
    for i in order:
        norm = normalized[i]
        if norm in seen_texts:
            to_keep[i] = False
            logger.info(
                f"Deduplicate (texte) chunk {i} (page {chunks[i][0]}) — doublon exact après normalisation whitespace"
            )
        else:
            seen_texts.add(norm)

    # ── Passe 2 : quasi-doublons via cosine similarity ───────────────────────
    embeddings = np.array(embeddings)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.clip(norms, 1e-10, None)

    for pos, i in enumerate(order):
        if not to_keep[i]:
            continue

        remaining = [j for j in order[pos + 1:] if to_keep[j]]
        if not remaining:
            continue

        sims = cosine_similarity(
            embeddings[i].reshape(1, -1),
            embeddings[remaining]
        )[0]

        for j, sim in zip(remaining, sims):
            if sim > threshold:
                to_keep[j] = False
                logger.info(
                    f"Deduplicate (cosine) chunk {j} (page {chunks[j][0]}) "
                    f"similar to chunk {i} (page {chunks[i][0]}) | sim={sim:.3f}"
                )

    unique_chunks = [chunks[i] for i in range(n) if to_keep[i]]
    unique_embeddings = [embeddings[i] for i in range(n) if to_keep[i]]
    return unique_chunks, unique_embeddings
