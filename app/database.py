# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config  # Импортируем конфигурацию из Config

# Создаём движок для подключения к базе данных
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    pool_size=10,          # Размер пула соединений для стабильности
    max_overflow=20,       # Максимальное переполнение пула
    pool_timeout=30,       # Тайм-аут ожидания соединения
    echo=False             # Отключаем логи SQL в продакшене (включи True для отладки)
)

# Создаём фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)

# Базовый класс для моделей
Base = declarative_base()

def init_db():
    """Инициализирует все таблицы в базе данных."""
    # Импортируем все модели, чтобы они зарегистрировались в Base.metadata
    from models import KGUOOPT, Fire, FireForce, User, AuditLog, ReportCache, Region
    Base.metadata.create_all(bind=engine)

def get_db():
    """Генератор для получения сессии базы данных."""
    db = Session()
    try:
        yield db
    finally:
        db.close()