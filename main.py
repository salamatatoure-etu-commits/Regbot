import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routes.auth_routes import router as auth_router
from routes.rag_routes import router as rag_router
from routes.service_routes import router as service_router
from routes.utilisateur_routes import router as utilisateur_router
from routes.bot_routes import router as bot_router
from routes.conversation_routes import router as conversation_router
from routes.message_routes import router as message_router
from routes.document_routes import router as document_router
from routes.stats_routes import router as stats_router
from sqlalchemy import exists, or_
from models import Document
from models.chunk_model import Chunk
from models.base import SessionLocal

logger = logging.getLogger("uvicorn")

# Un document tout juste créé n'a pas encore ses chunks (indexation encore en
# cours). Sans ce délai, un redémarrage --reload pendant un upload supprime
# le document avant la fin de son indexation (race condition).
_CLEANUP_MIN_AGE_MINUTES = 10


def _cleanup_zero_chunk_documents():
    db = SessionLocal()
    try:
        cutoff = datetime.now(UTC) - timedelta(minutes=_CLEANUP_MIN_AGE_MINUTES)
        orphans = db.query(Document).filter(
            ~exists().where(Chunk.document_id == Document.documentId),
            or_(Document.last_modified == None, Document.last_modified <= cutoff),
        ).all()
        if orphans:
            for doc in orphans:
                db.delete(doc)
            db.commit()
            logger.info(f"[Startup] {len(orphans)} document(s) sans chunks supprimé(s).")
        else:
            logger.info("[Startup] Aucun document sans chunks trouvé.")
    except Exception as e:
        logger.error(f"[Startup] Erreur nettoyage documents : {e}")
        db.rollback()
    finally:
        db.close()


def _run_periodic_cleanup():
    from services.temp_document_service import cleanup_expired_documents, mark_expired_conversations
    db = SessionLocal()
    try:
        mark_expired_conversations(db)
        cleanup_expired_documents(db)
    except Exception as e:
        logger.error(f"[Cleanup] Erreur : {e}")
    finally:
        db.close()


async def _periodic_cleanup():
    while True:
        await asyncio.sleep(3600)  # toutes les heures
        await asyncio.to_thread(_run_periodic_cleanup)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _cleanup_zero_chunk_documents()
    await asyncio.to_thread(_preload_models)
    task = asyncio.create_task(_periodic_cleanup())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _preload_models():
    try:
        from rag.embedder import _get_model
        _get_model()
        logger.info("[Startup] Modèle d'embedding chargé.")
    except Exception as e:
        logger.warning(f"[Startup] Chargement embedding échoué : {e}")

    try:
        from rag.reranker import _get_model as _get_reranker
        _get_reranker()
    except Exception as e:
        logger.warning(f"[Startup] Chargement reranker échoué : {e}")



app = FastAPI(
    title="RegBot API",
    description="API du chatbot RAG interne",
    version="1.0.0",
    lifespan=lifespan,
)

_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(service_router)
app.include_router(utilisateur_router)
app.include_router(bot_router)
app.include_router(conversation_router)
app.include_router(message_router)
app.include_router(document_router)
app.include_router(stats_router)

@app.get("/", tags=["Root"])
def root():
    return {"message": "RegBot API", "docs": "/docs"}
