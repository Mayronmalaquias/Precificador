from sqlalchemy import Column, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.models.base import Base


class DfImoveisAcesso(Base):
    __tablename__ = "dfimoveis_acessos"
    __table_args__ = (
        UniqueConstraint("data_relatorio", "codigo_busca", name="uq_dfimoveis_relatorio_codigo"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_relatorio = Column(Date, nullable=False, index=True)
    arquivo_origem = Column(Text, nullable=True)
    criado_por = Column(String(50), nullable=True)
    endereco = Column(Text, nullable=True)
    bairro = Column(Text, nullable=True, index=True)
    codigo_busca = Column(String(100), nullable=False)
    negocio = Column(String(50), nullable=True)
    situacao_cadastro = Column(String(50), nullable=True)
    acesso = Column(Integer, nullable=False, default=0)
    impressao = Column(Integer, nullable=False, default=0)
    emails = Column(Integer, nullable=False, default=0)
    telefone = Column(Integer, nullable=False, default=0)
    whatsapp_emails_gerados = Column(Integer, nullable=False, default=0)
    indique = Column(Integer, nullable=False, default=0)
    indique_whatsapp = Column(Integer, nullable=False, default=0)
    termo = Column(Integer, nullable=False, default=0)
    compartilhe_facebook = Column(Integer, nullable=False, default=0)
    compartilhe_google = Column(Integer, nullable=False, default=0)
    compartilhe_twitter = Column(Integer, nullable=False, default=0)
    atendimento_online_lancamento = Column(Integer, nullable=False, default=0)
    visita = Column(Integer, nullable=False, default=0)
    proposta = Column(Integer, nullable=False, default=0)
    importado_em = Column(DateTime, server_default=func.now(), nullable=False)
