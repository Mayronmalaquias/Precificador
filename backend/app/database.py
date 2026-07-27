from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import Config


engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    echo=Config.SQLALCHEMY_ECHO,
    **Config.SQLALCHEMY_ENGINE_OPTIONS,
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
)


def remove_session(exception=None):
    SessionLocal.remove()
