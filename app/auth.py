from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas
from .config import Config
import jwt
from datetime import datetime, timedelta
import logging
import pyotp
import qrcode
from io import BytesIO
import base64

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
logger = logging.getLogger(__name__)

def create_token(user_id: int, role: str, region: str):
    payload = {
        "user_id": user_id,
        "role": role,
        "region": region,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        user = db.query(models.User).filter(models.User.id == payload["user_id"]).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not user.check_password(form_data.password):
        logger.warning(f"Failed login attempt for {form_data.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.totp_secret:
        totp = pyotp.TOTP(user.totp_secret)
        if not form_data.totp or not totp.verify(form_data.totp):
            return {"2fa_required": True, "message": "2FA code required"}
    
    token = create_token(user.id, user.role, user.region)
    logger.info(f"User {form_data.username} logged in successfully")
    return {"access_token": token, "token_type": "bearer"}

@router.post("/totp/setup")
def setup_totp(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    
    totp_secret = pyotp.random_base32()
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=current_user.username, issuer_name="ForestFires")
    
    current_user.totp_secret = totp_secret
    db.commit()
    logger.info(f"2FA setup initiated for user {current_user.id}")
    return {"totp_uri": totp_uri}

@router.put("/profile")
def update_profile(
    password: str = Form(None),
    region: str = Form(None),
    totp_enable: bool = Form(False),
    totp_disable: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if password:
        current_user.set_password(password)
    if region:
        current_user.region = region
    
    if totp_enable and not current_user.totp_secret:
        totp_secret = pyotp.random_base32()
        current_user.totp_secret = totp_secret
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=current_user.username, issuer_name="ForestFires")
        db.commit()
        logger.info(f"2FA enabled for user {current_user.id}")
        return {"totp_uri": totp_uri}
    
    if totp_disable and current_user.totp_secret:
        current_user.totp_secret = None
        db.commit()
        logger.info(f"2FA disabled for user {current_user.id}")
        return {"totp_disabled": True}
    
    db.commit()
    logger.info(f"Profile updated for user {current_user.id}")
    return {"success": True}

@router.post("/logout")
def logout():
    logger.info("User logged out")
    return {"success": True}