import os


def find_project_root(current_dir: str) -> str:
    """Remonte l'arborescence jusqu'à trouver le dossier contenant main.py."""
    while "main.py" not in os.listdir(current_dir):
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            raise ValueError("Impossible de trouver la racine du projet.")
        current_dir = parent
    return current_dir
