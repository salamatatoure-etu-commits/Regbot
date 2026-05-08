import os
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

app = FastAPI(
    title="RegBot API",
    description="API du chatbot RAG interne",
    version="1.0.0",
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


@app.get("/", tags=["Root"])
def root():
    return {"message": "RegBot API", "docs": "/docs"}
