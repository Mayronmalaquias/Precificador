from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
# from app.models.base import Base
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from app import engine
from app.models.base import Base


# Conexão com o banco
# Base = declarative_base()
# engine = create_engine('postgresql://postgres:1234@localhost:5432/database', echo=True)

class Usuarios(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100))
    password = Column(String(50))
    team = Column(String(100))


if __name__ == '__main__':
    Base.metadata.create_all(engine)