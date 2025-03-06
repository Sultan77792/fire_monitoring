from sqlalchemy.orm import Session
from models.fire_model import Fire

def create_fire(db: Session, date, region, area, damage, description):
    """Добавляет информацию о пожаре в базу данных."""
    new_fire = Fire(date=date, region=region, area=area, damage=damage, description=description)
    db.add(new_fire)
    db.commit()
    db.refresh(new_fire)
    return new_fire

def get_fires(db: Session):
    """Получает все записи о пожарах."""
    return db.query(Fire).all()

def get_fire_by_id(db: Session, fire_id: int):
    """Получает пожар по ID."""
    return db.query(Fire).filter(Fire.id == fire_id).first()

def update_fire(db: Session, fire_id: int, updates: dict):
    """Обновляет информацию о пожаре."""
    fire = db.query(Fire).filter(Fire.id == fire_id).first()
    if fire:
        for key, value in updates.items():
            setattr(fire, key, value)
        db.commit()
        db.refresh(fire)
    return fire

def delete_fire(db: Session, fire_id: int):
    """Удаляет информацию о пожаре."""
    fire = db.query(Fire).filter(Fire.id == fire_id).first()
    if fire:
        db.delete(fire)
        db.commit()
    return fire