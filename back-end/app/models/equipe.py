from sqlalchemy import Boolean, Column, String
from app.models.base import Base


class Equipe(Base):
    """Equipes da 61. id_equipe = IdGerente (mesmo valor usado em usuarios.team)."""

    __tablename__ = "equipes"

    id_equipe = Column(String(50), primary_key=True)
    nome = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1")
