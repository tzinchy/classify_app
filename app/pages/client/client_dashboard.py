import streamlit as st
from database.db_operations import Database
from utils.ml_utils import MODELS, MODELS_ZIP, classify_document, load_model, AnomalyAwareClassifier
from utils.file_utils import extract_text_from_file
import plotly.express as px
import pandas as pd
import os
import io
import zipfile
import tempfile
import shutil


db = Database()

# Личный кабинет клиента
def client_page(user, vectorizer):
    # Проверка авторизации
    if not user:
        st.error("Пожалуйста, войдите в систему для доступа к этой странице.")
        st.stop()

    st.title(f"Добро пожаловать, {user['login']}")

    # Кнопка выхода
    if st.button("Выйти"):
        st.session_state.user = None
        st.rerun()

    # Функция перевода классов для всех моделей
    def translate_class(pred, model):
        # Для кластеризации
        if model == "Кластеризация":
            cluster_names = {
                0: "Приказ",
                1: "Постановление", 
                2: "Письмо",
                3: "Общее"
            }
            return cluster_names.get(pred, f"Кластер {pred}")
        
        # Для других моделей
        class_map = {
            "Order": "Приказ",
            "Ordinance": "Постановление",
            "Letters": "Письмо",
            "Miscellaneous": "Общее"
        }
        return class_map.get(pred, pred)

    # Секция классификации
    st.markdown("### 📄 Классификация документа")
    model_name = st.selectbox("🧠 Модель", list(MODELS.keys()), key="client_model",
                            on_change=lambda: st.session_state.pop("last_classification_id", None))
    uploaded_file = st.file_uploader("📎 Загрузите файл", type=["txt", "pdf", "docx"], key="client_upload")

    # Кнопка классификации
    if uploaded_file and st.button(
        "🚀 Классифицировать",
        key="client_classify",
        use_container_width=True
    ):
        with st.spinner("🔍 Анализируем документ..."):
            try:
                prediction, confidence, preview, wc, lang = classify_document(uploaded_file, model_name, vectorizer)
                
                if prediction is not None:
                    # Получаем название класса на русском
                    russian_class = translate_class(prediction, model_name)
                    
                    # Формируем сообщение
                    if model_name == "Кластеризация":
                        msg = f"✅ Класс: **{russian_class}**"
                    else:
                        confidence_str = f"{confidence:.2%}" if confidence is not None else "не определена"
                        msg = f"✅ Класс: **{russian_class}** (уверенность: **{confidence_str}**)"
                    
                    st.success(msg)
                    st.caption(f"🌐 Язык: **{lang}** | 📏 Слов: **{wc}**")
                    
                    with st.expander("📄 Просмотреть текст"):
                        st.text(preview[:5000] + "..." if len(preview) > 5000 else preview)
                        
                    # Сохраняем в БД (русские названия для всех моделей)
                    classification_id = db.create_classification(
                        user["id"],
                        uploaded_file.name,
                        model_name,
                        russian_class,
                        float(confidence) if confidence is not None else None
                    )
                    
                    # Сохраняем ID для оценки
                    if classification_id:
                        st.session_state.last_classification_id = classification_id
                        st.session_state.show_rating = True
                else:
                    st.error("⚠️ Не удалось классифицировать документ")
                    
            except Exception as e:
                st.error(f"❌ Ошибка классификации: {str(e)}")

    # Форма оценки результата
    if st.session_state.get("show_rating") and "last_classification_id" in st.session_state:
        with st.form("rating_form"):
            st.subheader("Оцените точность классификации")
            rating = st.slider("Оценка", 1, 5, 3, key="rating_slider")
            comment = st.text_area("Комментарий (необязательно)", key="rating_comment")
            
            if st.form_submit_button("📤 Отправить оценку"):
                try:
                    if db.create_rating(
                        st.session_state.last_classification_id,
                        user["id"],
                        rating,
                        comment
                    ):
                        st.session_state.rating_submitted = True
                        st.session_state.pop("last_classification_id", None)
                        st.session_state.pop("show_rating", None)
                        st.rerun()
                    else:
                        st.error("⚠️ Не удалось сохранить оценку")
                except Exception as e:
                    st.error(f"❌ Ошибка при сохранении оценки: {str(e)}")

    # Сообщение об успешной оценке
    if st.session_state.get("rating_submitted", False):
        st.success("✅ Спасибо за вашу оценку! Ваш отзыв сохранен.")
        st.session_state.pop("rating_submitted", None)


    st.markdown("---")

    # Секция обработки архивов
    st.markdown("### 🗂 Классификация архива с документами")
    st.info("Загрузите `.zip` файл с документами (txt, pdf, docx), и получите архив, отсортированный по папкам-классам.")

    zip_model = st.selectbox("🧠 Модель для архива", list(MODELS_ZIP.keys()), key="zip_model")
    zip_file = st.file_uploader("📎 Загрузите архив", type=["zip"], key="zip_upload")

    # Функция перевода названий классов
    def translate_class_name(class_name):
        translation = {
            "Order": "Приказ",
            "Ordinance": "Постановление",
            "Letters": "Письмо",
            "Miscellaneous": "Общее"
        }
        return translation.get(class_name, class_name)

    if zip_file and st.button(
        "📂 Классифицировать архив", 
        key="zip_classify",
        use_container_width=True
    ):
        with st.spinner("🔍 Обработка архива..."):
            try:
                # Создаем запись об архиве
                zip_folder_id = db.create_zip_folder(
                    user["id"],
                    zip_file.name,
                    0
                )
                
                if not zip_folder_id:
                    st.error("❌ Не удалось создать запись об архиве в БД")
                    return

                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_input = os.path.join(tmpdir, "input")
                    tmp_output = os.path.join(tmpdir, "output")
                    os.makedirs(tmp_input, exist_ok=True)
                    os.makedirs(tmp_output, exist_ok=True)

                    # Распаковка архива
                    with zipfile.ZipFile(zip_file, "r") as zip_ref:
                        zip_ref.extractall(tmp_input)

                    # Создаем директории для классов (с русскими названиями)
                    class_dirs = {
                        "Письмо": os.path.join(tmp_output, "Письмо"),
                        "Приказ": os.path.join(tmp_output, "Приказ"),
                        "Постановление": os.path.join(tmp_output, "Постановление"),
                        "Общее": os.path.join(tmp_output, "Общее")
                    }
                    for path in class_dirs.values():
                        os.makedirs(path, exist_ok=True)

                    processed_files = 0
                    
                    for root, _, files in os.walk(tmp_input):
                        for fname in files:
                            file_path = os.path.join(root, fname)
                            ext = os.path.splitext(fname)[1].lower()
                            
                            if ext not in ['.txt', '.pdf', '.docx']:
                                continue
                            
                            try:
                                # Чтение файла
                                if ext == '.txt':
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        text = f.read()
                                else:
                                    with open(file_path, 'rb') as f:
                                        file_content = f.read()
                                    
                                    class FileLikeObject(io.BytesIO):
                                        name = fname
                                        seekable = lambda self: True
                                        readable = lambda self: True
                                        writable = lambda self: False
                                        mode = 'rb'
                                        
                                        @property
                                        def type(self):
                                            return {
                                                '.pdf': 'application/pdf',
                                                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                                            }.get(ext, 'application/octet-stream')
                                    
                                    file_obj = FileLikeObject(file_content)
                                    text = extract_text_from_file(file_obj)

                                if not text or len(text.strip()) < 10:
                                    st.warning(f"⚠️ Файл `{fname}` не содержит текста или слишком короткий.")
                                    continue
                                
                                # Классификация
                                vector = vectorizer.transform([text])
                                model = load_model(zip_model)
                                pred = model.predict(vector)[0]
                                confidence = model.predict_proba(vector)[0].max() if hasattr(model, 'predict_proba') else None
                                
                                # Определение класса с переводом
                                if zip_model == "Clustering":
                                    class_map = {
                                        0: "Приказ",
                                        1: "Постановление",
                                        2: "Письмо",
                                        3: "Общее"
                                    }
                                    russian_class = class_map.get(pred, "Общее")
                                else:
                                    english_class = pred if isinstance(pred, str) else "Miscellaneous"
                                    russian_class = translate_class_name(english_class)
                                
                                # Сохраняем в БД
                                classification_id = db.create_archive_classification(
                                    id_user=user["id"],
                                    filename=fname,
                                    model_name=zip_model,
                                    predicted_class=russian_class,
                                    confidence=float(confidence) if confidence is not None else None,
                                    id_folder_zip=zip_folder_id
                                )
                                
                                if not classification_id:
                                    continue
                                
                                # Копирование файла в соответствующую папку
                                dst_dir = class_dirs.get(russian_class, class_dirs["Общее"])
                                shutil.copy2(file_path, dst_dir)
                                processed_files += 1
                                
                            except Exception as e:
                                st.error(f"❌ Ошибка обработки файла `{fname}`: {str(e)}")

                    # Обновляем счетчик файлов
                    if processed_files > 0:
                        db.update_zip_file_count(zip_folder_id, processed_files)

                    # Создаем итоговый архив
                    if processed_files > 0:
                        result_zip_path = os.path.join(tmpdir, "classified.zip")
                        with zipfile.ZipFile(result_zip_path, 'w') as zipf:
                            for class_name, class_dir in class_dirs.items():
                                if any(os.listdir(class_dir)):
                                    for root, _, files in os.walk(class_dir):
                                        for file in files:
                                            file_path = os.path.join(root, file)
                                            arcname = os.path.join(class_name, file)
                                            zipf.write(file_path, arcname)

                        with open(result_zip_path, "rb") as f:
                            st.success(f"✅ Обработано файлов: {processed_files}")
                            st.download_button(
                                "📥 Скачать классифицированный архив",
                                f,
                                file_name="classified.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                    else:
                        st.error("⚠️ Ни один файл не был обработан. Проверьте содержимое архива.")

            except Exception as e:
                st.error(f"❌ Критическая ошибка при обработке архива: {str(e)}")


    # Секция истории операций
    st.markdown("---")
    st.subheader("📋 История операций")

    def get_russian_class(eng_class):
        class_map = {
            "Order": "Приказ",
            "Ordinance": "Постановление",
            "Letters": "Письмо",
            "Miscellaneous": "Общее",
            0: "Приказ",
            1: "Постановление",
            2: "Письмо",
            3: "Общее",
        }
        return class_map.get(eng_class, eng_class)

    # Получение истории пользователя
    history = db.get_user_history(user["id"])

    # Проверка наличия данных
    if history is None or not isinstance(history, pd.DataFrame) or history.empty:
        st.info("История операций отсутствует")
        st.stop()

    # Переименование колонок и обработка данных
    history = history.rename(columns={
        'filename': 'Документ',
        'model_used': 'Модель',
        'predicted_class': 'Класс',
        'confidence': 'Уверенность',
        'created_at': 'Дата',
        'rating': 'Оценка',
        'comment_user': 'Комментарий'
    })

    # Обработка данных
    history['Дата'] = pd.to_datetime(history['Дата'])
    min_date, max_date = history['Дата'].min().date(), history['Дата'].max().date()
    history['Категория'] = history['Класс'].apply(get_russian_class)

    # === ФИЛЬТРЫ ===
    with st.sidebar.expander("🔎 Фильтры", expanded=True):
        st.markdown("### Основные фильтры")
        date_range = st.date_input("📅 Диапазон дат", [min_date, max_date], min_value=min_date, max_value=max_date)
        search_query = st.text_input("🔍 Поиск по названию")
        
        categories = history['Категория'].unique().tolist()
        selected_categories = st.multiselect("📂 Категории", categories, default=categories)
        
        models = history['Модель'].unique().tolist()
        selected_models = st.multiselect("🧠 Модели", models, default=models)
        
        st.markdown("### Фильтры оценок")
        min_rating, max_rating = st.slider(
            "⭐ Оценка пользователя", 
            min_value=1, 
            max_value=5, 
            value=(1, 5),
            step=1
        )
        show_only_rated = st.checkbox("Показать только с оценками", value=False)

    # Применение фильтров
    if len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
        history = history[(history['Дата'] >= start_date) & (history['Дата'] < end_date)]

    if search_query:
        history = history[history['Документ'].str.contains(search_query, case=False, na=False)]

    if selected_categories:
        history = history[history['Категория'].isin(selected_categories)]

    if selected_models:
        history = history[history['Модель'].isin(selected_models)]

    # Фильтрация по оценкам
    if show_only_rated:
        history = history[history['Оценка'].notna()]
    else:
        history['Оценка'] = history['Оценка'].apply(lambda x: x if pd.notna(x) else "—")

    history = history[(history['Оценка'].apply(lambda x: min_rating <= x <= max_rating if isinstance(x, (int, float)) else not show_only_rated))]

    # Сортировка и форматирование
    history = history.sort_values(['Дата', 'Категория'], ascending=[False, True])
    history['Дата'] = history['Дата'].dt.strftime('%d.%m.%Y %H:%M')
    history['Уверенность'] = history['Уверенность'].apply(
        lambda x: f"{float(x) * 100:.1f}%" if pd.notnull(x) else "—"
    )

    # === ВИЗУАЛИЗАЦИЯ ===
    with st.expander("📊 Визуализация данных", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Распределение по категориям**")
            fig_cat = px.pie(history, names='Категория')
            st.plotly_chart(fig_cat, use_container_width=True)
        
        with col2:
            st.markdown("**Распределение по моделям**")
            fig_model = px.pie(history, names='Модель')
            st.plotly_chart(fig_model, use_container_width=True)
        
        # График оценок (если есть оценки)
        if not history[history['Оценка'] != "—"].empty:
            st.markdown("**Распределение оценок**")
            fig_rating = px.histogram(history[history['Оценка'] != "—"], x='Оценка', nbins=5)
            st.plotly_chart(fig_rating, use_container_width=True)

    # === ПАГИНАЦИЯ ===
    ITEMS_PER_PAGE = 50
    total_records = len(history)

    if total_records > ITEMS_PER_PAGE:
        total_pages = (total_records // ITEMS_PER_PAGE) + (1 if total_records % ITEMS_PER_PAGE else 0)
        page = st.number_input(
            "Страница", 
            min_value=1, 
            max_value=total_pages, 
            value=1
        )
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_records)
        
        # Получаем данные для текущей страницы
        paginated_history = history.iloc[start_idx:end_idx]
    else:
        paginated_history = history

    # === ТАБЛИЦА С ДАННЫМИ ===
    columns_to_show = ['Документ', 'Модель', 'Категория', 'Уверенность', 'Дата', 'Оценка', 'Комментарий']

    st.dataframe(
        paginated_history[columns_to_show],
        column_config={
            "Дата": st.column_config.TextColumn("Дата"),
            "Документ": "Документ",
            "Модель": "Модель",
            "Категория": "Категория",
            "Уверенность": st.column_config.TextColumn("Уверенность"),
            "Оценка": st.column_config.NumberColumn("Оценка", format="%d"),
            "Комментарий": "Комментарий"
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )

    # Отображение информации о записях ПОД таблицей
    if total_records > ITEMS_PER_PAGE:
        st.caption(f"Показаны записи {start_idx + 1}-{end_idx} из {total_records}")
    else:
        st.caption(f"Всего записей: {total_records}")