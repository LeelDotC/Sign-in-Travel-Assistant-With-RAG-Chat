import time
from copy import deepcopy

import streamlit as st

from config import load_settings
from firebase_client import FirebaseError, create_account, sign_in, validate_config
from rag import GenerationError, RetrievalError, answer_question


APP_NAME = "BL Travel Companion"


def show_auth_form(register: bool) -> None:
    st.session_state["show_registration"] = register
    st.session_state.pop("auth_feedback", None)


def submit_auth(register: bool) -> None:
    email = st.session_state["auth_email"]
    password = st.session_state["auth_password"]
    st.session_state["auth_password"] = ""

    try:
        if register:
            confirmation = st.session_state["auth_password_confirmation"]
            st.session_state["auth_password_confirmation"] = ""
            if not password:
                raise FirebaseError("Enter a password.")
            if not confirmation:
                raise FirebaseError("Re-enter your password.")
            if password != confirmation:
                raise FirebaseError("Passwords do not match.")
            create_account(email, password)
            show_auth_form(False)
            st.session_state["auth_feedback"] = ("success", "Account created. Please sign in")
        else:
            user = sign_in(email, password)
            st.session_state.clear()
            st.session_state["user"] = user
    except FirebaseError as error:
        st.session_state["auth_email"] = email
        st.session_state["auth_feedback"] = ("error", str(error))


def require_active_user() -> dict:
    user = st.session_state.get("user")
    if user is None:
        st.rerun()
    if time.monotonic() >= user["expires_at"]:
        st.session_state.clear()
        st.session_state["auth_feedback"] = ("info", "Your session expired. Please sign in again.")
        st.rerun()
    return user


@st.fragment(run_every=5)
def monitor_session() -> None:
    require_active_user()


def render_turn(turn: dict) -> None:
    with st.chat_message("user"):
        st.text(turn["question"])
    with st.chat_message("assistant"):
        st.text(turn["answer"])
        with st.expander("Retrieved evidence"):
            for index, result in enumerate(turn["retrieved"]):
                if index:
                    st.divider()
                entry = result["entry"]
                st.text(f"{entry['id']} · {entry['title']}")
                st.caption(f"Cosine similarity: {result['score']:.4f}")
                st.text(entry["text"])
                st.link_button(f"Source for {entry['id']}", entry["source"])


def process_question(question: str) -> None:
    require_active_user()
    question = question.strip()
    if not question:
        st.warning("Enter a question before submitting.")
        return

    try:
        with st.spinner("Searching the guide and preparing an answer…"):
            require_active_user()
            result = answer_question(question)
    except (RetrievalError, GenerationError) as error:
        require_active_user()
        st.session_state["failed_chat"] = {"question": question, "error": str(error)}
    else:
        require_active_user()
        st.session_state.setdefault("chat_history", []).append({
            "question": question,
            "answer": result["answer"],
            "retrieved": deepcopy(result["retrieved"]),
        })
        st.session_state.pop("failed_chat", None)
    st.rerun()


def protected_screen() -> None:
    user = require_active_user()
    monitor_session()

    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()

    st.text(f"Signed in as {user['email']}")
    for turn in st.session_state.get("chat_history", []):
        render_turn(turn)

    failed = st.session_state.get("failed_chat")
    retry = False
    if failed:
        st.error(f"Could not answer the question. {failed['error']}")
        st.text(f"Failed question: {failed['question']}")
        retry = st.button("Retry question")

    question = st.chat_input("Ask about Bảo Lộc", key="chat_question")
    if question is not None:
        process_question(question)
    elif retry:
        process_question(failed["question"])


st.set_page_config(page_title=APP_NAME)
st.markdown(
    """
    <style>
    div[data-testid="InputInstructions"] > span:nth-child(1) {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title(APP_NAME)
st.write("A travel assistant for Bảo Lộc, Vietnam.")

if "user" not in st.session_state:
    try:
        validate_config(load_settings())
    except FirebaseError as error:
        st.info(str(error))
        st.stop()

    feedback_area = st.empty()
    feedback = st.session_state.pop("auth_feedback", None)
    if feedback:
        kind, message = feedback
        if kind == "error":
            feedback_area.error(message)
        elif kind == "success":
            feedback_area.success(message)
        else:
            feedback_area.info(message)

    register = st.session_state.get("show_registration", False)
    action = "Create account" if register else "Sign in"
    st.subheader(action)
    if register:
        st.caption("Use an email address you control and a separate app password.")

    with st.form("register" if register else "sign_in", enter_to_submit=True):
        st.text_input("Email", key="auth_email")
        st.text_input("Password", type="password", key="auth_password")
        if register:
            st.text_input("Re-enter password", type="password", key="auth_password_confirmation")
        st.form_submit_button(action, on_click=submit_auth, args=(register,))

    switch_label = "Back to sign in" if register else "Create an account"
    st.button(switch_label, on_click=show_auth_form, args=(not register,))
    st.stop()

protected_screen()
