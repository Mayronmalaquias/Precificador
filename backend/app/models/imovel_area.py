"""Area do imovel por codigo do Imoview.

Existe porque a API do Imoview so devolve imovel ATIVO: assim que o imovel vende,
ele some de `RetornarImoveisDisponiveis` e de `RetornarImoveis` — e e justamente ai
que a gente precisa da metragem, p/ calcular o valor do m2 do contrato fechado.

O job `sync_areas_imoview.py` varre o catalogo periodicamente e grava aqui, entao a
area fica registrada ANTES da venda e sobrevive ao imovel sair do ar.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, func

from sqlalchemy.dialects.postgresql import JSONB

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
    # Documentacao: o Imoview tem `matriculacartorio`/`indiceiptu`, mas a operacao nao
    # preenche (3% e 0% da amostra) — o dado ia so p/ o Sheets e o Trello no lancamento.
    # Aqui ele fica consultavel e editavel pela Consulta de Imoveis.
    matricula = Column(String(120), nullable=True)
    inscricao_iptu = Column(String(120), nullable=True)
    # `datahoracadastro` do Imoview: e por ele que a Consulta ordena (lancamento recente
    # primeiro). Codigo cresce junto, mas a data e o criterio explicito.
    cadastrado_em = Column(DateTime, nullable=True, index=True)
    # Venda | Aluguel. O estoque comercial e so venda — locacao e outra operacao.
    finalidade = Column(String(30), nullable=True, index=True)
    # `datahoraultimasituacao`: quando a situacao mudou pela ultima vez. E o que define
    # SAIDA de estoque (mudou p/ algo que nao e disponivel nem moderacao, no periodo).
    situacao_em = Column(DateTime, nullable=True, index=True)
    # Cartao do Trello criado no lancamento. Guardado p/ conseguir ATUALIZAR o cartao
    # quando a matricula/inscricao for corrigida na Consulta de Imoveis.
    trello_card_id = Column(String(40), nullable=True)
    trello_card_url = Column(Text, nullable=True)
    # ── captadores, vindos da API com `exibircaptadores=true` ─────────────────
    # A flag e o que faz `captadores` vir preenchido; sem ela a API devolve `[]`, e era
    # por isso que se achava que o captador so existia na planilha exportada a mao.
    # Cobertura medida em 27/08/2026: 100% (160 de 160 na amostra).
    #
    # `percentual` e o rateio oficial entre co-captadores — e NAO e sempre meio a meio:
    # ha imovel com principal em 0% e o outro em 100%. Guardar o numero evita supor `1/n`.
    captador1 = Column(Text, nullable=True, index=True)
    captador2 = Column(Text, nullable=True)
    captador3 = Column(Text, nullable=True)
    percentual1 = Column(Numeric(5, 2), nullable=True)
    percentual2 = Column(Numeric(5, 2), nullable=True)
    percentual3 = Column(Numeric(5, 2), nullable=True)
    captador_principal = Column(Text, nullable=True)

    # ── publicacao nos portais (RetornarPortaisImoveis) ───────────────────────
    # Agregado, nao uma linha por portal: a tela pergunta "quantos estao publicados e com
    # que destaque". `destaque_nivel` guarda o MAIOR nivel ativo — imovel Simples em
    # quatro portais e Super Destaque num quinto esta, na pratica, em Super Destaque.
    portais_ativos = Column(Integer, nullable=True, index=True)
    portais_total = Column(Integer, nullable=True)
    destaque_nivel = Column(Integer, nullable=True, index=True)
    destaque_portal = Column(Text, nullable=True)
    # Site proprio nao e portal: vem em campos separados do imovel, e `codigoportal=0`
    # devolve `portais` vazio de proposito.
    exibir_meu_site = Column(Boolean, nullable=True)
    destaque_site = Column(Text, nullable=True)
    portais_em = Column(DateTime, nullable=True)

    # ── fotos e anexos (RetornarImoveis com `exibiranexos=true`) ──────────────
    # `anexos_nomes` guarda so nome e visibilidade. A URL do Imoview abre sem
    # autenticacao — nao grava-la e o que impede a tela de redistribuir certidao e ficha
    # cadastral do proprietario por engano.
    qtd_fotos = Column(Integer, nullable=True, index=True)
    qtd_anexos = Column(Integer, nullable=True, index=True)
    anexos_nomes = Column(JSONB, nullable=True)
    tem_video = Column(Boolean, nullable=True)
    midia_em = Column(DateTime, nullable=True)

    origem = Column(String(30), nullable=True, default="imoview")
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
