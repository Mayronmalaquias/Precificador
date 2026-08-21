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

from app.database import SessionLocal
from app.extensions import cache
from app.models.equipe import Equipe
from app.models.estoque_legado import LeadLegado
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
            status: str = "") -> Dict[str, Any]:
    """Uma pagina crua da API, com cache curto e espera no rate limit."""
    chave = f"c2s:{campo_data}:{inicio}:{fim}:{status}:{page}"
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

def _passa(item: Dict[str, Any], f: Dict[str, str], escopo: Dict[str, Any]) -> bool:
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
    # Acompanhamento e da base interna (chega em `_ids_internos`), nao do C2S — por isso
    # este filtro so existe no caminho de varredura, onde o casamento ja foi feito.
    if f.get("sem_acompanhamento") and item.get("acompanhamento_em"):
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
    locais = ["fonte", "canal", "equipe", "funil", "corretor", "motivo",
              "com_motivo", "sem_acompanhamento", "busca"]
    # Estes tres viram `status` na API; se nao viraram (combinacao sem equivalente),
    # continuam sendo filtro local.
    if not status_api:
        locais += ["situacao", "arquivado", "fechado"]
    elif _norm(f.get("arquivado")) in {"nao", "não", "0", "false"} or             _norm(f.get("fechado")) in {"nao", "não", "0", "false"}:
        locais += ["arquivado", "fechado"]
    return any(_texto(f.get(k)) for k in locais)


# ── casamento com a base interna (para manter o acompanhamento) ─────────────────

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

def listar(solicitante_id, inicio, fim, page=1, per_page=PER_PAGE_API,
           campo_data="created", filtros=None) -> Dict[str, Any]:
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

        if not precisa_local:
            # Caminho normal: a API pagina, filtra por status e conta.
            alvo = _pagina(campo_data, inicio, fim, page, status_api)
            itens = [x for x in (_traduzir(l) for l in alvo["data"]) if x]
            _ids_internos(session, itens)
            total = alvo["total"] or 0
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
            casados.extend(x for x in lote if _passa(x, filtros, escopo))
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
