import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Document, Utilisateur
from models.base import SessionLocal
from schemas import DocumentCreate, DocumentOut
from rag.indexer import index_document
from auth.dependencies import get_db, require_admin

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
def list_documents(
    skip: int = 0,
    limit: int = 20,
    service_id: int = None,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    query = db.query(Document)
    if service_id:
        query = query.filter(Document.service_id == service_id)
    docs = query.offset(skip).limit(limit).all()
    return [
        {
            "documentId":   d.documentId,
            "name":         d.name,
            "source":       d.source,
            "service_id":   d.service_id,
            "last_modified": d.last_modified,
            "size":         d.size,
            "mime_type":    d.mime_type,
            "web_url":      d.web_url,
            "download_url": d.download_url,
            "chunk_count":  len(d.chunks),
        }
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    doc = db.query(Document).filter(Document.documentId == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return {
        "documentId":    doc.documentId,
        "name":          doc.name,
        "source":        doc.source,
        "service_id":    doc.service_id,
        "last_modified": doc.last_modified,
        "size":          doc.size,
        "mime_type":     doc.mime_type,
        "web_url":       doc.web_url,
        "download_url":  doc.download_url,
        "chunk_count":   len(doc.chunks),
    }


@router.post("/", response_model=DocumentOut, status_code=201)
def create_document(
    data: DocumentCreate,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    doc = Document(**data.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    doc = db.query(Document).filter(Document.documentId == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    db.delete(doc)
    db.commit()


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    service_id: Optional[int] = Form(None),
    source: str = Form(default="local"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
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

    document_id = doc.documentId
    background_tasks.add_task(_index_background, document_id, content_bytes, mime_type)

    return doc


@router.post("/upload-multiple", status_code=201)
async def upload_multiple_documents(
    background_tasks: BackgroundTasks,
    service_id: Optional[int] = Form(None),
    source: str = Form(default="local"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(require_admin),
):
    ALLOWED_EXT = (".pdf", ".txt", ".md", ".docx", ".doc", ".xlsx", ".xls", ".html", ".htm")
    results = []

    for file in files:
        filename = file.filename or ""
        mime_type = file.content_type or ""

        if not filename.lower().endswith(ALLOWED_EXT):
            results.append({"name": filename, "status": "erreur", "detail": "Format non supporté"})
            continue

        content_bytes = await file.read()

        doc = Document(
            documentId=str(uuid.uuid4()),
            name=filename,
            source=source,
            service_id=service_id,
            mime_type=mime_type,
            size=round(len(content_bytes) / 1024, 2),
            last_modified=datetime.now(UTC),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        background_tasks.add_task(_index_background, doc.documentId, content_bytes, mime_type)
        results.append({"documentId": doc.documentId, "name": filename, "status": "indexation en cours"})

    return {"uploaded": len(results), "documents": results}


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
