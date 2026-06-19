import re
import unicodedata
from functools import lru_cache
import regex

# spaCy optionnel : utilisé pour la segmentation en phrases et les stop words FR/EN
try:
    import spacy
    from spacy.lang.fr.stop_words import STOP_WORDS as FR
    from spacy.lang.en.stop_words import STOP_WORDS as EN
except ImportError:
    spacy = None
    FR = set()
    EN = set()

# tiktoken optionnel : comptage de tokens compatible 
try:
    import tiktoken
except ImportError:
    tiktoken = None


def init_spacy_segmenter():
    # Essaie d'abord le modèle français, puis le modèle multilingue
    if spacy is None:
        return None
    for lang in ("fr", "xx"):
        try:
            nlp = spacy.blank(lang)
            nlp.add_pipe("sentencizer")
            return nlp
        except Exception:
            continue
    return None


nlp = init_spacy_segmenter()


def init_token_encoder():
    # cl100k_base = encodeur utilisé par GPT-4 et les embeddings text-embedding-ada-002
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


enc = init_token_encoder()


def clean_text(content: str) -> str:
    # Supprime les octets nuls et normalise les caractères Unicode (ex. ligatures, espaces insécables)
    content = content.replace("\x00", "")
    return unicodedata.normalize("NFKC", content).strip()


@lru_cache(maxsize=10000)
def token_length(text: str) -> int:
    # Fallback sur le nombre de mots si tiktoken n'est pas disponible
    if enc is not None:
        return len(enc.encode(text))
    return len(text.split())


@lru_cache(maxsize=500)
def cached_sent_tokenize(text: str):
    # Fallback regex sur la ponctuation de fin de phrase si spaCy est absent
    if nlp is not None:
        doc = nlp(text)
        return [s.text.strip() for s in doc.sents]
    return [s.strip() for s in regex.split(r'(?<=[.!?])\s+', text) if s.strip()]


# ------------------------------------------------------------------ #
# TRANSITIONS INTER-PAGES                                              #
# ------------------------------------------------------------------ #

def find_sentence_continuation(current_content: str, next_content: str) -> str:
    """Retourne la jointure fin/début si la dernière phrase de la page courante est incomplète."""
    current_sents = cached_sent_tokenize(current_content)
    next_sents = cached_sent_tokenize(next_content)
    if not current_sents or not next_sents:
        return ""
    last_sent = current_sents[-1].strip()
    first_sent = next_sents[0].strip()
    # Phrase sans ponctuation finale = coupée en milieu de page
    if last_sent and last_sent[-1] not in ".!?":
        return f"{last_sent} {first_sent}"
    return ""


def find_concept_bridge(current_content: str, next_content: str, overlap_size: int) -> str:
    """Construit un chunk pont avec les phrases des deux pages partageant des concepts communs."""
    current_sents = cached_sent_tokenize(current_content)
    next_sents = cached_sent_tokenize(next_content)
    if not current_sents or not next_sents:
        return ""

    # Mots clés = mots longs hors stop words FR et EN
    def keywords(text: str) -> set:
        return {w.lower() for w in text.split() if len(w) > 4 and w.lower() not in FR and w.lower() not in EN}

    common = keywords(current_content) & keywords(next_content)
    if not common:
        return ""

    # Phrases de fin de page courante contenant un concept commun
    bridge: list[str] = []
    current_tokens = 0
    half = overlap_size // 2
    for sent in reversed(current_sents):
        if keywords(sent) & common:
            t = token_length(sent)
            if current_tokens + t <= half:
                bridge.insert(0, sent)
                current_tokens += t

    # Phrases de début de page suivante contenant un concept commun
    for sent in next_sents:
        if keywords(sent) & common:
            t = token_length(sent)
            if current_tokens + t <= overlap_size:
                bridge.append(sent)
                current_tokens += t

    return " ".join(bridge).strip()


# ------------------------------------------------------------------ #
# CHUNKING AVEC OVERLAP                                                #
# ------------------------------------------------------------------ #

CHUNK_SIZE = 400  # taille cible d'un chunk en tokens
OVERLAP    = 80  # tokens partagés entre deux chunks consécutifs pour préserver le contexte


# ------------------------------------------------------------------ #
# TITLE-BASED CHUNKING                                                 #
# ------------------------------------------------------------------ #

# Lettre majuscule (ASCII + accents français)
_U = r'[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇ]'

# Patterns reconnus comme titres de section
_TITLE_PATTERNS = [
    re.compile(r'^#{1,4}\s+.+'),                                        # Markdown : # Titre, ## Sous-titre
    re.compile(r'^(?:Article|Chapitre|Section|Annexe|Titre)\s+\w+', re.IGNORECASE),  # Juridique FR
    re.compile(rf'^\d+[\.\)]\s+{_U}.{{2,}}'),                          # 1. Titre  /  1) Titre
    re.compile(rf'^\d+\.\d+[\s\.]+{_U}.{{2,}}'),                       # 1.1 Titre /  1.1. Titre
    re.compile(rf'^[IVXLC]+\.\s+{_U}.{{2,}}'),                         # I. Titre  /  II. Titre
    re.compile(rf'^{_U}{{3,}}(?:\s+{_U}+){{0,5}}$'),                   # TITRE EN MAJUSCULES (3–6 mots)
]


def is_title_line(line: str) -> bool:
    """Retourne True si la ligne ressemble à un titre de section."""
    line = line.strip()
    if not line or len(line) > 120:  # titre trop long = probablement du contenu
        return False
    return any(p.match(line) for p in _TITLE_PATTERNS)


def chunk_by_titles(page_num: int, text: str) -> list[tuple[int, str]]:
    """
    Découpe le texte aux frontières de titres détectés.
    Chaque section (titre + contenu) devient un chunk.
    Les sections trop petites sont fusionnées avec la suivante pour éviter les micro-chunks.
    Si une section dépasse CHUNK_SIZE, chunk_text() la subdivise.
    Retourne les chunks fixes si aucun titre n'est détecté (fallback).
    """
    lines = text.splitlines()
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if is_title_line(line) and current:
            section = "\n".join(current).strip()
            if section:
                sections.append(section)
            current = [line]
        else:
            current.append(line)

    if current:
        section = "\n".join(current).strip()
        if section:
            sections.append(section)

    # Moins de 2 sections → pas de structure détectée, fallback chunk_text
    if len(sections) <= 1:
        return chunk_text(page_num, text)

    # Fusion des sections trop petites avec la section suivante
    # Évite les micro-chunks (< 50 tokens) qui nuisent à la qualité du retrieval
    _MIN_SECTION_TOKENS = 80
    merged_sections: list[str] = []
    buffer = ""

    for section in sections:
        if buffer:
            combined = buffer + "\n\n" + section
            if token_length(buffer) < _MIN_SECTION_TOKENS:
                # Section précédente trop petite → on la fusionne avec la courante
                buffer = combined
            else:
                merged_sections.append(buffer)
                buffer = section
        else:
            buffer = section

    if buffer:
        # Si le dernier buffer est trop petit, le fusionner avec le précédent
        if merged_sections and token_length(buffer) < _MIN_SECTION_TOKENS:
            merged_sections[-1] = merged_sections[-1] + "\n\n" + buffer
        else:
            merged_sections.append(buffer)

    chunks: list[tuple[int, str]] = []
    for section in merged_sections:
        if token_length(section) <= CHUNK_SIZE:
            chunks.append((page_num, section))
        else:
            # Section trop longue : subdivise en gardant le titre dans chaque sous-chunk
            sub = chunk_text(page_num, section)
            chunks.extend(sub)

    return chunks


def chunk_text(page_num: int, text: str) -> list[tuple[int, str]]:
    """Découpe un texte en chunks de ~CHUNK_SIZE tokens avec chevauchement (overlap)."""
    sentences = cached_sent_tokenize(text)
    chunks: list[tuple[int, str]] = []
    current_sents: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = token_length(sent)
        if current_tokens + sent_tokens > CHUNK_SIZE and current_sents:
            # Sauvegarde le chunk courant
            chunks.append((page_num, " ".join(current_sents).strip()))
            # Conserve les dernières phrases pour l'overlap
            overlap_sents: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sents):
                t = token_length(s)
                if overlap_tokens + t <= OVERLAP:
                    overlap_sents.insert(0, s)
                    overlap_tokens += t
                else:
                    break
            current_sents = overlap_sents
            current_tokens = overlap_tokens
        current_sents.append(sent)
        current_tokens += sent_tokens

    if current_sents:
        chunks.append((page_num, " ".join(current_sents).strip()))
    return chunks



# ------------------------------------------------------------------ #
# COUPURE INTELLIGENTE (DÉBUT / FIN)                                   #
# ------------------------------------------------------------------ #

def get_smart_text_end(content: str, size: int) -> str:
    """Extrait la fin du texte jusqu'à `size` tokens, en coupant à la frontière de phrase."""
    if token_length(content) <= size:
        return content

    sentences = cached_sent_tokenize(content)
    current_tokens = 0
    best_sentences = []

    # Parcourt les phrases en sens inverse pour remplir le budget depuis la fin
    for sentence in reversed(sentences):
        sent_tokens = token_length(sentence)
        # +1 pour l'espace inter-phrases ; +50 = tolérance pour éviter de couper une phrase courte
        if current_tokens + sent_tokens + 1 <= size + 50:
            best_sentences.insert(0, sentence)
            current_tokens += sent_tokens + 1
        else:
            break

    if best_sentences:
        return " ".join(best_sentences).strip()

    # Fallback : aucune phrase entière ne tient — coupure mot par mot depuis la fin
    words = content.split()
    current_tokens = 0
    best_words = []
    for word in reversed(words):
        wt = token_length(word)
        if current_tokens + wt + 1 <= size + 50:
            best_words.insert(0, word)
            current_tokens += wt + 1
        else:
            break
    return " ".join(best_words).strip()


# ------------------------------------------------------------------ #
# SEMANTIC CHUNKING                                                    #
# ------------------------------------------------------------------ #

def chunk_by_semantics(page_num: int, text: str) -> list[tuple[int, str]]:
    """
    Découpe le texte aux frontières sémantiques : coupe quand la similarité
    cosinus entre deux phrases consécutives chute sous (moyenne - écart-type).
    Utilise le même modèle d'embedding que le pipeline de recherche.
    Fallback sur chunk_text() si moins de 3 phrases ou si numpy est absent.
    """
    sentences = cached_sent_tokenize(text)
    if len(sentences) < 3:
        return chunk_text(page_num, text)

    try:
        import numpy as np
        # Import local pour éviter la dépendance circulaire au niveau module
        from rag.embedder import embed_texts

        embeddings = embed_texts(sentences)  # batch : 1 appel modèle pour toutes les phrases

        # Similarité cosinus entre phrases consécutives
        sims = []
        for i in range(len(embeddings) - 1):
            a = np.array(embeddings[i])
            b = np.array(embeddings[i + 1])
            norm = np.linalg.norm(a) * np.linalg.norm(b)
            sims.append(float(np.dot(a, b) / norm) if norm > 0 else 1.0)

        # Seuil dynamique : coupe quand la similarité passe sous (moyenne - écart-type)
        # Plus robuste qu'un seuil fixe car il s'adapte au document
        threshold = float(np.mean(sims) - np.std(sims))

        # Indices des phrases qui marquent le début d'une nouvelle section
        breakpoints = [i + 1 for i, s in enumerate(sims) if s < threshold]

        if not breakpoints:
            return chunk_text(page_num, text)

        # Regroupe les phrases entre chaque point de rupture
        chunks: list[tuple[int, str]] = []
        boundaries = [0] + breakpoints + [len(sentences)]
        for start, end in zip(boundaries, boundaries[1:]):
            group = " ".join(sentences[start:end]).strip()
            if not group or token_length(group) < 30:  # ignore les groupes trop courts
                continue
            if token_length(group) > CHUNK_SIZE:
                chunks.extend(chunk_text(page_num, group))  # subdivise si trop long
            else:
                chunks.append((page_num, group))

        return chunks if chunks else chunk_text(page_num, text)

    except Exception:
        # Fallback silencieux si numpy ou embedder indisponible
        return chunk_text(page_num, text)


def get_smart_text_start(content: str, size: int) -> str:
    """Extrait le début du texte jusqu'à `size` tokens, en coupant à la frontière de phrase."""
    if token_length(content) <= size:
        return content

    sentences = cached_sent_tokenize(content)
    current_tokens = 0
    best_sentences = []

    # Parcourt les phrases dans l'ordre pour remplir le budget depuis le début
    for sentence in sentences:
        sent_tokens = token_length(sentence)
        # +1 pour l'espace inter-phrases ; +50 = tolérance pour éviter de couper une phrase courte
        if current_tokens + sent_tokens + 1 <= size + 50:
            best_sentences.append(sentence)
            current_tokens += sent_tokens + 1
        else:
            break

    if best_sentences:
        return " ".join(best_sentences).strip()

    # Fallback : aucune phrase entière ne tient — coupure mot par mot depuis le début
    words = content.split()
    current_tokens = 0
    best_words = []
    for word in words:
        wt = token_length(word)
        if current_tokens + wt + 1 <= size + 50:
            best_words.append(word)
            current_tokens += wt + 1
        else:
            break
    return " ".join(best_words).strip()
