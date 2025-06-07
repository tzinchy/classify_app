from joblib import load
from pathlib import Path
import streamlit as st

def load_vectorizer():
    """Загрузка векторизатора с русской обработкой текста"""
    try:
        model_path = Path("/app/app/models/vectorizer.pkl")
        
        # Проверка существования файла
        if not model_path.exists():
            st.error(f"Файл векторизатора не найден: {model_path}")
            raise FileNotFoundError(f"Файл векторизатора не найден: {model_path}")
        
        # Загрузка с обработкой русской кодировки
        vectorizer = load(model_path)
        
        # Проверка работоспособности
        test_text = "проверка русского текста"
        _ = vectorizer.transform([test_text])
        
        return vectorizer
        
    except Exception as e:
        st.error(f"Ошибка загрузки векторизатора: {str(e)}")
        raise