from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class Captacao(Base):
    __tablename__ = "captacao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_corretor = Column(String(50), nullable=False, index=True)
    nome_corretor = Column(String(255), nullable=True)
    team = Column(String(100), nullable=True, index=True)

    endereco = Column(Text, nullable=False)
    bairro = Column(Text, nullable=True)
    bloco = Column(Text, nullable=True)

    etapa_atual = Column(String(20), nullable=False, default="escolha")
    status = Column(String(20), nullable=False, default="ativo")
    motivo_fechamento = Column(Text, nullable=True)
    data_fechamento = Column(Date, nullable=True)
    exclusividade_ate = Column(Date, nullable=True)
    data_entrada_etapa = Column(DateTime, nullable=True)

    # Etapa: Escolha
    tem_numero = Column(Boolean, nullable=True)
    acao_sem_numero = Column(Text, nullable=True)
    data_acao_sem_numero = Column(Date, nullable=True)
    acao_escolha_realizada = Column(Boolean, nullable=True)

    # Etapa: Prospecção
    nome_cliente = Column(Text, nullable=True)
    telefone_cliente = Column(Text, nullable=True)
    numero_imovel = Column(Text, nullable=True)
    book_enviado = Column(Boolean, nullable=True)
    link_anuncio = Column(Text, nullable=True)

    # Etapa: Interação
    falou_proprietario = Column(Boolean, nullable=True)
    motivo_nao_interacao = Column(Text, nullable=True)
    proxima_acao_interacao = Column(Text, nullable=True)
    data_proxima_acao_interacao = Column(Date, nullable=True)
    acao_interacao_realizada = Column(Boolean, nullable=True)

    # Etapa: Apresentação
    visitou_imovel = Column(Boolean, nullable=True)
    motivo_nao_apresentacao = Column(Text, nullable=True)
    proxima_acao_apresentacao = Column(Text, nullable=True)
    data_proxima_acao_apresentacao = Column(Date, nullable=True)
    acao_apresentacao_realizada = Column(Boolean, nullable=True)

    # Etapa: Captação
    captou_imovel = Column(Boolean, nullable=True)
    objecao_captacao = Column(Text, nullable=True)
    proxima_acao_captacao = Column(Text, nullable=True)
    data_proxima_acao_captacao = Column(Date, nullable=True)
    acao_captacao_realizada = Column(Boolean, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
