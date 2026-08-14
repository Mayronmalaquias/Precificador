from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text
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

    # ── Acompanhamento (nosso, nao vem do C2S) ────────────────────────────────
    # sem_contato | whatsapp | telefone | email
    contato_status = Column(String(20), nullable=True, index=True)
    # Nulo = ninguem respondeu ainda. Sem o nulo nao daria p/ separar "nao agendou" de
    # "nao olharam o lead".
    visita_agendada = Column(Boolean, nullable=True, index=True)
    motivo_sem_visita = Column(Text, nullable=True)
    proxima_acao = Column(Text, nullable=True)
    acompanhamento_por = Column(String(50), nullable=True)
    acompanhamento_em = Column(DateTime, nullable=True)
