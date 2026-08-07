"""Propostas efetivas lancadas pelos gerentes.

NAO confundir com a `proposta` da visita (Visita.proposta = SIM/NAO/TALVEZ, que e a
impressao do cliente na visita). Aqui e a proposta formal de compra sobre um imovel:
valor, forma de pagamento, situacao e o historico de acoes ate fechar ou cair.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import Base

# Situacoes que encerram a proposta — param o contador de "periodo em aberto".
SITUACOES_FECHADAS = ("aceita", "recusada", "cancelada")
SITUACOES = ("em_analise", "contraproposta") + SITUACOES_FECHADAS

FORMAS_PAGAMENTO = ("permuta", "consorcio", "financiamento", "recurso_proprio", "outros")


class PropostaEfetiva(Base):
    __tablename__ = "proposta_efetiva"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Imovel: `codigo_imovel` e o codigo do Imoview; o resto e snapshot do momento do
    # lancamento, p/ a listagem nao depender da API do Imoview estar de pe.
    codigo_imovel = Column(String(50), nullable=True, index=True)
    imovel_endereco = Column(Text, nullable=True)
    bairro = Column(String(120), nullable=True)
    tipo = Column(String(80), nullable=True)
    numero = Column(String(40), nullable=True)

    valor = Column(Numeric(14, 2), nullable=True)
    # Permuta entra como 2a proposta: o bem dado em troca tem valor proprio.
    valor_permuta = Column(Numeric(14, 2), nullable=True)
    descricao_permuta = Column(Text, nullable=True)

    forma_pagamento = Column(String(30), nullable=True)
    situacao = Column(String(30), nullable=False, default="em_analise", index=True)

    # Dono da proposta: equipe manda no escopo (gerente so ve/edita a propria).
    team = Column(String(50), nullable=True, index=True)
    id_gerente = Column(String(50), nullable=True, index=True)
    gerente_nome = Column(String(255), nullable=True)
    # Corretor no nome de quem a proposta foi lancada. Diretor/administrativo escolhem
    # qualquer um; gerente so os da propria equipe. A `team` sai deste corretor.
    id_corretor = Column(String(50), nullable=True, index=True)
    corretor_nome = Column(String(255), nullable=True)
    # Visita que originou a proposta (opcional) — so visita da mesma equipe.
    id_visita = Column(String(50), nullable=True, index=True)
    cliente = Column(String(255), nullable=True)
    observacao = Column(Text, nullable=True)

    data_proposta = Column(Date, nullable=True, index=True)
    data_fechamento = Column(Date, nullable=True)
    # Marca a ultima mexida do gerente (acao ou edicao) — base do "sem acao ha X dias".
    ultima_acao_em = Column(DateTime, nullable=True, index=True)

    ativo = Column(Boolean, nullable=False, default=True)
    criado_por = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    acoes = relationship(
        "PropostaEfetivaAcao", back_populates="proposta",
        cascade="all, delete-orphan", order_by="PropostaEfetivaAcao.created_at.desc()",
    )


class PropostaEfetivaAcao(Base):
    """Historico de acoes da proposta (follow-up, contraproposta, troca de situacao)."""

    __tablename__ = "proposta_efetiva_acao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposta_id = Column(Integer, ForeignKey("proposta_efetiva.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao = Column(Text, nullable=False)
    situacao = Column(String(30), nullable=True)  # situacao apos a acao, quando mudou
    autor_id = Column(String(50), nullable=True)
    autor_nome = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True, index=True)

    proposta = relationship("PropostaEfetiva", back_populates="acoes")
