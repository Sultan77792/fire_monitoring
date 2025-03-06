from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database import get_db
from services.user_service import create_user, get_user_by_id, get_user_by_username, update_user, delete_user
from utils.logger import log_action

user_bp = Blueprint("users", __name__)

@user_bp.route("/users", methods=["POST"])
def add_user():
    """Создает нового пользователя"""
    db: Session = get_db()
    data = request.get_json()
    user = create_user(db, data["username"], data["password"], data.get("role", "user"))
    log_action("admin", "create_user", f"Created user {data['username']}")
    return jsonify({"message": "Пользователь создан", "user": user.__dict__}), 201

@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Получает пользователя по ID"""
    db: Session = get_db()
    user = get_user_by_id(db, user_id)
    return jsonify(user.__dict__) if user else (jsonify({"error": "Пользователь не найден"}), 404)

@user_bp.route("/users/by-username/<string:username>", methods=["GET"])
def get_user_by_name(username):
    """Получает пользователя по имени"""
    db: Session = get_db()
    user = get_user_by_username(db, username)
    return jsonify(user.__dict__) if user else (jsonify({"error": "Пользователь не найден"}), 404)

@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def edit_user(user_id):
    """Обновляет данные пользователя"""
    db: Session = get_db()
    updates = request.get_json()
    user = update_user(db, user_id, updates)
    return jsonify({"message": "Пользователь обновлен", "user": user.__dict__}) if user else (jsonify({"error": "Пользователь не найден"}), 404)

@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def remove_user(user_id):
    """Удаляет пользователя"""
    db: Session = get_db()
    user = delete_user(db, user_id)
    return jsonify({"message": "Пользователь удален"}) if user else (jsonify({"error": "Пользователь не найден"}), 404)