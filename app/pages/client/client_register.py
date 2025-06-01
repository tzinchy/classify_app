import streamlit as st
from database.db_operations import Database
import re


db = Database()

# Регистрация клиента
def client_register_page():
    # Инициализация состояния
    if 'route' not in st.session_state:
        st.session_state.route = 'register'

    # Функции валидации
    def validate_login(login):
        if not 4 <= len(login) <= 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9]+$', login))
    
    def validate_password(password):
        if not 8 <= len(password) <= 25:
            return False
        return True
    
    def validate_email(email):
        if len(email) > 50:
            return False
        return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

    # Основной контейнер
    with st.container():
        st.title("📝 Регистрация нового аккаунта")
        st.markdown("---")

        # Поля формы
        login = st.text_input("**Придумайте логин**", 
                           placeholder="От 4 до 20 символов",
                           help="Латинские буквы и цифры")

        email = st.text_input("**Ваш Email**",
                            placeholder="example@domain.com",
                            help="На этот email придет подтверждение")

        password = st.text_input("**Придумайте пароль**", 
                               type="password",
                               placeholder="Не менее 8 символов",
                               help="Строчные и заглавные буквы, цифры")

        confirm = st.text_input("**Повторите пароль**", 
                              type="password",
                              placeholder="Введите пароль еще раз",
                              help="Пароли должны совпадать")

        # Контейнер для кнопок
        col1, col2 = st.columns(2)
        
        with col1:
            register_clicked = st.button("**Зарегистрироваться** ✨", 
                                      type="primary", 
                                      use_container_width=True)
        
        with col2:
            cancel_clicked = st.button("**← Отмена**", 
                                    type="secondary", 
                                    use_container_width=True)

        # Обработка регистрации
        if register_clicked:
            error = None
            
            if not all([login, email, password, confirm]):
                error = "❌ Заполните все обязательные поля"
            elif not validate_login(login):
                error = "❌ Логин должен быть 4-20 символов (латиница и цифры)"
            elif not validate_email(email):
                error = "❌ Введите корректный email (макс. 50 символов)"
            elif not validate_password(password):
                error = "❌ Пароль должен быть 8-25 символов"
            elif password != confirm:
                error = "❌ Пароли не совпадают"
            elif db.user_exists(login, email):
                error = "⚠️ Пользователь с таким логином или email уже существует"
            
            if error:
                st.error(error, icon="🚨")
            else:
                # Если все проверки пройдены, создаем пользователя
                if db.create_user(login, email, password):
                    st.success("🎉 Регистрация успешно завершена!")
                    st.session_state.route = "login"
                    st.rerun()
                else:
                    st.error("⚠️ Ошибка при создании пользователя", icon="⛔")
        
        if cancel_clicked:
            st.session_state.route = None
            st.rerun()

        # Информационный блок
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("""
        **Требования к учетной записи:**
        - Логин: 4-20 символов (латиница и цифры)
        - Пароль: 8-25 символов
        - Email должен быть действительным (макс. 50 символов)
        """)

