import streamlit as st
from database.db_operations import Database


db = Database()

# Авторизация аналитика
def analyst_login_page():
    with st.container():
        st.title("🔐 Авторизация аналитика")
        st.markdown("---")  # Декоративная линия
    
        # Обработка выхода при наличии флага
        if st.session_state.get('force_logout'):
            st.session_state.force_logout = False
            st.session_state.route = None
            st.session_state.user = None
            st.query_params.clear()
            st.rerun()

        # Поля ввода с иконками через псевдо-элементы
        login = st.text_input("**Логин аналитика**", 
                            placeholder="Введите ваш логин",
                            help="Используйте корпоративный логин")

        password = st.text_input("**Пароль**", 
                               type="password", 
                               placeholder="Введите ваш пароль",
                               help="Пароль чувствителен к регистру")

        # Кнопки с иконками и цветами
        col1, col2 = st.columns(2)
        
        with col1:
            login_clicked = st.button("**Войти** →", 
                        type="primary", 
                        use_container_width=True,
                        help="Авторизация в системе")
        
        with col2:
            if st.button("**← Назад**", 
                        type="secondary", 
                        use_container_width=True,
                        help="Вернуться на главную страницу"):
                st.session_state.force_logout = True
                st.rerun()

        # Обработка входа (вынесена из колонки)
        if login_clicked:
            emploee = db.get_emploee(login)
            if emploee and emploee['id_role'] == 2 and emploee['password_hash'] == db._hash_password(password):
                st.session_state.user = {
                    "id": emploee["id"],
                    "login": emploee["login"],
                    "id_role": emploee["id_role"]
                }
                st.session_state.route = None
                st.query_params.clear()
                st.rerun()
            else:
                # Сообщение об ошибке на всю ширину
                st.error("Неверные учетные данные", icon="🚨")        

        # Дополнительный отступ
        st.markdown("<br>", unsafe_allow_html=True)

        # Информационный блок
        st.info("""
        **Справка:**  
        • Для входа используйте корпоративные учетные данные  
        • При проблемах обратитесь в IT-отдел  
        • Не передавайте свои учетные данные третьим лицам
        """)