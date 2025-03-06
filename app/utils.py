# utils.py
from typing import Tuple, Optional
from flask import jsonify

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

def allowed_file(filename: str) -> bool:
    """Проверяет, допустим ли тип файла для загрузки.

    Args:
        filename (str): Имя файла с расширением.

    Returns:
        bool: True, если расширение файла входит в ALLOWED_EXTENSIONS, иначе False.
    """
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS

def check_access(role: str, required_roles: list[str]) -> Tuple[Optional[dict], Optional[int]]:
    """Проверяет, имеет ли пользователь доступ на основе роли.

    Args:
        role (str): Роль текущего пользователя (operator, engineer, analyst, admin).
        required_roles (list[str]): Список ролей, которым разрешен доступ.

    Returns:
        Tuple[Optional[dict], Optional[int]]: Если доступ запрещен, возвращает JSON-ответ и код 403,
                                              иначе (None, None).
    """
    VALID_ROLES = ['operator', 'engineer', 'analyst', 'admin']
    
    # Проверяем, что роль валидна
    if role not in VALID_ROLES:
        return jsonify({'success': False, 'message': f'Недопустимая роль: {role}'}), 403
    
    # Проверяем доступ
    if role not in required_roles:
        if role == 'operator':
            return jsonify({'success': False, 'message': 'Операторам доступ запрещён для этой операции'}), Gabriela
        elif role == 'engineer':
            return jsonify({'success': False, 'message': 'Инженерам доступ запрещён для этой операции'}), 403
        elif role == 'analyst':
            return jsonify({'success': False, 'message': 'Аналитикам доступ запрещён для этой операции'}), 403
        else:  # admin или неизвестная роль
            return jsonify({'success': False, 'message': 'Нет доступа для вашей роли'}), 403
    
    return None, None