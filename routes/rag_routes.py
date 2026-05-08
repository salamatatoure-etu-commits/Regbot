from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from rag.pipeline import rag_query
from auth.dependencies import get_db
from services.bot_service import resolve_prompt_for_bot

router = APIRouter(prefix="/rag", tags=["RAG"])


class QueryRequest(BaseModel):
    question: str
    bot_id: Optional[int] = None
    service_id: Optional[int] = None
    conversation_id: Optional[int] = None
    llm_model: str = "llama3.2:3b"
    top_k: int = 5


class SourceOut(BaseModel):
    id: str
    titre: str
    service_id: Optional[int]


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    prompt_used: str


@router.post("/query", response_model=QueryResponse)
def query_rag(data: QueryRequest, db: Session = Depends(get_db)):
    try:
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
        )
        result["prompt_used"] = system_prompt or "prompt par défaut"
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
