"""Consulta consolidada de imóvel: Imoview + bases internas.

Tela de apoio para estagiário/assistente: acha o imóvel por código ou endereço e mostra,
numa página só, o que o CRM sabe e o que a inteligência sabe.

Divisão que a tela precisa respeitar:
- **Imoview** (`origem: imoview`) — só leitura. Editar, só no CRM.
- **Interno** (`origem: banco`) — o que nasce aqui: foco, captadores, estoque, mídia,
  visitas, propostas, contrato. O foco é editável (ver `atualizar_interno`).

A busca usa o cache `imovel_area` (alimentado por `sync_areas_imoview.py`) porque a API
do Imoview **não filtra por código** — só por endereço, e paginado de 20 em 20.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import BigInteger, and_, case, func, or_, text

from app.database import SessionLocal
from app.extensions import cache
from app.models.contrato import Contrato
from app.models.dfimoveis_acesso import DfImoveisAcesso
from app.models.fato_bases import FatoCaptacao, FatoEstoque, FatoSaida
from app.models.imovel_area import ImovelArea
from app.models.legado_diversos import ImovelLegado
from app.models.proposta_efetiva import PropostaEfetiva
from app.models.usuarios import Usuarios
from app.models.visita import Visita

PERFIS_COM_ACESSO = {"assistente", "gerente", "administrador", "diretor", "administrativo"}

# Quanto tempo uma captação sem imóvel no catálogo ainda conta como "recém-lançada".
# A varredura roda 1x/dia; 7 dias cobre feriado e cron que falhou sem trazer lixo antigo.
DIAS_LANCAMENTO_RECENTE = 7


class ConsultaErro(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _texto(valor):
    return str(valor or "").strip()


def _codigo_limpo(valor):
    """"10.961,00" -> "10961". O código chega formatado em `contratos`."""
    texto = _texto(valor)
    if not texto:
        return ""
    return "".join(ch for ch in texto.split(",")[0] if ch.isdigit())


def _float(valor):
    return float(valor) if valor is not None else None


@cache.memoize(timeout=300)
def _perfil_do_usuario(solicitante_id):
    """Cadastro do solicitante, cacheado 5 min — é lido em toda requisição da tela."""
    session = SessionLocal()
    try:
        user = session.query(Usuarios).filter(
            Usuarios.id_usuarios == _texto(solicitante_id), Usuarios.ativo.is_(True)
        ).first()
        if not user:
            return None
        return {
            "id_usuarios": user.id_usuarios,
            "nome": user.nome or user.username,
            "permissao": _texto(user.permissao).lower(),
            "team": _texto(user.team),
        }
    finally:
        session.close()


def checar_acesso(solicitante_id):
    """Consulta é liberada p/ assistente (estagiário) e gestão. Corretor não entra."""
    perfil = _perfil_do_usuario(solicitante_id)
    if not perfil:
        raise ConsultaErro("Sem permissão para consultar imóveis", 403)
    if perfil["permissao"] in PERFIS_COM_ACESSO or perfil["team"].lower() == "administrativo":
        return perfil
    raise ConsultaErro("Sem permissão para consultar imóveis", 403)


def _codigos_da_equipe(session, perfil):
    """Imoveis relacionados a equipe do gerente pela captacao operacional.

    `fato_captacao.id_gerente` e a ligacao principal. Os captadores entram como
    fallback para linhas legadas cujo gerente veio vazio; aceitamos id, nome e username
    porque as cargas antigas nao usaram uma representacao unica.
    """
    if perfil.get("permissao") != "gerente":
        return None
    team = _texto(perfil.get("team"))
    if not team:
        return set()
    membros = session.query(Usuarios).filter(Usuarios.team == team).all()
    chaves = {
        _texto(valor).lower()
        for usuario in membros
        for valor in (usuario.id_usuarios, usuario.nome, usuario.username)
        if _texto(valor)
    }
    condicoes = [func.lower(FatoCaptacao.id_gerente) == team.lower()]
    if chaves:
        for coluna in (FatoCaptacao.captador1, FatoCaptacao.captador2, FatoCaptacao.captador3):
            condicoes.append(func.lower(coluna).in_(chaves))
    rows = session.query(FatoCaptacao.codigo_imovel).filter(
        FatoCaptacao.codigo_imovel.isnot(None), or_(*condicoes)
    ).distinct().all()
    codigos = set()
    for (codigo,) in rows:
        bruto = _texto(codigo)
        if bruto:
            codigos.add(bruto)
            codigos.add(_codigo_limpo(bruto) or bruto)
    return codigos


def _restringir_catalogo_ao_gerente(query, codigos_equipe):
    if codigos_equipe is None:
        return query
    if not codigos_equipe:
        return query.filter(False)
    return query.filter(ImovelArea.codigo.in_(codigos_equipe))


def _validar_imovel_no_escopo(codigo, codigos_equipe):
    if codigos_equipe is not None and codigo not in codigos_equipe:
        raise ConsultaErro("Esse imóvel pertence a outra equipe", 403)


# Chips da tela -> o que filtrar em `imovel_area.situacao`.
FILTROS_SITUACAO = {
    "disponivel": ["Vago/Disponível", "Vago/Disponivel"],
    "vendido": ["Vendido"],
    "desativado": ["Desativado"],
    "moderacao": ["Em moderação", "Em moderacao"],
    "reforma": ["Em reforma"],
    # "Saiu do estoque" = deixou de estar disponivel. Nao e uma situacao do Imoview, e a
    # uniao das que significam saida — e o mesmo criterio da Visao do Diretor, que ja
    # tinha errado por contar so parte delas.
    "saiu": ["Vendido", "Desativado", "Em reforma"],
    "todos": None,
}

# Filtros que trabalham sobre o catalogo. Quando qualquer um esta ligado, a injecao de
# lancamentos recentes (`_do_lancamento_fora_do_cache`) e desligada: aquela lista vem de
# `fato_captacao`, que nao tem area, situacao nem data de mudanca, entao entraria
# furando o filtro que o usuario acabou de pedir.
FILTROS_DE_CATALOGO = (
    "bairro", "tipo", "finalidade", "foco", "valor_min", "valor_max",
    "area_min", "area_max", "quartos_min", "vagas_min",
    "mudou_de", "mudou_ate", "captado_de", "captado_ate",
    "visitas", "visita_de", "visita_ate",
)


# Pares acento -> sem acento para o `translate` do Postgres. `unaccent` seria mais
# limpo, mas e extensao e pode nao estar instalada no RDS; `translate` e builtin.
_COM_ACENTO = "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ"
_SEM_ACENTO = "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC"


def _sem_acento(coluna):
    return func.lower(func.translate(coluna, _COM_ACENTO, _SEM_ACENTO))


def _contem_sem_acento(coluna, termo: str):
    """Busca parcial que ignora acento E caixa.

    `ILIKE` sozinho ignora so a caixa: com ele, procurar "aguas" nao achava "Águas
    Claras" — e ninguem digita o acento na busca. O indice nao e usado nessa comparacao,
    mas o catalogo tem alguns milhares de linhas e a varredura e barata.
    """
    alvo = termo.strip().lower()
    for com, sem in zip(_COM_ACENTO, _SEM_ACENTO):
        alvo = alvo.replace(com, sem)
    return _sem_acento(coluna).like(f"%{alvo}%")


def _num_filtro(valor):
    """Numero vindo da query string. Vazio ou lixo viram None, nao excecao.

    Separado de `_float`, que converte valor JA validado do banco: la, um valor que nao
    e numero e sintoma de dado corrompido e deve estourar em vez de virar None em
    silencio. Aqui a entrada e do usuario e campo em branco e o caso normal.
    """
    texto = _texto(valor)
    if not texto:
        return None
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def _data_ou_none(valor):
    texto = _texto(valor)[:10]
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def _valor_json(valor):
    """Converte tipos nativos do banco em valores aceitos pelo JSON da API."""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {chave: _valor_json(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_valor_json(item) for item in valor]
    if isinstance(valor, tuple):
        return [_valor_json(item) for item in valor]
    return valor


def _codigos_marcados(session, coluna):
    """Subconsulta com os codigos que tem a marca de foco pedida.

    Fica em SQL em vez de virar `set` em Python: `imovel_legado` e a tabela legada
    inteira, e carrega-la para descobrir quatro contagens custava 13s na primeira
    chamada. Como subconsulta o Postgres resolve junto com o filtro do catalogo.
    """
    return session.query(ImovelLegado.codigo).filter(coluna.is_(True)).scalar_subquery()


def _filtro_de_foco(session, foco: str):
    """Condicao SQL para o recorte de foco, ou None se o valor nao for reconhecido."""
    pp = _codigos_marcados(session, ImovelLegado.foco_pp)
    ac = _codigos_marcados(session, ImovelLegado.foco_ac)
    if foco == "pp":
        return ImovelArea.codigo.in_(pp)
    if foco == "ac":
        return ImovelArea.codigo.in_(ac)
    if foco == "pp_ac":
        return and_(ImovelArea.codigo.in_(pp), ImovelArea.codigo.in_(ac))
    if foco == "qualquer":
        return or_(ImovelArea.codigo.in_(pp), ImovelArea.codigo.in_(ac))
    if foco == "nao_foco":
        # Ausencia de marca: nao esta em nenhuma das duas listas.
        return and_(ImovelArea.codigo.notin_(pp), ImovelArea.codigo.notin_(ac))
    return None


def _aplicar_recortes(session, query, termo, situacao, f):
    """Aplica busca livre, situação e os filtros da Gestão de Imóveis.

    Extraído de `buscar` para a listagem e os gráficos partirem do MESMO recorte. Com o
    filtro duplicado nos dois lugares, o primeiro filtro novo que alguém acrescentasse
    num só faria a tabela mostrar 20 imóveis e o gráfico contar 300 — e a divergência só
    apareceria quando alguém somasse as barras.

    Devolve `None` quando o recorte é vazio por construção (foco pedido que ninguém tem),
    para o chamador responder lista vazia sem ir ao banco de novo.
    """
    if termo:
        alvo = f"%{termo}%"
        query = query.filter(or_(
            ImovelArea.codigo.ilike(alvo),
            ImovelArea.endereco.ilike(alvo),
            ImovelArea.bairro.ilike(alvo),
            ImovelArea.tipo.ilike(alvo),
        ))

    rotulos = FILTROS_SITUACAO.get(str(situacao or "disponivel").lower(),
                                   FILTROS_SITUACAO["disponivel"])
    if rotulos:
        query = query.filter(or_(*[ImovelArea.situacao.ilike(r) for r in rotulos]))

    if f.get("bairro"):
        query = query.filter(_contem_sem_acento(ImovelArea.bairro, f["bairro"]))
    if f.get("tipo"):
        query = query.filter(_contem_sem_acento(ImovelArea.tipo, f["tipo"]))
    if f.get("finalidade"):
        query = query.filter(_contem_sem_acento(ImovelArea.finalidade, f["finalidade"]))

    for chave, coluna, comparador in (
        ("valor_min", ImovelArea.valor, "ge"), ("valor_max", ImovelArea.valor, "le"),
        ("area_min", ImovelArea.area, "ge"), ("area_max", ImovelArea.area, "le"),
        ("quartos_min", ImovelArea.quartos, "ge"), ("vagas_min", ImovelArea.vagas, "ge"),
    ):
        valor = _num_filtro(f.get(chave))
        if valor is not None:
            query = query.filter(coluna >= valor if comparador == "ge" else coluna <= valor)

    # Janela da última mudança de situação: é o que responde "vendido no período".
    d_de, d_ate = _data_ou_none(f.get("mudou_de")), _data_ou_none(f.get("mudou_ate"))
    if d_de:
        query = query.filter(ImovelArea.situacao_em >= d_de)
    if d_ate:
        query = query.filter(ImovelArea.situacao_em < d_ate + timedelta(days=1))

    c_de, c_ate = _data_ou_none(f.get("captado_de")), _data_ou_none(f.get("captado_ate"))
    if c_de:
        query = query.filter(ImovelArea.cadastrado_em >= c_de)
    if c_ate:
        query = query.filter(ImovelArea.cadastrado_em < c_ate + timedelta(days=1))

    # Visitas: recorta pelos imoveis que a operacao levou cliente para ver. Sao 406 dos
    # 12.450 do catalogo (3%) — e justamente por ser pouco que interessa isolar.
    #
    # Subconsulta, nao join: um imovel com 12 visitas apareceria 12 vezes na listagem e o
    # total mentiria.
    visitas = _texto(f.get("visitas")).lower()
    if visitas in {"com", "sem"}:
        visitados = session.query(Visita.id_imovel).filter(Visita.id_imovel.isnot(None))
        # A janela vale para o filtro "com": "visitado em agosto" e uma pergunta; "nunca
        # visitado" nao tem janela — ou tem visita ou nao tem.
        v_de, v_ate = _data_ou_none(f.get("visita_de")), _data_ou_none(f.get("visita_ate"))
        if visitas == "com":
            if v_de:
                visitados = visitados.filter(Visita.data_visita >= v_de)
            if v_ate:
                visitados = visitados.filter(Visita.data_visita <= v_ate)
            query = query.filter(ImovelArea.codigo.in_(visitados.scalar_subquery()))
        else:
            query = query.filter(ImovelArea.codigo.notin_(visitados.scalar_subquery()))

    if f.get("foco"):
        condicao = _filtro_de_foco(session, f["foco"].lower())
        if condicao is not None:
            query = query.filter(condicao)

    return query


def buscar(solicitante_id, termo="", page=1, per_page=24, situacao="disponivel",
           apenas_meus=False, filtros=None):
    """Lista os imóveis do catálogo com os recortes da Gestão de Imóveis.

    O padrão é `disponivel` porque é o dia a dia de quem consulta; as demais situações e
    `todos` existem p/ conferência de histórico (o cache guarda todas).

    **"Vendidos no período"** é a combinação de `situacao=vendido` com a janela
    `mudou_de`/`mudou_ate`, que filtra `situacao_em` — o `datahoraultimasituacao` do
    Imoview. Não existe "data da venda" na API; o que existe é quando a situação mudou
    pela última vez. Se o imóvel mudar de situação de novo depois, a data anterior é
    perdida — quem guarda a transição é `imovel_situacao_evento`, alimentado pelo cron.

    `apenas_meus` filtra pelos imóveis cuja CAPTAÇÃO foi lançada pelo solicitante — é o
    "o que eu lancei" do estagiário. A marca fica em `fato_captacao.criado_por`, gravada
    no lançamento; a carga legada tem `criado_por='import'` e nunca casa com ninguém.
    """
    perfil = checar_acesso(solicitante_id)
    termo = _texto(termo)
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 24), 1), 100)
    f = {k: _texto(v) for k, v in (filtros or {}).items()}
    tem_filtro_extra = any(f.get(k) for k in FILTROS_DE_CATALOGO)

    session = SessionLocal()
    try:
        codigos_equipe = _codigos_da_equipe(session, perfil)
        query = _restringir_catalogo_ao_gerente(session.query(ImovelArea), codigos_equipe)

        codigos_meus = None
        if apenas_meus:
            codigos_meus = _codigos_lancados_por(session, perfil)
            if not codigos_meus:
                return {"ok": True, "itens": [], "total": 0, "page": page,
                        "per_page": per_page, "paginas": 1, "apenas_meus": True}
            query = query.filter(ImovelArea.codigo.in_(codigos_meus))

        query = _aplicar_recortes(session, query, termo, situacao, f)
        if query is None:
            return {"ok": True, "itens": [], "total": 0, "page": page,
                    "per_page": per_page, "paginas": 1,
                    "apenas_meus": bool(apenas_meus), "resumo": _resumo_vazio()}

        total = query.count()
        resumo = _resumo_da_query(query)
        # Lancamento mais recente primeiro. `cadastrado_em` vem do `datahoracadastro` do
        # Imoview; quem ainda nao tem (catalogo antigo) cai no codigo, que cresce junto —
        # cast numerico porque a coluna e texto e "999" > "12400" em ordem alfabetica.
        linhas = query.order_by(
            ImovelArea.cadastrado_em.desc().nullslast(),
            func.nullif(func.regexp_replace(ImovelArea.codigo, r"[^0-9]", "", "g"), "").cast(BigInteger).desc().nullslast(),
        ).offset((page - 1) * per_page).limit(per_page).all()

        # Imóvel lançado depois da última varredura do catálogo ainda não está no cache.
        # Ele existe em `fato_captacao` desde o lançamento, então entra por aqui — senão
        # "acabei de lançar e não acho" (caso do 12400, lançado 12/08 com cache de 11/08).
        # Só na 1ª página e só o que é de fato recente: são os mais novos de todos, então
        # é o topo da ordenação por lançamento.
        if page == 1 and not tem_filtro_extra:
            codigos_fora_cache = codigos_meus
            if codigos_equipe is not None:
                codigos_fora_cache = (codigos_equipe if codigos_meus is None
                                      else set(codigos_meus) & codigos_equipe)
            faltantes = _do_lancamento_fora_do_cache(
                session, termo, {l.codigo for l in linhas}, codigos_fora_cache)
            if faltantes:
                linhas = faltantes + list(linhas)
                total += len(faltantes)

        # Marca quais já têm captação registrada — é o que diferencia "imóvel do CRM" de
        # "imóvel que a inteligência acompanha".
        codigos = [linha.codigo for linha in linhas]
        com_captacao = set()
        focos = {}
        if codigos:
            com_captacao = {
                row[0] for row in session.query(FatoCaptacao.codigo_imovel).filter(
                    FatoCaptacao.codigo_imovel.in_(codigos)
                ).all()
            }
            for codigo, pp, ac in session.query(
                ImovelLegado.codigo, ImovelLegado.foco_pp, ImovelLegado.foco_ac
            ).filter(ImovelLegado.codigo.in_(codigos)).all():
                atual = focos.get(codigo, (False, False))
                focos[codigo] = (atual[0] or bool(pp), atual[1] or bool(ac))

        itens = []
        for linha in linhas:
            pp, ac = focos.get(linha.codigo, (False, False))
            itens.append({
                "codigo": linha.codigo,
                "endereco": linha.endereco,
                "bairro": linha.bairro,
                "tipo": linha.tipo,
                "quartos": linha.quartos,
                "vagas": linha.vagas,
                "area": _float(linha.area),
                "valor": _float(linha.valor),
                "situacao": getattr(linha, "situacao", None),
                "cadastrado_em": (linha.cadastrado_em.isoformat()
                                  if getattr(linha, "cadastrado_em", None) else None),
                "foco_label": _foco_label(pp, ac),
                "tem_captacao": linha.codigo in com_captacao,
                "atualizado_em": linha.atualizado_em.isoformat() if linha.atualizado_em else None,
            })
        return {
            "ok": True, "itens": itens, "total": total, "page": page, "per_page": per_page,
            "paginas": max(-(-total // per_page), 1),
            "apenas_meus": bool(apenas_meus),
            "resumo": resumo,
        }
    finally:
        session.close()


# Piso de area para entrar no calculo de R$/m2. Abaixo disso o registro e erro de
# cadastro (area em hectare, campo trocado), nao imovel — e cada um vira um outlier de
# milhoes por metro.
AREA_MINIMA_M2 = 10


def _resumo_vazio():
    return {"total": 0, "vgv": 0.0, "ticket_medio": None, "area_media": None,
            "valor_m2_medio": None, "com_valor": 0, "com_area_e_valor": 0}


def _resumo_da_query(query):
    """Agregados do recorte inteiro, não só da página.

    Uma consulta com `count/sum/avg` em vez de somar os itens em Python: a página traz 24
    linhas e o número que interessa ("quanto vendemos no período") é sobre o total.

    O valor/m² é a razão entre as SOMAS (Σvalor ÷ Σárea), restrita às linhas que têm os
    dois preenchidos. A média das médias parecia mais natural e dava R$ 2.092.391/m²: o
    catálogo tem linhas com área perto de 1 m², cada uma virava um "R$ 2 mi por m²" e
    dominava a média. A razão das somas dá o preço médio ponderado, que é o número que
    alguém usaria para avaliar.

    `com_valor` e `com_area_e_valor` dizem sobre quantas linhas cada número foi apurado —
    sem isso não dá para saber se o ticket cobre o recorte todo ou um punhado de linhas.
    """
    # Só entram no m² as linhas com valor E área utilizável; `nullif` tira área zero, que
    # é divisão por zero, e o filtro tira as áreas irrisórias que distorcem o preço.
    area_valida = func.nullif(ImovelArea.area, 0)
    linha = query.with_entities(
        func.count(ImovelArea.codigo),
        func.sum(ImovelArea.valor),
        func.avg(ImovelArea.valor),
        func.avg(area_valida),
        func.sum(func.coalesce(
            case((ImovelArea.area >= AREA_MINIMA_M2, ImovelArea.valor), else_=None), 0)),
        func.sum(func.coalesce(
            case((ImovelArea.area >= AREA_MINIMA_M2, ImovelArea.area), else_=None), 0)),
        func.count(ImovelArea.valor),
        func.count(case((ImovelArea.area >= AREA_MINIMA_M2, ImovelArea.valor), else_=None)),
    ).one()
    total, soma, ticket, area_media, valor_m2_num, valor_m2_den, com_valor, com_area = linha

    numerador, denominador = _float(valor_m2_num) or 0.0, _float(valor_m2_den) or 0.0
    return {
        "total": int(total or 0),
        "vgv": _float(soma) or 0.0,
        "ticket_medio": _float(ticket),
        "area_media": _float(area_media),
        "valor_m2_medio": (numerador / denominador) if denominador else None,
        "com_valor": int(com_valor or 0),
        "com_area_e_valor": int(com_area or 0),
    }


# Faixas de preço do estoque. Cortes redondos e alinhados com como a operação fala do
# produto ("até 500", "de 1 a 2 milhões"); faixas iguais dariam uma barra gigante embaixo
# e nada em cima, porque a distribuição de preço é assimétrica.
FAIXAS_VALOR = [
    ("Até 500 mil", None, 500_000),
    ("500 mil a 1 mi", 500_000, 1_000_000),
    ("1 a 2 mi", 1_000_000, 2_000_000),
    ("2 a 3 mi", 2_000_000, 3_000_000),
    ("3 a 5 mi", 3_000_000, 5_000_000),
    ("Acima de 5 mi", 5_000_000, None),
]

TOPO_BARRAS = 10


def _fatias(pares, limite=TOPO_BARRAS, vazio="Não informado"):
    """Contagens -> lista ordenada, com a cauda somada em "Outros"."""
    contagem = {}
    for valor, total in pares:
        chave = _texto(valor) or vazio
        contagem[chave] = contagem.get(chave, 0) + int(total or 0)
    ordenado = sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))
    saida = [{"rotulo": k, "total": v} for k, v in ordenado[:limite]]
    resto = sum(v for _, v in ordenado[limite:])
    if resto:
        saida.append({"rotulo": "Outros", "total": resto})
    return saida


def graficos(solicitante_id, termo="", situacao="disponivel", apenas_meus=False,
             filtros=None, meses=12):
    """Distribuições do estoque para os gráficos, sobre o MESMO recorte da listagem.

    Um `group by` por eixo em vez de carregar as linhas e agrupar em Python: o recorte
    padrão já passa de mil imóveis e o de `todos` é várias vezes isso.

    A série mensal cruza duas datas diferentes de propósito: `cadastrado_em` diz quando o
    imóvel ENTROU no catálogo e `situacao_em` quando ele SAIU (mudou para vendido,
    desativado ou em reforma). É a única leitura de fluxo possível — o catálogo guarda
    estado atual, não histórico.
    """
    perfil = checar_acesso(solicitante_id)
    termo = _texto(termo)
    f = {k: _texto(v) for k, v in (filtros or {}).items()}
    meses = min(max(int(meses or 12), 1), 60)

    session = SessionLocal()
    try:
        codigos_equipe = _codigos_da_equipe(session, perfil)
        query = _restringir_catalogo_ao_gerente(session.query(ImovelArea), codigos_equipe)
        if apenas_meus:
            codigos_meus = _codigos_lancados_por(session, perfil)
            if not codigos_meus:
                return _graficos_vazio()
            query = query.filter(ImovelArea.codigo.in_(codigos_meus))

        query = _aplicar_recortes(session, query, termo, situacao, f)
        if query is None:
            return _graficos_vazio()

        def agrupar(coluna, limite=TOPO_BARRAS):
            return _fatias(
                query.with_entities(coluna, func.count(ImovelArea.codigo))
                     .group_by(coluna).all(),
                limite,
            )

        total = query.with_entities(func.count(ImovelArea.codigo)).scalar() or 0

        # Faixa de valor: um `case` só, para não fazer seis consultas.
        ramos = []
        for rotulo, minimo, maximo in FAIXAS_VALOR:
            condicoes = []
            if minimo is not None:
                condicoes.append(ImovelArea.valor >= minimo)
            if maximo is not None:
                condicoes.append(ImovelArea.valor < maximo)
            ramos.append((and_(*condicoes), rotulo))
        faixa = case(*ramos, else_=None)
        por_faixa_bruto = dict(
            query.with_entities(faixa, func.count(ImovelArea.codigo)).group_by(faixa).all()
        )
        # Ordem das faixas é a do preço, não a da contagem: fora dela o gráfico deixa de
        # ser distribuição e vira ranking.
        por_faixa = [{"rotulo": rotulo, "total": int(por_faixa_bruto.get(rotulo, 0) or 0)}
                     for rotulo, _, _ in FAIXAS_VALOR]

        # Foco em UMA consulta: as duas marcas viram booleanos por subconsulta e o
        # `case` classifica direto no banco. A versao anterior trazia os 1063 codigos
        # para Python e devolvia um `IN` com todos eles — duas idas ao banco e uma lista
        # gigante no SQL, para um numero que o Postgres calcula sozinho.
        tem_pp = ImovelArea.codigo.in_(_codigos_marcados(session, ImovelLegado.foco_pp))
        tem_ac = ImovelArea.codigo.in_(_codigos_marcados(session, ImovelLegado.foco_ac))
        rotulo_foco = case(
            (and_(tem_pp, tem_ac), "Foco PP + AC"),
            (tem_pp, "Foco PP"),
            (tem_ac, "Foco AC"),
            else_="Não foco",
        )
        bruto = dict(
            query.with_entities(rotulo_foco, func.count(ImovelArea.codigo))
                 .group_by(rotulo_foco).all()
        )
        # Ordem fixa: as fatias precisam ficar no mesmo lugar entre um filtro e outro,
        # senao a cor da legenda muda de significado a cada consulta.
        por_foco = [{"rotulo": r, "total": int(bruto.get(r, 0) or 0)}
                    for r in ("Foco PP", "Foco AC", "Foco PP + AC", "Não foco")]

        # ── fluxo mensal: entradas x saídas ──────────────────────────────────
        corte = (date.today().replace(day=1) - timedelta(days=31 * (meses - 1))).replace(day=1)
        mes_entrada = func.to_char(ImovelArea.cadastrado_em, "YYYY-MM")
        fluxo_query = _restringir_catalogo_ao_gerente(
            session.query(ImovelArea), codigos_equipe
        )
        entradas = dict(
            fluxo_query.with_entities(mes_entrada, func.count(ImovelArea.codigo))
                   .filter(ImovelArea.cadastrado_em >= corte)
                   .group_by(mes_entrada).all()
        )
        mes_saida = func.to_char(ImovelArea.situacao_em, "YYYY-MM")
        saidas = dict(
            fluxo_query.with_entities(mes_saida, func.count(ImovelArea.codigo))
                   .filter(ImovelArea.situacao_em >= corte,
                           or_(*[ImovelArea.situacao.ilike(r) for r in FILTROS_SITUACAO["saiu"]]))
                   .group_by(mes_saida).all()
        )

        serie = []
        ano, mes = corte.year, corte.month
        for _ in range(meses):
            chave = f"{ano:04d}-{mes:02d}"
            serie.append({
                "data": chave,
                "label": f"{mes:02d}/{str(ano)[2:]}",
                "entradas": int(entradas.get(chave, 0) or 0),
                "saidas": int(saidas.get(chave, 0) or 0),
            })
            mes += 1
            if mes > 12:
                ano, mes = ano + 1, 1

        return {
            "ok": True,
            "total": int(total),
            "por_situacao": agrupar(ImovelArea.situacao),
            "por_tipo": agrupar(ImovelArea.tipo),
            "por_bairro": agrupar(ImovelArea.bairro),
            "por_finalidade": agrupar(ImovelArea.finalidade, 5),
            "por_faixa_valor": por_faixa,
            "por_foco": por_foco,
            "fluxo_mensal": serie,
        }
    finally:
        session.close()


def _graficos_vazio():
    return {"ok": True, "total": 0, "por_situacao": [], "por_tipo": [], "por_bairro": [],
            "por_finalidade": [], "por_faixa_valor": [], "por_foco": [], "fluxo_mensal": []}


def opcoes_de_filtro(solicitante_id):
    """Bairros, tipos e finalidades presentes no catálogo, para os dropdowns.

    Sai do catálogo e não de lista fixa: bairro novo aparece sozinho quando a operação
    capta lá pela primeira vez.
    """
    perfil = checar_acesso(solicitante_id)
    session = SessionLocal()
    try:
        codigos_equipe = _codigos_da_equipe(session, perfil)
        def distintos(coluna):
            return sorted({
                _texto(v) for (v,) in _restringir_catalogo_ao_gerente(
                    session.query(ImovelArea), codigos_equipe
                ).with_entities(coluna).distinct().all() if _texto(v)
            }, key=lambda x: x.lower())

        return {
            "ok": True,
            "bairros": distintos(ImovelArea.bairro),
            "tipos": distintos(ImovelArea.tipo),
            "finalidades": distintos(ImovelArea.finalidade),
            "situacoes": [
                {"value": "disponivel", "label": "Disponíveis"},
                {"value": "vendido", "label": "Vendidos"},
                {"value": "desativado", "label": "Desativados"},
                {"value": "moderacao", "label": "Em moderação"},
                {"value": "reforma", "label": "Em reforma"},
                {"value": "saiu", "label": "Saíram do estoque"},
                {"value": "todos", "label": "Todos"},
            ],
        }
    finally:
        session.close()


class _LinhaCaptacao:
    """Adapta uma linha de `fato_captacao` ao formato que a listagem espera.

    O cache do catálogo tem endereço e área; a captação não — ela guarda bairro, tipo e
    valor. É o suficiente p/ o card, e o detalhe completa o resto.
    """

    def __init__(self, registro):
        self.codigo = registro.codigo_imovel
        self.endereco = None
        self.bairro = registro.bairro_nome
        self.tipo = registro.tipo_nome
        self.quartos = None
        self.vagas = None
        self.area = None
        self.valor = registro.valor
        self.situacao = "Recém-lançado"
        self.atualizado_em = registro.created_at


def _codigos_lancados_por(session, perfil):
    """Códigos cuja captação foi lançada por esta pessoa.

    `criado_por` recebe `assistente_id` **ou** `assistente_nome` (o lançamento aceita os
    dois), então a comparação cobre id, nome e username — mesma lógica do casamento de
    leads.
    """
    chaves = [v for v in (perfil.get("id_usuarios"), perfil.get("nome")) if _texto(v)]
    if not chaves:
        return []
    linhas = session.query(FatoCaptacao.codigo_imovel).filter(
        FatoCaptacao.codigo_imovel.isnot(None),
        FatoCaptacao.criado_por.in_(chaves),
    ).distinct().all()
    return [l[0] for l in linhas if l[0]]


def _do_lancamento_fora_do_cache(session, termo, ja_listados, codigos_meus=None):
    """Captações recentes que o `sync_areas_imoview` ainda não trouxe pro cache."""
    query = session.query(FatoCaptacao).filter(
        ~FatoCaptacao.codigo_imovel.in_(
            session.query(ImovelArea.codigo)
        ),
        FatoCaptacao.codigo_imovel.isnot(None),
    )
    if termo:
        alvo = f"%{termo}%"
        query = query.filter(or_(
            FatoCaptacao.codigo_imovel.ilike(alvo),
            FatoCaptacao.bairro_nome.ilike(alvo),
            FatoCaptacao.tipo_nome.ilike(alvo),
        ))
    # Janela curta de propósito. Sem ela entravam 30 captações quaisquer no topo da
    # lista — códigos velhos, sem imóvel no catálogo (imóvel que já saiu do ar), furando
    # a ordenação por lançamento. Aqui só cabe o que a varredura ainda não teve chance
    # de ver.
    if codigos_meus is not None:
        query = query.filter(FatoCaptacao.codigo_imovel.in_(codigos_meus))
    corte = date.today() - timedelta(days=DIAS_LANCAMENTO_RECENTE)
    linhas = query.filter(FatoCaptacao.data_entrada >= corte).order_by(
        FatoCaptacao.data_entrada.desc()
    ).limit(30).all()
    return [_LinhaCaptacao(r) for r in linhas if r.codigo_imovel not in ja_listados]


def _foco_label(pp, ac):
    if pp and ac:
        return "Foco PP + AC"
    if pp:
        return "Foco PP"
    if ac:
        return "Foco AC"
    return "Não foco"


def _vazio(valor):
    """Imoview manda zero como '0', '0,00', 'R$ 0,00' — tudo isso é 'não informado'."""
    texto = str(valor or "").strip()
    return texto in ("", "0", "0,00", "0.00", "R$ 0,00", "0,00%", "false", "False", "None")


def _limpar(dicionario):
    return {k: v for k, v in dicionario.items() if not _vazio(v)}


def _normalizar_imoview(item):
    """Payload cru do Imoview -> o shape que a tela consome, agrupado por assunto.

    O item tem ~120 campos; aqui ficam os que a operação usa. Campos zerados saem do
    dicionário (`_limpar`) p/ a tela não virar um mar de "R$ 0,00".
    """
    return {
        # Identificação e comercialização
        "codigo": item.get("codigo"),
        "tipo": item.get("tipo") or "",
        "destinacao": item.get("destinacao") or "",
        "finalidade": item.get("finalidade") or "",
        "situacao": item.get("situacao") or "",
        "destaque": item.get("destaque") or "",
        "edificio": item.get("edificio") or "",
        "titulo": item.get("titulo") or "",
        "descricao": item.get("descricao") or "",

        # Endereço
        "endereco": item.get("endereco") or item.get("titulo") or "",
        "numero": item.get("numero") or "",
        "bloco": item.get("bloco") or "",
        "complemento": item.get("complemento") or "",
        "bairro": item.get("bairro") or "",
        "cidade": item.get("cidade") or "",
        "estado": item.get("estado") or "",
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),

        # Características
        "caracteristicas": _limpar({
            "Área principal": item.get("areaprincipal"),
            "Área interna": item.get("areainterna"),
            "Área externa": item.get("areaexterna"),
            "Área do lote": item.get("arealote"),
            "Quartos": item.get("numeroquartos"),
            "Suítes": item.get("numerosuites"),
            "Banheiros": item.get("numerobanhos"),
            "Vagas": item.get("numerovagas"),
            "Salas": item.get("numerosalas"),
            "Varandas": item.get("numerovarandas"),
            "Ano de construção": item.get("anoconstrucao"),
            "Andar": item.get("andar"),
            "Mobiliado": "Sim" if item.get("mobiliado") else None,
        }),

        # Valores
        "valores": _limpar({
            "Valor": item.get("valor"),
            "Valor do m²": item.get("valorm2"),
            "Condomínio": item.get("valorcondominio"),
            "IPTU": item.get("valoriptu"),
            "IPTU anual": item.get("valoriptuanual"),
            "Comissão": f"{item.get('taxacomissao')}%" if not _vazio(item.get("taxacomissao")) else None,
            "Avaliação": item.get("valoravaliacao"),
            "Valor anterior": item.get("valoranterior"),
            "Valor mínimo": item.get("valorminimo"),
            "Valor + condomínio + IPTU": item.get("valormaiscondominiomaisiptu"),
        }),

        # Gestão / comercialização
        "gestao": _limpar({
            "Local da chave": item.get("localchave"),
            "Placa/faixa": item.get("placafaixa"),
            "Aceita financiamento": "Sim" if item.get("aceitafinanciamento") else None,
            "Aceita permuta": "Sim" if item.get("aceitapermuta") else None,
            "Exclusivo": "Sim" if item.get("exclusivo") else None,
            "Unidade": item.get("nomeunidade"),
            "Cadastrado em": item.get("datahoracadastro"),
            "Última alteração": item.get("datahoraultimaalteracao"),
            "Vago desde": item.get("datahoravagodesde"),
        }),

        # Links e mídia
        "urlvideo": item.get("urlvideo") or "",
        "urlpublica": item.get("urlpublica") or "",
        "urlfoto": item.get("urlfotoprincipal") or "",

        # Diferenciais marcados no CRM (piscina, academia, etc.)
        "extras": sorted(
            str(e.get("nome")) for e in (item.get("extras2") or [])
            if isinstance(e, dict) and e.get("valor") in (True, "true", "True")
        ),
    }


@cache.memoize(timeout=1800)
def _imoview_ao_vivo(codigo, endereco_cache):
    """Consulta o Imoview e guarda por 30 min (chave: código + endereço).

    O detalhe é aberto várias vezes seguidas — o estagiário volta pra lista, abre outro,
    volta. Sem cache, cada abertura custa 2 a 10 chamadas externas de ~1s. Trinta minutos
    é folgado p/ o uso e curto o bastante p/ pegar alteração feita no CRM no mesmo turno.
    """
    from app.services.imoview_service import buscar_brutos_por_endereco, buscar_imovel_por_codigo

    # Com endereço conhecido, a busca por logradouro custa 2 chamadas — mais barata que
    # a binária. Sem endereço (lançamento fora do cache), vai pelo código.
    if endereco_cache:
        try:
            for item in buscar_brutos_por_endereco(endereco_cache):
                if str(item.get("codigo")) == str(codigo):
                    return _normalizar_imoview(item)
        except Exception:
            pass  # API fora do ar não derruba a consulta

    try:
        item = buscar_imovel_por_codigo(codigo)
        if item:
            return _normalizar_imoview(item)
    except Exception:
        pass
    return None


def _dados_imoview(session, codigo, endereco_cache):
    """Dados do CRM. Ao vivo (cacheado 30 min); cai no cache local se a API não achar."""
    dados = _imoview_ao_vivo(codigo, endereco_cache)
    if dados:
        return {**dados, "origem": "imoview", "ao_vivo": True}

    cache_local = session.query(ImovelArea).filter(ImovelArea.codigo == codigo).first()
    if not cache_local:
        return None
    return {
        "codigo": cache_local.codigo, "endereco": cache_local.endereco, "bairro": cache_local.bairro,
        "tipo": cache_local.tipo, "situacao": cache_local.situacao,
        "caracteristicas": _limpar({
            "Área": cache_local.area, "Quartos": cache_local.quartos, "Vagas": cache_local.vagas,
        }),
        "valores": _limpar({"Valor": cache_local.valor}),
        "gestao": {}, "extras": [],
        "origem": "imoview", "ao_vivo": False,
        "capturado_em": cache_local.atualizado_em.isoformat() if cache_local.atualizado_em else None,
    }


SQL_DETALHE_INTERNO = """
select json_build_object(
  'foco', (select json_build_object('pp', bool_or(coalesce(foco_pp,false)),
                                    'ac', bool_or(coalesce(foco_ac,false)),
                                    'linhas', count(*))
           from imoveis_legado where codigo = :cod),
  'captacao', (select row_to_json(t) from (
      select captador1, captador2, captador3, id_gerente, data_entrada, valor, comissao_pct,
             origem, foco_origem, foco_pp_sugerido, foco_ac_sugerido, bairro_nome
      from fato_captacao where codigo_imovel = :cod limit 1) t),
  'estoque', (select row_to_json(t) from (
      select data_estoque, exclusivo, publicacao_na_internet, id_gerente
      from fato_estoque where codigo_imovel = :cod order by data_estoque desc limit 1) t),
  'saida', (select row_to_json(t) from (
      select data_saida, motivo from fato_saida where codigo_imovel = :cod
      order by data_saida desc limit 1) t),
  'midia', (select row_to_json(t) from (
      select data_relatorio, acesso, impressao,
             (emails + telefone + whatsapp_emails_gerados + visita + proposta) as leads
      from dfimoveis_acessos where codigo_busca = :cod order by data_relatorio desc limit 1) t),
  'visitas', (select coalesce(json_agg(t), '[]'::json) from (
      select id_visita, data_visita, proposta, id_corretor
      from visitas where id_imovel = :cod order by data_visita desc limit 20) t),
  'propostas', (select coalesce(json_agg(t), '[]'::json) from (
      select id, valor, situacao, coalesce(corretor_nome, gerente_nome) as corretor,
             data_proposta, team
      from proposta_efetiva where codigo_imovel = :cod and ativo order by data_proposta desc) t),
  'venda', (select row_to_json(t) from (
      select id_contrato, data_contrato, valor_negocio, valor_total_61,
             corretor_venda_1_nome, gerente_venda_nome
      from contratos
      where regexp_replace(split_part(codigo_imovel, ',', 1), '[^0-9]', '', 'g') = :cod
      order by data_contrato desc limit 1) t)
) as tudo
"""


def detalhe(solicitante_id, codigo):
    """Tudo que sabemos do imóvel, separado por origem.

    Os 8 blocos internos vêm em **uma única consulta** (json_build_object). Cada ida ao
    banco custa ~250ms de latência, então as 9 idas originais gastavam ~2,4s — agora é
    ~400ms. O Imoview vem do wrapper cacheado (30 min).
    """
    perfil = checar_acesso(solicitante_id)
    codigo = _codigo_limpo(codigo) or _texto(codigo)
    if not codigo:
        raise ConsultaErro("Informe o código do imóvel")

    session = SessionLocal()
    try:
        _validar_imovel_no_escopo(codigo, _codigos_da_equipe(session, perfil))
        cache_local = session.query(ImovelArea).filter(ImovelArea.codigo == codigo).first()
        imoview = _dados_imoview(session, codigo, cache_local.endereco if cache_local else None)

        bruto = session.execute(text(SQL_DETALHE_INTERNO), {"cod": codigo}).scalar() or {}
        foco_bloco = bruto.get("foco") or {}
        captacao = bruto.get("captacao") or None
        estoque = bruto.get("estoque") or None
        saida = bruto.get("saida") or None
        midia = bruto.get("midia") or None
        visitas = bruto.get("visitas") or []
        propostas = bruto.get("propostas") or []
        venda = bruto.get("venda") or None

        if perfil.get("permissao") == "gerente":
            team = _texto(perfil.get("team"))
            membros = session.query(Usuarios).filter(Usuarios.team == team).all()
            ids_equipe = {_texto(u.id_usuarios) for u in membros if _texto(u.id_usuarios)}
            visitas = [v for v in visitas if _texto(v.get("id_corretor")) in ids_equipe]
            propostas = [p for p in propostas if _texto(p.get("team")) == team]

            chaves = {
                _texto(valor).lower()
                for usuario in membros
                for valor in (usuario.id_usuarios, usuario.nome, usuario.username)
                if _texto(valor)
            }
            condicoes = [func.lower(FatoCaptacao.id_gerente) == team.lower()]
            for coluna in (FatoCaptacao.captador1, FatoCaptacao.captador2, FatoCaptacao.captador3):
                if chaves:
                    condicoes.append(func.lower(coluna).in_(chaves))
            captacao_equipe = session.query(FatoCaptacao).filter(
                FatoCaptacao.codigo_imovel.in_({codigo, _codigo_limpo(codigo)}),
                or_(*condicoes),
            ).order_by(FatoCaptacao.data_entrada.desc().nullslast()).first()
            if captacao_equipe:
                captacao = {
                    "captador1": captacao_equipe.captador1,
                    "captador2": captacao_equipe.captador2,
                    "captador3": captacao_equipe.captador3,
                    "id_gerente": captacao_equipe.id_gerente,
                    "data_entrada": captacao_equipe.data_entrada,
                    "valor": captacao_equipe.valor,
                    "comissao_pct": captacao_equipe.comissao_pct,
                    "origem": captacao_equipe.origem,
                    "bairro_nome": captacao_equipe.bairro_nome,
                    "foco_origem": captacao_equipe.foco_origem,
                    "foco_pp_sugerido": captacao_equipe.foco_pp_sugerido,
                    "foco_ac_sugerido": captacao_equipe.foco_ac_sugerido,
                }

        tem_algo = any([imoview, captacao, estoque, midia, visitas, propostas, venda,
                        (foco_bloco.get("linhas") or 0)])
        if not tem_algo:
            raise ConsultaErro("Imóvel não encontrado no CRM nem nas bases internas", 404)

        foco_pp = bool(foco_bloco.get("pp"))
        foco_ac = bool(foco_bloco.get("ac"))
        nomes = _nomes_de_usuarios(session, [
            (captacao or {}).get("captador1"), (captacao or {}).get("captador2"),
            (captacao or {}).get("captador3"),
        ])

        return _valor_json({
            "ok": True,
            "codigo": codigo,
            "imoview": imoview,
            "interno": {
                "foco": {
                    "foco_pp": foco_pp, "foco_ac": foco_ac, "label": _foco_label(foco_pp, foco_ac),
                    "origem": (captacao or {}).get("foco_origem"),
                    "sugerido_pp": (captacao or {}).get("foco_pp_sugerido"),
                    "sugerido_ac": (captacao or {}).get("foco_ac_sugerido"),
                    "editavel": True,
                },
                "captacao": {
                    "captadores": nomes,
                    "id_gerente": captacao.get("id_gerente"),
                    "data_entrada": captacao.get("data_entrada"),
                    "valor": captacao.get("valor"),
                    "comissao_pct": captacao.get("comissao_pct"),
                    "origem": captacao.get("origem"),
                    "bairro": captacao.get("bairro_nome"),
                } if captacao else None,
                # Matrícula e inscrição não vêm do CRM (o Imoview tem os campos, mas a
                # operação não preenche) — são digitadas no lançamento ou aqui.
                "documentacao": {
                    "matricula": getattr(cache_local, "matricula", None),
                    "inscricao_iptu": getattr(cache_local, "inscricao_iptu", None),
                    "trello_url": getattr(cache_local, "trello_card_url", None),
                    "editavel": bool(cache_local),
                },
                "estoque": estoque,
                "saida": saida,
                "midia": {
                    "data_relatorio": midia.get("data_relatorio"),
                    "acessos": midia.get("acesso"),
                    "impressoes": midia.get("impressao"),
                    "leads": midia.get("leads"),
                } if midia else None,
                "visitas": {
                    "total": len(visitas),
                    "ultima": visitas[0]["data_visita"] if visitas else None,
                    "itens": [{
                        "id_visita": v["id_visita"], "data": v["data_visita"],
                        "proposta": v["proposta"], "corretor": v["id_corretor"],
                    } for v in visitas],
                },
                "propostas": [{
                    "id": p["id"], "valor": p["valor"], "situacao": p["situacao"],
                    "corretor": p["corretor"], "data_proposta": p["data_proposta"],
                } for p in propostas],
                "venda": {
                    "id_contrato": venda.get("id_contrato"),
                    "data": venda.get("data_contrato"),
                    "valor": venda.get("valor_negocio"),
                    "valor_total_61": venda.get("valor_total_61"),
                    "corretor": venda.get("corretor_venda_1_nome"),
                    "gerente": venda.get("gerente_venda_nome"),
                } if venda else None,
            },
        })
    finally:
        session.close()


def _nomes_de_usuarios(session, ids):
    alvo = [i for i in ids if i]
    if not alvo:
        return []
    rows = session.query(Usuarios.id_usuarios, Usuarios.nome).filter(
        Usuarios.id_usuarios.in_(alvo)
    ).all()
    mapa = {i: n for i, n in rows}
    return [{"id": i, "nome": mapa.get(i, i)} for i in alvo]



def _sincronizar_trello(registro, matricula, inscricao):
    """Replica matrícula/inscrição no cartão do Trello do imóvel.

    Devolve um dicionário de status — nunca levanta. A gravação na nossa base já foi
    feita quando isto roda; deixar uma falha do Trello desfazer a correção seria pior
    que o cartão ficar desatualizado (que é o estado de antes).

    Imóvel lançado antes de guardarmos o id do cartão cai na busca por código, que varre
    o board. Achando, o id é persistido — a varredura acontece uma vez por imóvel.
    """
    from app.services import trello_service

    try:
        card_id = _texto(getattr(registro, "trello_card_id", None))
        if not card_id:
            achado = trello_service.buscar_cartao_por_codigo(registro.codigo)
            if not achado:
                return {"ok": False, "motivo": "cartão não encontrado no board"}
            card_id = achado["id"]
            registro.trello_card_id = card_id
            registro.trello_card_url = achado.get("url")

        resultado = trello_service.atualizar_campos(card_id, matricula=matricula, iptu=inscricao) or {}
        return {
            "ok": True,
            "card_url": getattr(registro, "trello_card_url", None),
            # Cartao de cessao de direitos guarda o texto no campo matricula; a tela
            # precisa dizer que aquele campo especifico nao foi tocado.
            "matricula_preservada": bool(resultado.get("matricula_preservada")),
        }
    except Exception as e:
        return {"ok": False, "motivo": str(e)[:200]}


def atualizar_interno(solicitante_id, codigo, dados):
    """Edita o que é nosso: foco e documentação (matrícula / inscrição IPTU).

    Os dois campos são independentes — a tela pode mandar só um. Foco grava nos DOIS
    lugares que o resto do sistema lê (`imoveis_legado`, base do ranking e do XLSX de
    VGC, e `fato_captacao`, com `foco_origem='manual'` p/ a auditoria saber que a
    mudança foi humana). Documentação mora no catálogo `imovel_area`.
    """
    perfil = checar_acesso(solicitante_id)
    codigo = _codigo_limpo(codigo) or _texto(codigo)
    if not codigo:
        raise ConsultaErro("Informe o código do imóvel")

    from app.services.lancamento_service import FOCO_OPCOES

    mexe_no_foco = "foco" in dados
    campos_doc = {c: _texto(dados.get(c)) or None for c in ("matricula", "inscricao_iptu") if c in dados}
    if not mexe_no_foco and not campos_doc:
        raise ConsultaErro("Nada para atualizar: envie `foco`, `matricula` ou `inscricao_iptu`")

    foco_pp = foco_ac = None
    if mexe_no_foco:
        escolha = _texto(dados.get("foco")).lower()
        if escolha not in FOCO_OPCOES:
            raise ConsultaErro(f"Foco inválido. Use um destes: {', '.join(FOCO_OPCOES)}")
        foco_pp, foco_ac = FOCO_OPCOES[escolha]

    session = SessionLocal()
    try:
        _validar_imovel_no_escopo(codigo, _codigos_da_equipe(session, perfil))
        resposta = {"ok": True, "codigo": codigo}

        if mexe_no_foco:
            linhas = session.query(ImovelLegado).filter(ImovelLegado.codigo == codigo).all()
            if not linhas:
                raise ConsultaErro("Imóvel sem registro na base de imóveis — lance pelo CRM primeiro", 404)
            for linha in linhas:
                linha.foco_pp = foco_pp
                linha.foco_ac = foco_ac

            captacao = session.query(FatoCaptacao).filter(FatoCaptacao.codigo_imovel == codigo).first()
            if captacao:
                captacao.foco_pp = foco_pp
                captacao.foco_ac = foco_ac
                captacao.foco_origem = "manual"
                captacao.criado_por = perfil["id_usuarios"] or captacao.criado_por
            resposta["foco"] = {
                "foco_pp": foco_pp, "foco_ac": foco_ac, "label": _foco_label(foco_pp, foco_ac),
            }

        if campos_doc:
            registro = session.query(ImovelArea).filter(ImovelArea.codigo == codigo).first()
            if registro is None:
                # Sem linha no catálogo não há onde gravar — acontece com imóvel que só
                # existe em base legada, nunca varrido pelo sync.
                raise ConsultaErro("Imóvel fora do catálogo — não dá para gravar documentação", 404)
            for campo, valor in campos_doc.items():
                setattr(registro, campo, valor)
            resposta["documentacao"] = campos_doc

            # Fecha o ciclo com o Trello: o cartão nasce no lançamento com matrícula e
            # inscrição, e a correção feita aqui precisa chegar lá também.
            resposta["trello"] = _sincronizar_trello(
                registro,
                campos_doc.get("matricula", registro.matricula),
                campos_doc.get("inscricao_iptu", registro.inscricao_iptu),
            )

        session.commit()
        resposta["alterado_por"] = perfil["nome"]
        resposta["alterado_em"] = datetime.now().isoformat(timespec="seconds")
        return resposta
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
