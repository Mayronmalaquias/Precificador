"""Tabela `vendas` — camada CANONICA unificada de vendas 2015 -> hoje (Etapa B).

Consolida `contratos` (2024+) + `vendas_legado` (<2024) com pessoa resolvida para
`usuarios.id_usuarios` (via pessoa_alias). Mantem `*_nome` ao lado do `*_id` para
preservar o original (auditoria + linhas historicas nao casadas). As tabelas-fonte
ficam intactas como arquivo bruto. Popular com sql/popula_vendas.sql.
"""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class Venda(Base):
    __tablename__ = "vendas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fonte = Column(String(20), nullable=True)          # 'contrato' | 'legado'
    id_contrato = Column(String(50), nullable=True, index=True)
    data_venda = Column(Date, nullable=True, index=True)
    data_captacao = Column(Date, nullable=True)
    bairro = Column(Text, nullable=True)
    tipo = Column(Text, nullable=True)
    codigo_imovel = Column(String(50), nullable=True, index=True)
    valor_negocio = Column(Numeric(14, 2), nullable=True)
    valor_comissao = Column(Numeric(14, 2), nullable=True)

    vendedor_nome = Column(Text, nullable=True)
    vendedor_id = Column(String(50), ForeignKey("usuarios.id_usuarios"), nullable=True)
    captador_nome = Column(Text, nullable=True)
    captador_id = Column(String(50), ForeignKey("usuarios.id_usuarios"), nullable=True)
    gerente_venda_nome = Column(Text, nullable=True)
    gerente_venda_id = Column(String(50), ForeignKey("usuarios.id_usuarios"), nullable=True)
    gerente_captacao_nome = Column(Text, nullable=True)
    gerente_captacao_id = Column(String(50), ForeignKey("usuarios.id_usuarios"), nullable=True)
    diretor_nome = Column(Text, nullable=True)
    diretor_id = Column(String(50), ForeignKey("usuarios.id_usuarios"), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=True)
