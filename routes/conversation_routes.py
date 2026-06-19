from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import exists
from sqlalchemy.orm import Session
from typing import List, Optional

from models import Conversation, Message, Bot
from models.conversation_model import ConversationStatus
from models.enums import MessageTypeEnum, PriorityEnum, RoleEnum
from schemas import ConversationCreate, ConversationOut, MessageOut
from auth.dependencies import get_db, get_current_user, require_admin
from models import Utilisateur
from rag.pipeline import rag_query, is_document_summary_question, rag_summarize_uploaded_documents
from rag.smalltalk import is_smalltalk, get_default_response
from services.bot_service import resolve_prompt_for_bot
from services.temp_document_service import (
    upload_temp_document,
    index_temp_document_background,
    list_temp_documents,
    cleanup_expired_documents,
    mark_expired_conversations,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class SavePairRequest(BaseModel):
    question: str
    answer: str
    temp_document_ids: List[int] = []


class ChatRequest(BaseModel):
    question: str
    langue: str = "fr"
    llm_model: str = "llama-3.3-70b-versatile"
    top_k: int = 5
    temp_document_ids: List[int] = []
    provider: str = "groq"


class SourceOut(BaseModel):
    id: str
    titre: str
    service_id: Optional[int]


class ChatResponse(BaseModel):
    message: MessageOut
    sources: List[SourceOut]
    type: str


@router.get("/me", response_model=List[ConversationOut])
def my_conversations(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    has_messages = exists().where(Message.conversation_id == Conversation.conversationid)
    return db.query(Conversation).filter(
        Conversation.utilisateur_id == current_user.utilisateurId,
        has_messages,
    ).order_by(Conversation.last_activity.desc()).limit(30).all()


@router.post("/start", response_model=ConversationOut, status_code=201)
def start_conversation(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = db.query(Bot).filter(
        Bot.service_id == current_user.service_id,
        Bot.actif == True,
    ).first()

    conv = Conversation(
        utilisateur_id=current_user.utilisateurId,
        service_id=current_user.service_id,
        bot_id=bot.botId if bot else None,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/", response_model=List[ConversationOut])
def list_conversations(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    return db.query(Conversation).offset(skip).limit(limit).all()


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return conv


@router.post("/", response_model=ConversationOut, status_code=201)
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    conv = Conversation(**data.model_dump())
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.patch("/{conversation_id}/titre", status_code=200)
def rename_conversation(
    conversation_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    if current_user.role != RoleEnum.admin and conv.utilisateur_id != current_user.utilisateurId:
        raise HTTPException(status_code=403, detail="Action non autorisée")
    titre = (data.get("titre") or "").strip()
    if not titre:
        raise HTTPException(status_code=400, detail="Le titre ne peut pas être vide")
    conv.titre = titre[:80]
    db.commit()
    return {"titre": conv.titre}


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    if current_user.role != RoleEnum.admin and conv.utilisateur_id != current_user.utilisateurId:
        raise HTTPException(status_code=403, detail="Action non autorisée")
    # Supprime les Documents temporaires (et leurs chunks) avant la conversation
    from models import Document
    for td in conv.temp_documents:
        if td.filepath:
            doc = db.query(Document).filter(Document.documentId == td.filepath).first()
            if doc:
                db.delete(doc)
    db.delete(conv)
    db.commit()


@router.get("/{conversation_id}/messages", response_model=List[MessageOut])
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
def chat(conversation_id: int, data: ChatRequest, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
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
        temp_document_ids=",".join(str(i) for i in data.temp_document_ids) or None,
    )
    db.add(user_msg)

    # Mettre à jour last_activity et rouvrir la conversation si elle avait été fermée
    conv.last_activity = datetime.now(UTC)
    if conv.status == ConversationStatus.closed:
        conv.status = ConversationStatus.active
        conv.end_time = None
    db.commit()

    # Smalltalk ou RAG
    start = datetime.now(UTC)
    sources = []

    if is_smalltalk(data.question):
        bot_text = get_default_response(data.question, data.langue)
        type_question = "smalltalk"
    elif is_document_summary_question(data.question):
        system_prompt = None
        if conv.bot_id:
            system_prompt = resolve_prompt_for_bot(db, conv.bot_id)
        result = rag_summarize_uploaded_documents(
            db,
            conversation_id=conversation_id,
            llm_model=data.llm_model,
            system_prompt=system_prompt,
            provider=data.provider,
        )
        bot_text = result["answer"]
        sources = []
        type_question = "summary"
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
            provider=data.provider,
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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(index_temp_document_background, temp_doc.filepath, content_bytes, mime_type)

    return {
        "id": temp_doc.id,
        "filename": temp_doc.filename,
        "expires_at": temp_doc.expires_at,
    }


def _generate_conversation_title(question: str, answer: str) -> str:
    """Génère un titre court via le LLM pour la conversation."""
    import os, httpx
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return question[:50]
    prompt = (
        f"Génère un titre très court (3 à 5 mots maximum) en français pour cette conversation. "
        f"Le titre doit être descriptif et ne pas être une question. "
        f"Réponds UNIQUEMENT avec le titre, sans ponctuation ni guillemets.\n\n"
        f"Question : {question[:200]}\n"
        f"Réponse : {answer[:200]}\n\n"
        f"Titre :"
    )
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "stream": False, "max_tokens": 20},
            timeout=10,
        )
        response.raise_for_status()
        titre = response.json()["choices"][0]["message"]["content"].strip()
        titre = titre.strip('"\'').strip()
        return titre[:60] if titre else question[:50]
    except Exception:
        return question[:50]


@router.post("/{conversation_id}/save", status_code=201)
def save_message_pair(
    conversation_id: int,
    data: SavePairRequest,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    now = datetime.now(UTC)
    temp_document_ids = ",".join(str(i) for i in data.temp_document_ids) or None
    db.add(Message(conversation_id=conversation_id, contenu=data.question, type_message=MessageTypeEnum.user, timestamp=now, langue="fr", priority=PriorityEnum.medium, temp_document_ids=temp_document_ids))
    db.add(Message(conversation_id=conversation_id, contenu=data.answer,   type_message=MessageTypeEnum.bot,  timestamp=now, langue="fr", priority=PriorityEnum.medium))
    conv = db.query(Conversation).filter(Conversation.conversationid == conversation_id).first()
    titre_genere = None
    if conv:
        conv.last_activity = now
        if conv.status == ConversationStatus.closed:
            conv.status = ConversationStatus.active
            conv.end_time = None
        if not conv.titre:
            titre_genere = _generate_conversation_title(data.question, data.answer)
            conv.titre = titre_genere
    db.commit()
    return {"ok": True, "titre": titre_genere}


@router.get("/{conversation_id}/documents")
def get_temp_documents(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    return list_temp_documents(db, conversation_id)


@router.post("/cleanup", status_code=200)
def cleanup(
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    """Nettoie les documents expirés et ferme les conversations terminées."""
    convs = mark_expired_conversations(db)
    docs = cleanup_expired_documents(db)
    return {"documents_supprimes": docs, "conversations_fermees": convs}
