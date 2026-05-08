import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from models import Document
from models.base import SessionLocal
from schemas import DocumentCreate, DocumentOut
from rag.indexer import index_document
from auth.dependencies import get_db

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_MIME = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/html",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}


@router.get("/", response_model=List[DocumentOut])
def list_documents(skip: int = 0, limit: int = 20, service_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Document)
    if service_id:
        query = query.filter(Document.service_id == service_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.documentId == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return doc


@router.post("/", response_model=DocumentOut, status_code=201)
def create_document(data: DocumentCreate, db: Session = Depends(get_db)):
    doc = Document(**data.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.documentId == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    db.delete(doc)
    db.commit()


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    service_id: int = Form(...),
    source: str = Form(default="local"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    mime_type = file.content_type or ""
    filename  = file.filename or ""

    ALLOWED_EXT = (".pdf", ".txt", ".md", ".docx", ".doc", ".xlsx", ".xls", ".html", ".htm")
    if not filename.lower().endswith(ALLOWED_EXT):
        raise HTTPException(status_code=400, detail="Format non supporté. Utilisez PDF, TXT, MD, Word, Excel ou HTML.")

    content_bytes = await file.read()

    doc = Document(
        documentId=str(uuid.uuid4()),
        name=name,
        source=source,
        service_id=service_id,
        mime_type=mime_type,
        size=round(len(content_bytes) / 1024, 2),
        last_modified=datetime.now(UTC),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Indexation en arrière-plan pour ne pas bloquer la réponse
    document_id = doc.documentId
    background_tasks.add_task(
        _index_background, document_id, content_bytes, mime_type
    )

    return doc


def _index_background(document_id: str, content_bytes: bytes, mime_type: str):
    db = SessionLocal()
    try:
        n = index_document(db, document_id, content_bytes, mime_type)
        if n == 0:
            doc = db.query(Document).filter(Document.documentId == document_id).first()
            if doc:
                db.delete(doc)
                db.commit()
            print(f"[WARN] Document {document_id} : aucun chunk extrait, document supprimé.")
        else:
            print(f"[INFO] Document {document_id} : {n} chunks indexés.")
    except Exception as e:
        print(f"[ERROR] Indexation {document_id} : {e}")
        try:
            doc = db.query(Document).filter(Document.documentId == document_id).first()
            if doc:
                db.delete(doc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
