"""Solicitacoes operacionais, historico e anexos privados."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, LargeBinary, UniqueConstraint
from app.models.base import Base
from app.models import usuarios  # noqa: F401 - FK metadata for the standalone worker

class Solicitacao(Base):
    __tablename__ = "solicitacoes"
    __table_args__ = (UniqueConstraint("usuario_id", "chave_cliente"),)
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    chave_cliente = Column(String(64), nullable=False)
    email = Column(String(255), nullable=False)
    tipo = Column(String(40), nullable=False)
    dados = Column(JSON, nullable=False)
    status = Column(String(40), nullable=False, default="aguardando_trello", index=True)
    trello_id = Column(String(64), unique=True)
    trello_url = Column(Text)
    lista_nome = Column(String(255))
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    integrado_em = Column(DateTime)
    concluido_em = Column(DateTime)
    enviado_em = Column(DateTime)
    sincronizado_em = Column(DateTime)
    erro = Column(Text)
    tentativas = Column(Integer, nullable=False, default=0)
    resultado = Column(JSON)

class SolicitacaoAnexo(Base):
    __tablename__ = "solicitacao_anexos"
    id = Column(Integer, primary_key=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    mime = Column(String(100), nullable=False)
    conteudo = Column(LargeBinary, nullable=False)
    trello_id = Column(String(64))

class SolicitacaoEvento(Base):
    __tablename__ = "solicitacao_eventos"
    id = Column(Integer, primary_key=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes.id"), nullable=False, index=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    descricao = Column(Text, nullable=False)
