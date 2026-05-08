import sys
sys.path.insert(0, '.')
from models.base import SessionLocal
from models import Document
from rag.indexer import index_document
import uuid

db = SessionLocal()
try:
    with open("docs_test/guide_paie.pdf", "rb") as f:
        content = f.read()

    doc_id = str(uuid.uuid4())
    doc = Document(documentId=doc_id, name="Guide de la paie", source="local", service_id=1)
    db.add(doc)
    db.commit()

    n = index_document(db, doc_id, content, "application/pdf")
    print(f"[OK] Guide de la paie (PDF) — {n} chunks indexes (doc_id: {doc_id})")
finally:
    db.close()
