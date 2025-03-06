# /api/weather.py - Погодные данные
from flask import jsonify
import requests
from . import weather_bp

API_KEY = "ТВОЙ_КЛЮЧ"

@weather_bp.route('/')
def get_weather_data():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Astana&appid={API_KEY}&units=metric"
    response = requests.get(url)
    return jsonify(response.json()) if response.status_code == 200 else jsonify({"error": "Ошибка получения данных"})