from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..app.database import get_db
from .. import models, schemas
from ..auth import get_current_user
import logging
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@router.get("/")
def get_analytics(
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Получение аналитических данных о пожарах с фильтрацией по году и месяцу."""
    if user.role not in ["admin", "analyst"]:
        logger.warning(f"Unauthorized access to analytics by user {user.id} with role {user.role}")
        raise HTTPException(status_code=403, detail="Only admins and analysts can access analytics")
    
    query = db.query(
        models.Fire.region,
        func.extract('month', models.Fire.fire_date).label('month'),
        func.count(models.Fire.id).label('count'),
        func.sum(models.Fire.area).label('total_area'),
        func.sum(models.Fire.damage_tenge).label('total_damage')
    ).group_by(models.Fire.region, func.extract('month', models.Fire.fire_date))
    
    if year:
        query = query.filter(func.extract('year', models.Fire.fire_date) == year)
    if month:
        query = query.filter(func.extract('month', models.Fire.fire_date) == month)
    
    results = query.all()
    fires = db.query(models.Fire).all()  # Для получения полных данных о силах
    
    data = [
        {
            "region": row.region,
            "month": int(row.month),
            "count": row.count,
            "total_area": float(row.total_area),
            "total_damage": float(row.total_damage) if row.total_damage else 0,
            "forces": [
                {"force_type": f.force_type, "people_count": f.people_count}
                for fire in fires if fire.region == row.region and fire.fire_date.month == row.month for f in fire.forces
            ]
        }
        for row in results
    ]
    
    logger.info(f"User {user.id} retrieved analytics data")
    return {"data": data}

@router.get("/predict")
def predict_fires(
    days_ahead: int,
    model: str = "linear",
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Прогнозирование площади пожаров с использованием линейной регрессии или ARIMA."""
    if user.role not in ["admin", "analyst"]:
        logger.warning(f"Unauthorized access to prediction by user {user.id} with role {user.role}")
        raise HTTPException(status_code=403, detail="Only admins and analysts can access predictions")
    
    if days_ahead < 1 or days_ahead > 365:
        raise HTTPException(status_code=400, detail="Days ahead must be between 1 and 365")
    
    fires = db.query(models.Fire).order_by(models.Fire.fire_date).all()
    dates = [fire.fire_date for fire in fires]
    areas = [fire.area for fire in fires]
    df = pd.DataFrame({"date": dates, "area": areas}).set_index("date").resample("D").sum().fillna(0)
    
    try:
        if model == "linear":
            slope = (df["area"].iloc[-1] - df["area"].iloc[0]) / max(1, len(df) - 1)
            predicted_area = max(0, df["area"].iloc[-1] + slope * days_ahead)
        elif model == "arima":
            arima_model = ARIMA(df["area"], order=(5, 1, 0)).fit()
            forecast = arima_model.forecast(steps=days_ahead)
            predicted_area = max(0, forecast.iloc[-1])
        else:
            raise HTTPException(status_code=400, detail="Unsupported model. Use 'linear' or 'arima'")
        
        predicted_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        logger.info(f"User {user.id} generated {model} prediction for {days_ahead} days ahead: {predicted_area} ha")
        return {
            "success": True,
            "date": predicted_date,
            "predicted_area": float(predicted_area)
        }
    except Exception as e:
        logger.error(f"Error in prediction for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/export/csv")
def export_analytics_csv(
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Экспорт аналитических данных в CSV."""
    if user.role not in ["admin", "analyst"]:
        logger.warning(f"Unauthorized export attempt by user {user.id} with role {user.role}")
        raise HTTPException(status_code=403, detail="Only admins and analysts can export analytics")
    
    query = db.query(models.Fire)
    if year:
        query = query.filter(func.extract('year', models.Fire.fire_date) == year)
    if month:
        query = query.filter(func.extract('month', models.Fire.fire_date) == month)
    
    fires = query.all()
    output = StringIO()
    writer = csv.writer(output)
    
    headers = [
        "id", "fire_date", "region", "area", "damage_tenge", "forces", "quarter", "allotment",
        "damage_les", "damage_les_lesopokryt", "damage_les_verh", "damage_not_les", "firefighting_costs"
    ]
    writer.writerow(headers)
    
    for fire in fires:
        forces_str = "; ".join(f"{f.force_type}: {f.people_count} people, {f.tecnic_count} tecnic, {f.aircraft_count} aircraft" for f in fire.forces)
        writer.writerow([
            fire.id, fire.fire_date.isoformat(), fire.region, fire.area, fire.damage_tenge or 0, forces_str,
            fire.quarter or '', fire.allotment or '', fire.damage_les or 0, fire.damage_les_lesopokryt or 0,
            fire.damage_les_verh or 0, fire.damage_not_les or 0, fire.firefighting_costs or 0
        ])
    
    logger.info(f"User {user.id} exported analytics to CSV")
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@router.get("/export/pdf")
def export_analytics_pdf(
    year: int = None,
    month: int = None,
    lang: str = "ru",
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Экспорт аналитических данных в PDF."""
    if user.role not in ["admin", "analyst"]:
        logger.warning(f"Unauthorized export attempt by user {user.id} with role {user.role}")
        raise HTTPException(status_code=403, detail="Only admins and analysts can export analytics")
    
    query = db.query(models.Fire)
    if year:
        query = query.filter(func.extract('year', models.Fire.fire_date) == year)
    if month:
        query = query.filter(func.extract('month', models.Fire.fire_date) == month)
    
    fires = query.all()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    title = "Аналитика пожаров" if lang == "ru" else "Өрт аналитикасы"
    elements.append(Paragraph(title, styles['Title']))
    
    headers = [
        "ID", "Дата", "Регион", "Площадь (га)", "Ущерб (тенге)", "Силы", "Квартал", "Выдел",
        "Ущерб лесу (га)", "Ущерб лесопокрытым (га)", "Ущерб верхним (га)", "Ущерб нелесным (га)", "Затраты (тенге)"
    ]
    data = [headers]
    
    for fire in fires:
        forces_str = "; ".join(f"{f.force_type}: {f.people_count}" for f in fire.forces)
        data.append([
            str(fire.id), fire.fire_date.strftime("%Y-%m-%d %H:%M:%S"), fire.region, f"{fire.area:.2f}",
            f"{fire.damage_tenge or 0:.2f}", forces_str, fire.quarter or '', fire.allotment or '',
            f"{fire.damage_les or 0:.2f}", f"{fire.damage_les_lesopokryt or 0:.2f}", f"{fire.damage_les_verh or 0:.2f}",
            f"{fire.damage_not_les or 0:.2f}", f"{fire.firefighting_costs or 0:.2f}"
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    
    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    logger.info(f"User {user.id} exported analytics to PDF")
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
    )