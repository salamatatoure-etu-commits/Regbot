import json as _json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger("uvicorn")
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from rag.pipeline import rag_query, rag_query_stream, is_document_summary_question, rag_summarize_uploaded_documents
from rag.smalltalk import is_smalltalk, get_default_response
from auth.dependencies import get_db, get_current_user
from models import Utilisateur
from services.bot_service import resolve_prompt_for_bot

router = APIRouter(prefix="/rag", tags=["RAG"])


class QueryRequest(BaseModel):
    question: str
    bot_id: Optional[int] = None
    service_id: int
    conversation_id: Optional[int] = None
    llm_model: str = "llama-3.3-70b-versatile"
    top_k: int = 5
    history: list[dict] = []
    provider: str = "groq"


class SourceOut(BaseModel):
    id: str
    titre: str
    service_id: Optional[int]
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    confidence: float
    is_reliable: bool
    prompt_used: str


@router.post("/query", response_model=QueryResponse)
def query_rag(data: QueryRequest, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    try:
        if is_smalltalk(data.question):
            return {
                "answer": get_default_response(data.question, "fr"),
                "sources": [],
                "confidence": 1.0,
                "is_reliable": True,
                "prompt_used": "smalltalk",
            }

        system_prompt = None
        if data.bot_id:
            system_prompt = resolve_prompt_for_bot(db, data.bot_id)

        result = rag_query(
            db,
            question=data.question,
            llm_model=data.llm_model,
            service_id=data.service_id,
            top_k=data.top_k,
            system_prompt=system_prompt,
            conversation_id=data.conversation_id,
            history=data.history or [],
            provider=data.provider,
        )
        result["prompt_used"] = system_prompt or "prompt par défaut"
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faq")
def get_faq(service_id: int = Query(...), limit: int = Query(default=5, le=10), _: Utilisateur = Depends(get_current_user)):
    return {"faq": []}


@router.post("/query/stream")
def query_rag_stream(data: QueryRequest, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    if is_smalltalk(data.question):
        def _smalltalk():
            resp = get_default_response(data.question, "fr")
            yield f'data: {_json.dumps({"token": resp})}\n\n'
            yield f'data: {_json.dumps({"done": True, "sources": [], "confidence": 1.0, "is_reliable": True})}\n\n'
        return StreamingResponse(_smalltalk(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # Détection des questions sur le contenu d'un document uploadé
    if is_document_summary_question(data.question) and data.conversation_id:
        def _summary_stream():
            system_prompt = None
            if data.bot_id:
                system_prompt = resolve_prompt_for_bot(db, data.bot_id)
            result = rag_summarize_uploaded_documents(
                db,
                conversation_id=data.conversation_id,
                llm_model=data.llm_model,
                system_prompt=system_prompt,
                provider=data.provider,
            )
            answer = result["answer"]
            yield f'data: {_json.dumps({"token": answer})}\n\n'
            yield f'data: {_json.dumps({"done": True, "sources": [], "confidence": 1.0, "is_reliable": True})}\n\n'
        return StreamingResponse(_summary_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    system_prompt = None
    if data.bot_id:
        system_prompt = resolve_prompt_for_bot(db, data.bot_id)

    return StreamingResponse(
        rag_query_stream(
            db,
            question=data.question,
            llm_model=data.llm_model,
            service_id=data.service_id,
            top_k=data.top_k,
            system_prompt=system_prompt,
            conversation_id=data.conversation_id,
            history=data.history or [],
            provider=data.provider,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

