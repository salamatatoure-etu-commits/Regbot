from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from models import Conversation, Message
from models.enums import MessageTypeEnum, PriorityEnum
from schemas import ConversationCreate, ConversationOut, MessageOut
from auth.dependencies import get_db, get_current_user
from models import Utilisateur
from rag.pipeline import rag_query
from rag.smalltalk import is_smalltalk, get_default_response
from services.bot_service import resolve_prompt_for_bot
from services.temp_document_service import (
    upload_temp_document,
    list_temp_documents,
    cleanup_expired_documents,
    mark_expired_conversations,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ChatRequest(BaseModel):
    question: str
    langue: str = "fr"
    llm_model: str = "llama3.2:3b"
    top_k: int = 5


class SourceOut(BaseModel):
    id: str
    titre: str
    service_id: Optional[int]


class ChatResponse(BaseModel):
    message: MessageOut
    sources: List[SourceOut]
    type: str


@router.get("/", response_model=List[ConversationOut])
def list_conversations(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Conversation).offset(skip).limit(limit).all()


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return conv


@router.post("/", response_model=ConversationOut, status_code=201)
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    conv = Conversation(**data.model_dump())
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    db.delete(conv)
    db.commit()


@router.get("/{conversation_id}/messages", response_model=List[MessageOut])
def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
def chat(conversation_id: int, data: ChatRequest, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")

    # Enregistrer le message utilisateur
    user_msg = Message(
        conversation_id=conversation_id,
        contenu=data.question,
        type_message=MessageTypeEnum.user,
        timestamp=datetime.now(UTC),
        langue=data.langue,
        priority=PriorityEnum.medium,
    )
    db.add(user_msg)

    # Mettre à jour last_activity
    conv.last_activity = datetime.now(UTC)
    db.commit()

    # Smalltalk ou RAG
    start = datetime.now(UTC)
    sources = []

    if is_smalltalk(data.question):
        bot_text = get_default_response(data.langue)
        type_question = "smalltalk"
    else:
        system_prompt = None
        if conv.bot_id:
            system_prompt = resolve_prompt_for_bot(db, conv.bot_id)
        result = rag_query(
            db,
            question=data.question,
            llm_model=data.llm_model,
            service_id=conv.service_id,
            top_k=data.top_k,
            system_prompt=system_prompt,
            conversation_id=conversation_id,
        )
        bot_text = result["answer"]
        sources = result.get("sources", [])
        type_question = "rag"

    response_time = datetime.now(UTC) - start

    # Enregistrer la réponse du bot
    bot_msg = Message(
        conversation_id=conversation_id,
        contenu=bot_text,
        type_message=MessageTypeEnum.bot,
        timestamp=datetime.now(UTC),
        langue=data.langue,
        type_question=type_question,
        response_time=response_time,
        priority=PriorityEnum.medium,
    )
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)

    return ChatResponse(
        message=MessageOut.model_validate(bot_msg),
        sources=[SourceOut(**s) for s in sources],
        type=type_question,
    )


@router.post("/{conversation_id}/upload", status_code=201)
async def upload_temp_doc(
    conversation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    filename = file.filename or ""
    ALLOWED_EXT = (".pdf", ".txt", ".md", ".docx", ".doc", ".xlsx", ".xls", ".html", ".htm")
    if not filename.lower().endswith(ALLOWED_EXT):
        raise HTTPException(status_code=400, detail="Format non supporté. Utilisez PDF, TXT, MD, Word, Excel ou HTML.")

    content_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    try:
        temp_doc = upload_temp_document(
            db=db,
            conversation_id=conversation_id,
            filename=filename,
            content_bytes=content_bytes,
            mime_type=mime_type,
            utilisateur_id=current_user.utilisateurId,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": temp_doc.id,
        "filename": temp_doc.filename,
        "expires_at": temp_doc.expires_at,
    }


@router.get("/{conversation_id}/documents")
def get_temp_documents(conversation_id: int, db: Session = Depends(get_db)):
    return list_temp_documents(db, conversation_id)


@router.post("/cleanup", status_code=200)
def cleanup(db: Session = Depends(get_db)):
    """Nettoie les documents expirés et ferme les conversations terminées."""
    docs = cleanup_expired_documents(db)
    convs = mark_expired_conversations(db)
    return {"documents_supprimes": docs, "conversations_fermees": convs}
