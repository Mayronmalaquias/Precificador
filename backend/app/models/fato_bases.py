"""Tabelas de fato CORRENTES da gestao de bases pelo site.

Substituem os scripts Bases/registrarCapitacao.py, registrarSaida.py e
tratamento_estoque.py (que escreviam nas abas Fato_Captacao/Fato_Saida/Fato_Estoque
do Google Sheets). Separadas do historico congelado em eventos_imovel_legado:
a gestao do dia a dia grava aqui, o import historico continua intocado.

Atencao: 'fato_captacao' e diferente da tabela 'captacao' (Jornada do corretor,
app/models/captacao.py) - nomes propositalmente distintos pra nao colidir.
"""

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class FatoCaptacao(Base):
    __tablename__ = "fato_captacao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_imovel = Column(String(50), nullable=True, index=True)
    captador1 = Column(String(255), nullable=True)
    captador2 = Column(String(255), nullable=True)
    captador3 = Column(String(255), nullable=True)
    id_gerente = Column(String(50), nullable=True)
    data_entrada = Column(Date, nullable=True, index=True)

    # snapshot da dimensao do imovel no momento da captacao
    bairro_id = Column(String(50), nullable=True)
    bairro_nome = Column(String(255), nullable=True)
    tipo_id = Column(String(50), nullable=True)
    tipo_nome = Column(String(255), nullable=True)
    valor = Column(Numeric(14, 2), nullable=True)
    comissao_pct = Column(Numeric(6, 2), nullable=True)
    foco_pp = Column(Boolean, nullable=True)
    foco_ac = Column(Boolean, nullable=True)
    finalidade = Column(String(50), nullable=True)

    # proveniencia
    # 'upload' | 'manual' | 'lancamento' (Lancar Imovel, ver lancamento_service).
    # captador1/2/3 guardam id_usuarios (C61xxx); linhas antigas podem ter nome.
    # codigo_imovel e a chave logica de dedup: o lancamento faz upsert por ele.
    origem = Column(String(20), nullable=True)
    arquivo_origem = Column(String(255), nullable=True)
    criado_por = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class FatoSaida(Base):
    __tablename__ = "fato_saida"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_imovel = Column(String(50), nullable=True, index=True)
    captador1 = Column(String(255), nullable=True)
    captador2 = Column(String(255), nullable=True)
    captador3 = Column(String(255), nullable=True)
    id_gerente = Column(String(50), nullable=True)
    motivo = Column(Text, nullable=True)
    data_saida = Column(Date, nullable=True, index=True)

    origem = Column(String(20), nullable=True)
    arquivo_origem = Column(String(255), nullable=True)
    criado_por = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class FatoEstoque(Base):
    __tablename__ = "fato_estoque"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_imovel = Column(String(50), nullable=True, index=True)
    captador1 = Column(String(255), nullable=True)
    captador2 = Column(String(255), nullable=True)
    captador3 = Column(String(255), nullable=True)
    id_gerente = Column(String(50), nullable=True)
    data_estoque = Column(Date, nullable=True, index=True)

    publicacao_na_internet = Column(String(50), nullable=True)
    exclusivo = Column(String(50), nullable=True)
    categoria_df = Column(Text, nullable=True)
    categoria_df_seguro = Column(Text, nullable=True)
    categoria_wi = Column(Text, nullable=True)
    id_anuncio_meta = Column(String(100), nullable=True)

    origem = Column(String(20), nullable=True)
    arquivo_origem = Column(String(255), nullable=True)
    criado_por = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class FatoDestaque(Base):
    __tablename__ = "fato_destaque"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_imovel = Column(String(50), nullable=True, index=True)
    captador1 = Column(String(255), nullable=True)
    captador2 = Column(String(255), nullable=True)
    captador3 = Column(String(255), nullable=True)
    id_gerente = Column(String(50), nullable=True)
    data_destaque = Column(Date, nullable=True, index=True)

    endereco = Column(Text, nullable=True)
    bairro = Column(Text, nullable=True)
    publicacao_web = Column(String(50), nullable=True)
    categoria_df = Column(Text, nullable=True)
    categoria_wi = Column(Text, nullable=True)
    categoria_df_seguro = Column(Text, nullable=True)
    categoria_df_assinado = Column(Text, nullable=True)
    valor = Column(Numeric(14, 2), nullable=True)

    origem = Column(String(20), nullable=True)
    arquivo_origem = Column(String(255), nullable=True)
    criado_por = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
