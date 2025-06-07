from pathlib import Path
import pickle
import streamlit as st

def load_vectorizer():
    try:
        # Абсолютный путь внутри контейнера
        model_path = Path("/app/app/models/vectorizer.pkl")
        
        # Отладочная информация
        st.write(f"Ищем векторизатор по пути: {model_path}")
        st.write(f"Файл существует: {model_path.exists()}")
        
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        st.error(f"Ошибка загрузки векторизатора: {str(e)}")
        raise