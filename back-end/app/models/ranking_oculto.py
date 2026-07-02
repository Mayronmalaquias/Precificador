from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class RankingOculto(Base):
    """Corretores ocultados manualmente do ranking (via olhinho no front)."""

    __tablename__ = "ranking_ocultos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_corretor = Column(String(50), nullable=False, unique=True, index=True)
    nome = Column(String(255), nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=True)
