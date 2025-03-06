import logging 
import os
import sqlite3
from datetime import datetime

# Папка для логов
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "fire_system.log")
DB_FILE = "fire_monitoring/db/logs.db"

# Настройка логирования в файл
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_to_db(user, action, details=""):
    """Записывает лог в базу данных"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user TEXT,
            action TEXT,
            details TEXT
        )
    ''')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO audit_logs (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
                   (timestamp, user, action, details))
    conn.commit()
    conn.close()

def log_action(user, action, details=""):
    """Записывает действие в файл и базу данных"""
    log_message = f"User: {user}, Action: {action}, Details: {details}"
    logging.info(log_message)
    log_to_db(user, action, details)
