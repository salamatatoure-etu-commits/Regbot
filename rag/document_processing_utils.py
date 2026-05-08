import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("uvicorn")

# -----------------------------
# DEDUPLICATION CHUNKS (OPTIMISÉE)
# -----------------------------
def deduplicate_chunks(chunks, embeddings, threshold: float = 0.95):
    """
    Supprime les chunks trop similaires via cosine similarity.
    Optimisé pour éviter calcul O(n²) inutile.
    """

    if not chunks or not embeddings:
        return [], []

    embeddings = np.array(embeddings)

    # normalisation optionnelle (améliore stabilité cosine)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.clip(norms, 1e-10, None)

    to_keep = np.ones(len(chunks), dtype=bool)

    unique_chunks = []
    unique_embeddings = []

    for i in range(len(chunks)):
        if not to_keep[i]:
            continue

        unique_chunks.append(chunks[i])
        unique_embeddings.append(embeddings[i])

        if i == len(chunks) - 1:
            break

        # comparaison vectorisée (au lieu de boucle j)
        sims = cosine_similarity(
            embeddings[i].reshape(1, -1),
            embeddings[i + 1:]
        )[0]

        for offset, sim in enumerate(sims, start=i + 1):
            if to_keep[offset] and sim > threshold:
                to_keep[offset] = False

                logger.info(
                    f"Deduplicate chunk {offset} (page {chunks[offset][0]}) "
                    f"similar to chunk {i} (page {chunks[i][0]}) | sim={sim:.3f}"
                )

    return unique_chunks, unique_embeddings

# -----------------------------
# PAGE COVERAGE CHECK (SAFE)
# -----------------------------
def verify_page_coverage(chunks, docs_with_pages):
    """
    Vérifie couverture des pages.
    """

    if not docs_with_pages:
        return {
            "total_pages": 0,
            "covered_pages": 0,
            "missing_pages": [],
            "coverage_percentage": 0.0
        }

    covered_pages = {page for page, _ in chunks}
    all_pages = {page for page, _ in docs_with_pages}

    missing_pages = sorted(all_pages - covered_pages)

    total = len(all_pages)
    covered = len(covered_pages)

    return {
        "total_pages": total,
        "covered_pages": covered,
        "missing_pages": missing_pages,
        "coverage_percentage": (covered / total) * 100 if total else 0.0
    }