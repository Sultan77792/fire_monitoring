# /api/fires.py - API для данных о пожарах
from flask import jsonify
from extensions import db
from models.fire_model import Fire
from . import fires_bp

@fires_bp.route('/')
def get_fires_data():
    fires = db.session.query(Fire).all()
    return jsonify([{"date": fire.date, "region": fire.region, "area": fire.damage_area} for fire in fires])