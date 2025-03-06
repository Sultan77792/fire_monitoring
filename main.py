from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database import engine, Base
from app.routes import fires, users, analytics
from app.auth import router as auth_router
import logging

# --- 🔹 Настройка логирования ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 🔹 Инициализация базы данных ---
Base.metadata.create_all(bind=engine)

# --- 🔹 Инициализация FastAPI приложения ---
app = FastAPI(
    title="Forest Fires Monitoring System",
    description="A comprehensive system for monitoring and analyzing forest fires in Kazakhstan",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- 🔹 Настройка CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можно заменить на ["http://localhost:3000", "http://frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🔹 Подключение маршрутов ---
app.include_router(fires.router, prefix="/fires", tags=["Fires"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# --- 🔹 Корневой эндпоинт ---
@app.get("/")
def root():
    """Корневой эндпоинт приложения."""
    logger.info("Root endpoint accessed")
    return {"message": "🔥 Система мониторинга лесных пожаров работает!"}

# --- 🔹 Обработчики ошибок ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return {"detail": exc.errors()}, 422

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP error: {exc.detail}")
    return {"detail": exc.detail}, exc.status_code

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    return {"detail": "Internal server error"}, 500

# --- 🔹 Middleware для логирования всех запросов ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# --- 🔹 Запуск приложения ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
