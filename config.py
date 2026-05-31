"""Конфигурация приложения.

Локально используется SQLite (файл app.db), на Render — PostgreSQL,
адрес которого передаётся через переменную окружения DATABASE_URL.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _normalize_db_url(url: str) -> str:
    """Render отдаёт URL вида postgres://..., а SQLAlchemy ждёт postgresql://."""
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    _database_url = _normalize_db_url(os.environ.get("DATABASE_URL", ""))
    SQLALCHEMY_DATABASE_URI = _database_url or "sqlite:///" + os.path.join(BASE_DIR, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Перечитывать шаблоны на каждом запросе (удобно при разработке)
    TEMPLATES_AUTO_RELOAD = True

    # Лимит размера загружаемого файла (изображения изделий) — 3 МБ
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024

    # Логин администратора по умолчанию (создаётся при первом сидировании БД)
    ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
