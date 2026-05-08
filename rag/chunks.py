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
OVERLAP    = 50   # tokens partagés entre deux chunks consécutifs pour préserver le contexte


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


def build_chunks(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Applique chunk_text sur toutes les pages d'un document."""
    all_chunks = []
    for page_num, text in pages:
        all_chunks.extend(chunk_text(page_num, text))
    return all_chunks


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
