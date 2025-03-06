from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, validator
from typing import Optional, List
import bcrypt
from .database import Base

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base

class Fire(Base):
    __tablename__ = 'fires'
    id = Column(Integer, primary_key=True, index=True)
    fire_date = Column(DateTime, nullable=False)
    region = Column(String, nullable=False)
    kgu_oopt_id = Column(Integer, ForeignKey('kgu_oopt.id'))
    area = Column(Float, nullable=False)
    description = Column(String)
    file_path = Column(String)
    created_by = Column(Integer, ForeignKey('users.id'))
    latitude = Column(Float)
    longitude = Column(Float)
    damage_tenge = Column(Float, default=0.0)

class FireForce(Base):
    __tablename__ = 'fire_forces'
    id = Column(Integer, primary_key=True, index=True)
    fire_id = Column(Integer, ForeignKey('fires.id'), nullable=False)
    force_type = Column(String, nullable=False)  # Например, "firefighters", "volunteers", "military"
    people_count = Column(Integer, nullable=False, default=0)
    
# Список регионов Казахстана
REGIONS = [
    'Akmola', 'Aktobe', 'Almaty', 'Atyrau', 'East Kazakhstan', 'Zhambyl', 'West Kazakhstan',
    'Karaganda', 'Kostanay', 'Kyzylorda', 'Mangystau', 'Pavlodar', 'North Kazakhstan',
    'Turkistan', 'Astana', 'Almaty City', 'Shymkent', 'Abai', 'Zhetysu', 'Ulytau'
]

VALID_ROLES = ['operator', 'engineer', 'analyst', 'admin']
VALID_FORCE_TYPES = ['APS', 'KPS', 'MIO', 'LO', 'Other']

class KGUOOPT(Base):
    """Модель для КГУ/ООПТ (казенные государственные учреждения или особо охраняемые природные территории)."""
    __tablename__ = "kgu_oopt"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True, comment="Название КГУ/ООПТ")

    fires = relationship("Fire", back_populates="kgu_oopt")

class Fire(Base):
    """Модель для учета лесных пожаров с полной поддержкой всех полей из дампа базы."""
    __tablename__ = "fires"

    id = Column(Integer, primary_key=True, index=True)
    fire_date = Column(DateTime, default=func.now(), nullable=False, index=True, comment="Дата и время пожара")
    region = Column(String(255), nullable=False, index=True, comment="Регион пожара")
    kgu_oopt_id = Column(Integer, ForeignKey("kgu_oopt.id", ondelete="SET NULL"), nullable=True, comment="ID КГУ/ООПТ")
    area = Column(Float, nullable=False, comment="Общая площадь пожара (га)")
    file_path = Column(String(255), nullable=True, comment="Путь к прикрепленному файлу")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, comment="ID пользователя, создавшего запись")
    quarter = Column(String(255), nullable=True, comment="Квартал(ы), разделенные запятыми")
    allotment = Column(String(255), nullable=True, comment="Выдел(ы), разделенные запятыми")
    damage_tenge = Column(Float, nullable=True, comment="Ущерб в тенге")
    damage_les = Column(Float, nullable=True, comment="Ущерб лесным насаждениям (га)")
    damage_les_lesopokryt = Column(Float, nullable=True, comment="Ущерб лесопокрытым территориям (га)")
    damage_les_verh = Column(Float, nullable=True, comment="Ущерб верхним лесам (га)")
    damage_not_les = Column(Float, nullable=True, comment="Ущерб нелесным территориям (га)")
    firefighting_costs = Column(Float, nullable=True, comment="Затраты на тушение (тенге)")
    description = Column(String(1000), nullable=True, comment="Описание пожара")
    edited_by_engineer = Column(Boolean, default=False, comment="Отредактировано инженером")

    creator = relationship("User", back_populates="fires")
    kgu_oopt = relationship("KGUOOPT", back_populates="fires")
    forces = relationship("FireForce", back_populates="fire", cascade="all, delete-orphan")

class FireForce(Base):
    """Модель для задействованных сил в пожарах с полной детализацией."""
    __tablename__ = "fire_forces"

    id = Column(Integer, primary_key=True, index=True)
    fire_id = Column(Integer, ForeignKey("fires.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID пожара")
    force_type = Column(String(50), nullable=False, comment="Тип сил: APS, KPS, MIO, LO, Other")
    people_count = Column(Integer, nullable=True, default=0, comment="Количество людей")
    tecnic_count = Column(Integer, nullable=True, default=0, comment="Количество техники")
    aircraft_count = Column(Integer, nullable=True, default=0, comment="Количество авиации")

    fire = relationship("Fire", back_populates="forces")

class User(Base):
    """Модель пользователей системы с поддержкой 2FA и регионов."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="Уникальное имя пользователя")
    password_hash = Column(String(255), nullable=False, comment="Хэш пароля")
    role = Column(String(20), nullable=False, comment="Роль: operator, engineer, analyst, admin")
    region = Column(String(255), nullable=True, comment="Регион пользователя")
    totp_secret = Column(String(32), nullable=True, comment="Секретный ключ для 2FA")

    fires = relationship("Fire", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")

    def set_password(self, password: str) -> None:
        """Устанавливает хэшированный пароль."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Проверяет соответствие пароля хэшу."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class AuditLog(Base):
    """Модель журнала событий с полной детализацией."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True, comment="Время события")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, comment="ID пользователя")
    action = Column(String(50), nullable=False, comment="Действие: INSERT, UPDATE, DELETE")
    table_name = Column(String(50), nullable=False, comment="Имя таблицы")
    record_id = Column(Integer, nullable=True, comment="ID записи")
    changes = Column(String(1000), nullable=True, comment="Изменения в формате JSON")

    user = relationship("User", back_populates="audit_logs")

class ReportCache(Base):
    """Модель для кэширования отчетов."""
    __tablename__ = "report_cache"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), nullable=False, comment="Тип отчета: summary, analytics")
    filters = Column(String(255), nullable=False, comment="Фильтры в формате JSON")
    data = Column(String(10000), nullable=False, comment="Данные отчета в формате JSON")
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="Дата создания")

# Pydantic модели для валидации
class FireForceData(BaseModel):
    """Валидация данных о задействованных силах."""
    force_type: str
    people_count: Optional[int] = 0
    tecnic_count: Optional[int] = 0
    aircraft_count: Optional[int] = 0

    @validator('force_type')
    def force_type_must_be_valid(cls, value: str) -> str:
        if value not in VALID_FORCE_TYPES:
            raise ValueError(f"Invalid force type: {value}. Must be one of {VALID_FORCE_TYPES}")
        return value

    @validator('people_count', 'tecnic_count', 'aircraft_count')
    def counts_must_be_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Count must be non-negative")
        return value

class FireData(BaseModel):
    """Валидация данных о пожарах."""
    fire_date: str
    region: str
    kgu_oopt_id: Optional[int] = None
    area: float
    file_path: Optional[str] = None
    quarter: Optional[str] = None
    allotment: Optional[str] = None
    damage_tenge: Optional[float] = None
    damage_les: Optional[float] = None
    damage_les_lesopokryt: Optional[float] = None
    damage_les_verh: Optional[float] = None
    damage_not_les: Optional[float] = None
    firefighting_costs: Optional[float] = None
    description: Optional[str] = None
    forces: Optional[List[FireForceData]] = None

    @validator('region')
    def region_must_be_valid(cls, value: str) -> str:
        if value not in REGIONS:
            raise ValueError(f"Invalid region: {value}. Must be one of {REGIONS}")
        return value

    @validator('area', 'damage_tenge', 'damage_les', 'damage_les_lesopokryt', 'damage_les_verh', 'damage_not_les', 'firefighting_costs')
    def values_must_be_positive(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("Value must be non-negative")
        return value

class UserData(BaseModel):
    """Валидация данных пользователей."""
    username: str
    password: str
    role: str
    region: Optional[str] = None
    totp_secret: Optional[str] = None

    @validator('role')
    def role_must_be_valid(cls, value: str) -> str:
        if value not in VALID_ROLES:
            raise ValueError(f"Invalid role: {value}. Must be one of {VALID_ROLES}")
        return value

    @validator('region')
    def region_must_be_valid(cls, value: Optional[str]) -> Optional[str]:
        if value and value not in REGIONS:
            raise ValueError(f"Invalid region: {value}. Must be one of {REGIONS}")
        return value

    @validator('password')
    def password_must_be_strong(cls, value: str) -> str:
        if len(value) < 12 or not any(c.isupper() for c in value) or not any(c.islower() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must be at least 12 characters long and contain uppercase, lowercase, and digits")
        return value