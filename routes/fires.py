from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, models
from ..auth import get_current_user
from ..app.database import get_db
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
import csv
from io import StringIO

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки для загрузки файлов
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

router = APIRouter(
    prefix="/fires",
    tags=["fires"],
    responses={404: {"description": "Fire not found"}}
)

def validate_file(file: UploadFile) -> None:
    """Валидирует загружаемый файл."""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit"
        )

def save_file(file: UploadFile) -> str:
    """Сохраняет файл и возвращает путь."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1].lower()
    file_path = UPLOAD_DIR / f"{timestamp}_{file.filename.replace(' ', '_')}"
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return str(file_path)
    except Exception as e:
        logger.error(f"Error saving file {file.filename}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving file")

# --- Создание пожара с файлом ---
@router.post(
    "/",
    response_model=schemas.FireResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new fire record with optional file",
    description="Creates a new fire with associated forces and an optional file upload."
)
def create_fire(
    fire_data: schemas.FireCreate = Depends(),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "engineer"]:
        logger.warning(f"Unauthorized attempt to create fire by user {current_user.id} with role {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins and engineers can create fire records")
    
    if file:
        validate_file(file)
        fire_data.file_path = save_file(file)
        logger.info(f"File {file.filename} uploaded to {fire_data.file_path}")

    try:
        db_fire = crud.create_fire(db, fire_data, current_user.id)
        return db_fire
    except ValueError as e:
        if file and fire_data.file_path and os.path.exists(fire_data.file_path):
            os.remove(fire_data.file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if file and fire_data.file_path and os.path.exists(fire_data.file_path):
            os.remove(fire_data.file_path)
        logger.error(f"Unexpected error creating fire: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Получение списка пожаров ---
@router.get(
    "/",
    response_model=List[schemas.FireResponse],
    summary="Get list of fires",
    description="Returns a paginated list of fires, filtered by region for engineers."
)
def read_fires(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    region_filter = current_user.region if current_user.role == "engineer" else None
    try:
        fires = crud.get_fires(db, skip=skip, limit=limit, region=region_filter)
        crud.log_action(db, current_user.id, "READ", "fires", None, f"Retrieved {len(fires)} records")
        logger.info(f"User {current_user.id} retrieved {len(fires)} fires")
        return fires
    except Exception as e:
        logger.error(f"Error retrieving fires: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Получение конкретного пожара ---
@router.get(
    "/{fire_id}",
    response_model=schemas.FireResponse,
    summary="Get a specific fire",
    description="Returns details of a specific fire by ID, including file path if available."
)
def read_fire(
    fire_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_fire = crud.get_fire(db, fire_id)
    if not db_fire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fire not found")
    if current_user.role == "engineer" and db_fire.region != current_user.region:
        logger.warning(f"User {current_user.id} attempted to access fire {fire_id} outside their region")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this region")
    crud.log_action(db, current_user.id, "READ", "fires", fire_id)
    logger.info(f"User {current_user.id} retrieved fire {fire_id}")
    return db_fire

# --- Обновление пожара с файлом ---
@router.put(
    "/{fire_id}",
    response_model=schemas.FireResponse,
    summary="Update a fire record with optional file",
    description="Updates an existing fire record with an optional file upload."
)
def update_fire(
    fire_id: int,
    fire_data: schemas.FireCreate = Depends(),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_fire = crud.get_fire(db, fire_id)
    if not db_fire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fire not found")
    
    if current_user.role not in ["admin", "engineer"]:
        logger.warning(f"Unauthorized attempt to update fire {fire_id} by user {current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins and engineers can update fires")
    if current_user.role == "engineer" and (db_fire.created_by != current_user.id or db_fire.region != current_user.region):
        logger.warning(f"Engineer {current_user.id} attempted to update fire {fire_id} without permission")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update fires you created in your region")
    
    old_file_path = db_fire.file_path
    if file:
        validate_file(file)
        fire_data.file_path = save_file(file)
        logger.info(f"File {file.filename} uploaded to {fire_data.file_path}")
    
    try:
        updated_fire = crud.update_fire(db, fire_id, fire_data, current_user.id)
        if not updated_fire:
            if file and fire_data.file_path and os.path.exists(fire_data.file_path):
                os.remove(fire_data.file_path)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fire not found")
        
        if file and old_file_path and os.path.exists(old_file_path):
            os.remove(old_file_path)
            logger.info(f"Old file {old_file_path} deleted after update")
        
        return updated_fire
    except ValueError as e:
        if file and fire_data.file_path and os.path.exists(fire_data.file_path):
            os.remove(fire_data.file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if file and fire_data.file_path and os.path.exists(fire_data.file_path):
            os.remove(fire_data.file_path)
        logger.error(f"Error updating fire {fire_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Удаление пожара ---
@router.delete(
    "/{fire_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a fire record",
    description="Deletes a fire record and its associated file."
)
def delete_fire(
    fire_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized attempt to delete fire {fire_id} by user {current_user.id} with role {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete fire records")
    
    db_fire = crud.get_fire(db, fire_id)
    if not db_fire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fire not found")
    
    file_path = db_fire.file_path
    try:
        success = crud.delete_fire(db, fire_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fire not found")
        
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File {file_path} deleted with fire {fire_id}")
        
        return None
    except Exception as e:
        logger.error(f"Error deleting fire {fire_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# --- Экспорт пожаров в CSV ---
@router.get(
    "/export",
    response_class=Response,
    summary="Export fires to CSV",
    description="Exports all fire records to a CSV file. Accessible to admins and analysts."
)
def export_fires(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "analyst"]:
        logger.warning(f"Unauthorized attempt to export fires by user {current_user.id} with role {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins and analysts can export fires")
    
    try:
        fires = crud.get_fires(db, skip=0, limit=None, region=current_user.region if current_user.role == "engineer" else None)
        output = StringIO()
        writer = csv.writer(output)
        
        # Заголовки CSV
        headers = [
            "id", "fire_date", "region", "kgu_oopt_id", "area", "file_path", "created_by", "quarter", "allotment",
            "damage_tenge", "damage_les", "damage_les_lesopokryt", "damage_les_verh", "damage_not_les",
            "firefighting_costs", "description", "forces"
        ]
        writer.writerow(headers)
        
        # Данные
        for fire in fires:
            forces_str = "; ".join(
                f"{force.force_type}: {force.people_count} people, {force.tecnic_count} tecnic, {force.aircraft_count} aircraft"
                for force in fire.forces
            )
            writer.writerow([
                fire.id, fire.fire_date.isoformat(), fire.region, fire.kgu_oopt_id, fire.area, fire.file_path,
                fire.created_by, fire.quarter, fire.allotment, fire.damage_tenge, fire.damage_les,
                fire.damage_les_lesopokryt, fire.damage_les_verh, fire.damage_not_les, fire.firefighting_costs,
                fire.description, forces_str
            ])
        
        crud.log_action(db, current_user.id, "EXPORT", "fires", None, "Exported all fire records to CSV")
        logger.info(f"User {current_user.id} exported fires to CSV")
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=fires_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting fires: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")