import json
import math
import os
import re
import httpx
from sqlalchemy.orm import Session

from rag.embedder import embed_query
from rag.vectorizer import search_hybrid, search_in_documents, get_embeddings_for_chunks
from rag.reranker import rerank
from services.bot_service import DEFAULT_PROMPT

# Nombre maximum de candidats soumis au reranker avant sélection finale
_RERANK_CANDIDATES = 8
# Limites du nombre de chunks retournés à l'utilisateur
_TOP_K_MIN = 3
_TOP_K_MAX = 10
# Nombre de tours de conversation envoyés au LLM (1 tour = 1 question + 1 réponse)
_MAX_HISTORY = 4
# Score brut minimum du CrossEncoder pour garder un chunk dans le contexte LLM
# -4.5 : inclut les sections procédurales qui ne mentionnent pas tous les mots de la question
_MIN_RERANK_SCORE = -4.5
# Seuil de confiance pour marquer une réponse comme fiable
# Le CrossEncoder mmarco plafonne naturellement à 0.2-0.3 sur du contenu RH/IT
_RELIABLE_THRESHOLD = 0.15

# Mots-clés qui indiquent une question complexe → on cherche plus de chunks
_COMPLEX_KEYWORDS = {
    "comment", "pourquoi", "expliquez", "comparez", "différence", "différences",
    "liste", "toutes", "tous", "étapes", "processus", "procédure", "détail",
    "détails", "résumé", "ensemble", "exhaustif", "complètement",
}

# Clé API Groq lue depuis le fichier .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# URL de l'API Groq (compatible format OpenAI)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Modèle LLM utilisé par défaut
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Ollama : LLM local, API compatible OpenAI
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.1:8b")


# ─── Ajustement dynamique du nombre de chunks ─────────────────────────────────

def _adaptive_top_k(question: str, base_top_k: int) -> int:
    """Augmente ou réduit top_k selon la complexité de la question."""
    words = question.lower().split()
    word_count = len(words)
    has_complex_keyword = bool(_COMPLEX_KEYWORDS & set(words))

    if word_count <= 5 and not has_complex_keyword:
        # Question courte et simple → moins de chunks suffisent
        adjusted = base_top_k - 2
    elif word_count > 12 or has_complex_keyword:
        # Question longue ou complexe → on cherche plus de chunks
        adjusted = base_top_k + 3
    else:
        adjusted = base_top_k

    # On reste dans les bornes [_TOP_K_MIN, _TOP_K_MAX]
    return max(_TOP_K_MIN, min(_TOP_K_MAX, adjusted))


# ─── Fonctions mathématiques ──────────────────────────────────────────────────

def _sigmoid(x: float) -> float:
    """Transforme un score brut en valeur entre 0 et 1 (pour la confiance)."""
    return 1 / (1 + math.exp(-x))


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs d'embedding."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── Query Expansion ──────────────────────────────────────────────────────────

def _expand_query(question: str, model: str) -> list[str]:
    """
    Génère 2 reformulations de la question via le LLM pour élargir la recherche.
    Désactivée en production car trop coûteuse en temps sur CPU.
    """
    prompt = (
        "Génère 2 reformulations courtes et différentes de cette question pour améliorer "
        "la recherche documentaire. Retourne UNIQUEMENT 2 lignes, sans numérotation ni explication.\n\n"
        f"Question: {question}\n\nReformulations:"
    )
    try:
        response = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=30,
        )
        response.raise_for_status()
        lines = [l.strip() for l in response.json()["choices"][0]["message"]["content"].strip().split("\n") if l.strip()]
        return [question] + lines[:2]
    except Exception:
        # Si le LLM échoue, on garde juste la question originale
        return [question]


# ─── MMR (Maximal Marginal Relevance) ─────────────────────────────────────────

def _mmr(
    ranked: list[tuple[float, any]],
    embeddings_map: dict[int, list[float]],
    top_k: int,
    lambda_: float = 0.45,
) -> list[tuple[float, any]]:
    """
    Sélectionne les chunks les plus pertinents ET les plus diversifiés.
    - lambda_ proche de 1.0 → favorise la pertinence
    - lambda_ proche de 0.0 → favorise la diversité (évite les doublons)
    """
    selected = []
    remaining = list(ranked)

    while len(selected) < top_k and remaining:
        best_idx, best_score = 0, -float("inf")
        for i, (rel_score, row) in enumerate(remaining):
            emb = embeddings_map.get(row.chunkId)
            # Convertit le score du reranker en valeur entre 0 et 1
            relevance = _sigmoid(rel_score)

            if not selected or emb is None:
                # Premier chunk sélectionné : on prend le plus pertinent
                mmr_score = relevance
            else:
                # Calcule la similarité max avec les chunks déjà sélectionnés
                sims = [
                    _cosine_sim(emb, embeddings_map[s_row.chunkId])
                    for _, s_row in selected
                    if embeddings_map.get(s_row.chunkId) is not None
                ]
                max_sim = max(sims) if sims else 0.0
                # Score MMR = équilibre entre pertinence et nouveauté
                mmr_score = lambda_ * relevance - (1 - lambda_) * max_sim

            if mmr_score > best_score:
                best_score, best_idx = mmr_score, i

        selected.append(remaining.pop(best_idx))

    return selected


# ─── Construction du contexte et du prompt ────────────────────────────────────

# Limite la taille de chaque chunk envoyé au LLM (évite de dépasser la fenêtre de contexte)
# Certains documents (.docx, .md) produisent des chunks dépassant 7000 caractères :
# une limite trop basse tronque l'information avant qu'elle n'atteigne le LLM.
_MAX_CHUNK_CHARS = 8000

# Limite la taille totale du contexte envoyé en un seul appel pour un résumé de
# document complet (rag_summarize_uploaded_documents) : sans ce plafond, un gros
# document (ex: 200+ pages) dépasse la limite de tokens/minute de l'API Groq (429).
_MAX_SUMMARY_CONTEXT_CHARS = 24000


def _build_context(rows) -> str:
    """Assemble les chunks sélectionnés en un bloc de texte pour le LLM."""
    parts = [f"[{row.name}]\n{row.contenu[:_MAX_CHUNK_CHARS]}" for row in rows]
    return "\n\n---\n\n".join(parts)


# Réponse standard quand aucune information n'est trouvée dans les documents
_FALLBACK = "Je n'ai pas trouvé cette information dans les documents de votre service. Essayez de reformuler votre question ou contactez directement le service concerné."

# Instruction envoyée au LLM pour qu'il reste strictement dans le contexte fourni
_GROUNDING_INSTRUCTION = (
    "RÈGLES ABSOLUES — respecte-les sans aucune exception :\n"
    "1. Réponds UNIQUEMENT en te basant sur le texte du contexte fourni ci-dessous.\n"
    "2. Si la réponse n'est PAS dans le contexte, tu dois écrire EXACTEMENT et UNIQUEMENT : "
    f"\"{_FALLBACK}\" — sans ajouter aucun mot avant ou après.\n"
    "3. Il est STRICTEMENT INTERDIT d'inventer, de supposer ou de compléter "
    "avec des connaissances extérieures au contexte.\n"
    "4. Il est INTERDIT de modifier, arrondir ou paraphraser des chiffres, dates, noms ou montants.\n"
    "5. Ne donne aucune suggestion, recommandation ou opinion non demandée.\n"
    "6. Il est INTERDIT de commenter la question, d'expliquer ta démarche ou de mentionner "
    "les documents sources dans ta réponse. Réponds directement sans introduction.\n"
    "7. Ne commence JAMAIS ta réponse par une remarque sur la question ou sur le contexte.\n"
    "8. Si tu n'es pas sûr, écris la phrase de fallback exacte."
)


def _build_history_block(history: list[dict]) -> str:
    """Formate les derniers messages de la conversation pour les inclure dans le prompt."""
    if not history:
        return ""
    lines = []
    # On ne garde que les _MAX_HISTORY derniers messages pour ne pas surcharger le prompt
    for msg in history[-_MAX_HISTORY:]:
        role = "Utilisateur" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    if not lines:
        return ""
    return "Historique de la conversation:\n" + "\n".join(lines) + "\n\n"


def _build_prompt(
    context: str,
    question: str,
    system_prompt: str,
    history: list[dict] = None,
) -> str:
    """
    Construit le prompt complet envoyé au LLM.
    Structure : instruction système + règles + contexte documentaire + historique + question
    """
    return (
        f"{system_prompt}\n\n"
        f"{_GROUNDING_INSTRUCTION}\n\n"
        f"Contexte:\n{context}\n\n"
        f"{_build_history_block(history)}"
        f"Question: {question}\n\n"
        "Réponse:"
    )


_FALLBACK_VARIANTS = [
    _FALLBACK,
    "Je ne trouve pas cette information dans les documents disponibles.",
    "Je ne trouve pas cette information",
    "cette information n'est pas disponible",
    "cette information ne figure pas",
]

def _clean_answer(answer: str) -> str:
    """Remplace toute variante connue du fallback par la phrase officielle."""
    answer_lower = answer.lower()
    for variant in _FALLBACK_VARIANTS:
        if variant.lower() in answer_lower:
            return _FALLBACK
    return answer.strip()


# ─── Appels au LLM via l'API Groq ─────────────────────────────────────────────

def _ask_llm(
    model: str,
    context: str,
    question: str,
    system_prompt: str,
    history: list[dict] = None,
) -> str:
    """
    Envoie le prompt à Groq et retourne la réponse complète en une seule fois.
    Utilisé par l'endpoint POST /rag/query (réponse JSON classique).
    """
    # Construit le prompt final avec contexte, règles et historique
    prompt = _build_prompt(context, question, system_prompt, history)

    # Requête HTTP POST vers l'API Groq avec le prompt en JSON
    response = httpx.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()  # lève une exception si code HTTP 4xx/5xx

    # Extrait le texte de la réponse depuis la structure JSON de Groq
    return response.json()["choices"][0]["message"]["content"]


def _ask_llm_stream(
    model: str,
    context: str,
    question: str,
    system_prompt: str,
    history: list[dict] = None,
):
    """
    Envoie le prompt à Groq et retourne les tokens un par un (streaming SSE).
    Utilisé par l'endpoint POST /rag/query/stream → l'utilisateur voit le texte apparaître progressivement.
    """
    prompt = _build_prompt(context, question, system_prompt, history)

    # Ouvre une connexion HTTP persistante pour recevoir les tokens au fil de l'eau
    with httpx.stream(
        "POST",
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        },
        timeout=60,
    ) as response:
        response.raise_for_status()

        # Groq envoie une ligne SSE par token, ex: data: {"choices":[{"delta":{"content":"Bon"}}]}
        for line in response.iter_lines():
            # Ignore les lignes vides et le signal de fin de stream
            if not line or line.strip() == "data: [DONE]":
                continue
            if line.startswith("data: "):
                try:
                    # Parse le JSON après "data: " pour extraire le token
                    chunk = json.loads(line[6:])
                    token = chunk["choices"][0].get("delta", {}).get("content", "")
                    if token:
                        yield token  # envoie le token immédiatement au frontend
                except Exception:
                    continue  # ignore les lignes malformées


# ─── Appels au LLM local via Ollama ──────────────────────────────────────────

def _ollama_options(model: str) -> dict:
    """Retourne les options Ollama : étend le contexte au-delà du défaut de 2048 tokens."""
    return {"num_ctx": 8192}


def _ask_llm_ollama(model: str, context: str, question: str, system_prompt: str, history: list[dict] = None) -> str:
    """Envoie le prompt à Ollama via l'API native et retourne la réponse complète."""
    prompt = _build_prompt(context, question, system_prompt, history)
    effective_model = model or OLLAMA_DEFAULT_MODEL
    payload = {
        "model": effective_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    options = _ollama_options(effective_model)
    if options:
        payload["options"] = options
    response = httpx.post(OLLAMA_API_URL, json=payload, timeout=httpx.Timeout(connect=30, read=300, write=30, pool=30))
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"{response.status_code}: {response.text[:300]}",
            request=response.request,
            response=response,
        )
    return response.json()["message"]["content"]


def _ask_llm_ollama_stream(model: str, context: str, question: str, system_prompt: str, history: list[dict] = None):
    """Envoie le prompt à Ollama en mode streaming via l'API native."""
    prompt = _build_prompt(context, question, system_prompt, history)
    effective_model = model or OLLAMA_DEFAULT_MODEL
    payload = {
        "model": effective_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    options = _ollama_options(effective_model)
    if options:
        payload["options"] = options
    with httpx.stream("POST", OLLAMA_API_URL, json=payload, timeout=httpx.Timeout(connect=30, read=300, write=30, pool=30)) as response:
        if response.status_code >= 400:
            body = b""
            for chunk_bytes in response.iter_bytes():
                body += chunk_bytes
                if len(body) > 500:
                    break
            raise httpx.HTTPStatusError(
                f"{response.status_code}: {body.decode('utf-8', errors='replace')[:300]}",
                request=response.request,
                response=response,
            )
        for line in response.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
            except Exception:
                continue


def _stream_tokens(token_iter, sources: list, confidence: float):
    """Convertit un flux de tokens bruts en évènements SSE, jusqu'au signal 'done'."""
    full_answer = ""
    for token in token_iter:
        full_answer += token
        if _FALLBACK in full_answer:
            yield f'data: {json.dumps({"replace": _FALLBACK})}\n\n'
            yield f'data: {json.dumps({"done": True, "sources": sources, "confidence": confidence, "is_reliable": confidence >= _RELIABLE_THRESHOLD})}\n\n'
            return
        yield f'data: {json.dumps({"token": token})}\n\n'
    yield f'data: {json.dumps({"done": True, "sources": sources, "confidence": confidence, "is_reliable": confidence >= _RELIABLE_THRESHOLD})}\n\n'


# ─── Réécriture contextuelle de la question ──────────────────────────────────

# Pronoms et références vagues qui indiquent que la question dépend du contexte
_VAGUE_INDICATORS = {
    "chacune", "chacun", "elles", "ils", "eux", "les deux",
    "celles-ci", "ceux-ci", "celle-ci", "celui-ci",
    "laquelle", "lesquelles", "lequel", "lesquels",
    "cette", "ces", "leur", "leurs", "y", "en",
    "il", "elle", "ce", "cela", "ça", "cet",
}


def _rewrite_question(question: str, history: list[dict], model: str) -> str:
    """
    Réécrit la question en remplaçant les références vagues par les entités
    explicites du contexte. Ne fait rien si la question est déjà autonome.
    """
    if not history or not GROQ_API_KEY:
        return question

    words = set(question.lower().split())
    if not words & _VAGUE_INDICATORS:
        return question

    recent = history[-4:]
    history_text = "\n".join(
        f"{'Utilisateur' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')[:200]}"
        for m in recent
    )

    prompt = (
        "Voici un historique de conversation et une question de suivi.\n"
        "Réécris la question de façon autonome et complète en remplaçant tous les pronoms "
        "et références vagues par les entités explicites du contexte.\n"
        "Réponds UNIQUEMENT avec la question réécrite, sans explication ni guillemets.\n\n"
        f"Historique:\n{history_text}\n\n"
        f"Question: {question}\n\n"
        "Question réécrite:"
    )

    try:
        response = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "max_tokens": 60,
                "temperature": 0,
            },
            timeout=10,
        )
        response.raise_for_status()
        rewritten = response.json()["choices"][0]["message"]["content"].strip().strip('"\'')
        return rewritten if rewritten else question
    except Exception:
        return question


# ─── Recherche hybride avec query expansion ───────────────────────────────────

def _search_with_expansion(
    db: Session,
    question: str,
    queries: list[str],
    service_id: int,
    candidates: int,
) -> list:
    """
    Lance search_hybrid pour chaque reformulation de la question
    et fusionne les résultats en éliminant les doublons.
    """
    merged: dict[int, any] = {}
    for q in queries:
        q_emb = embed_query(q)
        rows = search_hybrid(
            db, q, q_emb,
            service_id=service_id,
            top_k=candidates,
            candidates=candidates * 2,
        )
        for row in rows:
            if row.chunkId not in merged:
                merged[row.chunkId] = row
            elif float(row.distance) < float(merged[row.chunkId].distance):
                # Garde le meilleur score cosinus si le chunk apparaît plusieurs fois
                merged[row.chunkId] = row
    return list(merged.values())


# ─── Pipeline principal (réponse complète) ────────────────────────────────────

def rag_query(
    db: Session,
    question: str,
    llm_model: str = "llama-3.1-8b-instant",
    service_id: int = None,
    top_k: int = 5,
    system_prompt: str = None,
    conversation_id: int = None,
    history: list[dict] = None,
    provider: str = "groq",
) -> dict:
    prompt = system_prompt or DEFAULT_PROMPT

    # ── Étape 1 : ajuster top_k selon la complexité de la question ─────────────
    top_k = _adaptive_top_k(question, top_k)
    candidates = max(top_k, _RERANK_CANDIDATES)

    # ── Étape 1b : réécriture contextuelle si la question est vague ────────────
    search_question = _rewrite_question(question, history or [], llm_model)

    # ── Étape 2 : recherche hybride (query expansion désactivée en production) ──
    rows = list(_search_with_expansion(db, search_question, [search_question], service_id, candidates))

    # ── Étape 3 : inclure les documents temporaires de la conversation ──────────
    # Si l'utilisateur a uploadé un fichier dans cette conversation, on le cherche aussi
    if conversation_id:
        from services.temp_document_service import get_active_document_ids
        doc_ids = get_active_document_ids(db, conversation_id)
        if doc_ids:
            q_emb = embed_query(search_question)
            temp_rows = search_in_documents(db, q_emb, doc_ids, top_k=candidates)
            existing_ids = {r.chunkId for r in rows}
            for r in temp_rows:
                if r.chunkId not in existing_ids:
                    rows.insert(0, r)  # priorité aux documents temporaires

    if not rows:
        return {"answer": "Aucun document pertinent trouvé.", "sources": [], "confidence": 0.0, "is_reliable": False}

    # ── Étape 4 : reranking + filtre qualité + MMR ──────────────────────────────
    # CrossEncoder reranke les chunks par pertinence réelle (plus précis que la similarité cosinus)
    # On utilise search_question (réécrite) pour que le reranker évalue les chunks
    # avec une question explicite et non des pronoms vagues ("chacun", "elles"…)
    ranked = rerank(search_question, rows, top_k * 2)

    # Filtre : on garde uniquement les chunks dont le score dépasse le seuil minimum
    # Évite d'envoyer au LLM des chunks non pertinents qui perturbent la réponse
    ranked = [(score, row) for score, row in ranked if score >= _MIN_RERANK_SCORE]
    if not ranked:
        return {"answer": _FALLBACK, "sources": [], "confidence": 0.0, "is_reliable": False}

    # MMR sélectionne les chunks pertinents ET diversifiés (évite les répétitions)
    chunk_ids = [row.chunkId for _, row in ranked]
    embeddings_map = get_embeddings_for_chunks(db, chunk_ids)
    final_ranked = _mmr(ranked, embeddings_map, top_k)

    # ── Étape 5 : génération de la réponse par le LLM ──────────────────────────
    top_rows = [row for _, row in final_ranked]
    context = _build_context(top_rows)  # assemble les chunks en texte
    try:
        if provider == "ollama":
            answer = _clean_answer(_ask_llm_ollama(llm_model, context, search_question, prompt, history))
        else:
            answer = _clean_answer(_ask_llm(llm_model, context, search_question, prompt, history))
    except httpx.ReadTimeout:
        label = "Ollama" if provider == "ollama" else "Groq"
        return {"answer": f"⚠ Le service {label} ne répond pas (timeout). Vérifiez votre connexion.", "sources": [], "confidence": 0.0, "is_reliable": False}
    except httpx.ConnectError:
        label = "Ollama (localhost:11434)" if provider == "ollama" else "l'API Groq"
        return {"answer": f"⚠ Impossible de joindre {label}. Vérifiez que le service est démarré.", "sources": [], "confidence": 0.0, "is_reliable": False}
    except httpx.HTTPStatusError as e:
        label = "Ollama" if provider == "ollama" else "Groq"
        if provider != "ollama" and e.response.status_code == 429:
            return {"answer": "⚠ Le service est temporairement surchargé (limite de requêtes atteinte). Réessayez dans quelques instants.", "sources": [], "confidence": 0.0, "is_reliable": False}
        detail = str(e).split(":", 1)[-1].strip()[:200] if ":" in str(e) else ""
        return {"answer": f"⚠ Erreur de l'API {label} ({e.response.status_code}).{(' — ' + detail) if detail else ''}", "sources": [], "confidence": 0.0, "is_reliable": False}

    # ── Étape 6 : construction de la réponse finale avec sources et confiance ───
    all_sources = [
        {
            "id": row.document_id,
            "titre": row.name,
            "service_id": row.service_id,
            "page": row.page_num,
            "score": round(_sigmoid(float(reranker_score)), 3),
        }
        for reranker_score, row in final_ranked
    ]
    # N'affiche à l'utilisateur que les sources dont le score est significatif (> 5%)
    sources = [s for s in all_sources if s["score"] >= 0.05]
    confidence = round(max(s["score"] for s in all_sources), 3)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "is_reliable": confidence >= _RELIABLE_THRESHOLD,
    }


# ─── Résumé de documents uploadés ────────────────────────────────────────────

_SUMMARY_QUESTION_KEYWORDS = {
    "contient", "contenu", "parle", "résume", "résumé", "resume",
    "sujet", "thème", "theme", "présente", "presente", "porte sur",
    "décrit", "decrit", "traite", "dit",
}
_DOCUMENT_KEYWORDS = {
    "document", "fichier", "ajouté", "ajoute", "envoyé", "envoye",
    "uploadé", "uploade", "joint", "importé", "importe",
}


def _contains_word(q: str, keywords: set[str]) -> bool:
    """Présence d'un mot-clé (sous-chaîne, pour couvrir les conjugaisons/pluriels).

    Cas particulier "document" : exclu quand il fait partie de "documentation",
    sans quoi toute question contenant ce mot déclenche à tort le résumé complet
    des documents uploadés (voir is_document_summary_question).
    """
    for kw in keywords:
        if kw == "document":
            if re.search(r"document(?!ation)", q):
                return True
        elif kw in q:
            return True
    return False


def is_document_summary_question(question: str) -> bool:
    """Détecte si la question porte sur le contenu global d'un document uploadé."""
    q = question.lower()
    return (
        _contains_word(q, _SUMMARY_QUESTION_KEYWORDS) and
        _contains_word(q, _DOCUMENT_KEYWORDS)
    )


def rag_summarize_uploaded_documents(
    db: Session,
    conversation_id: int,
    llm_model: str = DEFAULT_MODEL,
    system_prompt: str = None,
    provider: str = "groq",
) -> dict:
    """
    Contourne la recherche vectorielle et envoie tous les chunks des documents
    uploadés au LLM pour générer un résumé complet.
    """
    from services.temp_document_service import get_active_document_ids
    from models.chunk_model import Chunk
    from models.document_model import Document as Doc

    doc_ids = get_active_document_ids(db, conversation_id)
    if not doc_ids:
        return {"answer": "Aucun document actif trouvé dans cette conversation.", "sources": [], "confidence": 0.0, "is_reliable": False}

    context_parts = []
    for doc_id in doc_ids:
        doc = db.query(Doc).filter(Doc.documentId == doc_id).first()
        chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.chunk_index).all()
        if doc and chunks:
            text = "\n\n".join(c.contenu for c in chunks)
            context_parts.append(f"=== {doc.name} ===\n{text}")

    if not context_parts:
        return {"answer": "Aucun contenu trouvé dans les documents.", "sources": [], "confidence": 0.0, "is_reliable": False}

    context = "\n\n".join(context_parts)[:_MAX_SUMMARY_CONTEXT_CHARS]
    prompt = system_prompt or DEFAULT_PROMPT
    summary_question = "Fais un résumé structuré et complet de ce document en présentant les principaux thèmes abordés."

    try:
        if provider == "ollama":
            answer = _clean_answer(_ask_llm_ollama(llm_model, context, summary_question, prompt))
        else:
            answer = _clean_answer(_ask_llm(llm_model, context, summary_question, prompt))
    except httpx.HTTPStatusError as e:
        label = "Ollama" if provider == "ollama" else "Groq"
        if provider != "ollama" and e.response.status_code == 429:
            return {"answer": "⚠ Le service est temporairement surchargé (limite de requêtes atteinte). Réessayez dans quelques instants.", "sources": [], "confidence": 0.0, "is_reliable": False}
        return {"answer": f"Erreur de l'API {label} ({e.response.status_code}).", "sources": [], "confidence": 0.0, "is_reliable": False}
    except Exception as e:
        return {"answer": f"Erreur lors de la génération du résumé : {e}", "sources": [], "confidence": 0.0, "is_reliable": False}

    return {"answer": answer, "sources": [], "confidence": 1.0, "is_reliable": True}


# ─── Pipeline streaming (tokens envoyés au fur et à mesure) ───────────────────

def rag_query_stream(
    db: Session,
    question: str,
    llm_model: str = "llama-3.1-8b-instant",
    service_id: int = None,
    top_k: int = 5,
    system_prompt: str = None,
    conversation_id: int = None,
    history: list[dict] = None,
    provider: str = "groq",
):
    """
    Même pipeline que rag_query, mais envoie les tokens SSE un par un.
    Le frontend reçoit chaque mot dès qu'il est généré → effet "frappe en direct".
    Format SSE : data: {"token": "..."} ou data: {"done": true, ...}
    """
    prompt = system_prompt or DEFAULT_PROMPT

    # ── Étapes 1-4 : identiques à rag_query ────────────────────────────────────
    top_k = _adaptive_top_k(question, top_k)
    candidates = max(top_k, _RERANK_CANDIDATES)

    # Réécriture contextuelle si la question est vague
    search_question = _rewrite_question(question, history or [], llm_model)

    # Recherche hybride (query expansion désactivée en production)
    rows = list(_search_with_expansion(db, search_question, [search_question], service_id, candidates))

    if conversation_id:
        from services.temp_document_service import get_active_document_ids
        doc_ids = get_active_document_ids(db, conversation_id)
        if doc_ids:
            q_emb = embed_query(search_question)
            temp_rows = search_in_documents(db, q_emb, doc_ids, top_k=candidates)
            existing_ids = {r.chunkId for r in rows}
            for r in temp_rows:
                if r.chunkId not in existing_ids:
                    rows.insert(0, r)

    if not rows:
        yield f'data: {json.dumps({"token": "Aucun document pertinent trouvé."})}\n\n'
        yield f'data: {json.dumps({"done": True, "sources": [], "confidence": 0.0, "is_reliable": False})}\n\n'
        return

    # Reranking + filtre qualité + MMR (question réécrite pour éviter les pronoms vagues)
    ranked = rerank(search_question, rows, top_k * 2)

    # Filtre : élimine les chunks non pertinents avant de les envoyer au LLM
    ranked = [(score, row) for score, row in ranked if score >= _MIN_RERANK_SCORE]
    if not ranked:
        yield f'data: {json.dumps({"token": _FALLBACK})}\n\n'
        yield f'data: {json.dumps({"done": True, "sources": [], "confidence": 0.0, "is_reliable": False})}\n\n'
        return

    chunk_ids = [row.chunkId for _, row in ranked]
    embeddings_map = get_embeddings_for_chunks(db, chunk_ids)
    final_ranked = _mmr(ranked, embeddings_map, top_k)

    top_rows = [row for _, row in final_ranked]
    context = _build_context(top_rows)

    # Prépare les sources (envoyées à la fin avec le signal "done")
    all_sources = [
        {
            "id": row.document_id,
            "titre": row.name,
            "service_id": row.service_id,
            "page": row.page_num,
            "score": round(_sigmoid(float(reranker_score)), 3),
        }
        for reranker_score, row in final_ranked
    ]
    # N'affiche à l'utilisateur que les sources dont le score est significatif (> 5%)
    sources = [s for s in all_sources if s["score"] >= 0.05]
    confidence = round(max(s["score"] for s in all_sources), 3)

    # ── Étape 5 : streaming des tokens LLM ─────────────────────────────────────
    try:
        if provider == "ollama":
            token_iter = _ask_llm_ollama_stream(llm_model, context, search_question, prompt, history)
        else:
            token_iter = _ask_llm_stream(llm_model, context, search_question, prompt, history)
        yield from _stream_tokens(token_iter, sources, confidence)
        return
    except httpx.ReadTimeout:
        label = "Ollama" if provider == "ollama" else "Groq"
        yield f'data: {json.dumps({"token": f"\n\n⚠ Le service {label} ne répond pas (timeout)."})}\n\n'
        yield f'data: {json.dumps({"done": True, "sources": [], "confidence": 0.0, "is_reliable": False})}\n\n'
        return
    except httpx.ConnectError:
        label = "Ollama (localhost:11434)" if provider == "ollama" else "l'API Groq"
        yield f'data: {json.dumps({"token": f"\n\n⚠ Impossible de joindre {label}. Vérifiez que le service est démarré."})}\n\n'
        yield f'data: {json.dumps({"done": True, "sources": [], "confidence": 0.0, "is_reliable": False})}\n\n'
        return
    except httpx.HTTPStatusError as e:
        label = "Ollama" if provider == "ollama" else "Groq"
        if provider != "ollama" and e.response.status_code == 429:
            msg = "\n\n⚠ Le service est temporairement surchargé (limite de requêtes atteinte). Réessayez dans quelques instants."
        else:
            detail = str(e).split(":", 1)[-1].strip()[:200] if ":" in str(e) else ""
            msg = f"\n\n⚠ Erreur de l'API {label} ({e.response.status_code}).{(' — ' + detail) if detail else ''}"
        yield f'data: {json.dumps({"token": msg})}\n\n'
        yield f'data: {json.dumps({"done": True, "sources": [], "confidence": 0.0, "is_reliable": False})}\n\n'
        return
