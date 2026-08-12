"""Area do imovel por codigo do Imoview.

Existe porque a API do Imoview so devolve imovel ATIVO: assim que o imovel vende,
ele some de `RetornarImoveisDisponiveis` e de `RetornarImoveis` — e e justamente ai
que a gente precisa da metragem, p/ calcular o valor do m2 do contrato fechado.

O job `sync_areas_imoview.py` varre o catalogo periodicamente e grava aqui, entao a
area fica registrada ANTES da venda e sobrevive ao imovel sair do ar.
"""
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, func

from app.models.base import Base


class ImovelArea(Base):
    __tablename__ = "imovel_area"

    codigo = Column(String(50), primary_key=True)
    area = Column(Numeric(12, 2), nullable=True)          # a que vale p/ o m2 (principal/interna)
    area_principal = Column(Numeric(12, 2), nullable=True)
    area_interna = Column(Numeric(12, 2), nullable=True)
    area_privativa = Column(Numeric(12, 2), nullable=True)
    area_lote = Column(Numeric(12, 2), nullable=True)
    endereco = Column(Text, nullable=True)
    bairro = Column(String(120), nullable=True)
    tipo = Column(String(80), nullable=True)
    quartos = Column(Integer, nullable=True)
    vagas = Column(Integer, nullable=True)
    valor = Column(Numeric(14, 2), nullable=True)
    # Vago/Disponivel | Vendido | Desativado | Em moderacao | Em reforma
    situacao = Column(String(40), nullable=True, index=True)
    origem = Column(String(30), nullable=True, default="imoview")
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
