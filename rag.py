import json
from functools import lru_cache
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

import numpy as np
import requests

from check_services import CheckError, get_json, valid_tunnel_url
from config import load_settings


GUIDE_PATH = Path(__file__).with_name("knowledge_base.json")
EMBEDDING_MODEL = "embeddinggemma"
INDEX_LOCK = Lock()


class RetrievalError(Exception):
    """A retrieval failure with a message safe to show."""


def _nonblank_string(value):
    return isinstance(value, str) and bool(value.strip())


def _valid_source(source):
    try:
        url = urlsplit(source)
        return url.scheme in ("http", "https") and bool(url.hostname)
    except ValueError:
        return False


def load_guide(path=GUIDE_PATH):
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RetrievalError("Could not read the guide as UTF-8 JSON.") from None
    if not isinstance(entries, list) or not entries:
        raise RetrievalError("The guide must contain a non-empty list of entries.")

    ids = set()
    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or not all(
            _nonblank_string(entry.get(field)) for field in ("id", "title", "text", "source")
        ):
            raise RetrievalError(f"Guide entry {position} needs an ID, title, text, and source URL.")
        if entry["id"] in ids:
            raise RetrievalError(f"Guide entry {position} has a duplicate ID.")
        ids.add(entry["id"])
        if not _valid_source(entry["source"]):
            raise RetrievalError(f"Guide entry {position} needs a valid source URL.")
        tags = entry.get("tags")
        if not (
            _nonblank_string(entry.get("category")) and isinstance(tags, list)
            and tags and all(_nonblank_string(tag) for tag in tags)
        ):
            raise RetrievalError(f"Guide entry {position} needs a category and non-empty tags.")
        if len({tag.strip().casefold() for tag in tags}) != len(tags):
            raise RetrievalError(f"Guide entry {position} has duplicate tags.")
    return entries


def _unit_vectors(vectors, expected_rows):
    invalid = "Ollama returned malformed or unusable embedding vectors."
    if not isinstance(vectors, list) or len(vectors) != expected_rows or not all(
        isinstance(row, list) and row and all(type(value) in (int, float) for value in row)
        for row in vectors
    ):
        raise RetrievalError(invalid)
    try:
        matrix = np.array(vectors, dtype=np.float64)
    except (ValueError, OverflowError):
        raise RetrievalError(invalid) from None

    if not np.isfinite(matrix).all():
        raise RetrievalError(invalid)
    scale = np.max(np.abs(matrix), axis=1, keepdims=True)
    if np.any(scale == 0):
        raise RetrievalError(invalid)
    scaled = matrix / scale
    return scaled / np.linalg.norm(scaled, axis=1, keepdims=True)


def _embed(base_url, model, texts):
    with requests.Session() as session:
        try:
            data = get_json(
                session, "POST", base_url + "/api/embed", 120,
                json={"model": model, "input": list(texts)},
            )
        except CheckError as error:
            raise RetrievalError(f"Ollama embedding request failed. {error}") from None
    return _unit_vectors(data.get("embeddings"), len(texts))


@lru_cache(maxsize=4)
def _guide_index(base_url, model, documents):
    return _embed(base_url, model, documents)


def retrieve(question, guide_path=GUIDE_PATH):
    """Return up to three results with complete entries and cosine scores."""
    if not isinstance(question, str) or not question.strip():
        raise RetrievalError("Enter a nonblank question.")
    base_url = load_settings()["OLLAMA_BASE_URL"]
    if not base_url:
        raise RetrievalError("Set OLLAMA_BASE_URL in the project .env.")
    if not valid_tunnel_url(base_url):
        raise RetrievalError("OLLAMA_BASE_URL must be the HTTPS tunnel origin.")
    base_url = base_url.rstrip("/")

    entries = load_guide(guide_path)
    documents = tuple(f"{entry['title']}\n{entry['text']}" for entry in entries)
    with INDEX_LOCK:
        index = _guide_index(base_url, EMBEDDING_MODEL, documents)
    query = _embed(base_url, EMBEDDING_MODEL, (question.strip(),))[0]
    if query.shape[0] != index.shape[1]:
        raise RetrievalError(
            "Ollama returned inconsistent embedding dimensions. Check the model and restart the checker."
        )

    scores = np.clip(index @ query, -1.0, 1.0)
    order = np.argsort(-scores, kind="stable")[:3]
    return [{"entry": entries[i], "score": float(scores[i])} for i in order]
