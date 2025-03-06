# /api/logs.py - Логирование
from flask import jsonify
from . import logs_bp

@logs_bp.route('/')
def get_logs():
    return jsonify({"logs": "История изменений"})