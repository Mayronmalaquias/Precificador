from sqlalchemy import Column, DateTime, Integer, Text

from app.models.base import Base


class ImovelPortal(Base):
    """Publicacao de um imovel num portal, uma linha por par.

    Complementa as colunas agregadas de `imovel_area` (`portais_ativos`,
    `destaque_nivel`), que respondem "esta publicado?" e "qual o maior destaque?" sem
    varrer nada. Esta tabela responde o que o agregado nao consegue: quantos anuncios e
    com que destaque em CADA portal.

    A diferenca importa. Em 29/08/2026 o card agregado dizia "Super destaque: 106", e
    117 deles eram do Imovel Web — o DF imoveis, portal principal da operacao, tinha
    zero. O maior nivel entre os portais escondia o portal que interessa.

    `situacao` 2 (retirado) fica gravado de proposito: apagar a linha perderia a
    diferenca entre "nunca foi para esse portal" e "saiu de la".
    """

    __tablename__ = "imovel_portal"

    codigo = Column(Text, primary_key=True)
    codigo_portal = Column(Integer, primary_key=True)
    nome_portal = Column(Text, nullable=True)

    situacao = Column(Integer, nullable=True)
    situacao_rotulo = Column(Text, nullable=True)

    destaque_nivel = Column(Integer, nullable=True)
    destaque_rotulo = Column(Text, nullable=True)

    dias_publicacao = Column(Integer, nullable=True)
    primeiro_envio = Column(DateTime, nullable=True)
    ultimo_envio = Column(DateTime, nullable=True)
    atualizado_em = Column(DateTime, nullable=True)
