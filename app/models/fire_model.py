from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from database import Base

# Модель пожара
class Fire(Base):
    __tablename__ = "fires"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow)
    region = Column(String(100), nullable=False)
    area = Column(Float, nullable=False)
    damage = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)
