from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, jsonify, send_file
import requests
from extensions import db
from models.fire_model import Fire
from datetime import datetime, timedelta
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.statespace.sarimax import SARIMAX
from fbprophet import Prophet
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import xlsxwriter
import schedule
import time
import threading

# Функция получения данных из MySQL и NASA FIRMS

def fetch_fire_data(region=None, year=None):
    query = db.session.query(Fire.date, Fire.region, Fire.damage_area, Fire.damage_tenge, Fire.latitude, Fire.longitude)
    if region:
        query = query.filter(Fire.region == region)
    if year:
        query = query.filter(Fire.date >= datetime(year, 1, 1), Fire.date <= datetime(year, 12, 31))
    fire_data = query.all()
    
    fires = pd.DataFrame([
        {"region": fire.region,
         "year": fire.date.year if fire.date else None,
         "month": fire.date.month if fire.date else None,
         "damage_area": fire.damage_area or 0,
         "damage_tenge": fire.damage_tenge or 0,
         "latitude": fire.latitude,
         "longitude": fire.longitude}
        for fire in fire_data
    ])
    
    response = requests.get("http://localhost:8080/api/firms")
    if response.status_code == 200:
        nasa_fires = pd.DataFrame(response.json())
        if not nasa_fires.empty:
            nasa_fires["region"] = "NASA_FIRMS"
            nasa_fires["year"] = pd.to_datetime(nasa_fires["acq_date"]).dt.year
            nasa_fires["month"] = pd.to_datetime(nasa_fires["acq_date"]).dt.month
            nasa_fires["damage_area"] = nasa_fires["confidence"] * 0.1
            nasa_fires["damage_tenge"] = nasa_fires["confidence"] * 5000
            fires = pd.concat([fires, nasa_fires], ignore_index=True)
    
    return fires

# Функция получения данных о погоде с OpenWeather (бесплатный API)

def fetch_weather_data(lat, lon):
    API_KEY = "ВАШ_API_КЛЮЧ"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"]
        }
    return None

# SARIMA-прогнозирование пожаров

def predict_fires_sarima(data):
    if len(data) < 10:
        return None
    data = data.groupby("year")["damage_area"].sum().reset_index()
    model = SARIMAX(data["damage_area"], order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
    model_fit = model.fit()
    future_years = [data["year"].max() + i for i in range(1, 6)]
    predictions = model_fit.forecast(steps=5)
    return pd.DataFrame({"year": future_years, "predicted_area": predictions})

# Prophet-прогнозирование пожаров

def predict_fires_prophet(data):
    if len(data) < 10:
        return None
    data = data.groupby("year")["damage_area"].sum().reset_index()
    df = data.rename(columns={"year": "ds", "damage_area": "y"})
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=5, freq='Y')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat']].rename(columns={"ds": "year", "yhat": "predicted_area"})

# Автообновление данных

def auto_update_data():
    print("🔄 Обновление данных из NASA FIRMS и OpenWeather...")
    fetch_fire_data()
    print("✅ Данные успешно обновлены!")

# Запуск фонового процесса для автообновления

def start_scheduler():
    schedule.every(30).minutes.do(auto_update_data)
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=start_scheduler, daemon=True).start()

# Подключаем Dash к Flask

def create_dashboard(flask_app):
    dash_app = Dash(server=flask_app, name="Dashboard", url_base_pathname="/dashboard/")
    dash_app.layout = html.Div([
        html.H1("🔥 Полный Аналитический Дашборд по Лесным Пожарам", style={'textAlign': 'center', 'color': '#FF5733'}),
        dcc.Dropdown(id="region-dropdown", placeholder="Выберите регион"),
        dcc.Dropdown(id="year-dropdown", placeholder="Выберите год"),
        dcc.Interval(id='interval-component', interval=300000, n_intervals=0),
        html.Button("📄 Скачать отчёт PDF", id="pdf-btn"),
        html.Button("📊 Скачать отчёт Excel", id="excel-btn"),
        dcc.Graph(id="fire-trends"),
        dcc.Graph(id="fire-predictions"),
    ])
    
    @flask_app.route("/download_report", methods=["GET"])
    def download_report():
        pdf = generate_pdf_report()
        return send_file(pdf, as_attachment=True, download_name="fire_report.pdf", mimetype="application/pdf")
    
    @flask_app.route("/download_excel", methods=["GET"])
    def download_excel():
        excel = generate_excel_report()
        return send_file(excel, as_attachment=True, download_name="fire_report.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    return dash_app