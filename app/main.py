import streamlit as st
from utils.auth_utils import load_vectorizer
from utils.ml_utils import MODELS
import sys
from pathlib import Path
from config import Config
import os
from pages.user.home_page import user_page
from pages.admin.admin_dashboard import admin_page
from pages.admin.admin_register import admin_register_page
from pages.admin.admin_login import admin_login_page
from pages.client.client_dashboard import client_page
from pages.client.client_login import client_login_page
from pages.client.client_register import client_register_page


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
    if 'admin_step' not in st.session_state:
        st.session_state.admin_step = None
    if 'vectorizer' not in st.session_state:
        st.session_state.vectorizer = load_vectorizer()
    if 'route' not in st.session_state:
        st.session_state.route = None

    user = st.session_state.user
    vectorizer = st.session_state.vectorizer

    if st.session_state.route == "login":
        client_login_page()
    elif st.session_state.route == "register":
        client_register_page()
    elif "admin_register" in current_url:
        admin_register_page()
    elif "admin_login" in current_url:
        admin_login_page()
    elif user:
        if user.get("id_role") == 2:
            admin_page(user)
        else:
            client_page(user, vectorizer)
    else:
        user_page(vectorizer)


if __name__ == "__main__":
    missing = [name for name, path in MODELS.items() if not os.path.exists(path)]
    if missing:
        st.error(f"Отсутствуют модели: {', '.join(missing)}")
        st.stop()
    main()