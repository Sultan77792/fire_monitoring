from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database import get_db
from services.log_service import get_logs, get_logs_by_user, delete_log
from utils.logger import log_action

log_bp = Blueprint("logs", __name__)

@log_bp.route("/logs", methods=["GET"])
def list_logs():
    """Получает все логи."""
    db: Session = get_db()
    logs = get_logs(db)
    return jsonify([log.__dict__ for log in logs])

@log_bp.route("/logs/user/<int:user_id>", methods=["GET"])
def user_logs(user_id):
    """Получает все логи конкретного пользователя."""
    db: Session = get_db()
    logs = get_logs_by_user(db, user_id)
    return jsonify([log.__dict__ for log in logs])

@log_bp.route("/logs/<int:log_id>", methods=["DELETE"])
def remove_log(log_id):
    """Удаляет лог по ID."""
    db: Session = get_db()
    log = delete_log(db, log_id)
    return jsonify({"message": "Лог удален"}) if log else (jsonify({"error": "Лог не найден"}), 404)
