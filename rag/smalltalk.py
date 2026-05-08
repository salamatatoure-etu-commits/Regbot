import re
from typing import Set

SMALLTALK_PATTERN = {
    "fr": [
        "bonjour", "salut", "bonsoir", "coucou", "hey", "yo", "hello",
        "allô", "rebonjour",
        "ça va ?", "comment ça va ?", "comment tu vas ?", "comment allez-vous ?",
        "tu vas bien ?", "quoi de neuf ?", "bien ou bien ?", "ça roule ?",
        "merci", "merci beaucoup", "merci pour ton aide", "super, merci",
        "c'est gentil", "je te remercie", "ok merci",
        "bonne journée", "bonne nuit", "à bientôt", "à plus",
        "super", "top", "parfait", "génial", "nickel", "trop bien",
        "trop cool", "cool", "j'adore", "bien joué", "bravo", "excellent",
        "test", "mdr", "lol", "haha", "...", "ok", "d'accord",
        "ah bon", "ah ok", "hm", "ouais", "oui",
        "y a quelqu'un ?", "il y a quelqu'un ?", "j'ai besoin d'aide",
        "tu es là ?", "quelqu'un ici ?", "j'ai une question",
        "aide moi", "je suis perdu",
    ],
    "en": [
        "hello", "hi", "hey", "yo",
        "how are you?", "how's it going?", "you there?", "are you there?",
        "anybody here?", "i need help", "can you help me?",
        "i have a question", "help me please",
        "thanks", "thank you", "thanks a lot", "appreciate it",
        "i'm fine, thanks", "all good", "cheers", "howdy",
        "nice to meet you", "take care",
        "good morning", "good evening", "good night",
        "what's up?", "sup?", "awesome", "perfect", "amazing",
        "love it", "cool", "great job", "well done",
        "ok thanks", "ok", "okay", "sure", "right",
        "ah", "lol", "haha", "hm", "hmm", "test",
    ],
    "es": [
        "hola", "buenas", "buenas tardes", "buenas noches", "buen día",
        "¿cómo estás?", "¿cómo te va?", "¿qué tal?", "¿qué hay?", "¿qué pasa?",
        "todo bien", "bien, gracias", "gracias", "muchas gracias",
        "te lo agradezco", "muy bien", "perfecto", "excelente",
        "genial", "increíble", "me encanta", "buen trabajo",
        "ok gracias", "ok", "vale", "está bien", "ah ok", "entendido",
        "encantado", "un placer", "hasta luego", "hasta pronto",
        "cuidate", "saludos", "jajaja", "jeje", "mmm", "test",
        "aló", "estás ahí?", "hay alguien?", "necesito ayuda",
        "me puedes ayudar?", "tengo una pregunta", "ayuda por favor",
    ],
}

DEFAULT_RESPONSES = {
    "fr": "Bonjour ! N'hésitez pas à poser une question liée à la documentation interne.",
    "en": "Hello! Feel free to ask a documentation-related question.",
    "es": "¡Hola! No dudes en hacer una pregunta relacionada con la documentación.",
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[.,!?;:"\'\(\)\[\]\{\}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


_SMALLTALK_SET: Set[str] = set()


def _build_set():
    global _SMALLTALK_SET
    for phrases in SMALLTALK_PATTERN.values():
        _SMALLTALK_SET.update(_normalize(p) for p in phrases)


_build_set()


def is_smalltalk(query: str) -> bool:
    q = _normalize(query)

    if q in _SMALLTALK_SET:
        return True

    words = q.split()
    if 1 < len(words) <= 3 and all(w in _SMALLTALK_SET for w in words):
        return True

    if len(q) < 25:
        for pattern in _SMALLTALK_SET:
            if re.search(r'\b' + re.escape(pattern) + r'\b', q):
                return True

    return False


def get_default_response(langue: str = "fr") -> str:
    return DEFAULT_RESPONSES.get(langue, DEFAULT_RESPONSES["fr"])
