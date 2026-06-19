import re
from datetime import datetime, UTC

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from sqlalchemy import text


def store_embedding(db: Session, chunk_id: int, embedding: list[float]):
    """Sauvegarde l'embedding d'un seul chunk et le marque comme indexé."""
    # Convertit la liste de floats en chaîne "[x, y, ...]" attendue par pgvector
    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
    db.execute(
        text("""
            UPDATE chunk
            SET embedding = CAST(:emb AS vector), is_indexed = true
            WHERE "chunkId" = :id
        """),
        {"emb": emb_str, "id": chunk_id},
    )
    db.commit()


def store_embeddings_batch(db: Session, chunk_embeddings: list[tuple[int, list[float]]]):
    """Met à jour les embeddings de N chunks en une seule transaction."""
    for chunk_id, embedding in chunk_embeddings:
        # Même conversion float[] → chaîne pgvector que pour un chunk unique
        emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
        db.execute(
            text("""
                UPDATE chunk
                SET embedding = CAST(:emb AS vector), is_indexed = true
                WHERE "chunkId" = :id
            """),
            {"emb": emb_str, "id": chunk_id},
        )
    # Un seul commit pour tout le batch : plus performant et atomique
    db.commit()


def store_chunks(db: Session, document_id: str, chunks: list[tuple[int, str]]) -> list[int]:
    """
    Insère une liste de (page_num, contenu) pour un document.
    Retourne la liste des chunkId créés.
    """
    chunk_ids = []
    for index, (page_num, contenu) in enumerate(chunks):
        # is_indexed=false : l'embedding n'est pas encore calculé à ce stade
        result = db.execute(
            text("""
                INSERT INTO chunk (document_id, page_num, chunk_index, contenu, is_indexed, created_at)
                VALUES (:doc_id, :page_num, :chunk_index, :contenu, false, :created_at)
                RETURNING "chunkId"
            """),
            {"doc_id": document_id, "page_num": page_num, "chunk_index": index, "contenu": contenu, "created_at": datetime.now(UTC)},
        )
        chunk_ids.append(result.scalar())
    db.commit()
    return chunk_ids


def search_similar(
    db: Session,
    query_embedding: list[float],
    service_id: int = None,
    top_k: int = 5,
):
    """
    Recherche les top_k chunks les plus proches sémantiquement de la question.
    Filtre optionnellement par service (RH, Finance, etc.).
    """
    # Convertit le vecteur de la question en chaîne lisible par pgvector
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # <=> : opérateur de distance cosinus pgvector (valeur faible = forte similarité)
    sql = """
        SELECT c."chunkId", c.document_id, c.page_num, c.contenu,
               d.name, d.service_id,
               c.embedding <=> CAST(:emb AS vector) AS distance
        FROM chunk c
        JOIN document d ON d."documentId" = c.document_id
        WHERE c.is_indexed = true
          AND c.embedding IS NOT NULL
    """
    params: dict = {"emb": emb_str, "top_k": top_k}

    # Restreint la recherche aux documents du service demandé si précisé
    if service_id:
        sql += " AND d.service_id = :service_id"
        params["service_id"] = service_id

    # Tri par distance croissante : les chunks les plus pertinents en premier
    sql += " ORDER BY distance LIMIT :top_k"

    return db.execute(text(sql), params).fetchall()


def search_in_documents(
    db: Session,
    query_embedding: list[float],
    document_ids: list[str],
    top_k: int = 3,
):
    """
    Recherche uniquement dans une liste précise de documents.
    Utilisé pour les documents temporaires uploadés par l'utilisateur.
    """
    if not document_ids:
        return []

    # Convertit le vecteur de la question en chaîne lisible par pgvector
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Génère des placeholders nommés (:doc_0, :doc_1, ...) pour éviter l'injection SQL
    placeholders = ",".join(f":doc_{i}" for i in range(len(document_ids)))
    params = {"emb": emb_str, "top_k": top_k}
    for i, doc_id in enumerate(document_ids):
        params[f"doc_{i}"] = doc_id

    # Même logique cosinus que search_similar, mais limitée aux document_ids fournis
    sql = f"""
        SELECT c."chunkId", c.document_id, c.page_num, c.contenu,
               d.name, d.service_id,
               c.embedding <=> CAST(:emb AS vector) AS distance
        FROM chunk c
        JOIN document d ON d."documentId" = c.document_id
        WHERE c.is_indexed = true
          AND c.embedding IS NOT NULL
          AND c.document_id IN ({placeholders})
        ORDER BY distance LIMIT :top_k
    """
    return db.execute(text(sql), params).fetchall()


def get_embeddings_for_chunks(db: Session, chunk_ids: list[int]) -> dict[int, list[float]]:
    """Récupère les vecteurs stockés pour une liste de chunks (utilisé par MMR)."""
    if not chunk_ids:
        return {}
    placeholders = ",".join(f":id_{i}" for i in range(len(chunk_ids)))
    params = {f"id_{i}": cid for i, cid in enumerate(chunk_ids)}
    sql = f'SELECT "chunkId", embedding::text FROM chunk WHERE "chunkId" IN ({placeholders}) AND embedding IS NOT NULL'
    rows = db.execute(text(sql), params).fetchall()
    result = {}
    for row in rows:
        emb_str = row[1].strip("[]")
        result[row[0]] = [float(x) for x in emb_str.split(",")]
    return result


def _tokenize(text: str) -> list[str]:
    # Mots de 2+ caractères, insensible à la casse — utilisé par BM25
    return re.findall(r'\b\w{2,}\b', text.lower())


def search_hybrid(
    db: Session,
    query: str,
    query_embedding: list[float],
    service_id: int = None,
    top_k: int = 5,
    candidates: int = 20,
):
    """
    Recherche hybride : similarité cosinus pgvector + BM25, fusionnés via RRF.
    Retourne les top_k chunks les plus pertinents.
    """
    # Étape 1 : récupère plus de candidats qu'on en veut (pool pour BM25)
    rows = list(search_similar(db, query_embedding, service_id=service_id, top_k=candidates))
    if not rows:
        return []

    # Étape 2 : score BM25 sur les chunks candidats
    corpus = [_tokenize(row.contenu) for row in rows]
    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(_tokenize(query))

    # Étape 3 : Reciprocal Rank Fusion (RRF) pondérée
    # Le vecteur (sémantique) pèse 2x plus que BM25 (lexical)
    # Évite que des termes génériques (ex: "informatiques") surclassent la pertinence sémantique
    K = 60
    VECTOR_WEIGHT = 3.0
    BM25_WEIGHT   = 1.0
    vector_rank = {row.chunkId: i for i, row in enumerate(rows)}
    bm25_rank = {
        rows[i].chunkId: rank
        for rank, i in enumerate(sorted(range(len(rows)), key=lambda x: bm25_scores[x], reverse=True))
    }

    def rrf_score(row):
        cid = row.chunkId
        return VECTOR_WEIGHT / (K + vector_rank[cid]) + BM25_WEIGHT / (K + bm25_rank[cid])

    return sorted(rows, key=rrf_score, reverse=True)[:top_k]
