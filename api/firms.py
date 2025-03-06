# /api/firms.py - NASA FIRMS API
from flask import jsonify
import requests
from . import firms_bp

@firms_bp.route('/')
def get_firms_data():
    response = requests.get("https://firms.modaps.eosdis.nasa.gov/api/area/csv/...")
    return response.text if response.status_code == 200 else jsonify({"error": "Ошибка получения данных"})
