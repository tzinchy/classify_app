import os
from dotenv import load_dotenv

load_dotenv()

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Все значения ТОЛЬКО через os.getenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")
    ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
    
    @classmethod
    def validate_config(cls):
        """Проверяет, что все переменные загружены"""
        required_vars = ['DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME', 'ADMIN_SECRET_KEY']
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Хеширует пароль для безопасного хранения"""
        import hashlib
        from secrets import token_hex
        salt = token_hex(16)  # Добавляем соль для безопасности
        return hashlib.sha256((password + salt).encode()).hexdigest()