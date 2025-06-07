import streamlit as st
from utils.auth_utils import load_vectorizer
from utils.ml_utils import MODELS
import sys
from pathlib import Path
from config import Config
import os
from pages.user.home_page import user_page
from pages.analyst.analyst_dashboard import analyst_page
from pages.analyst.analyst_register import analyst_register_page
from pages.analyst.analyst_login import analyst_login_page
from pages.emploee.emploee_dashboard import emploee_page
from pages.emploee.emploee_login import emploee_login_page
from pages.emploee.emploee_register import emploee_register_page


# Добавляем корень проекта в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))


# Основная логика
def main():
    try:
        Config.validate_config()
    except ValueError as e:
        st.error(f"Configuration error: {str(e)}")
        st.stop()
        
    current_url = st.query_params

    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'client' not in st.session_state:
        st.session_state.client = None
    if 'analyst_step' not in st.session_state:
        st.session_state.analyst_step = None
    if 'vectorizer' not in st.session_state:
        st.session_state.vectorizer = load_vectorizer()
    if 'route' not in st.session_state:
        st.session_state.route = None

    user = st.session_state.user
    vectorizer = st.session_state.vectorizer

    if st.session_state.route == "login":
        emploee_login_page()
    elif st.session_state.route == "register":
        emploee_register_page()
    elif "analyst_register" in current_url:
        analyst_register_page()
    elif "analyst_login" in current_url:
        analyst_login_page()
    elif user:
        if user.get("id_role") == 2:
            analyst_page(user)
        else:
            emploee_page(user, vectorizer)
    else:
        user_page(vectorizer)


if __name__ == "__main__":
    main()