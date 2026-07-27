from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class CaptacaoHistorico(Base):
    __tablename__ = "captacao_historico"

    id = Column(Integer, primary_key=True, autoincrement=True)
    captacao_id = Column(Integer, nullable=False, index=True)
    etapa = Column(String(50), nullable=True)
    tipo = Column(String(50), nullable=True)  # inicio, acao, realizada, avanco, dado, book, objecao, fechamento, captado
    descricao = Column(Text, nullable=True)
    data_acao = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
