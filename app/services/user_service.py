from sqlalchemy.orm import Session
from models.user_model import User
from utils.security import hash_password

def create_user(db: Session, username: str, password: str, role: str = "user"):
    """Создает нового пользователя с хешированным паролем."""
    hashed_password = hash_password(password)
    new_user = User(username=username, password_hash=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_id(db: Session, user_id: int):
    """Возвращает пользователя по ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    """Возвращает пользователя по имени."""
    return db.query(User).filter(User.username == username).first()

def update_user(db: Session, user_id: int, updates: dict):
    """Обновляет данные пользователя."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        for key, value in updates.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    """Удаляет пользователя."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return user