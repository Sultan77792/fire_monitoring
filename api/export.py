# /api/export.py - Экспорт данных
from flask import send_file
import pandas as pd
from io import BytesIO
from . import export_bp

@export_bp.route('/')
def export_data():
    data = pd.DataFrame([{ "region": "Астана", "fire_count": 10 }])
    buffer = BytesIO()
    data.to_csv(buffer, index=False)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="fires.csv", mimetype="text/csv")