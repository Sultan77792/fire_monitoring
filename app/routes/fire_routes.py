from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database import get_db
from services.fire_service import create_fire, get_fires, get_fire_by_id, update_fire, delete_fire
from utils.logger import log_action

fire_bp = Blueprint("fires", __name__)

@fire_bp.route("/fires", methods=["GET"])
def list_fires():
    """Получает список всех пожаров"""
    db: Session = get_db()
    fires = get_fires(db)
    return jsonify([fire.__dict__ for fire in fires])

@fire_bp.route("/fires", methods=["POST"])
def add_fire():
    """Добавляет новый пожар"""
    db: Session = get_db()
    data = request.get_json()
    fire = create_fire(db, data["date"], data["region"], data["area"], data["damage"], data.get("description", ""))
    log_action("admin", "create_fire", f"Added fire in {data['region']}")
    return jsonify({"message": "Пожар добавлен", "fire": fire.__dict__}), 201

@fire_bp.route("/fires/<int:fire_id>", methods=["GET"])
def get_fire(fire_id):
    """Получает данные о конкретном пожаре по ID"""
    db: Session = get_db()
    fire = get_fire_by_id(db, fire_id)
    return jsonify(fire.__dict__) if fire else (jsonify({"error": "Пожар не найден"}), 404)

@fire_bp.route("/fires/<int:fire_id>", methods=["PUT"])
def edit_fire(fire_id):
    """Редактирует информацию о пожаре"""
    db: Session = get_db()
    updates = request.get_json()
    fire = update_fire(db, fire_id, updates)
    return jsonify({"message": "Пожар обновлен", "fire": fire.__dict__}) if fire else (jsonify({"error": "Пожар не найден"}), 404)

@fire_bp.route("/fires/<int:fire_id>", methods=["DELETE"])
def remove_fire(fire_id):
    """Удаляет информацию о пожаре"""
    db: Session = get_db()
    fire = delete_fire(db, fire_id)
    return jsonify({"message": "Пожар удален"}) if fire else (jsonify({"error": "Пожар не найден"}), 404)
