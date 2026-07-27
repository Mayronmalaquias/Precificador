from sqlalchemy import Column, Integer, Text, Date, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class LeadLegado(Base):
    """Espelha Fato_Lead (Base Inteligencia, ~63k linhas)."""

    __tablename__ = "leads_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Date, nullable=True)
    fonte = Column(Text, nullable=True)
    contato = Column(Text, nullable=True)
    relatorio = Column(Text, nullable=True)  # 'Relatório ' (trailing space na origem)
    cliente = Column(Text, nullable=True)
    telefone = Column(Text, nullable=True)
    codigo_imovel = Column(Text, nullable=True)  # 'Código'
    atendimento = Column(Text, nullable=True)
    equipe = Column(Text, nullable=True)
    observacao = Column(Text, nullable=True)
    san_observacao = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
