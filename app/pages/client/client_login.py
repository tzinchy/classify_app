import streamlit as st
from database.db_operations import Database


db = Database()

# Авторизация клиента
def client_login_page():
    # Контейнер с улучшенным дизайном
    with st.container():
        st.title("👤 Вход в систему")
        st.markdown("---")  # Декоративная разделительная линия

        # Поля ввода
        login = st.text_input("**Ваш логин**", 
                            placeholder="Введите ваш логин",
                            help="Введите логин, указанный при регистрации")

        password = st.text_input("**Пароль**", 
                               type="password", 
                               placeholder="Введите ваш пароль",
                               help="Минимум 8 символов")

        # Кнопки
        col1, col2 = st.columns(2)
        
        with col1:
            login_clicked = st.button("**Войти в систему** →", 
                                    type="primary", 
                                    use_container_width=True,
                                    help="Авторизоваться")
        
        with col2:
            if st.button("**← На главную**", 
                        type="secondary", 
                        use_container_width=True,
                        help="Вернуться без входа"):
                st.session_state.route = None
                st.session_state.user = None
                st.rerun()

        # Контейнер для сообщений (расположен ПОД кнопками)
        msg_container = st.empty()

        # Обработка входа
        if login_clicked:
            user = db.get_user(login)
            if user and user["id_role"] == 1 and user['password_hash'] == db._hash_password(password):
                st.session_state.user = {
                    "id": user["id"],
                    "login": user["login"],
                    "id_role": user["id_role"]
                }
                msg_container.success("✅ Успешный вход в систему")
                st.session_state.route = None
                st.rerun()
            else:
                msg_container.error("❌ Неверный логин или пароль")

        # Дополнительные элементы - ЗАМЕНЯЕМ "ссылки" на настоящие кнопки
        st.markdown("<br>", unsafe_allow_html=True)

        st.info("""
            **Справка:**  
            • Для входа используйте учетные данные  
            • При проблемах обратитесь в IT-отдел  
            • Не передавайте свои учетные данные третьим лицам
            """)

        st.markdown('---')

        # Создаем колонки для кнопок "помощи"
        help_col1, help_col2 = st.columns(2)
        
        with help_col1:
            if st.button("**Восстановить пароль**", 
                        help="Нажмите, если забыли пароль",
                        use_container_width=True):
                st.session_state.route = "password_recovery"  # Предполагая, что у вас есть такой route
                st.rerun()
        
        with help_col2:
            if st.button("**Регистрация нового аккаунта**", 
                        help="Нажмите для создания нового аккаунта",
                        use_container_width=True):
                st.session_state.route = "register"  # Переход на страницу регистрации
                st.rerun()