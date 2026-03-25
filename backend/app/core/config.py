import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Subscription Monitoring API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/subscription_db")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "7b9e1c2a8f4d5b6c3e9a0f1d2e3b4a5c")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "G6h7J8k9M0n1P2q3R4s5T6u7V8w9X0y1")
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    YANDEX_CLIENT_ID: str = os.getenv("YANDEX_CLIENT_ID", "")
    YANDEX_CLIENT_SECRET: str = os.getenv("YANDEX_CLIENT_SECRET", "")
    FRONTEND_REDIRECT_URL: str = os.getenv("FRONTEND_REDIRECT_URL", "myapp://login")

    class Config:
        env_file = ".env"

settings = Settings()
