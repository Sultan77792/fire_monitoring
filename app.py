# app.py
import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flasgger import Swagger
from config import Config
from database import Base, engine, SessionLocal, init_db  # Импорт из database.py
from routes import register_routes
from dashboard import create_dashboard

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Инициализация приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True
)
cache = Cache(app)
csrf = CSRFProtect(app)
swagger = Swagger(app, template={
    "info": {
        "title": "Forest Fires API",
        "description": "API для автоматизированной платформы учета лесных пожаров МЧС РК",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        }
    }
})

# Инициализация базы данных
with app.app_context():
    init_db()  # Создаём все таблицы

# Регистрация маршрутов и дашборда
register_routes(app, socketio, cache, csrf)
create_dashboard(app)

if __name__ == '__main__':
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        logger.info("Starting Forest Fires Platform...")
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,  # Отключено для продакшена
            log_output=True
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise