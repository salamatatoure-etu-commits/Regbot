import httpx

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"


def embed_text(text: str) -> list[float]:
    text = text[:8000]
    response = httpx.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [embed_text(t) for t in texts]
