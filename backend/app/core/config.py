"""
Configuration and Environment Settings for rPPG Monitoring Backend.
"""

from typing import List, Optional
import os
import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Canonical project root: d:\BME\FYP (independent of current working directory)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Ensure Matplotlib config directory is in writable temp to avoid Windows permission warning and import delay
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "rPPG Vital Signs Monitoring System"
    VERSION: str = "1.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security & Multi-Device JWT Settings
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "bme_fyp_dev_only_jwt_secret_change_in_production_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # Database: Anchored to PROJECT_ROOT for SQLite unless overridden by DATABASE_URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'rppg_local.db').as_posix()}",
    )

    # Secure Media Storage & Retention (anchored to PROJECT_ROOT)
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", str(PROJECT_ROOT / "storage" / "videos"))
    MONITOR_IMAGES_DIR: str = os.getenv("MONITOR_IMAGES_DIR", str(PROJECT_ROOT / "storage" / "monitor_images"))
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", str(PROJECT_ROOT / "storage" / "reports"))
    EXPERIMENTS_DIR: str = os.getenv("EXPERIMENTS_DIR", str(PROJECT_ROOT / "storage" / "experiments"))
    CHECKPOINTS_DIR: str = os.getenv("CHECKPOINTS_DIR", str(PROJECT_ROOT / "storage" / "checkpoints"))
    MODELS_CACHE_DIR: str = os.getenv("MODELS_CACHE_DIR", str(PROJECT_ROOT / "storage" / "models"))
    VIDEO_RETENTION_DAYS: int = 30
    ENABLE_PSEUDONYMIZATION: bool = True

    # Google Drive & Google Sheets OAuth 2.0 (Server-Side Only - NEVER exposed to APK or GitHub)
    GOOGLE_CLIENT_SECRETS_FILE: str = os.getenv(
        "GOOGLE_CLIENT_SECRETS_FILE",
        str(PROJECT_ROOT / "secrets" / "google_client_secret.json"),
    )
    GOOGLE_TOKEN_FILE: str = os.getenv(
        "GOOGLE_TOKEN_FILE",
        str(PROJECT_ROOT / "secrets" / "google_oauth_token.json"),
    )
    GOOGLE_OAUTH_REDIRECT_URI: str = os.getenv(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://localhost:8000/api/v1/sync/google/callback",
    )
    GOOGLE_DRIVE_ROOT_FOLDER: str = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER", "RPPG_FYP")
    GOOGLE_SHEETS_SPREADSHEET_ID: Optional[str] = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "*",
    ]


settings = Settings()

# Ensure storage directories exist
for _dir in [
    settings.STORAGE_DIR,
    settings.MONITOR_IMAGES_DIR,
    settings.REPORTS_DIR,
    settings.EXPERIMENTS_DIR,
    settings.CHECKPOINTS_DIR,
    settings.MODELS_CACHE_DIR,
]:
    os.makedirs(_dir, exist_ok=True)
