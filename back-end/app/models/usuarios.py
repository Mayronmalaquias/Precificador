from sqlalchemy import Column, Integer, String,Text
from app.models.base import Base


class Usuarios(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100))
    password = Column(String(50))
    team = Column(String(100))
    nome      = Column(String(100), nullable=True)
    email     = Column(String(255), unique=True, nullable=True)
    telefone  = Column(String(20), nullable=True)
    instagram = Column(String(100), nullable=True)
    descricao = Column(Text, nullable=True)
    permissao = Column(String(20))
    id_usuarios = Column(String(50))


