import re
import time

import requests

from config import load_settings


AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:"
REQUEST_TIMEOUT = (5, 15)
INVALID_RESPONSE = "Firebase returned an unexpected response. Please try again."
EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
ERROR_MESSAGES = {
    "EMAIL_EXISTS": "That email is already registered. Please sign in.",
    "INVALID_EMAIL": "Enter a valid email address.",
    "WEAK_PASSWORD": "Choose a password that meets this Firebase project's password policy.",
    "PASSWORD_DOES_NOT_MEET_REQUIREMENTS": "Choose a password that meets this Firebase project's password policy.",
    "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
    "INVALID_PASSWORD": "Incorrect email or password.",
    "EMAIL_NOT_FOUND": "Incorrect email or password.",
    "USER_DISABLED": "This account is disabled. Contact the project administrator.",
    "OPERATION_NOT_ALLOWED": "Enable Email/Password in Firebase Authentication and try again.",
}


class FirebaseError(Exception):
    """An authentication error with a message safe to display."""


def validate_config(settings: dict[str, str]) -> None:
    if not settings["FIREBASE_PROJECT_ID"] or not settings["FIREBASE_API_KEY"]:
        raise FirebaseError(
            "Set FIREBASE_PROJECT_ID and FIREBASE_API_KEY in the project .env, then restart Streamlit."
        )
    if not re.fullmatch(r"[a-z0-9-]+", settings["FIREBASE_PROJECT_ID"]):
        raise FirebaseError("Use the Firebase Project ID from the console in .env.")


def _error_message(status: int, data: dict) -> str:
    error = data.get("error")
    message = error.get("message") if isinstance(error, dict) else None
    code = message.partition(":")[0].strip() if isinstance(message, str) else ""

    if status == 429 or code == "TOO_MANY_ATTEMPTS_TRY_LATER":
        return "Too many attempts. Wait a little and try again."
    if status in (401, 403, 404) or code.startswith(("API_KEY_", "PROJECT_NOT_FOUND")):
        return "Firebase access failed. Check the project ID and Web API key in .env."
    return ERROR_MESSAGES.get(code, "Firebase could not complete the request. Please try again.")


def _authenticate(action: str, email: str, password: str) -> dict:
    settings = load_settings()
    validate_config(settings)
    email = email.strip()
    if not EMAIL_PATTERN.fullmatch(email):
        raise FirebaseError("Enter a valid email address.")
    if not password:
        raise FirebaseError("Enter a password.")
    if action == "signUp" and len(password) < 6:
        raise FirebaseError("Choose a password with at least six characters.")

    started_at = time.monotonic()
    try:
        response = requests.post(
            AUTH_URL + action,
            params={"key": settings["FIREBASE_API_KEY"]},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
    except requests.Timeout:
        raise FirebaseError("Firebase took too long to respond. Please try again.") from None
    except requests.RequestException:
        raise FirebaseError("Could not reach Firebase. Check your connection and try again.") from None

    try:
        data = response.json()
    except ValueError:
        raise FirebaseError(INVALID_RESPONSE) from None
    if not isinstance(data, dict):
        raise FirebaseError(INVALID_RESPONSE)
    if response.status_code != 200:
        raise FirebaseError(_error_message(response.status_code, data))

    returned_email = data.get("email")
    uid = data.get("localId")
    token = data.get("idToken")
    lifetime = data.get("expiresIn")
    if not (
        isinstance(returned_email, str) and returned_email.casefold() == email.casefold()
        and isinstance(uid, str) and uid.strip()
        and isinstance(token, str) and token.strip()
        and isinstance(lifetime, str) and re.fullmatch(r"[0-9]{1,9}", lifetime)
    ):
        raise FirebaseError(INVALID_RESPONSE)

    expires_at = started_at + int(lifetime)
    if expires_at <= time.monotonic():
        raise FirebaseError(INVALID_RESPONSE)

    # The placeholder only needs the verified identity and expiry.
    return {"uid": uid, "email": returned_email, "expires_at": expires_at}


def create_account(email: str, password: str) -> None:
    _authenticate("signUp", email, password)


def sign_in(email: str, password: str) -> dict:
    return _authenticate("signInWithPassword", email, password)
