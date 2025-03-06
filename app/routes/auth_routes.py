from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from database import get_db
from services.user_service import get_user_by_username
from utils.security import verify_password
from utils.logger import log_action

# Создаем роутер FastAPI
router = APIRouter()

# Конфигурация для JWT
class Settings(BaseModel):
    authjwt_secret_key: str = "supersecretkey"

@AuthJWT.load_config
def get_config():
    return Settings()

# Модель данных для авторизации
class LoginModel(BaseModel):
    username: str
    password: str

@router.post("/auth/login", tags=["auth"])
def login(data: LoginModel, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    """
    Аутентификация пользователя и выдача JWT-токена.
    """
    user = get_user_by_username(db, data.username)

    if not user or not verify_password(data.password, user.password_hash):
        log_action(data.username, "failed_login", "Invalid credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учетные данные")
    
    # Создание JWT-токена
    access_token = Authorize.create_access_token(subject=user.username)
    
    log_action(user.username, "login", "User logged in")
    return {"message": "Вход выполнен", "access_token": access_token}

# Пример защищенного маршрута
@router.get("/protected", tags=["auth"])
def protected_route(Authorize: AuthJWT = Depends()):
    """
    Пример защищенного маршрута, доступного только с JWT-токеном.
    """
    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()
        return {"message": f"Hello, {current_user}!"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
