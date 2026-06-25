from sqlalchemy import Column, Integer, Text, Date, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class VendaLegado(Base):
    """Espelha Fato_Venda (Base Inteligencia, 59 colunas, dados desde 2015).
    Historico anterior a contratos/Vendas - schema e IDs diferentes, sem
    relacao direta com a tabela contratos. Tudo Text exceto datas/foco porque
    a planilha mistura texto e numero na mesma coluna em linhas diferentes
    (preservar exatamente como esta, sem arriscar perda/erro de conversao).
    """

    __tablename__ = "vendas_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    san = Column(Text, nullable=True)  # 'SAN'
    data_captacao = Column(Date, nullable=True)  # 'Data captação'
    data_venda = Column(Date, nullable=True)  # 'Data venda'
    tempo_de_venda = Column(Text, nullable=True)  # 'Tempo de venda'
    bairro = Column(Text, nullable=True)  # 'Bairro'
    quadra = Column(Text, nullable=True)  # 'Quadra'
    tipo = Column(Text, nullable=True)  # 'Tipo'
    foco = Column(Boolean, nullable=True)  # 'Foco'
    valor_do_negocio = Column(Text, nullable=True)  # 'Valor do negócio'
    valor_comissao = Column(Text, nullable=True)  # 'Valor comissão'
    percentual_comissao = Column(Text, nullable=True)  # '% comissão'
    valor_total_61 = Column(Text, nullable=True)  # 'Valor total 61'
    participacao61 = Column(Text, nullable=True)  # 'Participacao61'
    correcao61 = Column(Text, nullable=True)  # 'correção61'
    correcaovgv = Column(Text, nullable=True)  # 'correçãoVGV'
    nf_61_imovies = Column(Text, nullable=True)  # 'NF 61 imóvies'
    liquido_61 = Column(Text, nullable=True)  # 'Líquido 61'
    correcaovendedor1 = Column(Text, nullable=True)  # 'correçãoVendedor1'
    v1 = Column(Text, nullable=True)  # 'V1'
    q1 = Column(Text, nullable=True)  # 'Q1'
    vendedor_1 = Column(Text, nullable=True)  # 'vendedor 1'
    imobiliaria_vendedor_1 = Column(Text, nullable=True)  # 'Imobiliária'
    percentual_vendedor_1 = Column(Text, nullable=True)  # '% vendedor 1'
    valor_vendedor_1 = Column(Text, nullable=True)  # '$ vendedor 1'
    gerente_de_venda1 = Column(Text, nullable=True)  # 'Gerente de venda1'
    percentual_gerente_venda_1 = Column(Text, nullable=True)  # '% gerente venda 1'
    valor_gerente_venda_1 = Column(Text, nullable=True)  # '$ gerente venda 1'
    correcaovendedor2 = Column(Text, nullable=True)  # 'correçãoVendedor2'
    v2 = Column(Text, nullable=True)  # 'V2'
    q2 = Column(Text, nullable=True)  # 'Q2'
    vendedor_2 = Column(Text, nullable=True)  # 'Vendedor 2'
    percentual_vendedor_2 = Column(Text, nullable=True)  # '% vendedor 2'
    valor_vendedor_2 = Column(Text, nullable=True)  # '$ Vendedor 2'
    gerente_de_venda2 = Column(Text, nullable=True)  # 'Gerente de venda2'
    percentual_gerente_venda_2 = Column(Text, nullable=True)  # '% gerente venda 2'
    valor_gerente_venda_2 = Column(Text, nullable=True)  # '$ gerente venda 2'
    correcaocap1 = Column(Text, nullable=True)  # 'CorreçãoCap1'
    v3 = Column(Text, nullable=True)  # 'V3'
    q3 = Column(Text, nullable=True)  # 'Q3'
    captador_1 = Column(Text, nullable=True)  # 'Captador 1 '
    imobiliaria_captador_1 = Column(Text, nullable=True)  # 'Imobilíaria'
    percentual_captador_1 = Column(Text, nullable=True)  # '% captador 1'
    valor_captador_1 = Column(Text, nullable=True)  # '$ captador 1'
    gerente_de_captacao_1 = Column(Text, nullable=True)  # 'Gerente de captação 1'
    percentualgerente_de_captacao_1 = Column(Text, nullable=True)  # '%gerente de captação 1'
    valor_gerente_de_captacao_1 = Column(Text, nullable=True)  # '$ gerente de captação 1'
    correccaocap2 = Column(Text, nullable=True)  # 'CorreççaoCap2'
    v4 = Column(Text, nullable=True)  # 'V4'
    q4 = Column(Text, nullable=True)  # 'Q4'
    captador_2 = Column(Text, nullable=True)  # 'Captador 2'
    percentual_captador_2 = Column(Text, nullable=True)  # '% Captador 2'
    valor_captador_2 = Column(Text, nullable=True)  # '$ Captador 2'
    gerente_de_captacao_2 = Column(Text, nullable=True)  # 'Gerente de captação 2'
    percentual_gerente_de_captacao_2 = Column(Text, nullable=True)  # '% Gerente de captação 2'
    valor_gerente_de_captacao_2 = Column(Text, nullable=True)  # '$ Gerente de captação 2'
    origemleadvenda = Column(Text, nullable=True)  # 'OrigemLeadVenda'
    tempo_em_dias = Column(Text, nullable=True)  # 'Tempo em dias'
    entradalead = Column(Date, nullable=True)  # 'EntradaLead'
    idcontrato = Column(Text, nullable=True)  # 'IdContrato'

    created_at = Column(DateTime, server_default=func.now(), nullable=True)


# slug (atributo do model) -> nome ORIGINAL da coluna na planilha Fato_Venda.
HEADER_POR_SLUG = {
    'san': 'SAN',
    'data_captacao': 'Data captação',
    'data_venda': 'Data venda',
    'tempo_de_venda': 'Tempo de venda',
    'bairro': 'Bairro',
    'quadra': 'Quadra',
    'tipo': 'Tipo',
    'foco': 'Foco',
    'valor_do_negocio': 'Valor do negócio',
    'valor_comissao': 'Valor comissão',
    'percentual_comissao': '% comissão',
    'valor_total_61': 'Valor total 61',
    'participacao61': 'Participacao61',
    'correcao61': 'correção61',
    'correcaovgv': 'correçãoVGV',
    'nf_61_imovies': 'NF 61 imóvies',
    'liquido_61': 'Líquido 61',
    'correcaovendedor1': 'correçãoVendedor1',
    'v1': 'V1',
    'q1': 'Q1',
    'vendedor_1': 'vendedor 1',
    'imobiliaria_vendedor_1': 'Imobiliária',
    'percentual_vendedor_1': '% vendedor 1',
    'valor_vendedor_1': '$ vendedor 1',
    'gerente_de_venda1': 'Gerente de venda1',
    'percentual_gerente_venda_1': '% gerente venda 1',
    'valor_gerente_venda_1': '$ gerente venda 1',
    'correcaovendedor2': 'correçãoVendedor2',
    'v2': 'V2',
    'q2': 'Q2',
    'vendedor_2': 'Vendedor 2',
    'percentual_vendedor_2': '% vendedor 2',
    'valor_vendedor_2': '$ Vendedor 2',
    'gerente_de_venda2': 'Gerente de venda2',
    'percentual_gerente_venda_2': '% gerente venda 2',
    'valor_gerente_venda_2': '$ gerente venda 2',
    'correcaocap1': 'CorreçãoCap1',
    'v3': 'V3',
    'q3': 'Q3',
    'captador_1': 'Captador 1 ',
    'imobiliaria_captador_1': 'Imobilíaria',
    'percentual_captador_1': '% captador 1',
    'valor_captador_1': '$ captador 1',
    'gerente_de_captacao_1': 'Gerente de captação 1',
    'percentualgerente_de_captacao_1': '%gerente de captação 1',
    'valor_gerente_de_captacao_1': '$ gerente de captação 1',
    'correccaocap2': 'CorreççaoCap2',
    'v4': 'V4',
    'q4': 'Q4',
    'captador_2': 'Captador 2',
    'percentual_captador_2': '% Captador 2',
    'valor_captador_2': '$ Captador 2',
    'gerente_de_captacao_2': 'Gerente de captação 2',
    'percentual_gerente_de_captacao_2': '% Gerente de captação 2',
    'valor_gerente_de_captacao_2': '$ Gerente de captação 2',
    'origemleadvenda': 'OrigemLeadVenda',
    'tempo_em_dias': 'Tempo em dias',
    'entradalead': 'EntradaLead',
    'idcontrato': 'IdContrato',
}
