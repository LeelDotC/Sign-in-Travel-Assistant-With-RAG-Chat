import time

import streamlit as st

from config import load_settings
from firebase_client import FirebaseError, create_account, sign_in, validate_config


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


@st.fragment(run_every=5)
def protected_screen() -> None:
    user = st.session_state.get("user")
    if user is None:
        st.rerun()
    if time.monotonic() >= user["expires_at"]:
        st.session_state.clear()
        st.session_state["auth_feedback"] = ("info", "Your session expired. Please sign in again.")
        st.rerun()

    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()

    st.text(f"Signed in as {user['email']}")
    st.write("Travel chat is coming soon")


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
