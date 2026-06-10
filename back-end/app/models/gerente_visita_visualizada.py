from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class GerenteVisitaVisualizada(Base):
    __tablename__ = "gerente_visita_visualizada"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_gerente = Column(String(50), nullable=False, index=True)
    id_visita = Column(String(100), nullable=False)
    visualizado_em = Column(DateTime(timezone=True), server_default=func.now())
