# /api/__init__.py - Инициализация пакета API
from flask import Blueprint

fires_bp = Blueprint('fires', __name__)
analytics_bp = Blueprint('analytics', __name__)
weather_bp = Blueprint('weather', __name__)
firms_bp = Blueprint('firms', __name__)
logs_bp = Blueprint('logs', __name__)
export_bp = Blueprint('export', __name__)