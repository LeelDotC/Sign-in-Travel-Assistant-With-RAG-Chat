import math
import os
from urllib.parse import urlsplit

import requests
from dotenv import dotenv_values

from config import ENV_PATH, SETTING_NAMES, load_settings


EMBEDDING_TAGS = ("embeddinggemma:latest", "embeddinggemma")
GENERATION_MODEL = "qwen3:4b"


class CheckError(Exception):
    pass


def get_json(session, method, url, read_timeout, **kwargs):
    try:
        response = session.request(
            method, url, timeout=(10, read_timeout), allow_redirects=False, **kwargs
        )
    except requests.Timeout:
        raise CheckError("Request timed out. Check the runtime and tunnel.") from None
    except requests.RequestException:
        raise CheckError("Request failed. Check the HTTPS tunnel and network.") from None

    if response.status_code != 200:
        raise CheckError(f"Unexpected HTTP status {response.status_code}.")
    try:
        data = response.json()
    except ValueError:
        raise CheckError("Expected JSON from Ollama. Check the tunnel URL.") from None
    if not isinstance(data, dict):
        raise CheckError("Expected a JSON object from Ollama.")
    return data


def check_models(session, base_url):
    models = get_json(session, "GET", base_url + "/api/tags", 30).get("models")
    if not isinstance(models, list):
        raise CheckError("Expected a model list.")

    tags = set()
    for entry in models:
        if not isinstance(entry, dict):
            raise CheckError("Malformed model entry.")
        tag = entry.get("name") or entry.get("model")
        if not isinstance(tag, str) or not tag.strip():
            raise CheckError("Malformed model tag.")
        tags.add(tag)

    embedding_tag = next((tag for tag in EMBEDDING_TAGS if tag in tags), None)
    missing = []
    if embedding_tag is None:
        missing.append("embeddinggemma")
    if GENERATION_MODEL not in tags:
        missing.append(GENERATION_MODEL)
    if missing:
        raise CheckError("Missing models: " + ", ".join(missing) + ".")
    return embedding_tag


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def check_embedding(session, base_url, tag):
    data = get_json(
        session, "POST", base_url + "/api/embed", 120,
        json={"model": tag, "input": "Travel assistant service check"},
    )
    vectors = data.get("embeddings")
    if not isinstance(vectors, list) or len(vectors) != 1:
        raise CheckError("Expected one embedding vector.")
    vector = vectors[0]
    if not isinstance(vector, list) or not vector or not all(map(finite_number, vector)):
        raise CheckError("Expected a non-empty, finite numeric vector.")


def check_generation(session, base_url):
    data = get_json(
        session, "POST", base_url + "/api/generate", 180,
        json={
            "model": GENERATION_MODEL,
            "prompt": "Reply with a brief greeting.",
            "stream": False,
            "think": False,
            "options": {"num_predict": 32},
        },
    )
    answer = data.get("response")
    if data.get("done") is not True or not isinstance(answer, str) or not answer.strip():
        raise CheckError("Expected a completed response with non-empty final text.")


def valid_tunnel_url(url):
    try:
        parts = urlsplit(url)
        return (
            parts.scheme == "https" and bool(parts.hostname)
            and parts.username is None and parts.password is None
            and parts.port in (None, 443) and parts.path in ("", "/")
            and "?" not in url and "#" not in url
            and not any(char.isspace() or ord(char) < 32 for char in url)
        )
    except ValueError:
        return False


def main():
    shell_settings = {name: os.environ[name] for name in SETTING_NAMES if name in os.environ}
    try:
        file_settings = dotenv_values(ENV_PATH)
        settings = load_settings()
    except (OSError, UnicodeError):
        print("FAIL Configuration - could not read the project .env.")
        return 1

    for name, value in shell_settings.items():
        if name not in file_settings or value.strip() != (file_settings[name] or "").strip():
            print(f"NOTE {name} uses the existing environment value in this process.")

    firebase_missing = [name for name in SETTING_NAMES[:2] if not settings[name]]
    if firebase_missing:
        print("FAIL Firebase configuration - missing " + ", ".join(firebase_missing) + ".")
    else:
        print("PASS Firebase settings present. Sign-up and sign-in were not tested.")

    base_url = settings["OLLAMA_BASE_URL"]
    if not base_url:
        print("FAIL Ollama configuration - OLLAMA_BASE_URL is missing or blank.")
        return 1
    if not valid_tunnel_url(base_url):
        print("FAIL Ollama configuration - use the HTTPS tunnel origin without credentials or a path.")
        return 1
    base_url = base_url.rstrip("/")

    with requests.Session() as session:
        try:
            embedding_tag = check_models(session, base_url)
        except CheckError as error:
            print(f"FAIL Ollama model list - {error}")
            return 1
        print("PASS Ollama model list contains embeddinggemma and qwen3:4b.")

        failed = bool(firebase_missing)
        for label, check in (
            ("Ollama embedding", lambda: check_embedding(session, base_url, embedding_tag)),
            ("Ollama final text", lambda: check_generation(session, base_url)),
        ):
            try:
                check()
            except CheckError as error:
                print(f"FAIL {label} - {error}")
                failed = True
            else:
                print(f"PASS {label}.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
