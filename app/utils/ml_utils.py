import streamlit as st
import joblib
import os
from .file_utils import extract_text_from_file
from langdetect import detect
import numpy as np


# Конфигурация моделей для классификации единичного файла
MODELS = {
    "Наивный Байес": "models/naive_bayes.pkl",
    "Метод опорных векторов (SVC)": "models/svc.pkl",
    "Логистическая регрессия": "models/logistic_regression.pkl",
    "Случайный лес": "models/random_forest.pkl",
    "Кластеризация": "models/clasterisation.pkl",
    "Ансамбль моделей (детектор аномалий)": "models/anomaly_clf.pkl"
}

# Конфигурация моделей для классификации .zip архивов
MODELS_ZIP = {
    "Наивный Байес": "models/naive_bayes.pkl",
    "Метод опорных векторов (SVC)": "models/svc.pkl",
    "Логистическая регрессия": "models/logistic_regression.pkl",
    "Случайный лес": "models/random_forest.pkl",
    "Кластеризация": "models/clasterisation.pkl",
}


class AnomalyAwareClassifier:
    def __init__(self, knn_model, classifier, vectorizer, threshold=0.6):
        self.knn = knn_model
        self.clf = classifier
        self.vectorizer = vectorizer
        self.threshold = threshold

    def is_anomaly(self, vector):
        distances, _ = self.knn.kneighbors(vector, n_neighbors=1)
        return distances[0][0] > self.threshold

    def predict(self, text):
        vector = self.vectorizer.transform([text])
        return self.predict_vector(vector)

    def predict_vector(self, vector):
        if self.is_anomaly(vector):
            return "Аномалия", "-"
        else:
            label = self.clf.predict(vector)[0]
            confidence = f"{self.clf.predict_proba(vector).max():.2f}" if hasattr(self.clf, "predict_proba") else "-"
            return label, confidence
        

# Загрузчик моделей
def load_model(model_name):
    try:
        if model_name not in MODELS:
            st.error(f"Неизвестная модель: {model_name}")
            return None
            
        model_path = MODELS[model_name]
        if not os.path.exists(model_path):
            st.error(f"Файл модели {model_path} не найден")
            return None
            
        model = joblib.load(model_path)
        
        if model_name == "Ансамбль моделей (детектор аномалий)":
            if not isinstance(model, AnomalyAwareClassifier):
                st.error("Модель ансамблей должна быть экземпляром AnomalyAwareClassifier")
                return None
        elif not hasattr(model, 'predict'):
            st.error(f"Модель {model_name} не поддерживает метод predict")
            return None
            
        return model
        
    except Exception as e:
        st.error(f"Ошибка загрузки модели {model_name}: {str(e)}")
        return None
    

# Классификация документов в зависимости от модели
def classify_document(uploaded_file, model_name, vectorizer):
    try:
        text = extract_text_from_file(uploaded_file)
        if not text or len(text.strip()) < 10:
            return None, None, text[:500], 0, detect(text)
        
        vector = vectorizer.transform([text])
        model = load_model(model_name)
        
        if model is None:
            return None, None, text[:500], len(text.split()), detect(text)
        
        lang = detect(text) if len(text) > 50 else "Неизвестно"
        
        if model_name == "Ансамбль моделей (детектор аномалий)":
            label, conf_str = model.predict_vector(vector)
            prediction = label
            try:
                confidence = float(conf_str) if conf_str != "-" else None
            except (ValueError, TypeError):
                confidence = None
        elif model_name == "Кластеризация":
            prediction = model.predict(vector)[0]
            confidence = None  # Для кластеризации уверенность не определяется
        else:
            try:
                if hasattr(model, "predict_proba"):
                    proba = model.predict_proba(vector)[0]
                    prediction = model.classes_[np.argmax(proba)]
                    confidence = np.max(proba)
                elif hasattr(model, "decision_function"):
                    scores = model.decision_function(vector)[0]
                    prediction = model.classes_[np.argmax(scores)]
                    confidence = (scores.max() - scores.min()) / 10
                else:
                    prediction = model.predict(vector)[0]
                    confidence = None  # Для моделей без оценки уверенности
            except Exception as e:
                st.error(f"Ошибка предсказания: {str(e)}")
                return None, None, text[:500], len(text.split()), lang
        
        return prediction, confidence, text[:500], len(text.split()), lang
    
    except Exception as e:
        st.error(f"Ошибка обработки документа: {str(e)}")
        return None, None, text[:500] if 'text' in locals() else "", 0, "Неизвестно"