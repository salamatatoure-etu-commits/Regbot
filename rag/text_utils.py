import re

def strip_nul(text: str | None) -> str | None:
    """Enlève les caractères NUL d'une chaîne."""
    return text.replace("\x00", "") if text else text


def remove_binary_garbage(text: str) -> str:
    """
    Nettoie le texte en supprimant les caractères de contrôle indésirables.
    """
    # Supprimer les caractères de contrôle sauf \t \n \r
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", " ", text)
    return " ".join(text.split())  # Normaliser les espaces


