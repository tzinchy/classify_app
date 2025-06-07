import streamlit as st
from database.db_operations import Database
from utils.ml_utils import MODELS, MODELS_ZIP, classify_document, load_model
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
def emploee_page(user, vectorizer):
    # Проверка авторизации
    if not user:
        st.error("Пожалуйста, войдите в систему для доступа к этой странице.")
        st.stop()

    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.title(f"Добро пожаловать, {user['login']}")
    with header_col2:
        if st.button("🚪 Выйти", key="logout_btn", use_container_width=True):
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

    try:
        # Получаем данные из БД
        df = db.get_emploee_history(user["id"])
        
        if df.empty:
            st.info("📭 Нет данных для отображения")
            return

        # Подготовка данных
        df = df.rename(columns={
            'filename': 'document_name',
            'predicted_class': 'prediction',
            'created_at': 'classification_date',
            'rating': 'user_rating',
            'comment_user': 'user_comment'
        })

        # Перевод классов документов
        class_translation = {
            "Order": "Приказ",
            "Ordinance": "Постановление",
            "Letters": "Письмо",
            "Miscellaneous": "Общее",
            0: "Приказ", 1: "Постановление", 2: "Письмо", 3: "Общее"
        }
        df['russian_category'] = df['prediction'].map(class_translation).fillna(df['prediction'])
        
        # Форматирование данных
        df['classification_date'] = pd.to_datetime(df['classification_date'], errors='coerce')
        df = df.dropna(subset=['classification_date'])
        df['formatted_confidence'] = df['confidence'].apply(
            lambda x: f"{float(x)*100:.1f}%" if pd.notnull(x) and str(x).replace('.','',1).isdigit() else "—"
        )
        df['formatted_date'] = df['classification_date'].dt.strftime('%d.%m.%Y %H:%M')

        # Фильтры в сайдбаре
        with st.sidebar.expander("🔎 Фильтры", expanded=True):
            st.markdown("### Основные фильтры")
            
            # Диапазон дат
            min_date = df['classification_date'].min().date()
            max_date = df['classification_date'].max().date()
            date_range = st.date_input(
                "📅 Диапазон дат",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            # Поиск по названию файла
            search_query = st.text_input(
                "🔍 Поиск по названию",
                placeholder="Введите часть названия файла"
            )

            # Фильтр по категориям
            selected_categories = st.multiselect(
                "📂 Категории документов",
                options=sorted(df['russian_category'].unique()),
                default=sorted(df['russian_category'].unique())
            )
            
            # Фильтр по моделям
            selected_models = st.multiselect(
                "🧠 Использованные модели",
                options=df['model_used'].unique(),
                default=df['model_used'].unique()
            )
            
            # Фильтр по оценкам
            if 'user_rating' in df.columns and not df['user_rating'].isna().all():
                st.markdown("### Фильтры оценок")
                min_rating, max_rating = st.slider(
                    "⭐ Диапазон оценок", 
                    min_value=1, 
                    max_value=5, 
                    value=(1, 5), 
                    step=1
                )
                show_rated_only = st.checkbox("Только с оценками", value=False)

        # Применение фильтров
        filtered_df = df.copy()
        
        # Фильтр по дате
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
            filtered_df = filtered_df[
                (filtered_df['classification_date'] >= start_date) & 
                (filtered_df['classification_date'] <= end_date)
            ]

        # Остальные фильтры
        if search_query:
            filtered_df = filtered_df[filtered_df['document_name'].str.contains(search_query, case=False, na=False)]
        
        if selected_categories:
            filtered_df = filtered_df[filtered_df['russian_category'].isin(selected_categories)]
        
        if selected_models:
            filtered_df = filtered_df[filtered_df['model_used'].isin(selected_models)]
        
        # Фильтрация по оценкам (если есть оценки)
        if 'user_rating' in filtered_df.columns and not filtered_df['user_rating'].isna().all():
            if show_rated_only:
                filtered_df = filtered_df[
                    filtered_df['user_rating'].notna() & 
                    filtered_df['user_rating'].between(min_rating, max_rating)
                ]
            else:
                filtered_df = filtered_df[
                    filtered_df['user_rating'].isna() | 
                    filtered_df['user_rating'].between(min_rating, max_rating)
                ]

        # Сортировка по дате (новые сверху)
        filtered_df = filtered_df.sort_values('classification_date', ascending=False)

        # Основные метрики
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего операций", len(filtered_df))
        col2.metric("Уникальных моделей", filtered_df['model_used'].nunique())
        
        # Средняя оценка (если есть)
        if 'user_rating' in filtered_df.columns and not filtered_df['user_rating'].isna().all():
            avg_rating = filtered_df['user_rating'].mean()
            col3.metric("Средняя оценка", f"{avg_rating:.1f}")
        else:
            col3.metric("Оценок", "Нет данных")

        # Вкладки
        tab1, tab2 = st.tabs(["📋 Таблица операций", "📊 Статистика"])

        with tab1:
            # Настройки пагинации
            items_per_page = 20
            total_records = len(filtered_df)
            total_pages = (total_records // items_per_page) + (1 if total_records % items_per_page else 0)
            
            # Получаем данные для текущей страницы
            if total_pages > 1:
                page = st.number_input(
                    "Страница", 
                    min_value=1, 
                    max_value=total_pages, 
                    value=1,
                    key="pagination_page"
                )
                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, total_records)
                paginated_df = filtered_df.iloc[start_idx:end_idx]
            else:
                paginated_df = filtered_df

            # Отображаемые колонки
            display_columns = {
                'formatted_date': 'Дата операции',
                'document_name': 'Название документа',
                'model_used': 'Использованная модель',
                'russian_category': 'Категория',
                'formatted_confidence': 'Уверенность модели',
                'user_rating': 'Ваша оценка',
                'user_comment': 'Ваш комментарий'
            }

            # Таблица данных
            st.dataframe(
                paginated_df[list(display_columns.keys())].rename(columns=display_columns),
                column_config={
                    "Дата операции": st.column_config.TextColumn(width="medium"),
                    "Название документа": st.column_config.TextColumn(width="large"),
                    "Использованная модель": st.column_config.TextColumn(width="medium"),
                    "Категория": st.column_config.TextColumn(width="small"),
                    "Уверенность модели": st.column_config.TextColumn(width="small"),
                    "Ваша оценка": st.column_config.NumberColumn(format="%d", width="small"),
                    "Ваш комментарий": st.column_config.TextColumn(width="large")
                },
                hide_index=True,
                use_container_width=True,
                height=500
            )
            
            # Отображение пагинации
            if total_pages > 1:
                st.caption(f"Показаны записи {start_idx+1}-{end_idx} из {total_records}")

        with tab2:
            if not filtered_df.empty:
                col1, col2 = st.columns(2)
                
                # Распределение по категориям
                with col1:
                    st.plotly_chart(
                        px.pie(
                            filtered_df['russian_category'].value_counts(),
                            names=filtered_df['russian_category'].value_counts().index,
                            values=filtered_df['russian_category'].value_counts().values,
                            title="Распределение по категориям",
                            hole=0.3
                        ),
                        use_container_width=True
                    )
                
                # Распределение по моделям
                with col2:
                    st.plotly_chart(
                        px.bar(
                            filtered_df['model_used'].value_counts(),
                            x=filtered_df['model_used'].value_counts().index,
                            y=filtered_df['model_used'].value_counts().values,
                            title="Использованные модели",
                            labels={'x': 'Модель', 'y': 'Количество'}
                        ),
                        use_container_width=True
                    )
                
                # Распределение оценок (если есть)
                if 'user_rating' in filtered_df.columns and not filtered_df['user_rating'].isna().all():
                    st.plotly_chart(
                        px.histogram(
                            filtered_df[filtered_df['user_rating'].notna()],
                            x='user_rating',
                            nbins=5,
                            title="Распределение ваших оценок",
                            labels={'user_rating': 'Оценка'}
                        ),
                        use_container_width=True
                    )

    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {str(e)}")
        st.error("Попробуйте обновить страницу или обратитесь к администратору")