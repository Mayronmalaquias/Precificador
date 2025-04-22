from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()

class Config:
    # Codifique os valores de usuário e senha para garantir que caracteres especiais sejam corretamente tratados
    DB_USER = quote_plus(os.getenv('DB_USER', 'default_user'))
    DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', 'default_password'))

    # Montando a URL de conexão com os valores codificados
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print(SQLALCHEMY_DATABASE_URI)