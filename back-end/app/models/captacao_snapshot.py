"""Snapshot diario do estado de cada captacao (Jornada) — base do dashboard de
evolução temporal (volume por equipe/corretor/bairro/endereço/categoria).

1 linha por (dia, captacao). Populado diariamente (cron) e/ou backfill do historico.
"""

from sqlalchemy import Column, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.models.base import Base


class CaptacaoSnapshot(Base):
    __tablename__ = "captacao_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_snapshot = Column(Date, nullable=False, index=True)
    captacao_id = Column(Integer, nullable=False, index=True)
    team = Column(String(100), nullable=True)
    id_corretor = Column(String(50), nullable=True)
    nome_corretor = Column(String(255), nullable=True)
    bairro = Column(Text, nullable=True)
    endereco = Column(Text, nullable=True)
    etapa_atual = Column(String(20), nullable=True)
    status = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint("data_snapshot", "captacao_id", name="uq_captacao_snapshot_dia"),
    )
