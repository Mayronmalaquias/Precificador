from sqlalchemy import Column, Integer, String
from app.models.base import Base


class Usuarios(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100))
    password = Column(String(50))
    team = Column(String(100))


