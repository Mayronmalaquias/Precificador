from sqlalchemy import Column, String, Text, Date, DateTime, Numeric, Integer
from sqlalchemy.sql import func
from app.models.base import Base


class Contrato(Base):
    """Espelha a aba 'Vendas' da planilha Controle de Contratos (146 colunas originais).

    Tabela larga de propósito: troca só a camada de leitura do ranking/meta_service,
    sem normalizar pessoas/comissões agora (fase 2, se necessário).
    """

    __tablename__ = "contratos"

    id_contrato = Column(String(50), primary_key=True)

    data_contrato = Column(Date, nullable=True)  # 'Data_Contrato'
    contrato = Column(Text, nullable=True)  # 'Contrato'
    valor_negocio = Column(Numeric(14, 2), nullable=True)  # 'Valor_Negocio'
    valor_comissao = Column(Numeric(14, 2), nullable=True)  # 'Valor_Comissao'
    valor_total_61 = Column(Numeric(14, 2), nullable=True)  # 'Valor_Total_61'
    nf_61_imoveis = Column(Numeric(14, 2), nullable=True)  # 'NF_61_ Imoveis'
    percentual_gerente_venda = Column(Numeric(14, 2), nullable=True)  # '%_Gerente_Venda'
    percentual_gerente_captacao = Column(Numeric(14, 2), nullable=True)  # '%_Gerente_Captacao'
    percentual_diretor = Column(Numeric(14, 2), nullable=True)  # '%_Diretor'
    percentual_corretor_venda_1 = Column(Numeric(14, 2), nullable=True)  # '%_Corretor_Venda_1'
    percentual_corretor_captacao_1 = Column(Numeric(14, 2), nullable=True)  # '%_Corretor_Captação_1'
    percentual_corretor_venda_2 = Column(Numeric(14, 2), nullable=True)  # '%_Corretor_Venda_2'
    percentual_corretor_captacao_2 = Column(Numeric(14, 2), nullable=True)  # '%_Corretor_Captação_2'
    valor_gerente_venda = Column(Numeric(14, 2), nullable=True)  # '$_Gerente_Venda'
    gerente_venda_nome = Column(Text, nullable=True)  # 'Gerente_Venda_Nome'
    valor_gerente_captacao = Column(Numeric(14, 2), nullable=True)  # '$_Gerente_Captacao'
    gerente_captacao_nome = Column(Text, nullable=True)  # 'Gerente_Captacao_Nome'
    valor_diretor = Column(Numeric(14, 2), nullable=True)  # '$_Diretor'
    diretor_nome = Column(Text, nullable=True)  # 'Diretor_Nome'
    valor_corretor_venda_1 = Column(Numeric(14, 2), nullable=True)  # '$_Corretor_Venda_1'
    corretor_venda_1_nome = Column(Text, nullable=True)  # 'Corretor_Venda_1_Nome'
    valor_corretor_venda_2 = Column(Numeric(14, 2), nullable=True)  # '$_Corretor_Venda_2'
    corretor_venda_2_nome = Column(Text, nullable=True)  # 'Corretor_Venda_2_Nome'
    valor_corretor_captador_1 = Column(Numeric(14, 2), nullable=True)  # '$_Corretor_Captador_1'
    corretor_captador_1_nome = Column(Text, nullable=True)  # 'Corretor_Captador_1_Nome'
    valor_corretor_captador_2 = Column(Numeric(14, 2), nullable=True)  # '$_Corretor_Captador_2'
    corretor_captador_2_nome = Column(Text, nullable=True)  # 'Corretor_Captador_2_Nome'
    data_assinatura = Column(Date, nullable=True)  # 'Data_Assinatura'
    data_escritura = Column(Date, nullable=True)  # 'Data_Escritura'
    data_quitacao = Column(Date, nullable=True)  # 'Data_Quitação'
    data_posse = Column(Date, nullable=True)  # 'Data_Posse'
    parcelas_comissao = Column(Text, nullable=True)  # 'Parcelas_Comissao'
    data_parcela1_comissao = Column(Date, nullable=True)  # 'Data_Parcela1_Comissão'
    correspondente_bancario = Column(Text, nullable=True)  # 'Correspondente_Bancario'
    data_envio_docs_financ = Column(Date, nullable=True)  # 'Data_Envio_Docs_Financ'
    data_vistoria = Column(Date, nullable=True)  # 'Data_Vistoria'
    num_protocolo_1 = Column(Text, nullable=True)  # 'Num_Protocolo_1'
    num_protocolo_2 = Column(Text, nullable=True)  # 'Num_Protocolo_2'
    num_protocolo_3 = Column(Text, nullable=True)  # 'Num_Protocolo_3'
    num_protocolo_4 = Column(Text, nullable=True)  # 'Num_Protocolo_4'
    descricao_trello = Column(Text, nullable=True)  # 'Descricao_Trello'
    anexo_contrato = Column(Text, nullable=True)  # 'Anexo_Contrato'
    anexo_docs_pessoais_compradores = Column(Text, nullable=True)  # 'Anexo_Docs_Pessoais_Compradores'
    anexo_docs_pessoais_vendedores = Column(Text, nullable=True)  # 'Anexo_Docs_Pessoais_Vendedores'
    anexo_onus = Column(Text, nullable=True)  # 'Anexo_Onus'
    anexo_cert_negativas_vendedores = Column(Text, nullable=True)  # 'Anexo_Cert_Negativas_Vendedores'
    anexo_cert_negativa_imovel = Column(Text, nullable=True)  # 'Anexo_Cert_Negativa_Imovel'
    anexo_ficha_cadastral = Column(Text, nullable=True)  # 'Anexo_Ficha_Cadastral'
    nome_comprador1 = Column(Text, nullable=True)  # 'Nome_Comprador1'
    email_telefone_cpf_comprador1 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador1'
    nome_comprador2 = Column(Text, nullable=True)  # 'Nome_Comprador2'
    email_telefone_cpf_comprador2 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador2'
    finciamento = Column(Text, nullable=True)  # 'Finciamento'
    imobiliaria_venda = Column(Text, nullable=True)  # 'Imobiliaria_Venda'
    imobiliaria_cap = Column(Text, nullable=True)  # 'Imobiliaria_Cap'
    liquido_61 = Column(Numeric(14, 2), nullable=True)  # 'Liquido_61'
    neg_gerado_v1 = Column(Numeric(14, 2), nullable=True)  # 'neg_Gerado_V1'
    neg_gerado_v2 = Column(Numeric(14, 2), nullable=True)  # 'neg_Gerado_V2'
    neg_gerado_c1 = Column(Numeric(14, 2), nullable=True)  # 'neg_Gerado_C1'
    neg_gerado_c2 = Column(Numeric(14, 2), nullable=True)  # 'neg_Gerado_C2'
    vgv_v1 = Column(Numeric(14, 2), nullable=True)  # 'vgv_v1'
    vgv_v2 = Column(Numeric(14, 2), nullable=True)  # 'vgv_v2'
    vgv_c1 = Column(Numeric(14, 2), nullable=True)  # 'vgv_c1'
    vgv_c2 = Column(Numeric(14, 2), nullable=True)  # 'vgv_c2'
    percentual_comissao_61 = Column(Numeric(14, 2), nullable=True)  # '%_comissao_61'
    nome_vendedor1 = Column(Text, nullable=True)  # 'Nome_Vendedor1'
    email_telefone_cpf_vendedor1 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Vendedor1'
    nome_vendedor2 = Column(Text, nullable=True)  # 'Nome_Vendedor2'
    email_telefone_cpf_vendedor2 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Vendedor2'
    valor_parcela_comissao_1 = Column(Numeric(14, 2), nullable=True)  # 'Valor_Parcela_Comissao_1'
    data_parcela2_comissao = Column(Date, nullable=True)  # 'Data_Parcela2_Comissão'
    data_parcela3_comissao = Column(Date, nullable=True)  # 'Data_Parcela3_Comissão'
    nome_vendedor3 = Column(Text, nullable=True)  # 'Nome_Vendedor3'
    email_telefone_cpf_vendedor3 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Vendedor3'
    nome_vendedor4 = Column(Text, nullable=True)  # 'Nome_Vendedor4'
    email_telefone_cpf_vendedor4 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Vendedor4'
    nome_vendedor5 = Column(Text, nullable=True)  # 'Nome_Vendedor5'
    email_telefone_cpf_vendedor5 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Vendedor5'
    nome_comprador3 = Column(Text, nullable=True)  # 'Nome_Comprador3'
    email_telefone_cpf_comprador3 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador3'
    nome_comprador4 = Column(Text, nullable=True)  # 'Nome_Comprador4'
    email_telefone_cpf_comprador4 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador4'
    nome_comprador5 = Column(Text, nullable=True)  # 'Nome_Comprador5'
    email_telefone_cpf_comprador5 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador5'
    nome_comprador6 = Column(Text, nullable=True)  # 'Nome_Comprador6'
    email_telefone_cpf_comprador6 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador6'
    nome_comprador7 = Column(Text, nullable=True)  # 'Nome_Comprador7'
    email_telefone_cpf_comprador7 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador7'
    nome_comprador8 = Column(Text, nullable=True)  # 'Nome_Comprador8'
    email_telefone_cpf_comprador8 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador8'
    valor_parcela_comissao_2 = Column(Numeric(14, 2), nullable=True)  # 'Valor_Parcela_Comissao_2'
    valor_parcela_comissao_3 = Column(Numeric(14, 2), nullable=True)  # 'Valor_Parcela_Comissao_3'
    data_parcela4_comissao = Column(Date, nullable=True)  # 'Data_Parcela4_Comissão'
    valor_parcela_comissao_4 = Column(Numeric(14, 2), nullable=True)  # 'Valor_Parcela_Comissao_4'
    data_parcela5_comissao = Column(Date, nullable=True)  # 'Data_Parcela5_Comissão'
    valor_parcela_comissao_5 = Column(Numeric(14, 2), nullable=True)  # 'Valor_Parcela_Comissao_5'
    origem_lead = Column(Text, nullable=True)  # 'Origem_Lead'
    bairro = Column(Text, nullable=True)  # 'Bairro'
    tipo = Column(Text, nullable=True)  # 'Tipo'
    nome_comprador9 = Column(Text, nullable=True)  # 'Nome_Comprador9'
    email_telefone_cpf_comprador9 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador9'
    nome_comprador10 = Column(Text, nullable=True)  # 'Nome_Comprador10'
    email_telefone_cpf_comprador10 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador10'
    nome_comprador11 = Column(Text, nullable=True)  # 'Nome_Comprador11'
    email_telefone_cpf_comprador11 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador11'
    nome_comprador12 = Column(Text, nullable=True)  # 'Nome_Comprador12'
    email_telefone_cpf_comprador12 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador12'
    nome_comprador13 = Column(Text, nullable=True)  # 'Nome_Comprador13'
    email_telefone_cpf_comprador13 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador13'
    nome_comprador14 = Column(Text, nullable=True)  # 'Nome_Comprador14'
    email_telefone_cpf_comprador14 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador14'
    nome_comprador15 = Column(Text, nullable=True)  # 'Nome_Comprador15'
    email_telefone_cpf_comprador15 = Column(Text, nullable=True)  # 'Email/telefone/CPF_Comprador15'
    nome_vendedor6 = Column(Text, nullable=True)  # ' Nome_Vendedor6'
    email_telefone_cpf_vendedor6 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor6'
    nome_vendedor7 = Column(Text, nullable=True)  # ' Nome_Vendedor7'
    email_telefone_cpf_vendedor7 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor7'
    nome_vendedor8 = Column(Text, nullable=True)  # ' Nome_Vendedor8'
    email_telefone_cpf_vendedor8 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor8'
    nome_vendedor9 = Column(Text, nullable=True)  # ' Nome_Vendedor9'
    email_telefone_cpf_vendedor9 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor9'
    nome_vendedor10 = Column(Text, nullable=True)  # ' Nome_Vendedor10'
    email_telefone_cpf_vendedor10 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor10'
    nome_vendedor11 = Column(Text, nullable=True)  # ' Nome_Vendedor11'
    email_telefone_cpf_vendedor11 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor11'
    nome_vendedor12 = Column(Text, nullable=True)  # ' Nome_Vendedor12'
    email_telefone_cpf_vendedor12 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor12'
    nome_vendedor13 = Column(Text, nullable=True)  # ' Nome_Vendedor13'
    email_telefone_cpf_vendedor13 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor13'
    nome_vendedor14 = Column(Text, nullable=True)  # ' Nome_Vendedor14'
    email_telefone_cpf_vendedor14 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor14'
    nome_vendedor15 = Column(Text, nullable=True)  # ' Nome_Vendedor15'
    email_telefone_cpf_vendedor15 = Column(Text, nullable=True)  # ' Email/telefone/CPF_Vendedor15'
    percentual_premiacao_jose = Column(Numeric(14, 2), nullable=True)  # 'Percentual_Premiacao_Jose'
    percentual_premiacao_marcelo = Column(Numeric(14, 2), nullable=True)  # 'Percentual_Premiacao_Marcelo'
    percentual_premiacao_luana = Column(Numeric(14, 2), nullable=True)  # 'Percentual_Premiacao_Luana'
    percentual_premiacao_thais = Column(Numeric(14, 2), nullable=True)  # 'Percentual_Premiacao_Thais'
    percentual_premiacao_diretor = Column(Numeric(14, 2), nullable=True)  # 'Percentual_Premiacao_Diretor'
    check_box_gvenda = Column(Text, nullable=True)  # 'Check_Box_GVenda'
    check_box_gcap = Column(Text, nullable=True)  # 'Check_Box_GCap'
    check_box_diretor = Column(Text, nullable=True)  # 'Check_Box_Diretor'
    codigo_imovel = Column(Text, nullable=True)  # 'Codigo_Imovel'
    data_pagamento_sinal = Column(Date, nullable=True)  # 'Data_Pagamento_Sinal'
    data_parcela_intermediaria = Column(Date, nullable=True)  # 'Data_Parcela_Intermediaria'
    link_honorario = Column(Text, nullable=True)  # 'Link_Honorario'

    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)


class DivisaoComissao(Base):
    """Espelha a aba 'Divisao_Comissao' (lida por ranking_service.load_divisoes)."""

    __tablename__ = "divisao_comissao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_contrato = Column(String(50), nullable=True)
    papel = Column(String(50), nullable=True)
    id_corretor = Column(String(50), nullable=True)
    nome_corretor = Column(Text, nullable=True)
    percentual = Column(Numeric(14, 4), nullable=True)
    comissao_valor = Column(Numeric(14, 2), nullable=True)
    observacao = Column(Text, nullable=True)
    atualizado_em = Column(DateTime, nullable=True)  # 'UpdatedAt'


# slug da coluna (nome de atributo no model) -> nome ORIGINAL da coluna na planilha Vendas.
# Usado por app/services/db_loaders.py pra devolver os dados do banco com os mesmos
# nomes de coluna que ranking_service.py/meta_service.py ja esperam via .get("NomeOriginal").
HEADER_POR_SLUG = {
    'data_contrato': 'Data_Contrato',
    'contrato': 'Contrato',
    'valor_negocio': 'Valor_Negocio',
    'valor_comissao': 'Valor_Comissao',
    'valor_total_61': 'Valor_Total_61',
    'nf_61_imoveis': 'NF_61_ Imoveis',
    'percentual_gerente_venda': '%_Gerente_Venda',
    'percentual_gerente_captacao': '%_Gerente_Captacao',
    'percentual_diretor': '%_Diretor',
    'percentual_corretor_venda_1': '%_Corretor_Venda_1',
    'percentual_corretor_captacao_1': '%_Corretor_Captação_1',
    'percentual_corretor_venda_2': '%_Corretor_Venda_2',
    'percentual_corretor_captacao_2': '%_Corretor_Captação_2',
    'valor_gerente_venda': '$_Gerente_Venda',
    'gerente_venda_nome': 'Gerente_Venda_Nome',
    'valor_gerente_captacao': '$_Gerente_Captacao',
    'gerente_captacao_nome': 'Gerente_Captacao_Nome',
    'valor_diretor': '$_Diretor',
    'diretor_nome': 'Diretor_Nome',
    'valor_corretor_venda_1': '$_Corretor_Venda_1',
    'corretor_venda_1_nome': 'Corretor_Venda_1_Nome',
    'valor_corretor_venda_2': '$_Corretor_Venda_2',
    'corretor_venda_2_nome': 'Corretor_Venda_2_Nome',
    'valor_corretor_captador_1': '$_Corretor_Captador_1',
    'corretor_captador_1_nome': 'Corretor_Captador_1_Nome',
    'valor_corretor_captador_2': '$_Corretor_Captador_2',
    'corretor_captador_2_nome': 'Corretor_Captador_2_Nome',
    'data_assinatura': 'Data_Assinatura',
    'data_escritura': 'Data_Escritura',
    'data_quitacao': 'Data_Quitação',
    'data_posse': 'Data_Posse',
    'parcelas_comissao': 'Parcelas_Comissao',
    'data_parcela1_comissao': 'Data_Parcela1_Comissão',
    'correspondente_bancario': 'Correspondente_Bancario',
    'data_envio_docs_financ': 'Data_Envio_Docs_Financ',
    'data_vistoria': 'Data_Vistoria',
    'num_protocolo_1': 'Num_Protocolo_1',
    'num_protocolo_2': 'Num_Protocolo_2',
    'num_protocolo_3': 'Num_Protocolo_3',
    'num_protocolo_4': 'Num_Protocolo_4',
    'descricao_trello': 'Descricao_Trello',
    'anexo_contrato': 'Anexo_Contrato',
    'anexo_docs_pessoais_compradores': 'Anexo_Docs_Pessoais_Compradores',
    'anexo_docs_pessoais_vendedores': 'Anexo_Docs_Pessoais_Vendedores',
    'anexo_onus': 'Anexo_Onus',
    'anexo_cert_negativas_vendedores': 'Anexo_Cert_Negativas_Vendedores',
    'anexo_cert_negativa_imovel': 'Anexo_Cert_Negativa_Imovel',
    'anexo_ficha_cadastral': 'Anexo_Ficha_Cadastral',
    'nome_comprador1': 'Nome_Comprador1',
    'email_telefone_cpf_comprador1': 'Email/telefone/CPF_Comprador1',
    'nome_comprador2': 'Nome_Comprador2',
    'email_telefone_cpf_comprador2': 'Email/telefone/CPF_Comprador2',
    'finciamento': 'Finciamento',
    'imobiliaria_venda': 'Imobiliaria_Venda',
    'imobiliaria_cap': 'Imobiliaria_Cap',
    'liquido_61': 'Liquido_61',
    'neg_gerado_v1': 'neg_Gerado_V1',
    'neg_gerado_v2': 'neg_Gerado_V2',
    'neg_gerado_c1': 'neg_Gerado_C1',
    'neg_gerado_c2': 'neg_Gerado_C2',
    'vgv_v1': 'vgv_v1',
    'vgv_v2': 'vgv_v2',
    'vgv_c1': 'vgv_c1',
    'vgv_c2': 'vgv_c2',
    'percentual_comissao_61': '%_comissao_61',
    'nome_vendedor1': 'Nome_Vendedor1',
    'email_telefone_cpf_vendedor1': 'Email/telefone/CPF_Vendedor1',
    'nome_vendedor2': 'Nome_Vendedor2',
    'email_telefone_cpf_vendedor2': 'Email/telefone/CPF_Vendedor2',
    'valor_parcela_comissao_1': 'Valor_Parcela_Comissao_1',
    'data_parcela2_comissao': 'Data_Parcela2_Comissão',
    'data_parcela3_comissao': 'Data_Parcela3_Comissão',
    'nome_vendedor3': 'Nome_Vendedor3',
    'email_telefone_cpf_vendedor3': 'Email/telefone/CPF_Vendedor3',
    'nome_vendedor4': 'Nome_Vendedor4',
    'email_telefone_cpf_vendedor4': 'Email/telefone/CPF_Vendedor4',
    'nome_vendedor5': 'Nome_Vendedor5',
    'email_telefone_cpf_vendedor5': 'Email/telefone/CPF_Vendedor5',
    'nome_comprador3': 'Nome_Comprador3',
    'email_telefone_cpf_comprador3': 'Email/telefone/CPF_Comprador3',
    'nome_comprador4': 'Nome_Comprador4',
    'email_telefone_cpf_comprador4': 'Email/telefone/CPF_Comprador4',
    'nome_comprador5': 'Nome_Comprador5',
    'email_telefone_cpf_comprador5': 'Email/telefone/CPF_Comprador5',
    'nome_comprador6': 'Nome_Comprador6',
    'email_telefone_cpf_comprador6': 'Email/telefone/CPF_Comprador6',
    'nome_comprador7': 'Nome_Comprador7',
    'email_telefone_cpf_comprador7': 'Email/telefone/CPF_Comprador7',
    'nome_comprador8': 'Nome_Comprador8',
    'email_telefone_cpf_comprador8': 'Email/telefone/CPF_Comprador8',
    'valor_parcela_comissao_2': 'Valor_Parcela_Comissao_2',
    'valor_parcela_comissao_3': 'Valor_Parcela_Comissao_3',
    'data_parcela4_comissao': 'Data_Parcela4_Comissão',
    'valor_parcela_comissao_4': 'Valor_Parcela_Comissao_4',
    'data_parcela5_comissao': 'Data_Parcela5_Comissão',
    'valor_parcela_comissao_5': 'Valor_Parcela_Comissao_5',
    'origem_lead': 'Origem_Lead',
    'bairro': 'Bairro',
    'tipo': 'Tipo',
    'nome_comprador9': 'Nome_Comprador9',
    'email_telefone_cpf_comprador9': 'Email/telefone/CPF_Comprador9',
    'nome_comprador10': 'Nome_Comprador10',
    'email_telefone_cpf_comprador10': 'Email/telefone/CPF_Comprador10',
    'nome_comprador11': 'Nome_Comprador11',
    'email_telefone_cpf_comprador11': 'Email/telefone/CPF_Comprador11',
    'nome_comprador12': 'Nome_Comprador12',
    'email_telefone_cpf_comprador12': 'Email/telefone/CPF_Comprador12',
    'nome_comprador13': 'Nome_Comprador13',
    'email_telefone_cpf_comprador13': 'Email/telefone/CPF_Comprador13',
    'nome_comprador14': 'Nome_Comprador14',
    'email_telefone_cpf_comprador14': 'Email/telefone/CPF_Comprador14',
    'nome_comprador15': 'Nome_Comprador15',
    'email_telefone_cpf_comprador15': 'Email/telefone/CPF_Comprador15',
    'nome_vendedor6': 'Nome_Vendedor6',
    'email_telefone_cpf_vendedor6': 'Email/telefone/CPF_Vendedor6',
    'nome_vendedor7': 'Nome_Vendedor7',
    'email_telefone_cpf_vendedor7': 'Email/telefone/CPF_Vendedor7',
    'nome_vendedor8': 'Nome_Vendedor8',
    'email_telefone_cpf_vendedor8': 'Email/telefone/CPF_Vendedor8',
    'nome_vendedor9': 'Nome_Vendedor9',
    'email_telefone_cpf_vendedor9': 'Email/telefone/CPF_Vendedor9',
    'nome_vendedor10': 'Nome_Vendedor10',
    'email_telefone_cpf_vendedor10': 'Email/telefone/CPF_Vendedor10',
    'nome_vendedor11': 'Nome_Vendedor11',
    'email_telefone_cpf_vendedor11': 'Email/telefone/CPF_Vendedor11',
    'nome_vendedor12': 'Nome_Vendedor12',
    'email_telefone_cpf_vendedor12': 'Email/telefone/CPF_Vendedor12',
    'nome_vendedor13': 'Nome_Vendedor13',
    'email_telefone_cpf_vendedor13': 'Email/telefone/CPF_Vendedor13',
    'nome_vendedor14': 'Nome_Vendedor14',
    'email_telefone_cpf_vendedor14': 'Email/telefone/CPF_Vendedor14',
    'nome_vendedor15': 'Nome_Vendedor15',
    'email_telefone_cpf_vendedor15': 'Email/telefone/CPF_Vendedor15',
    'percentual_premiacao_jose': 'Percentual_Premiacao_Jose',
    'percentual_premiacao_marcelo': 'Percentual_Premiacao_Marcelo',
    'percentual_premiacao_luana': 'Percentual_Premiacao_Luana',
    'percentual_premiacao_thais': 'Percentual_Premiacao_Thais',
    'percentual_premiacao_diretor': 'Percentual_Premiacao_Diretor',
    'check_box_gvenda': 'Check_Box_GVenda',
    'check_box_gcap': 'Check_Box_GCap',
    'check_box_diretor': 'Check_Box_Diretor',
    'codigo_imovel': 'Codigo_Imovel',
    'data_pagamento_sinal': 'Data_Pagamento_Sinal',
    'data_parcela_intermediaria': 'Data_Parcela_Intermediaria',
    'link_honorario': 'Link_Honorario',
}
