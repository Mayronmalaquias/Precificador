import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _csv_env(name, default=""):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _database_uri():
    database_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if database_url:
        return database_url

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")

    if all([db_user, db_password, db_host, db_name]):
        return (
            f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}"
            f"@{db_host}:{db_port}/{db_name}"
        )

    return "sqlite:///precificador_dev.db"


class Config:
    API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
    CORS_ORIGINS = _csv_env(
        "CORS_ORIGINS",
        ",".join(
            [
                "http://15.228.241.137",
                "http://15.228.241.137:3000",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8081",
                "http://127.0.0.1:8081",
                "http://26.126.132.200",
                "http://127.0.0.1",
                "https://inteligencia61imoveis.com.br",
                "http://inteligencia61imoveis.com.br",
            ]
        ),
    )
