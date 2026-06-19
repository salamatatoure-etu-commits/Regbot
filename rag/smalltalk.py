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
        "test", "mdr", "lol", "haha", "...", "d'accord",
        "ah bon", "ah ok", "hm",
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
        "ok thanks", "okay", "sure", "right",
        "ah", "lol", "haha", "hm", "hmm", "test",
    ],
    "es": [
        "hola", "buenas", "buenas tardes", "buenas noches", "buen día",
        "¿cómo estás?", "¿cómo te va?", "¿qué tal?", "¿qué hay?", "¿qué pasa?",
        "todo bien", "bien, gracias", "gracias", "muchas gracias",
        "te lo agradezco", "muy bien", "perfecto", "excelente",
        "genial", "increíble", "me encanta", "buen trabajo",
        "ok gracias", "vale", "está bien", "ah ok", "entendido",
        "encantado", "un placer", "hasta luego", "hasta pronto",
        "cuidate", "saludos", "jajaja", "jeje", "mmm", "test",
        "aló", "estás ahí?", "hay alguien?", "necesito ayuda",
        "me puedes ayudar?", "tengo una pregunta", "ayuda por favor",
    ],
}

_GREETINGS = {"bonjour", "salut", "bonsoir", "coucou", "hey", "yo", "hello", "allô", "rebonjour", "hi", "howdy", "hola", "buenas"}
_THANKS    = {"merci", "merci beaucoup", "merci pour ton aide", "super merci", "je te remercie", "ok merci", "c'est gentil", "thanks", "thank you", "thanks a lot", "appreciate it", "cheers", "gracias", "muchas gracias", "te lo agradezco"}
_GOODBYES  = {"bonne journée", "bonne nuit", "à bientôt", "à plus", "take care", "good night", "good morning", "good evening", "hasta luego", "hasta pronto", "cuidate"}

_TYPED_RESPONSES = {
    "greeting": "Bonjour ! Posez-moi une question sur vos documents.",
    "thanks":   "De rien ! Si vous avez d'autres questions, je suis là.",
    "goodbye":  "Bonne journée ! À bientôt.",
    "default":  "N'hésitez pas à poser une question liée à la documentation interne.",
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

    # Uniquement pour les questions très courtes sans mot interrogatif
    # Évite les faux positifs sur "2FA", "salaire", "mot de passe"...
    _QUESTION_WORDS = {"quels", "quelle", "comment", "pourquoi", "qui", "que", "quel", "qu", "quoi", "cest", "kesako", "what", "explain"}
    words_set = set(q.split())
    if len(q) < 15 and not (words_set & _QUESTION_WORDS):
        for pattern in _SMALLTALK_SET:
            if re.search(r'\b' + re.escape(pattern) + r'\b', q):
                return True

    return False


def get_default_response(query: str = "", langue: str = "fr") -> str:
    q = _normalize(query)
    if any(q == _normalize(p) or q.startswith(_normalize(p)) for p in _GREETINGS):
        return _TYPED_RESPONSES["greeting"]
    if any(q == _normalize(p) or _normalize(p) in q for p in _THANKS):
        return _TYPED_RESPONSES["thanks"]
    if any(q == _normalize(p) or _normalize(p) in q for p in _GOODBYES):
        return _TYPED_RESPONSES["goodbye"]
    return _TYPED_RESPONSES["default"]
