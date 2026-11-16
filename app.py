import streamlit as st

from config import load_settings


APP_NAME = "BL Travel Companion"

st.set_page_config(page_title=APP_NAME)
st.title(APP_NAME)
st.write("A travel assistant for Bảo Lộc, Vietnam.")

st.subheader("Configuration status")
settings = load_settings()
missing_settings = [name for name, value in settings.items() if not value]

if missing_settings:
    st.warning("Required settings are missing or blank.")
    st.write(", ".join(missing_settings))
    st.info(
        "If needed, copy `.env.example` to `.env` in the project folder. "
        "Fill in the missing settings and restart the app. "
        "If a setting already exists in your shell environment, update it there."
    )
else:
    st.success("All required settings are present.")

st.caption("Service connections have not been verified.")
