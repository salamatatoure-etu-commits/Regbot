import httpx
from sqlalchemy.orm import Session

from rag.embedder import embed_text
from rag.vectorizer import search_similar, search_in_documents
from services.bot_service import DEFAULT_PROMPT

OLLAMA_URL = "http://localhost:11434"


def _build_context(rows) -> str:
    parts = [f"[{row.name}]\n{row.contenu}" for row in rows]
    return "\n\n---\n\n".join(parts)


def _ask_llm(model: str, context: str, question: str, system_prompt: str) -> str:
    prompt = (
        f"{system_prompt}\n\n"
        f"Contexte:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Réponse:"
    )
    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]


def rag_query(
    db: Session,
    question: str,
    llm_model: str = "llama3.2:3b",
    service_id: int = None,
    top_k: int = 5,
    system_prompt: str = None,
    conversation_id: int = None,
) -> dict:
    prompt = system_prompt or DEFAULT_PROMPT
    query_embedding = embed_text(question)

    # Recherche dans les documents permanents
    rows = list(search_similar(db, query_embedding, service_id=service_id, top_k=top_k))

    # Recherche dans les documents temporaires de la conversation
    if conversation_id:
        from services.temp_document_service import get_active_document_ids
        doc_ids = get_active_document_ids(db, conversation_id)
        if doc_ids:
            temp_rows = search_in_documents(db, query_embedding, doc_ids, top_k=3)
            rows = list(temp_rows) + rows  # docs temp en priorité

    if not rows:
        return {"answer": "Aucun document pertinent trouvé.", "sources": []}

    context = _build_context(rows[:top_k])
    answer = _ask_llm(llm_model, context, question, prompt)

    sources = [
        {"id": row.document_id, "titre": row.name, "service_id": row.service_id}
        for row in rows[:top_k]
    ]

    return {"answer": answer, "sources": sources}
