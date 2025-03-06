# FIRE SYSTEM

## 📌 Описание
FIRE SYSTEM — система мониторинга и учета лесных пожаров. Позволяет вести учет пожаров, экспортировать данные и анализировать статистику.

## 🚀 Установка

### 1️⃣ Клонирование репозитория
```sh
git clone https://github.com/your-repo/fire-system.git
cd fire-system
```

### 2️⃣ Установка зависимостей
```sh
pip install -r requirements.txt
```

### 3️⃣ Запуск API
```sh
python fire_routes.py
```

Сервер будет запущен на `http://127.0.0.1:5000`

## 📌 API Маршруты

### 🔥 Получить список пожаров
**GET** `/fires`
```sh
curl -X GET http://127.0.0.1:5000/fires
```

### 🔥 Добавить пожар
**POST** `/fires`
```sh
curl -X POST http://127.0.0.1:5000/fires -H "Content-Type: application/json" -d '{"date":"2024-03-06","region":"Алматы","area":10.5,"damage":50000,"description":"Лесной пожар"}'
```

### 🔥 Удалить пожар по ID
**DELETE** `/fires/{id}`
```sh
curl -X DELETE http://127.0.0.1:5000/fires/1
```

## 🛠 Структура проекта
```
FIRE SISTEM/
│── fire_monitoring/
│   ├── app/                          # Главная папка с кодом приложения
│   │   ├── __init__.py               # Инициализация пакета
│   │   ├── models.py                 # Определение моделей SQLAlchemy
│   │   ├── services/                  # Бизнес-логика
│   │   │   ├── fire_service.py        # Операции с пожарами
│   │   │   ├── user_service.py        # Операции с пользователями
│   │   ├── utils/                     # Утилиты
│   │   │   ├── logger.py              # Логирование
│   │   │   ├── validators.py          # Валидация данных
│   │   ├── routes/                    # API маршруты
│   │   │   ├── __init__.py            # Инициализация пакета
│   │   │   ├── fire_routes.py         # API для пожаров
│   │   │   ├── auth_routes.py         # API для аутентификации
│   │   │   ├── user_routes.py         # API для пользователей
│   │   ├── static/                    # Статические файлы (CSS, JS)
│   │   ├── templates/                 # HTML-шаблоны (если есть UI)
│   │   ├── auth.py                    # Модуль аутентификации
│   │   ├── database.py                # Работа с базой данных
│   │   ├── config.py                  # Конфигурация приложения
│   │   ├── manifest.json               # Метаданные (если нужен фронтенд)
│   │   ├── migrations/                 # Миграции базы данных
│   ├── tests/                          # Тестирование
│   │   ├── unit/                       # Юнит-тесты
│   │   ├── integration/                # Интеграционные тесты
│   │   ├── performance/                # Нагрузочные тесты
│   │   ├── locust/                     # Locust-скрипты
│   ├── db/                             # База данных и скрипты
│   │   ├── migrations/                 # Alembic миграции
│   │   ├── seed.sql                    # Начальные данные
│   │   ├── database.sql                # Структура БД
│   ├── docker/                         # Файлы для развертывания
│   │   ├── dockerfile                  # Основной Dockerfile
│   │   ├── docker-compose.yml          # Компоновка сервисов
│   ├── .env                            # Файл переменных окружения
│   ├── main.py                         # Точка входа (лучше `app.py` удалить)
│   ├── requirements.txt                 # Зависимости проекта
│   ├── README.md                        # Документация проекта

Полное содержимое директорий FIRE SYSTEM
Здесь перечислены все файлы, которые должны быть в каждой папке, чтобы проект был максимально организованным, масштабируемым и удобным для разработки.

🔥 **FIRE SYSTEM — надежное решение для учета пожаров!**
