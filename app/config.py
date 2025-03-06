import os
from typing import Optional

class Config:
    """Конфигурация приложения Forest Fires Platform."""
    
    # Общие настройки
import os

class Config:
     
     SQLALCHEMY_DATABASE_URI = "mysql+pymysql://your_db_user:your_secure_password_here@your_db_host/forest_fires_db?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY: str = os.getenv('SECRET_KEY') or "your_unique_secret_key_here_64_chars_long_very_secure_key_1234567890"
    UPLOAD_FOLDER: str = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 МБ

    # Кэширование (Redis для продакшена)
    CACHE_TYPE: str = 'redis'
    CACHE_REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT: int = 300  # 5 минут

    # Настройки базы данных MySQL
    MYSQL_HOST: str = os.getenv('MYSQL_HOST')
    MYSQL_USER: str = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD: str = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB: str = os.getenv('MYSQL_DB')
    DATABASE_URL: str = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
        "?charset=utf8mb4"
    )

    # API-ключи
    OPENWEATHERMAP_API_KEY: str = os.getenv('OPENWEATHERMAP_API_KEY')
    NASA_FIRMS_API_KEY: str = os.getenv('NASA_FIRMS_API_KEY')

    def __init__(self) -> None:
        """Проверяет наличие обязательных переменных окружения."""
        required_vars = [
            'SECRET_KEY', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB',
            'OPENWEATHERMAP_API_KEY', 'NASA_FIRMS_API_KEY'
        ]
        missing = [var for var in required_vars if not getattr(self, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    @staticmethod
    def validate() -> None:
        """Дополнительная валидация конфигурации."""
        if not os.path.isdir(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)