"""
Configuration and Environment Settings for rPPG Monitoring Backend.
"""

from typing import List
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "rPPG Vital Signs Monitoring System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "bme_fyp_super_secure_rppg_jwt_secret_key_2026_!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database: Defaults to PostgreSQL, gracefully uses SQLite for local offline testing if not configured
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./rppg_local.db"
    )

    # Secure Video Storage & Privacy Retention
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage/videos")
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", "./storage/reports")
    VIDEO_RETENTION_DAYS: int = 7
    ENABLE_PSEUDONYMIZATION: bool = True

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "*",  # Allow cross-platform mobile/web apps in development
    ]




settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
