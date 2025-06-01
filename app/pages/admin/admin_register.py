import streamlit as st
from database.db_operations import Database
from config import Config


db = Database()

# Регистрация администратора
def admin_register_page():
    with st.container():
        st.title("🔐 Регистрация администратора")
        st.markdown("---")

        # Отображение сообщения о успешной регистрации (если есть)
        if st.session_state.get('admin_registered'):
            st.success("""
            ✅ Администратор успешно зарегистрирован!
            
            Для входа в систему используйте специальную ссылку:
            `ваш_сайт.com/?page=admin_login`
            """)
            
            if st.button("**OK**", type="primary"):
                st.session_state.admin_registered = False
                st.query_params.clear()
                st.rerun()
            
            st.markdown("---")
            return
        
        # Поля формы
        secret_key = st.text_input(
            "**Секретный ключ**",
            type="password",
            placeholder="Введите секретный ключ",
            help="Получите у главного администратора"
        )

        login = st.text_input(
            "**Логин администратора**",
            placeholder="От 4 до 20 символов",
            help="Латинские буквы и цифры"
        )

        email = st.text_input(
            "**Email администратора**",
            placeholder="example@domain.com",
            help="Корпоративная почта"
        )

        password = st.text_input(
            "**Пароль**", 
            type="password",
            placeholder="Не менее 12 символов",
            help="Строчные, заглавные буквы, цифры и спецсимволы"
        )

        confirm = st.text_input(
            "**Подтвердите пароль**", 
            type="password",
            placeholder="Введите пароль еще раз",
            help="Пароли должны совпадать"
        )

        # Кнопки
        col1, col2 = st.columns(2)
        
        with col1:
            register_clicked = st.button(
                "**Зарегистрировать** →", 
                type="primary", 
                use_container_width=True,
                help="Создать аккаунт администратора"
            )
        
        with col2:
            back_clicked = st.button(
                "**← Назад**", 
                type="secondary", 
                use_container_width=True,
                help="Вернуться на главную страницу"
            )

        # Обработка регистрации
        if register_clicked:
            if not all([secret_key, login, email, password, confirm]):
                st.error("❌ Заполните все обязательные поля")
            elif password != confirm:
                st.error("❌ Пароли не совпадают")
            elif len(password) < 12:
                st.error("❌ Пароль должен содержать минимум 12 символов")
            elif secret_key != Config.ADMIN_SECRET_KEY:
                st.error("❌ Неверный секретный ключ")
            else:
                try:
                    if db.create_admin_user(login, email, password):
                        st.session_state.admin_registered = True
                        st.rerun()
                    else:
                        st.error("⚠️ Ошибка регистрации. Возможно, логин уже занят")
                except Exception as e:
                    st.error(f"⚠️ Ошибка при регистрации: {str(e)}")
        
        if back_clicked:
            st.query_params.clear()
            st.query_params["page"] = "main"
            st.rerun()

        # Информационный блок
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("""
        **Требования к учетной записи администратора:**  
        • Логин: 4-20 символов (латиница и цифры)  
        • Пароль: минимум 12 символов (строчные, заглавные, цифры и спецсимволы)  
        • Действительный корпоративный email  
        • Действительный секретный ключ          
        """)