import unicodedata
from functools import lru_cache
import regex

try:
    import spacy
    from spacy.lang.fr.stop_words import STOP_WORDS as FR
    from spacy.lang.en.stop_words import STOP_WORDS as EN
except ImportError:
    spacy = None
    FR = set()
    EN = set()

try:
    import tiktoken
except ImportError:
    tiktoken = None


def init_spacy_segmenter():
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
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


enc = init_token_encoder()


def clean_text(content: str) -> str:
    content = content.replace("\x00", "")
    return unicodedata.normalize("NFKC", content).strip()


@lru_cache(maxsize=10000)
def token_length(text: str) -> int:
    if enc is not None:
        return len(enc.encode(text))
    return len(text.split())


@lru_cache(maxsize=500)
def cached_sent_tokenize(text: str):
    if nlp is not None:
        doc = nlp(text)
        return [s.text.strip() for s in doc.sents]
    return [s.strip() for s in regex.split(r'(?<=[.!?])\s+', text) if s.strip()]
