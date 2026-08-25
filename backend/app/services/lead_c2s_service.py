"""Leads lidos AO VIVO do Contact2Sale, para a aba de leads do Relatorio do Gerente.

Por que existe, ao lado de `lead_gestao_service` (que le de `leads_legado`): a situacao
do lead muda no C2S depois da importacao — vira "Em negociacao", e arquivado com um
motivo, vira negocio fechado. A base interna guarda o retrato do dia da importacao,
entao o gerente via um status velho. Aqui a leitura e direta.

## O que a API aceita (documentacao oficial da C2S)

    page / perpage        paginacao (perpage <= 50)
    sort                  created_at | updated_at, prefixo "-" para DESC
    status                novo | em_negociacao | convertido | negocio_fechado |
                          arquivado | resgatado | pendente | recusado | finalizado
    created_gte/_lt       janela por data de criacao
    updated_gte/_lt       janela por data de atualizacao
    last_update           atualizados desde a data
    phone / email         telefone e e-mail do cliente
    tags                  nomes separados por virgula

Cuidado: a API **ignora em silencio** parametro que nao conhece — nome errado devolve a
lista inteira sem erro, entao filtro mal escrito vira numero errado sem aviso. Foi o que
aconteceu numa primeira versao daqui, que mandava `status=1` (a API espera o slug, nao o
id) e recebia zero.

O que ela NAO filtra, e por isso e aplicado neste modulo: portal (`lead_source`), canal,
equipe, corretor, etapa do funil, motivo do arquivamento e busca livre.

## Paginacao

A pagina da tela e a pagina da API (as duas com 50), entao sem filtro local a resposta
sai de UMA requisicao e o total vem de `meta.total`.

Com filtro local nao ha atalho: a API nao filtra por equipe, corretor, portal nem motivo
(testado — ela ignora esses parametros e devolve a lista inteira), entao a janela e
varrida do inicio ao fim. Um mes tem ~39 paginas e o teto e de 10 requisicoes por minuto,
entao a primeira consulta filtrada leva alguns minutos. Tres coisas amortecem isso:

  1. `status` vai para a API quando o filtro permite (arquivado, em negociacao, motivo
     preenchido) — isso sozinho corta agosto de 39 para ~16 paginas;
  2. as chamadas sao espacadas para nao bater no 429, que custa 65 s cada vez;
  3. as paginas cruas ficam 15 min em cache, entao so a PRIMEIRA consulta do periodo
     paga a varredura — trocar filtro ou pagina depois disso e instantaneo.
"""
import os
import time
import unicodedata
from typing import Any, Dict, List, Optional

import requests

from sqlalchemy import func

from app.database import SessionLocal
from app.extensions import cache
from app.models.equipe import Equipe
from app.models.estoque_legado import LeadLegado
from app.models.lead_c2s import LeadC2S
from app.models.usuarios import Usuarios

C2S_LEADS_URL = "https://api.contact2sale.com/integration/leads"

PERFIS_GLOBAIS = {"administrador", "administrativo", "diretor", "inteligencia"}

PER_PAGE_API = 50           # teto da API: acima disso responde 403

# Teto de seguranca, nao de precisao: com filtro local a varredura vai ate o fim da
# janela. Existia um teto de 12 paginas que cortava a contagem em silencio — LOTUS +
# motivo "Duplicado" em agosto devolvia 3 de 12 porque so via 600 dos 1.922 leads.
MAX_PAGINAS_BUSCA = 200

# A janela varrida fica em cache por 15 min. E o que torna a escolha viavel: a primeira
# consulta do periodo paga a varredura, e trocar de filtro ou de pagina depois disso nao
# volta na API.
CACHE_SEGUNDOS = 900
TIMEOUT = 120               # a API leva 5-10 s por pagina e piora nas profundas

# A API permite 10 requisicoes por minuto. Bater no 429 custa 65 s de espera; espacar
# 6,2 s entre chamadas evita o teto e corta quase pela metade a varredura de um mes
# (~240 s espacando, contra ~455 s levando 429 a cada 10 paginas).
INTERVALO_ENTRE_CHAMADAS = 6.2
_ultima_chamada = 0.0

# `status` da API <-> `lead_status.name` que vem no lead. Empurrar isto para a API evita
# varrer a janela: e o filtro mais usado (arquivado/em negociacao).
STATUS_API = {
    "novo": "novo",
    "em negociacao": "em_negociacao",
    "em negociação": "em_negociacao",
    "arquivado": "arquivado",
    "convertido": "convertido",
    "negocio fechado": "negocio_fechado",
    "negócio fechado": "negocio_fechado",
    "resgatado": "resgatado",
    "pendente": "pendente",
    "recusado": "recusado",
    "finalizado": "finalizado",
}


class LeadC2SErro(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _norm(valor) -> str:
    """Compara texto entre bases que nao combinaram grafia.

    O C2S guarda o nome como foi digitado: " AGEF" com espaco, "NOVA UNIAO" sem til
    contra "NOVA UNIÃO" do cadastro, "LÍDER" com til contra "LIDER". Sem tirar acento e
    colapsar espaco, o gerente dessas equipes nao via lead nenhum.
    """
    texto = unicodedata.normalize("NFKD", _texto(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().split())


def _norm_equipe(valor) -> str:
    """Idem, mais o prefixo que a C2S usa em algumas contas ("Equipe Locação")."""
    texto = _norm(valor)
    return texto[len("equipe "):] if texto.startswith("equipe ") else texto


def _token() -> str:
    token = os.getenv("CONTACT2SALE_TOKEN") or os.getenv("C2S_TOKEN")
    if not token:
        raise LeadC2SErro("Configure CONTACT2SALE_TOKEN no ambiente.", 503)
    return token


# ── acesso a API ────────────────────────────────────────────────────────────────

def _pagina(campo_data: str, inicio: str, fim: str, page: int,
            status: str = "", usar_cache: bool = True) -> Dict[str, Any]:
    """Uma pagina crua da API, com cache curto e espera no rate limit.

    `usar_cache=False` no sync, por dois motivos: uma pagina guardada ha 15 minutos
    gravaria estado velho na base — o oposto do que a sincronizacao existe para fazer —
    e o cache e do Flask, que exige contexto de aplicacao que o cron nao tem.
    """
    chave = f"c2s:{campo_data}:{inicio}:{fim}:{status}:{page}"
    if usar_cache:
        guardado = cache.get(chave)
        if guardado is not None:
            return guardado

    params = {
        "page": page,
        "perpage": PER_PAGE_API,
        # Sem ordenacao explicita a API nao garante estabilidade entre paginas, e o mesmo
        # lead podia aparecer duas vezes (ou sumir) ao avancar.
        "sort": f"-{campo_data}_at",
        f"{campo_data}_gte": f"{inicio}T00:00:00Z",
        f"{campo_data}_lt": f"{fim}T23:59:59Z",
    }
    if status:
        params["status"] = status

    global _ultima_chamada
    for _ in range(3):
        espera = INTERVALO_ENTRE_CHAMADAS - (time.monotonic() - _ultima_chamada)
        if espera > 0:
            time.sleep(espera)
        _ultima_chamada = time.monotonic()
        try:
            r = requests.get(
                C2S_LEADS_URL,
                headers={"Authorization": _token(), "Content-Type": "application/json"},
                params=params, timeout=TIMEOUT,
            )
        except requests.Timeout:
            continue
        if r.status_code == 429:
            # Teto de 10 req/min. Espera a janela virar e repete a mesma pagina.
            time.sleep(65)
            continue
        if r.status_code >= 400:
            raise LeadC2SErro(f"Contact2Sale respondeu {r.status_code}.", 502)
        corpo = r.json() or {}
        resultado = {"data": corpo.get("data") or [], "total": (corpo.get("meta") or {}).get("total")}
        if usar_cache:
            cache.set(chave, resultado, timeout=CACHE_SEGUNDOS)
        return resultado
    raise LeadC2SErro("Contact2Sale recusou por limite de requisições. Tente de novo em 1 minuto.", 429)


def _status_da_api(filtros: Dict[str, str]) -> str:
    """Traduz os filtros da tela no `status` que a API entende, quando da.

    Um filtro so pode virar `status` se for o unico pedido sobre situacao — combinar
    "arquivado=nao" com "situacao=Arquivado" nao tem status equivalente, e nesse caso a
    filtragem fica local.
    """
    if _norm(filtros.get("fechado")) in {"sim", "1", "true"}:
        return "negocio_fechado"
    situacao = _norm(filtros.get("situacao"))
    if situacao and situacao in STATUS_API:
        return STATUS_API[situacao]
    if _norm(filtros.get("arquivado")) in {"sim", "1", "true"}:
        return "arquivado"
    # Motivo de arquivamento so existe em lead arquivado, entao filtrar por ele ja
    # restringe o status. Isso corta a varredura de agosto de 39 para ~16 paginas.
    if _texto(filtros.get("motivo")) or _texto(filtros.get("com_motivo")):
        return "arquivado"
    return ""


# ── traducao de um lead ─────────────────────────────────────────────────────────

# `lost_reasons.name` vem como slug em ingles da propria C2S. Levantados os valores que
# aparecem de fato na conta (agosto/2026); slug novo cai no `replace`/`title` do fallback
# em vez de sumir, para nao esconder motivo que ainda nao foi mapeado.
MOTIVOS_PT = {
    "duplicated": "Duplicado",
    "partner_agent": "Corretor parceiro",
    "just_researching": "Apenas pesquisando",
    "invalid": "Lead inválido",
    "without_qualification": "Sem qualificação",
    "fail_to_contact": "Não consegui contato",
    "product_not_satisfy": "Produto não agradou",
    "sold": "Já foi vendido",
    "return_delay": "Demora no retorno",
    "price_high": "Preço alto",
    "purchase_postponed": "Compra adiada",
    "no_income": "Não possui renda",
    "location": "Localização não agradou",
    "low_offer": "Proposta com valor baixo",
}


def _motivo_pt(valor: str) -> str:
    chave = _norm(valor).replace(" ", "_")
    if chave in MOTIVOS_PT:
        return MOTIVOS_PT[chave]
    # Slug desconhecido: vira texto legivel ("some_new_reason" -> "Some New Reason").
    return _texto(valor).replace("_", " ").strip().capitalize() if valor else ""


def _motivo_arquivamento(a: Dict[str, Any]) -> str:
    """Motivo do arquivamento/perda, em português.

    Vem em dois lugares: `lost_reasons.name` (o motivo escolhido na lista, que a C2S
    devolve como slug em inglês) e `archive_details.archive_notes` (texto livre que o
    corretor digita). O primeiro manda; o segundo completa quando acrescenta algo.
    """
    perda = _motivo_pt(_texto((a.get("lost_reasons") or {}).get("name")))
    nota = _texto((a.get("archive_details") or {}).get("archive_notes"))
    if perda and nota and _norm(perda) != _norm(nota):
        return f"{perda} — {nota}"
    return perda or nota


def _traduzir(lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    a = lead.get("attributes") or {}
    if not a:
        return None
    cliente = a.get("customer") or {}
    produto = a.get("product") or {}
    arquivo = a.get("archive_details") or {}
    fechado = a.get("done_details") or {}
    situacao = a.get("lead_status") or {}
    return {
        "id_c2s": lead.get("id"),
        "cliente": _texto(cliente.get("name")),
        "telefone": _texto(cliente.get("phone")),
        "email": _texto(cliente.get("email")),
        "fonte": _texto((a.get("lead_source") or {}).get("name")),
        "canal": _texto((a.get("channel") or {}).get("name")),
        "equipe": _texto((a.get("company") or {}).get("name")),
        "corretor": _texto((a.get("seller") or {}).get("name")),
        "codigo_imovel": _texto(produto.get("prop_ref")),
        "imovel": _texto(a.get("description") or produto.get("description")),
        "url": _texto(a.get("url")),
        "situacao": _texto(situacao.get("name")),
        "situacao_alias": _texto(situacao.get("alias")),
        "funil": _texto((a.get("funnel_status") or {}).get("status")),
        "arquivado": bool(arquivo.get("archived")),
        "motivo_arquivamento": _motivo_arquivamento(a),
        "negocio_fechado": bool(fechado.get("done")),
        "valor_fechado": fechado.get("done_price"),
        "criado_em": _texto(a.get("created_at")),
        "atualizado_em": _texto(a.get("updated_at")),
        "ultima_atividade": _texto(a.get("last_activity_date")),
        "respondido_em": _texto(a.get("replied_at")),
        "favorito": bool(a.get("is_favorite")),
        "observacao": _texto(a.get("observation")),
    }


# ── escopo ──────────────────────────────────────────────────────────────────────

def _escopo(session, solicitante_id: str, equipe_pedida: Optional[str]) -> Dict[str, Any]:
    """Traduz o solicitante no recorte a aplicar sobre os campos do C2S.

    O C2S nao conhece os ids internos: a equipe vem como NOME (`company.name` = "SENNA")
    e o corretor tambem (`seller.name`). O casamento e por nome, entao o recorte e feito
    aqui e nunca a partir do que a tela mandou — gerente que forjasse `equipe` na query
    continuaria preso a propria.
    """
    user = session.query(Usuarios).filter(
        Usuarios.id_usuarios == _texto(solicitante_id), Usuarios.ativo.is_(True)
    ).first()
    if not user:
        raise LeadC2SErro("Sem permissão para ver leads", 403)

    permissao = _norm(user.permissao)
    team_id = _texto(user.team)
    global_ = permissao in PERFIS_GLOBAIS or _norm(team_id) == "administrativo"

    def nome_da_equipe(id_equipe):
        if not id_equipe:
            return ""
        eq = session.query(Equipe).filter(Equipe.id_equipe == _texto(id_equipe)).first()
        return _texto(eq.nome) if eq else _texto(id_equipe)

    if global_:
        # O dropdown de equipe do relatorio so vale para quem ja enxerga tudo.
        return {"ve_tudo": True, "equipe": nome_da_equipe(equipe_pedida), "corretor": ""}
    if permissao == "gerente" and team_id:
        return {"ve_tudo": False, "equipe": nome_da_equipe(team_id), "corretor": ""}
    # Corretor e assistente veem so o proprio atendimento.
    return {"ve_tudo": False, "equipe": "",
            "corretor": _texto(user.nome or user.username)}


# ── filtros locais ──────────────────────────────────────────────────────────────

def _passa(item: Dict[str, Any], f: Dict[str, str], escopo: Dict[str, Any],
           com_acomp: Optional[set] = None) -> bool:
    if escopo["equipe"] and _norm_equipe(item["equipe"]) != _norm_equipe(escopo["equipe"]):
        return False
    if escopo["corretor"] and _norm(escopo["corretor"]) not in _norm(item["corretor"]):
        return False

    if f.get("situacao") and _norm(item["situacao"]) != _norm(f["situacao"]):
        return False
    if f.get("fonte") and _norm(item["fonte"]) != _norm(f["fonte"]):
        return False
    if f.get("canal") and _norm(item["canal"]) != _norm(f["canal"]):
        return False
    if f.get("equipe") and _norm_equipe(item["equipe"]) != _norm_equipe(f["equipe"]):
        return False
    if f.get("funil") and _norm(item["funil"]) != _norm(f["funil"]):
        return False
    if f.get("corretor") and _norm(f["corretor"]) not in _norm(item["corretor"]):
        return False
    if f.get("motivo") and _norm(f["motivo"]) not in _norm(item["motivo_arquivamento"]):
        return False

    arquivado = _norm(f.get("arquivado"))
    if arquivado in {"sim", "1", "true"} and not item["arquivado"]:
        return False
    if arquivado in {"nao", "não", "0", "false"} and item["arquivado"]:
        return False

    fechado = _norm(f.get("fechado"))
    if fechado in {"sim", "1", "true"} and not item["negocio_fechado"]:
        return False
    if fechado in {"nao", "não", "0", "false"} and item["negocio_fechado"]:
        return False

    if f.get("com_motivo") and not item["motivo_arquivamento"]:
        return False
    # Acompanhamento e coluna NOSSA, nao do C2S. O conjunto de quem JA tem vem pronto de
    # `_chaves_com_acompanhamento` (13 linhas na base inteira), entao o filtro nao exige
    # casar lead a lead nem varrer a janela.
    if f.get("sem_acompanhamento") and com_acomp is not None:
        if (_norm(item["cliente"]), item["telefone"]) in com_acomp:
            return False

    busca = _norm(f.get("busca"))
    if busca:
        alvo = " ".join([
            item["cliente"], item["telefone"], item["email"], item["codigo_imovel"],
            item["imovel"], item["corretor"], item["fonte"], item["motivo_arquivamento"],
        ])
        if busca not in _norm(alvo):
            return False
    return True


def _tem_filtro_local(f: Dict[str, str], escopo: Dict[str, Any], status_api: str) -> bool:
    """Sobrou algo que a API nao filtra? So entao vale puxar pagina extra."""
    if escopo["equipe"] or escopo["corretor"]:
        return True
    # `sem_acompanhamento` NAO entra: e resolvido por um conjunto pequeno vindo do banco,
    # sem precisar varrer a janela (ver `_chaves_com_acompanhamento`).
    locais = ["fonte", "canal", "equipe", "funil", "corretor", "motivo",
              "com_motivo", "busca"]
    # Estes tres viram `status` na API; se nao viraram (combinacao sem equivalente),
    # continuam sendo filtro local.
    if not status_api:
        locais += ["situacao", "arquivado", "fechado"]
    elif _norm(f.get("arquivado")) in {"nao", "não", "0", "false"} or             _norm(f.get("fechado")) in {"nao", "não", "0", "false"}:
        locais += ["arquivado", "fechado"]
    return any(_texto(f.get(k)) for k in locais)


# ── casamento com a base interna (para manter o acompanhamento) ─────────────────

def _chaves_com_acompanhamento(session, inicio: str, fim: str) -> set:
    """Chaves (cliente, telefone) dos leads do periodo que JA tem acompanhamento.

    O acompanhamento e coluna NOSSA (`leads_legado.acompanhamento_em`), nao vem do C2S.
    E o conjunto e minusculo — 13 linhas na base inteira em 21/08/2026 — entao vale
    inverter: em vez de casar lead a lead durante a varredura, carrega-se esta lista uma
    vez e o filtro "sem acompanhamento" vira uma exclusao barata.
    """
    linhas = session.query(LeadLegado.cliente, LeadLegado.telefone).filter(
        LeadLegado.acompanhamento_em.isnot(None),
        LeadLegado.data >= inicio, LeadLegado.data <= fim,
    ).all()
    return {(_norm(c), _texto(t)) for c, t in linhas}


def _ids_internos(session, itens: List[Dict[str, Any]]) -> None:
    """Anexa `id_interno` e o acompanhamento quando o lead ja existe em `leads_legado`.

    O C2S identifica por hash e a base interna por inteiro; o elo e a mesma chave que a
    importacao usa (cliente + telefone). Sem isso o gerente perderia o botao de registrar
    acompanhamento nos leads que vieram da leitura ao vivo.
    """
    nomes = {item["cliente"] for item in itens if item["cliente"]}
    if not nomes:
        return
    linhas = session.query(LeadLegado).filter(LeadLegado.cliente.in_(nomes)).all()
    indice: Dict[tuple, Any] = {}
    for linha in linhas:
        indice.setdefault((_norm(linha.cliente), _texto(linha.telefone)), linha)
    for item in itens:
        achado = indice.get((_norm(item["cliente"]), item["telefone"]))
        item["id_interno"] = achado.id if achado else None
        item["acompanhamento_em"] = (
            achado.acompanhamento_em.isoformat() if achado and achado.acompanhamento_em else None
        )
        item["contato_status"] = _texto(achado.contato_status) if achado else ""


# ── listagem ────────────────────────────────────────────────────────────────────

def listar_ao_vivo(solicitante_id, inicio, fim, page=1, per_page=PER_PAGE_API,
                   campo_data="created", filtros=None) -> Dict[str, Any]:
    """Leitura direta da API do C2S. Nao e mais o caminho da tela.

    Continua aqui como escape hatch: se o espelho (`leads_c2s`) ficar atrasado ou
    quebrar, `LEADS_FONTE=api` no ambiente devolve o comportamento antigo sem deploy de
    codigo. Custa minutos por consulta filtrada — e o motivo de o espelho existir.
    """
    filtros = {k: _texto(v) for k, v in (filtros or {}).items()}
    if not inicio or not fim:
        raise LeadC2SErro("Informe o período (início e fim).")
    if campo_data not in {"created", "updated"}:
        campo_data = "created"

    page = max(int(page or 1), 1)
    # A pagina da tela e a da API: sem descasamento nao ha aritmetica de offset, e sem
    # filtro local a tela inteira sai de uma requisicao so.
    per_page = PER_PAGE_API

    session = SessionLocal()
    try:
        escopo = _escopo(session, solicitante_id, filtros.get("equipe"))
        # O escopo do cadastro ja manda; cruzar com o parametro devolveria lista vazia
        # (em vez da propria equipe) para quem mexesse na query.
        if escopo["equipe"]:
            filtros.pop("equipe", None)
        # O relatorio manda o NOME do corretor no dropdown; o escopo de corretor/assistente
        # ja prende ao proprio, entao o parametro so acrescenta para quem ve mais de um.
        if escopo["corretor"]:
            filtros.pop("corretor", None)

        status_api = _status_da_api(filtros)
        precisa_local = _tem_filtro_local(filtros, escopo, status_api)
        # Conjunto pequeno (13 linhas na base inteira em 21/08): carregado sempre que o
        # filtro de acompanhamento esta ligado, tanto no caminho rapido quanto na varredura.
        com_acomp = (_chaves_com_acompanhamento(session, inicio, fim)
                     if filtros.get("sem_acompanhamento") else None)

        if not precisa_local:
            # Caminho normal: a API pagina, filtra por status e conta.
            alvo = _pagina(campo_data, inicio, fim, page, status_api)
            itens = [x for x in (_traduzir(l) for l in alvo["data"]) if x]
            total = alvo["total"] or 0
            if com_acomp is not None:
                # Quem ja tem acompanhamento sai da pagina, e o total desconta os do
                # periodo — exato porque o conjunto vem do banco, nao de amostragem.
                itens = [x for x in itens if _passa(x, filtros, escopo, com_acomp)]
                total = max(total - len(com_acomp), 0)
            _ids_internos(session, itens)
            return {
                "ok": True, "itens": itens, "page": page, "per_page": per_page,
                "total": total, "total_c2s": total, "total_exato": True,
                "tem_mais": page * per_page < total, "paginas_lidas": 1,
                "fonte": "contact2sale", "opcoes": _opcoes(itens),
            }

        # Com filtro local: puxa pagina a pagina e PARA quando a pagina pedida encheu.
        # Nao varre o periodo inteiro — o custo acompanha o que a tela vai mostrar.
        casados: List[Dict[str, Any]] = []
        vistos: List[Dict[str, Any]] = []
        total_c2s = 0
        lidas = 0
        acabou = False
        for numero in range(1, MAX_PAGINAS_BUSCA + 1):
            alvo = _pagina(campo_data, inicio, fim, numero, status_api)
            lidas = numero
            total_c2s = alvo["total"] or total_c2s
            lote = [x for x in (_traduzir(l) for l in alvo["data"]) if x]
            vistos.extend(lote)
            # `sem_acompanhamento` depende da base interna, entao o casamento roda no lote.
            _ids_internos(session, lote)
            casados.extend(x for x in lote if _passa(x, filtros, escopo, com_acomp))
            if len(alvo["data"]) < PER_PAGE_API:
                acabou = True
                break

        corte = (page - 1) * per_page
        itens = casados[corte:corte + per_page]
        return {
            "ok": True, "itens": itens, "page": page, "per_page": per_page,
            # So afirma total quando a janela acabou; senao a tela mostra "50+".
            "total": len(casados) if acabou else None,
            "total_c2s": total_c2s, "total_exato": acabou,
            "tem_mais": len(casados) > corte + per_page or not acabou,
            "paginas_lidas": lidas, "fonte": "contact2sale",
            "opcoes": _opcoes(vistos),
        }
    finally:
        session.close()


# ── leitura do espelho local ────────────────────────────────────────────────────

# Colunas do espelho na ordem em que a tela espera, para montar o item sem repetir o
# nome de cada campo duas vezes.
_COLUNAS_ITEM = (
    "id_c2s", "cliente", "telefone", "email", "fonte", "canal", "equipe", "corretor",
    "codigo_imovel", "imovel", "url", "situacao", "situacao_alias", "funil",
    "motivo_arquivamento", "observacao",
)


def _item_do_banco(linha: LeadC2S) -> Dict[str, Any]:
    """Mesma forma que `_traduzir` devolve, para a tela nao saber de onde veio."""
    item = {campo: _texto(getattr(linha, campo)) for campo in _COLUNAS_ITEM}
    item.update({
        "arquivado": bool(linha.arquivado),
        "negocio_fechado": bool(linha.negocio_fechado),
        "valor_fechado": float(linha.valor_fechado) if linha.valor_fechado is not None else None,
        "favorito": bool(linha.favorito),
        "criado_em": linha.criado_em.isoformat() if linha.criado_em else "",
        "atualizado_em": linha.atualizado_em.isoformat() if linha.atualizado_em else "",
        "ultima_atividade": linha.ultima_atividade.isoformat() if linha.ultima_atividade else "",
        "respondido_em": linha.respondido_em.isoformat() if linha.respondido_em else "",
        "id_interno": linha.id_legado,
    })
    return item


def _igual(coluna, valor: str):
    """Comparacao exata sem depender de caixa.

    Nao usa `_norm` (que tira acento) porque os dois lados sao string do C2S: o valor do
    dropdown saiu da propria base. Tirar acento exigiria `unaccent`, que e extensao e
    pode nao estar instalada no RDS.
    """
    return func.lower(coluna) == valor.strip().lower()


def _contem(coluna, valor: str):
    return coluna.ilike(f"%{valor.strip()}%")


def _aplicar_filtros(query, f: Dict[str, str], escopo: Dict[str, Any]):
    """Traduz os filtros da tela em SQL.

    Antes cada um destes era um `if` em Python sobre a janela inteira puxada da API —
    o que obrigava a varrer o periodo para filtrar. No banco todos viram predicado, e o
    indice de data resolve o recorte.
    """
    if escopo["equipe"]:
        query = query.filter(_igual(LeadC2S.equipe, escopo["equipe"]))
    elif _texto(f.get("equipe")):
        query = query.filter(_igual(LeadC2S.equipe, f["equipe"]))
    if escopo["corretor"]:
        query = query.filter(_contem(LeadC2S.corretor, escopo["corretor"]))
    elif _texto(f.get("corretor")):
        query = query.filter(_contem(LeadC2S.corretor, f["corretor"]))

    for campo, coluna in (("situacao", LeadC2S.situacao), ("fonte", LeadC2S.fonte),
                          ("canal", LeadC2S.canal), ("funil", LeadC2S.funil)):
        if _texto(f.get(campo)):
            query = query.filter(_igual(coluna, f[campo]))

    if _texto(f.get("motivo")):
        query = query.filter(_contem(LeadC2S.motivo_arquivamento, f["motivo"]))
    if _texto(f.get("com_motivo")):
        query = query.filter(LeadC2S.motivo_arquivamento.isnot(None))

    arquivado = _norm(f.get("arquivado"))
    if arquivado in {"sim", "1", "true"}:
        query = query.filter(LeadC2S.arquivado.is_(True))
    elif arquivado in {"nao", "não", "0", "false"}:
        query = query.filter(LeadC2S.arquivado.isnot(True))

    fechado = _norm(f.get("fechado"))
    if fechado in {"sim", "1", "true"}:
        query = query.filter(LeadC2S.negocio_fechado.is_(True))
    elif fechado in {"nao", "não", "0", "false"}:
        query = query.filter(LeadC2S.negocio_fechado.isnot(True))

    busca = _texto(f.get("busca"))
    if busca:
        alvo = f"%{busca}%"
        query = query.filter(
            LeadC2S.cliente.ilike(alvo) | LeadC2S.telefone.ilike(alvo)
            | LeadC2S.email.ilike(alvo) | LeadC2S.codigo_imovel.ilike(alvo)
            | LeadC2S.imovel.ilike(alvo) | LeadC2S.corretor.ilike(alvo)
            | LeadC2S.fonte.ilike(alvo) | LeadC2S.motivo_arquivamento.ilike(alvo)
        )
    return query


def _acompanhamento_do_banco(session, itens: List[Dict[str, Any]]) -> None:
    """Anexa o acompanhamento, que mora em `leads_legado` e nao vem do C2S.

    Vai pelo `id_legado` ja resolvido no sync — o casamento por nome + telefone acontece
    uma vez por hora, fora do caminho do usuario, em vez de a cada consulta.
    """
    ids = {item["id_interno"] for item in itens if item.get("id_interno")}
    if not ids:
        for item in itens:
            item["acompanhamento_em"] = None
            item["contato_status"] = ""
        return
    indice = {
        linha.id: linha
        for linha in session.query(LeadLegado).filter(LeadLegado.id.in_(ids)).all()
    }
    for item in itens:
        achado = indice.get(item.get("id_interno"))
        item["acompanhamento_em"] = (
            achado.acompanhamento_em.isoformat() if achado and achado.acompanhamento_em else None
        )
        item["contato_status"] = _texto(achado.contato_status) if achado else ""


def _opcoes_do_banco(session, base) -> Dict[str, List[str]]:
    """Dropdowns a partir do que existe na janela consultada.

    Um `distinct` por campo em vez de montar em Python: sem isso seria preciso carregar
    a janela inteira so para saber quais valores existem — exatamente o custo que a
    mudanca para o banco veio eliminar.
    """
    def distintos(coluna):
        valores = [
            v for (v,) in base.with_entities(coluna).distinct().all()
            if _texto(v)
        ]
        return sorted(valores, key=_norm)

    def na_ordem(coluna, ordem):
        presentes = set(distintos(coluna))
        conhecidos = [v for v in ordem if v in presentes]
        return conhecidos + sorted(presentes - set(ordem), key=_norm)

    return {
        "situacoes": na_ordem(LeadC2S.situacao, ORDEM_SITUACAO),
        "funis": na_ordem(LeadC2S.funil, ORDEM_FUNIL),
        "fontes": distintos(LeadC2S.fonte),
        "canais": distintos(LeadC2S.canal),
        "equipes": distintos(LeadC2S.equipe),
        "motivos": distintos(LeadC2S.motivo_arquivamento),
    }


def listar(solicitante_id, inicio, fim, page=1, per_page=PER_PAGE_API,
           campo_data="created", filtros=None) -> Dict[str, Any]:
    """Leads do espelho local (`leads_c2s`), sincronizado de hora em hora.

    A leitura ao vivo continua em `listar_ao_vivo` e volta com `LEADS_FONTE=api`.

    O que muda para quem usa a tela: `total` passa a ser sempre exato e a resposta chega
    em milissegundos, com qualquer combinacao de filtros. O que se perde: a situacao
    mostrada e a da ultima sincronizacao, nao a do segundo atual — por isso a resposta
    traz `sincronizado_em`, para a tela dizer a idade do dado.
    """
    if _texto(os.getenv("LEADS_FONTE")).lower() == "api":
        return listar_ao_vivo(solicitante_id, inicio, fim, page, per_page, campo_data, filtros)

    filtros = {k: _texto(v) for k, v in (filtros or {}).items()}
    if not inicio or not fim:
        raise LeadC2SErro("Informe o período (início e fim).")
    if campo_data not in {"created", "updated"}:
        campo_data = "created"

    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or PER_PAGE_API), 1), 100)

    session = SessionLocal()
    try:
        escopo = _escopo(session, solicitante_id, filtros.get("equipe"))
        if escopo["equipe"]:
            filtros.pop("equipe", None)
        if escopo["corretor"]:
            filtros.pop("corretor", None)

        query = session.query(LeadC2S)
        # `data` e `criado_em` truncado e indexado; a janela por atualizacao usa a coluna
        # cheia porque o filtro ali e sobre o instante da mudanca.
        if campo_data == "updated":
            query = query.filter(
                LeadC2S.atualizado_em >= f"{inicio} 00:00:00",
                LeadC2S.atualizado_em <= f"{fim} 23:59:59",
            )
        else:
            query = query.filter(LeadC2S.data >= inicio, LeadC2S.data <= fim)

        query = _aplicar_filtros(query, filtros, escopo)

        # `sem_acompanhamento`: o elo com a base interna e o `id_legado`, resolvido no
        # sync. Sem elo o lead nunca teve acompanhamento, entao ele entra no recorte.
        if filtros.get("sem_acompanhamento"):
            com_acomp = [
                i for (i,) in session.query(LeadLegado.id).filter(
                    LeadLegado.acompanhamento_em.isnot(None)
                ).all()
            ]
            if com_acomp:
                query = query.filter(
                    LeadC2S.id_legado.is_(None) | LeadC2S.id_legado.notin_(com_acomp)
                )

        total = query.with_entities(func.count(LeadC2S.id_c2s)).scalar() or 0
        ordem = LeadC2S.atualizado_em if campo_data == "updated" else LeadC2S.criado_em
        linhas = (query.order_by(ordem.desc().nullslast(), LeadC2S.id_c2s)
                  .offset((page - 1) * per_page).limit(per_page).all())

        itens = [_item_do_banco(linha) for linha in linhas]
        _acompanhamento_do_banco(session, itens)

        sincronizado = session.query(func.max(LeadC2S.sincronizado_em)).scalar()
        return {
            "ok": True, "itens": itens, "page": page, "per_page": per_page,
            "total": int(total), "total_c2s": int(total), "total_exato": True,
            "tem_mais": page * per_page < total, "paginas_lidas": 0,
            "fonte": "banco",
            "sincronizado_em": sincronizado.isoformat() if sincronizado else None,
            "opcoes": _opcoes_do_banco(session, query),
        }
    finally:
        session.close()


# Etapas que tem ordem propria: alfabetica aqui atrapalharia ("Arquivado" antes de
# "Novo", "Done visit" antes de "New lead"). Valor fora da lista vai para o fim.
ORDEM_SITUACAO = ["Novo", "Em negociação", "Arquivado"]
ORDEM_FUNIL = ["New lead", "In attendance", "Scheduled visit", "Done visit"]


def catalogo_opcoes() -> Dict[str, Any]:
    """Opcoes fixas dos dropdowns, sem tocar na API do C2S.

    As listas eram montadas a partir do que aparecia na janela consultada. Como a aba
    deixou de buscar sozinha ao abrir, o dropdown de motivo nascia vazio — nao dava para
    escolher um filtro antes da primeira busca. Estes valores sao o catalogo da propria
    C2S, entao valem sempre; o que a janela trouxer de novo e acrescentado por cima.
    """
    return {
        "motivos": sorted(set(MOTIVOS_PT.values()), key=_norm),
        "situacoes": list(ORDEM_SITUACAO),
        "funis": list(ORDEM_FUNIL),
    }


def _opcoes(itens: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Valores presentes na janela, para os dropdowns só oferecerem o que existe."""
    def distintos(campo):
        # `_norm` como chave: `sorted` cru compara code point e joga acento depois do Z
        # ("Órion" cairia atras de "Xavier").
        return sorted({item[campo] for item in itens if item.get(campo)}, key=_norm)

    def na_ordem(campo, ordem):
        presentes = {item[campo] for item in itens if item.get(campo)}
        conhecidos = [v for v in ordem if v in presentes]
        return conhecidos + sorted(presentes - set(ordem), key=_norm)

    return {
        "situacoes": na_ordem("situacao", ORDEM_SITUACAO),
        "funis": na_ordem("funil", ORDEM_FUNIL),
        "fontes": distintos("fonte"),
        "canais": distintos("canal"),
        "equipes": distintos("equipe"),
        # Catalogo fixo primeiro; motivo com texto livre do corretor ("Corretor parceiro
        # — Corretora da Paolla") entra depois, sem sumir da lista.
        "motivos": sorted(
            set(MOTIVOS_PT.values()) | {i["motivo_arquivamento"] for i in itens
                                        if i.get("motivo_arquivamento")},
            key=_norm,
        ),
    }
