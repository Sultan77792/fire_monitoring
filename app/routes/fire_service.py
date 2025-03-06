import sqlite3
from datetime import datetime

DB_FILE = "fire_monitoring/db/fires.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            region TEXT,
            area REAL,
            damage INTEGER,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_fire(date: str, region: str, area: float, damage: int, description: str):
    """Добавляет информацию о пожаре"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO fires (date, region, area, damage, description) VALUES (?, ?, ?, ?, ?)",
                   (date, region, area, damage, description))
    conn.commit()
    conn.close()
    return "Пожар успешно добавлен"

def get_fires():
    """Получает все пожары"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fires")
    fires = cursor.fetchall()
    conn.close()
    return fires

def delete_fire(fire_id: int):
    """Удаляет информацию о пожаре по ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fires WHERE id = ?", (fire_id,))
    conn.commit()
    conn.close()
    return "Пожар успешно удалён"

# Инициализация базы при первом запуске
init_db()
