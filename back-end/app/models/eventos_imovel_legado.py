from sqlalchemy import Column, Integer, Text, Date, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class EventoImovelLegado(Base):
    """Consolida captacoes_legado/saidas_legado/estoque_legado/destaques_legado/
    destaques_mensal_legado (Base Inteligencia) - todas tinham o mesmo formato base
    (codigo_imovel + captador1/2/3 + gerente + data) com poucas colunas extras
    cada. 1 tabela so, 'tipo_evento' diz de qual veio. Colunas extras viram
    nullable porque nem todo tipo de evento usa todas."""

    __tablename__ = "eventos_imovel_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_evento = Column(Text, nullable=False)  # captacao / saida / estoque / destaque / destaque_mensal
    codigo_imovel = Column(Text, nullable=True)
    captador1 = Column(Text, nullable=True)
    captador2 = Column(Text, nullable=True)
    captador3 = Column(Text, nullable=True)
    id_gerente = Column(Text, nullable=True)
    data_evento = Column(Date, nullable=True)  # data_entrada / data_saida / data_estoque (segundo o tipo_evento)

    # so saida usa:
    motivo = Column(Text, nullable=True)

    # so estoque usa:
    publicacao_na_internet = Column(Text, nullable=True)
    exclusivo = Column(Text, nullable=True)
    id_anuncio_meta = Column(Text, nullable=True)

    # destaque / destaque_mensal usam:
    endereco = Column(Text, nullable=True)
    bairro = Column(Text, nullable=True)
    publicacao_web = Column(Text, nullable=True)
    categoria_df_assinado = Column(Text, nullable=True)
    valor = Column(Text, nullable=True)

    # estoque + destaque + destaque_mensal usam:
    categoria_df = Column(Text, nullable=True)
    categoria_df_seguro = Column(Text, nullable=True)
    categoria_wi = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=True)
