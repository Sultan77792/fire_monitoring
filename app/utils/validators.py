import re
from datetime import datetime

# Проверка email
def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

# Проверка номера телефона (формат: +1234567890)
def is_valid_phone(phone: str) -> bool:
    pattern = r"^\+?[1-9]\d{9,14}$"
    return re.match(pattern, phone) is not None

# Проверка даты (формат: YYYY-MM-DD)
def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# Проверка числа (для площади пожара, ущерба и т. д.)
def is_valid_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False
