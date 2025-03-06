from sqlalchemy.orm import Session
from models.log_model import Log
from datetime import datetime

def create_log(db: Session, user_id: int, action: str, details: str = ""):
    """Создает запись лога о действии пользователя."""
    new_log = Log(timestamp=datetime.utcnow(), user_id=user_id, action=action, details=details)
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log

def get_logs(db: Session):
    """Получает все логи."""
    return db.query(Log).all()

def get_logs_by_user(db: Session, user_id: int):
    """Получает все логи конкретного пользователя."""
    return db.query(Log).filter(Log.user_id == user_id).all()

def delete_log(db: Session, log_id: int):
    """Удаляет лог по ID."""
    log = db.query(Log).filter(Log.id == log_id).first()
    if log:
        db.delete(log)
        db.commit()
    return log