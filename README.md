# RegBot — Assistant documentaire intelligent

RegBot est une plateforme de chatbot RAG (Retrieval-Augmented Generation) destinée aux employés d'une entreprise. Elle permet d'interroger les documents internes de chaque service en langage naturel et d'obtenir des réponses précises, contextualisées et basées sur les documents réels de l'organisation.

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy |
| Base de données | PostgreSQL + pgvector |
| Embeddings | intfloat/multilingual-e5-small (dim 384) |
| Reranker | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 |
| LLM | Groq (llama-3.3-70b-versatile) / Ollama (llama3.1:8b) |
| Frontend | React 18, Vite, Framer Motion |
| Auth | JWT (access 60 min, refresh 7 jours), bcrypt |

---

## Fonctionnalités

- Chat RAG par service (RH, Juridique, Finance, Informatique...)
- Pipeline de recherche hybride : cosinus pgvector + BM25 + Fusion RRF
- Reranking CrossEncoder + diversification MMR
- Streaming des réponses en temps réel (SSE)
- Support Groq (cloud) et Ollama (local)
- Interface administrateur : gestion des utilisateurs, services, documents, bots
- Upload de documents temporaires dans une conversation
- Historique des conversations avec cache côté frontend
- Architecture multi-tenant : isolation des bases documentaires par service

---

## Prérequis

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ avec l'extension [pgvector](https://github.com/pgvector/pgvector)
- Une clé API [Groq](https://console.groq.com/) (ou [Ollama](https://ollama.com/) installé en local)

---

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/salamatatoure-etu-commits/Regbot.git
cd Regbot
```

### 2. Backend

```bash
# Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

---

## Configuration

Créer un fichier `.env` à la racine du projet :

```env
DATABASE_NAME=regbot
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432

SECRET_KEY=your_secret_key
ALGORITHM=HS256

GROQ_API_KEY=your_groq_api_key
OLLAMA_DEFAULT_MODEL=llama3.1:8b
```

---

## Initialisation de la base de données

```bash
# Créer les tables et les données de référence
python scripts/database.py init_db

# (Optionnel) Générer des données de test
python scripts/database.py generate_db_data
```

---

## Lancement

### Backend

```bash
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm run dev
```

L'application est accessible sur `http://localhost:5173`.

---

## Structure du projet

```
Regbot/
├── auth/               # Authentification JWT
├── models/             # Modèles SQLAlchemy
├── routes/             # Endpoints FastAPI
├── schemas/            # Schémas Pydantic
├── rag/                # Pipeline RAG (indexation, recherche, génération)
│   ├── pipeline.py     # Logique principale RAG
│   ├── indexer.py      # Extraction et chunking des documents
│   ├── vectorizer.py   # Recherche hybride BM25 + cosinus
│   ├── reranker.py     # CrossEncoder reranking
│   └── embedder.py     # Génération des embeddings
├── services/           # Services métier
├── scripts/            # Scripts d'administration
│   ├── database.py     # Init et seed de la base
│   └── dedup_document.py # Déduplication des chunks
├── frontend/           # Application React
│   └── src/
│       ├── pages/      # Chat, Admin, Login
│       ├── components/ # Sidebar, MessageList, InputBar...
│       ├── api/        # Appels API backend
│       └── hooks/      # useStream, useAuth
├── requirements.txt
└── main.py
```

---

## Comptes par défaut (données de test)

| Email | Mot de passe | Rôle |
|---|---|---|
| alice@regbot.com | pass1234 | Admin |
| clara@regbot.com | pass1234 | Employé |

---

## Auteur

**Salimata Touré** — Projet de fin d'études  
Université Hassan II Casablanca
