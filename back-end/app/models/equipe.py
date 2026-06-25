from sqlalchemy import Column, String
from app.models.base import Base


class Equipe(Base):
    """Espelha Dim_Gerente: id_equipe = IdGerente (mesmo valor usado em usuarios.team)."""

    __tablename__ = "equipes"

    id_equipe = Column(String(50), primary_key=True)
    nome = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
