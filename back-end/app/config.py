from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()

class Config:
    DB_USER = quote_plus(os.getenv("DB_USER", "inteligencia"))
    DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD", "61Imoveis!"))
    DB_HOST = os.getenv("DB_HOST", "coleta-61.ctug6oqcsj14.us-east-2.rds.amazonaws.com")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "coleta_imobiliaria")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
