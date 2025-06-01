import streamlit as st
import pandas as pd


# Обработка текстов документов, которые подаются в векторизатор
def extract_text_from_file(uploaded_file):
    try:
        if uploaded_file.type == "text/plain":
            return str(uploaded_file.read(), "utf-8")
        elif uploaded_file.type == "application/pdf":
            from PyPDF2 import PdfReader
            return "\n".join([page.extract_text() for page in PdfReader(uploaded_file).pages])
        elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            from docx import Document
            return "\n".join([para.text for para in Document(uploaded_file).paragraphs])
        else:
            st.error("Неподдерживаемый формат файла")
            return None
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return None
    
    
# Функция фильтрации истории классификаций
def filter_history(df):
    model_filter = st.selectbox(
        "Фильтр по модели", 
        options=["Все"] + sorted(df['model_used'].unique().tolist())
    )
    
    if model_filter != "Все":
        df = df[df['model_used'] == model_filter]
    
    if "created_at" in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.dropna(subset=['created_at'])
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "С даты", 
                value=df["created_at"].min().date(),
                min_value=df["created_at"].min().date(),
                max_value=df["created_at"].max().date()
            )
        with col2:
            end_date = st.date_input(
                "По дату", 
                value=df["created_at"].max().date(),
                min_value=df["created_at"].min().date(),
                max_value=df["created_at"].max().date()
            )
        
        df = df[
            (df["created_at"] >= pd.to_datetime(start_date)) & 
            (df["created_at"] <= pd.to_datetime(end_date))
        ]
    else:
        st.warning("В данных отсутствует информация о датах классификации")
    
    return df