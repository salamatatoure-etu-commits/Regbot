from datetime import datetime, UTC

from sqlalchemy.orm import Session
from sqlalchemy import text


def store_embedding(db: Session, chunk_id: int, embedding: list[float]):
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


def store_chunks(db: Session, document_id: str, chunks: list[tuple[int, str]]) -> list[int]:
    """
    Insère une liste de (page_num, contenu) pour un document.
    Retourne la liste des chunkId créés.
    """
    chunk_ids = []
    for index, (page_num, contenu) in enumerate(chunks):
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
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

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

    if service_id:
        sql += " AND d.service_id = :service_id"
        params["service_id"] = service_id

    sql += " ORDER BY distance LIMIT :top_k"

    return db.execute(text(sql), params).fetchall()


def search_in_documents(
    db: Session,
    query_embedding: list[float],
    document_ids: list[str],
    top_k: int = 3,
):
    """Recherche uniquement dans une liste de documents (ex: docs temporaires)."""
    if not document_ids:
        return []
    emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    placeholders = ",".join(f":doc_{i}" for i in range(len(document_ids)))
    params = {"emb": emb_str, "top_k": top_k}
    for i, doc_id in enumerate(document_ids):
        params[f"doc_{i}"] = doc_id

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
