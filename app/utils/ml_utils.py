import streamlit as st
import joblib
import os
from .file_utils import extract_text_from_file
from langdetect import detect
import numpy as np
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()  # Путь к папке app/
MODELS_DIR = BASE_DIR / "app" / "models"  # Путь к моделям

MODELS = {
    "Наивный Байес": str(MODELS_DIR / "naive_bayes.pkl"),
    "Метод опорных векторов (SVC)": str(MODELS_DIR / "svc.pkl"),
    "Логистическая регрессия": str(MODELS_DIR / "logistic_regression.pkl"),
    "Случайный лес": str(MODELS_DIR / "random_forest.pkl"),
    "Кластеризация": str(MODELS_DIR / "clasterisation.pkl")
}

# Model configurations for .zip archive classification
MODELS_ZIP = {
    "Наивный Байес": str(MODELS_DIR / "naive_bayes.pkl"),
    "Метод опорных векторов (SVC)": str(MODELS_DIR / "svc.pkl"),
    "Логистическая регрессия": str(MODELS_DIR / "logistic_regression.pkl"),
    "Случайный лес": str(MODELS_DIR / "random_forest.pkl"),
    "Кластеризация": str(MODELS_DIR / "clasterisation.pkl")
}

class AnomalyAwareClassifier:
    """Classifier with integrated anomaly detection capability"""
    
    def __init__(self, knn_model, classifier, vectorizer, threshold=0.6):
        """Initialize with KNN model, base classifier and vectorizer"""
        self.knn = knn_model
        self.clf = classifier
        self.vectorizer = vectorizer
        self.threshold = threshold

    def is_anomaly(self, vector):
        """Check if sample is anomalous based on KNN distance threshold"""
        distances, _ = self.knn.kneighbors(vector, n_neighbors=1)
        return distances[0][0] > self.threshold
    
    def predict(self, text):
        """Predict class for raw text input"""
        vector = self.vectorizer.transform([text])
        return self.predict_vector(vector)

    def predict_vector(self, vector):
        """Predict class for vectorized text, returns ('Аномалия', '-') if anomalous"""
        if self.is_anomaly(vector):
            return "Аномалия", "-"
        else:
            label = self.clf.predict(vector)[0]
            confidence = f"{self.clf.predict_proba(vector).max():.2f}" if hasattr(self.clf, "predict_proba") else "-"
            return label, confidence

def load_model(model_name):
    """Load trained model from pickle file with validation checks"""
    try:
        if model_name not in MODELS:
            st.error(f"Неизвестная модель: {model_name}")
            return None
            
        model_path = MODELS[model_name]
        if not os.path.exists(model_path):
            st.error(f"Файл модели {model_path} не найден")
            return None
            
        # Make sure AnomalyAwareClassifier is available when unpickling
        global AnomalyAwareClassifier
        model = joblib.load(model_path)
        
        # Special validation for anomaly detector
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
    

def classify_document(uploaded_file, model_name, vectorizer):
    """Classify document using specified model and return results"""
    try:
        # Extract and validate text
        text = extract_text_from_file(uploaded_file)
        if not text or len(text.strip()) < 10:
            return None, None, text[:500], 0, detect(text)
        
        # Vectorize text and load model
        vector = vectorizer.transform([text])
        model = load_model(model_name)
        
        if model is None:
            return None, None, text[:500], len(text.split()), detect(text)
        
        # Detect language if enough text
        lang = detect(text) if len(text) > 50 else "Неизвестно"
        
        # Handle different model types
        if model_name == "Ансамбль моделей (детектор аномалий)":
            label, conf_str = model.predict_vector(vector)
            prediction = label
            try:
                confidence = float(conf_str) if conf_str != "-" else None
            except (ValueError, TypeError):
                confidence = None
        elif model_name == "Кластеризация":
            prediction = model.predict(vector)[0]
            confidence = None  # Clustering doesn't provide confidence scores
        else:
            try:
                # Try different prediction methods
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
                    confidence = None
            except Exception as e:
                st.error(f"Ошибка предсказания: {str(e)}")
                return None, None, text[:500], len(text.split()), lang
        
        return prediction, confidence, text[:500], len(text.split()), lang
    
    except Exception as e:
        st.error(f"Ошибка обработки документа: {str(e)}")
        return None, None, text[:500] if 'text' in locals() else "", 0, "Неизвестно"