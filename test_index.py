import sys
sys.path.insert(0, '.')
from models.base import SessionLocal
from rag.indexer import index_document

doc_id = "6c859551-aa73-486b-9223-ed2693c4c622"

with open("test_doc.txt", "rb") as f:
    content = f.read()

db = SessionLocal()
try:
    n = index_document(db, doc_id, content, "text/plain")
    print(f"Indexed {n} chunks")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
finally:
    db.close()
