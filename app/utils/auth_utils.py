import joblib
import streamlit as st


VECTORIZER_PATH = "models/vectorizer.pkl"

# Функция загрузки векторизатора для обработки документов
def load_vectorizer():
    try:
        return joblib.load(VECTORIZER_PATH)
    except Exception as e:
        st.error(f"Ошибка загрузки векторизатора: {e}")
        return None