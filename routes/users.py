from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, models
from ..auth import get_current_user
from ..app.database import get_db
import logging
import csv
from io import StringIO
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User not found"}}
)

# --- Создание пользователя ---
@router.post(
    "/",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Creates a new user."
)
def create_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to create user by {current_user.id} with role {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create users")
    try:
        db_user = crud.create_user(db, user_data)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Получение списка пользователей ---
@router.get(
    "/",
    response_model=List[schemas.UserResponse],
    summary="Get list of users",
    description="Returns a paginated list of users."
)
def read_users(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to list users by {current_user.id} with role {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view user list")
    try:
        users = crud.get_users(db, skip=skip, limit=limit)
        crud.log_action(db, current_user.id, "READ", "users", None, f"Retrieved {len(users)} records")
        logger.info(f"User {current_user.id} retrieved {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Получение конкретного пользователя ---
@router.get(
    "/{user_id}",
    response_model=schemas.UserResponse,
    summary="Get a specific user",
    description="Returns details of a specific user by ID."
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to view user {user_id} by {current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view user details")
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    crud.log_action(db, current_user.id, "READ", "users", user_id)
    logger.info(f"User {current_user.id} retrieved details for user {user_id}")
    return db_user

# --- Обновление пользователя ---
@router.put(
    "/{user_id}",
    response_model=schemas.UserResponse,
    summary="Update a user",
    description="Updates an existing user."
)
def update_user(
    user_id: int,
    user_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to update user {user_id} by {current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update users")
    try:
        updated_user = crud.update_user(db, user_id, user_data, current_user.id)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Удаление пользователя ---
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="Deletes a user."
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to delete user {user_id} by {current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete users")
    if user_id == current_user.id:
        logger.warning(f"Admin {current_user.id} attempted to delete themselves")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete yourself")
    try:
        success = crud.delete_user(db, user_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return None
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Экспорт пользователей в CSV ---
@router.get(
    "/export",
    response_class=Response,
    summary="Export users to CSV",
    description="Exports all user records to a CSV file. Accessible only to admins."
)
def export_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to export users by user {current_user.id} with role {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can export users")
    
    try:
        users = crud.get_users(db, skip=0, limit=None)
        output = StringIO()
        writer = csv.writer(output)
        
        # Заголовки CSV
        headers = ["id", "username", "role", "region", "totp_secret"]
        writer.writerow(headers)
        
        # Данные
        for user in users:
            writer.writerow([
                user.id, user.username, user.role, user.region, user.totp_secret
            ])
        
        crud.log_action(db, current_user.id, "EXPORT", "users", None, "Exported all user records to CSV")
        logger.info(f"User {current_user.id} exported users to CSV")
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting users: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")