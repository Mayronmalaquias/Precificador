from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class GerenteVisitaVisualizada(Base):
    __tablename__ = "gerente_visita_visualizada"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_gerente = Column(String(50), nullable=False, index=True)
    id_visita = Column(String(100), nullable=False)
    visualizado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Flags de revisao do gerente (importantes p/ o diretor). Marcadas automaticamente
    # na interacao: abre anexo, abre notas, salva motivo (talvez/sim). Monotonicas: uma
    # vez True, permanecem True.
    viu_anexo = Column(Boolean, nullable=False, server_default="false")
    viu_notas = Column(Boolean, nullable=False, server_default="false")
    add_motivo = Column(Boolean, nullable=False, server_default="false")
