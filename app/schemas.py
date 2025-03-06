from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
import re

# Константы для валидации
REGIONS = [
    'Akmola', 'Aktobe', 'Almaty', 'Atyrau', 'East Kazakhstan', 'Zhambyl', 'West Kazakhstan',
    'Karaganda', 'Kostanay', 'Kyzylorda', 'Mangystau', 'Pavlodar', 'North Kazakhstan',
    'Turkistan', 'Astana', 'Almaty City', 'Shymkent', 'Abai', 'Zhetysu', 'Ulytau'
]

VALID_ROLES = ['operator', 'engineer', 'analyst', 'admin']
VALID_FORCE_TYPES = ['APS', 'KPS', 'MIO', 'LO', 'Other']

# --- Схемы для FireForce ---
class FireForceBase(BaseModel):
    """Базовая схема для задействованных сил."""
    force_type: str = Field(..., description="Type of force involved (e.g., APS, KPS)")
    people_count: Optional[int] = Field(0, ge=0, description="Number of people involved")
    tecnic_count: Optional[int] = Field(0, ge=0, description="Number of technical units involved")
    aircraft_count: Optional[int] = Field(0, ge=0, description="Number of aircraft involved")

    @validator('force_type')
    def force_type_must_be_valid(cls, value: str) -> str:
        if value not in VALID_FORCE_TYPES:
            raise ValueError(f"Invalid force type: {value}. Must be one of {VALID_FORCE_TYPES}")
        return value

class FireForceCreate(FireForceBase):
    """Схема для создания записи о силах."""
    pass

class FireForceResponse(FireForceBase):
    """Схема для ответа с данными о силах."""
    id: int

    class Config:
        orm_mode = True

# --- Схемы для Fire ---
class FireBase(BaseModel):
    """Базовая схема для данных о пожарах."""
    fire_date: str = Field(..., description="Date and time of the fire in format 'YYYY-MM-DD HH:MM:SS'")
    region: str = Field(..., description="Region where the fire occurred")
    kgu_oopt_id: Optional[int] = Field(None, description="ID of the KGU/OOPT associated with the fire")
    area: float = Field(..., gt=0, description="Total area affected by the fire in hectares")
    file_path: Optional[str] = Field(None, description="Path to the attached file")
    quarter: Optional[str] = Field(None, description="Comma-separated list of quarters affected")
    allotment: Optional[str] = Field(None, description="Comma-separated list of allotments affected")
    damage_tenge: Optional[float] = Field(None, ge=0, description="Damage in tenge")
    damage_les: Optional[float] = Field(None, ge=0, description="Damage to forested areas in hectares")
    damage_les_lesopokryt: Optional[float] = Field(None, ge=0, description="Damage to forest-covered areas in hectares")
    damage_les_verh: Optional[float] = Field(None, ge=0, description="Damage to upper forests in hectares")
    damage_not_les: Optional[float] = Field(None, ge=0, description="Damage to non-forested areas in hectares")
    firefighting_costs: Optional[float] = Field(None, ge=0, description="Firefighting costs in tenge")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the fire")
    forces: Optional[List[FireForceCreate]] = Field(None, description="List of forces involved in firefighting")

    @validator('region')
    def region_must_be_valid(cls, value: str) -> str:
        if value not in REGIONS:
            raise ValueError(f"Invalid region: {value}. Must be one of {REGIONS}")
        return value

    @validator('fire_date')
    def fire_date_must_be_valid(cls, value: str) -> str:
        try:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ValueError("Invalid date format. Must be 'YYYY-MM-DD HH:MM:SS'")
        return value

    @validator('quarter', 'allotment')
    def comma_separated_list(cls, value: Optional[str]) -> Optional[str]:
        if value and not re.match(r'^[\d,\s]+$', value):
            raise ValueError("Must be a comma-separated list of numbers")
        return value

class FireCreate(FireBase):
    """Схема для создания записи о пожаре."""
    pass

class FireResponse(FireBase):
    """Схема для ответа с данными о пожаре."""
    id: int = Field(..., description="Unique identifier of the fire")
    created_by: int = Field(..., description="ID of the user who created the record")
    edited_by_engineer: bool = Field(..., description="Whether the record was edited by an engineer")
    forces: List[FireForceResponse] = Field(..., description="List of forces involved")

    class Config:
        orm_mode = True

# --- Схемы для User ---
class UserBase(BaseModel):
    """Базовая схема для данных пользователя."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    role: str = Field(..., description="User role: operator, engineer, analyst, admin")
    region: Optional[str] = Field(None, description="Region assigned to the user")
    totp_secret: Optional[str] = Field(None, min_length=16, max_length=32, description="2FA secret key")

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

    @validator('username')
    def username_must_be_alphanumeric(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return value

class UserCreate(UserBase):
    """Схема для создания пользователя."""
    password: str = Field(..., min_length=12, description="Password with at least 12 characters")

    @validator('password')
    def password_must_be_strong(cls, value: str) -> str:
        if not (re.search(r'[A-Z]', value) and re.search(r'[a-z]', value) and re.search(r'[0-9]', value)):
            raise ValueError("Password must contain uppercase, lowercase, and digits")
        return value

class UserUpdate(UserBase):
    """Схема для обновления пользователя."""
    password: Optional[str] = Field(None, min_length=12, description="New password (optional)")

    @validator('password')
    def password_must_be_strong(cls, value: Optional[str]) -> Optional[str]:
        if value and not (re.search(r'[A-Z]', value) and re.search(r'[a-z]', value) and re.search(r'[0-9]', value)):
            raise ValueError("Password must contain uppercase, lowercase, and digits")
        return value

class UserResponse(UserBase):
    """Схема для ответа с данными пользователя."""
    id: int = Field(..., description="Unique identifier of the user")

    class Config:
        orm_mode = True

# --- Схемы для AuditLog (дополнительно) ---
class AuditLogBase(BaseModel):
    """Базовая схема для логов аудита."""
    timestamp: datetime = Field(..., description="Timestamp of the action")
    user_id: int = Field(..., description="ID of the user who performed the action")
    action: str = Field(..., description="Action performed: INSERT, UPDATE, DELETE")
    table_name: str = Field(..., description="Name of the table affected")
    record_id: Optional[int] = Field(None, description="ID of the affected record")
    changes: Optional[str] = Field(None, max_length=1000, description="Changes made in JSON format")

class AuditLogResponse(AuditLogBase):
    """Схема для ответа с данными лога аудита."""
    id: int = Field(..., description="Unique identifier of the audit log")

    class Config:
        orm_mode = True