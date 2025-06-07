import streamlit as st
from datetime import datetime, timedelta
from utils.ml_utils import MODELS, classify_document
import time


# Базовое окно пользователя с ограниченным функционалом
def user_page(vectorizer):
    # Константы
    MAX_FREE_CLASSIFICATIONS = 3
    SESSION_KEY = "doc_classification_limit"
    
    # Инициализация состояния
    if 'classification_result' not in st.session_state:
        st.session_state.classification_result = None
    if 'processing' not in st.session_state:
        st.session_state.processing = None
    if 'show_text' not in st.session_state:
        st.session_state.show_text = False

    # Управление лимитами
    def get_limit_data():
        if SESSION_KEY not in st.session_state:
            reset_time = datetime.now() + timedelta(days=1)
            st.session_state[SESSION_KEY] = {
                'used': 0,
                'reset_time': reset_time.timestamp()
            }
        return st.session_state[SESSION_KEY]
    
    limit_data = get_limit_data()
    remaining = MAX_FREE_CLASSIFICATIONS - limit_data['used']
    
    # Проверка сброса лимита
    if time.time() > limit_data['reset_time']:
        limit_data['used'] = 0
        limit_data['reset_time'] = (datetime.now() + timedelta(days=1)).timestamp()
    
    # --- Интерфейс ---
    
    # Заголовок и кнопки авторизации
    st.title("Анализ документов")
    
    # Блок авторизации под заголовком (исправленные кнопки)
    auth_cols = st.columns(2)  # Теперь только 2 колонки для кнопок
    with auth_cols[0]:
        if st.button("🔑 Войти", key="login_btn", use_container_width=True):
            st.session_state.route = "login"
            st.rerun()
    with auth_cols[1]:
        if st.button("📝 Регистрация", key="register_btn", use_container_width=True):
            st.session_state.route = "register"
            st.rerun()
    
    # Информация о доступном функционале
    st.info("🔒 Полный функционал (включая обработку архивов) доступен после авторизации")
    
    # Создаем placeholder для счетчика, чтобы обновлять его динамически
    counter_placeholder = st.empty()
    if remaining <= 0:
        counter_placeholder.warning(f"⚠️ Вы использовали все {MAX_FREE_CLASSIFICATIONS} бесплатных попыток")
        st.stop()
    else:
        counter_placeholder.info(f"🔄 Осталось попыток: {remaining} из {MAX_FREE_CLASSIFICATIONS}")
    
    # Блок классификации документа
    st.markdown("### 📄 Классификация документа")
    
    model_name = st.selectbox(
        "🧠 Модель", 
        list(MODELS.keys()), 
        key="client_model"
    )
    
    uploaded_file = st.file_uploader(
        "📎 Загрузите файл", 
        type=["txt", "pdf", "docx"], 
        key="client_upload"
    )
    
    # Кнопка классификации (полная ширина)
    if uploaded_file and st.button(
        "🚀 Классифицировать", 
        key="client_classify",
        use_container_width=True
    ):
        if limit_data['used'] >= MAX_FREE_CLASSIFICATIONS:
            st.error("Лимит исчерпан")
            st.stop()
        
        with st.spinner("🔍 Анализируем документ..."):
            try:
                prediction, confidence, preview, wc, lang = classify_document(
                    uploaded_file, 
                    model_name, 
                    vectorizer
                )
                
                # Увеличиваем счетчик использований сразу
                limit_data['used'] += 1
                remaining = MAX_FREE_CLASSIFICATIONS - limit_data['used']
                
                # Обновляем счетчик в интерфейсе
                if remaining <= 0:
                    counter_placeholder.warning(f"⚠️ Вы использовали все {MAX_FREE_CLASSIFICATIONS} бесплатных попыток")
                else:
                    counter_placeholder.info(f"🔄 Осталось попыток: {remaining} из {MAX_FREE_CLASSIFICATIONS}")
                
                # Функция перевода названий классов
                def translate_class(pred):
                    class_map = {
                        "Order": "Приказ",
                        "Ordinance": "Постановление",
                        "Letters": "Письмо",
                        "Miscellaneous": "Общее",
                        # Для кластеризации
                        0: "Приказ",
                        1: "Постановление",
                        2: "Письмо",
                        3: "Общее"
                    }
                    return class_map.get(pred, str(pred))
                
                if prediction is not None:
                    # Получаем русское название класса
                    russian_class = translate_class(prediction)
                    
                    if model_name == "Кластеризация":
                        st.success(f"✅ Класс: **{russian_class}**")
                    else:
                        confidence_str = f"{confidence:.2%}" if confidence is not None else "не определена"
                        st.success(f"✅ Класс: **{russian_class}** (уверенность: **{confidence_str}**)")
                    
                    st.caption(f"🌐 Язык: **{lang}** &nbsp;&nbsp;|&nbsp;&nbsp;📏 Кол-во слов: **{wc}**")
                    
                    with st.expander("📄 Просмотреть текст документа"):
                        st.text(preview)
                    
                    # Сохраняем результат с русским названием класса
                    st.session_state.classification_result = {
                        'prediction': russian_class,
                        'confidence': confidence,
                        'text': preview,
                        'words': wc,
                        'lang': lang
                    }
                else:
                    st.error("⚠️ Не удалось классифицировать документ")
                    
            except Exception as e:
                st.error(f"Ошибка: {str(e)}")