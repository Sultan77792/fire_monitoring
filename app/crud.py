from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from . import models, schemas
from typing import List, Optional
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Хеширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Хеширует пароль с использованием bcrypt."""
    return pwd_context.hash(password)

# --- Операции с Fire ---
def create_fire(db: Session, fire_data: schemas.FireData, user_id: int) -> models.Fire:
    """Создает запись о пожаре с учетом всех полей и связанных сил."""
    try:
        # Создаем объект пожара
        db_fire = models.Fire(
            fire_date=datetime.strptime(fire_data.fire_date, '%Y-%m-%d %H:%M:%S'),
            region=fire_data.region,
            kgu_oopt_id=fire_data.kgu_oopt_id,
            area=fire_data.area,
            file_path=fire_data.file_path,
            created_by=user_id,
            quarter=fire_data.quarter,
            allotment=fire_data.allotment,
            damage_tenge=fire_data.damage_tenge,
            damage_les=fire_data.damage_les,
            damage_les_lesopokryt=fire_data.damage_les_lesopokryt,
            damage_les_verh=fire_data.damage_les_verh,
            damage_not_les=fire_data.damage_not_les,
            firefighting_costs=fire_data.firefighting_costs,
            description=fire_data.description,
            edited_by_engineer=False
        )
        db.add(db_fire)
        db.flush()  # Получаем ID без коммита

        # Добавляем связанные силы, если они есть
        if fire_data.forces:
            for force in fire_data.forces:
                db_force = models.FireForce(
                    fire_id=db_fire.id,
                    force_type=force.force_type,
                    people_count=force.people_count,
                    tecnic_count=force.tecnic_count,
                    aircraft_count=force.aircraft_count
                )
                db.add(db_force)

        db.commit()
        db.refresh(db_fire)
        log_action(db, user_id, "INSERT", "fires", db_fire.id, str(fire_data.dict()))
        logger.info(f"Fire {db_fire.id} created by user {user_id}")
        return db_fire
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating fire: {str(e)}")
        raise ValueError("Database integrity error, check unique constraints or foreign keys")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating fire: {str(e)}")
        raise

def get_fires(db: Session, skip: int = 0, limit: int = 10, region: Optional[str] = None) -> List[models.Fire]:
    """Получает список пожаров с фильтрацией по региону."""
    query = db.query(models.Fire)
    if region:
        query = query.filter(models.Fire.region == region)
    return query.order_by(models.Fire.fire_date.desc()).offset(skip).limit(limit).all()

def get_fire(db: Session, fire_id: int) -> Optional[models.Fire]:
    """Получает конкретный пожар по ID."""
    return db.query(models.Fire).filter(models.Fire.id == fire_id).first()

def update_fire(db: Session, fire_id: int, fire_data: schemas.FireData, user_id: int) -> Optional[models.Fire]:
    """Обновляет запись о пожаре, включая связанные силы."""
    try:
        db_fire = get_fire(db, fire_id)
        if not db_fire:
            return None

        # Обновляем основные поля
        for key, value in fire_data.dict(exclude={"forces"}).items():
            if key == "fire_date" and value:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            if value is not None:
                setattr(db_fire, key, value)
        db_fire.edited_by_engineer = True if db.query(models.User).filter(models.User.id == user_id, models.User.role == "engineer").first() else db_fire.edited_by_engineer

        # Обновляем силы
        if fire_data.forces is not None:
            db.query(models.FireForce).filter(models.FireForce.fire_id == fire_id).delete()
            for force in fire_data.forces:
                db_force = models.FireForce(
                    fire_id=fire_id,
                    force_type=force.force_type,
                    people_count=force.people_count,
                    tecnic_count=force.tecnic_count,
                    aircraft_count=force.aircraft_count
                )
                db.add(db_force)

        db.commit()
        db.refresh(db_fire)
        log_action(db, user_id, "UPDATE", "fires", fire_id, str(fire_data.dict()))
        logger.info(f"Fire {fire_id} updated by user {user_id}")
        return db_fire
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating fire {fire_id}: {str(e)}")
        raise

def delete_fire(db: Session, fire_id: int, user_id: int) -> bool:
    """Удаляет пожар и связанные записи."""
    try:
        db_fire = get_fire(db, fire_id)
        if not db_fire:
            return False
        db.delete(db_fire)
        db.commit()
        log_action(db, user_id, "DELETE", "fires", fire_id)
        logger.info(f"Fire {fire_id} deleted by user {user_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting fire {fire_id}: {str(e)}")
        raise

# --- Операции с User ---
def create_user(db: Session, user_data: schemas.UserData) -> models.User:
    """Создает пользователя с хэшированным паролем."""
    try:
        hashed_password = get_password_hash(user_data.password)
        db_user = models.User(
            username=user_data.username,
            password_hash=hashed_password,
            role=user_data.role,
            region=user_data.region,
            totp_secret=user_data.totp_secret
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        log_action(db, db_user.id, "INSERT", "users", db_user.id, str(user_data.dict(exclude={"password"})))
        logger.info(f"User {db_user.id} created")
        return db_user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating user: {str(e)}")
        raise ValueError("Username already exists")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Получает пользователя по ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 10) -> List[models.User]:
    """Получает список пользователей."""
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, user_data: schemas.UserData, admin_id: int) -> Optional[models.User]:
    """Обновляет данные пользователя."""
    try:
        db_user = get_user(db, user_id)
        if not db_user:
            return None
        if user_data.password:
            db_user.password_hash = get_password_hash(user_data.password)
        db_user.username = user_data.username
        db_user.role = user_data.role
        db_user.region = user_data.region
        db_user.totp_secret = user_data.totp_secret
        db.commit()
        db.refresh(db_user)
        log_action(db, admin_id, "UPDATE", "users", user_id, str(user_data.dict(exclude={"password"})))
        logger.info(f"User {user_id} updated by admin {admin_id}")
        return db_user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating user {user_id}: {str(e)}")
        raise ValueError("Username already exists")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise

def delete_user(db: Session, user_id: int, admin_id: int) -> bool:
    """Удаляет пользователя."""
    try:
        db_user = get_user(db, user_id)
        if not db_user:
            return False
        db.delete(db_user)
        db.commit()
        log_action(db, admin_id, "DELETE", "users", user_id)
        logger.info(f"User {user_id} deleted by admin {admin_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise

# --- Логирование действий ---
def log_action(db: Session, user_id: int, action: str, table_name: str, record_id: int, changes: str = None) -> None:
    """Логирует действие пользователя в audit_logs."""
    try:
        audit_log = models.AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            changes=changes
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error logging action: {str(e)}")
        raise

def get_audit_logs(db: Session, skip: int = 0, limit: int = 10) -> List[models.AuditLog]:
    """Получает список записей аудита."""
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()