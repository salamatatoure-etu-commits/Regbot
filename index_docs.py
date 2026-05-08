import sys
sys.path.insert(0, '.')
from models.base import SessionLocal
from models import Document
from rag.indexer import index_document
import uuid

docs = [
    ("procedure_recrutement.txt", "Procédure de recrutement", 1),
    ("gestion_factures.txt",      "Gestion des factures",     2),
]

db = SessionLocal()
try:
    for filename, name, service_id in docs:
        path = f"docs_test/{filename}"
        with open(path, "rb") as f:
            content = f.read()

        doc_id = str(uuid.uuid4())
        doc = Document(documentId=doc_id, name=name, source="local", service_id=service_id)
        db.add(doc)
        db.commit()

        n = index_document(db, doc_id, content, "text/plain")
        print(f"[OK] {name} — {n} chunks indexés (doc_id: {doc_id})")
finally:
    db.close()
