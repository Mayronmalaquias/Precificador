from __future__ import annotations

import io
import logging
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from app.services.usuarios_service import retornar_lista
from app.services.cliente_acao_service import listar_acoes_clientes
from app.database import SessionLocal
from app.models.imovel import Imovel

load_dotenv()
logger = logging.getLogger(__name__)

API_BASE = (os.getenv("API_BASE") or "").rstrip("/")

# ---------------------------------------------------------------------------
# Constantes de validação
# ---------------------------------------------------------------------------

_TIPOS_RANKING_VALIDOS = frozenset({"visitas", "clientes"})
_TIPO_RANKING_PADRAO = "visitas"
_AGRUPAMENTOS_VALIDOS = frozenset({"dia", "semana", "mes"})
_AGRUPAMENTO_PADRAO = "dia"
_DIMENSOES_EVOLUCAO_VISITAS = frozenset({
    "total", "equipe", "corretor", "proposta", "quartos", "cliente", "imovel", "tipo_captacao",
})

# ---------------------------------------------------------------------------
# Importações reutilizadas do visita_service
# ---------------------------------------------------------------------------

from app.services.visita_service import (
    _get_services,
    _find_or_create_folder,
    _trash_same_name_files_in_folder,
    _safe_str,
    _is_true,
    _find_first_by_key,
    _norm_key,
    SPREADSHEET_ID as VISITAS_SPREADSHEET_ID,
    DRIVE_PARENT_FOLDER_NAME,
)

DRIVE_CORRETOR_REPORTS_SUBFOLDER_NAME = os.getenv(
    "DRIVE_CORRETOR_REPORTS_SUBFOLDER_NAME",
    "Relatorios_Corretor_Gerados",
)

DRIVE_GERENTE_REPORTS_SUBFOLDER_NAME = os.getenv(
    "DRIVE_GERENTE_REPORTS_SUBFOLDER_NAME",
    "Relatorios_Gerente_Gerados",
)

# ---------------------------------------------------------------------------
# Cache thread-safe (lock único cobre leitura + escrita)
# ---------------------------------------------------------------------------

_cache_lock = Lock()
_cache_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
_cache_expires: float = 0.0
_CACHE_TTL_SECONDS = 300
_quartos_cache_lock = Lock()
_quartos_cache: Dict[str, Optional[int]] = {}
_quartos_cache_expires: float = 0.0
_QUARTOS_CACHE_TTL_SECONDS = 3600


# ---------------------------------------------------------------------------
# TypedDicts para mapas internos
# ---------------------------------------------------------------------------

class VisitasMaps(TypedDict):
    corretor_map: Dict[str, Dict[str, Any]]
    gerente_map: Dict[str, Dict[str, Any]]
    cliente_map: Dict[str, Dict[str, Any]]
    parceiro_map: Dict[str, Dict[str, Any]]
    clientes_por_visita: Dict[str, List[Dict[str, Any]]]
    parceiros_por_visita: Dict[str, List[Dict[str, Any]]]
    avaliacoes_por_visita: Dict[str, List[Dict[str, Any]]]


# ---------------------------------------------------------------------------
# Utilitários de data
# ---------------------------------------------------------------------------

def _parse_date_any(v: Any) -> Optional[datetime]:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)

    s = _safe_str(v)
    if not s:
        return None

    formatos = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def _fmt_date(v: Any) -> str:
    dt = _parse_date_any(v)
    return dt.strftime("%d/%m/%Y") if dt else _safe_str(v)


def _fmt_datetime(v: Any) -> str:
    dt = _parse_date_any(v)
    return dt.strftime("%d/%m/%Y %H:%M") if dt else _safe_str(v)


def _display(v: Any, default: str = "—") -> str:
    s = _safe_str(v)
    return s if s else default


def _in_period(row_date: Any, start: Optional[str], end: Optional[str]) -> bool:
    dt = _parse_date_any(row_date)
    if not dt:
        return False
    if start and dt.date() < _parse_date_any(start).date():
        return False
    if end and dt.date() > _parse_date_any(end).date():
        return False
    return True


# ---------------------------------------------------------------------------
# Acesso ao Sheets
# ---------------------------------------------------------------------------

def _batch_get_rows_from_sheet(
    spreadsheet_id: str,
    ranges: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Le do Postgres (substitui o batchGet do Google Sheets). spreadsheet_id
    ignorado - so existe pra nao mudar a assinatura de quem chama isso."""
    from app.services import db_loaders

    out: Dict[str, List[Dict[str, Any]]] = {}
    for rg in ranges:
        sheet_name = rg.split("!")[0]
        out[sheet_name] = db_loaders.carregar_aba(sheet_name)
    return out


# ---------------------------------------------------------------------------
# Cache principal — lock cobre leitura E escrita, eliminando race condition
# ---------------------------------------------------------------------------

def _load_visitas_base(force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    global _cache_data, _cache_expires

    with _cache_lock:
        now = time.time()
        if not force_refresh and _cache_data is not None and now < _cache_expires:
            return _cache_data

        data = _batch_get_rows_from_sheet(
            VISITAS_SPREADSHEET_ID,
            [
                "Dim_Corretor!A1:I",
                "Dim_Gerente!A1:D",
                "Dim_Cliente_Visita!A1:F",
                "Dim_Parceiro_Visita!A1:D",
                "Fato_Visitas!A1:S",
                "Fato_Cliente_Visita!A1:D",
                "Fato_Parceiro_Visita!A1:D",
                "Fato_Avaliacao!A1:N",
            ],
        )
        _cache_data = data
        _cache_expires = time.time() + _CACHE_TTL_SECONDS
        return data


def invalidar_cache_visitas() -> None:
    """Força recarregamento do cache na próxima requisição."""
    global _cache_data, _cache_expires
    with _cache_lock:
        _cache_data = None
        _cache_expires = 0.0


def _listar_usuarios_ativos() -> List[Dict[str, Any]]:
    return retornar_lista(
        ativo=True,
        page=1,
        per_page=100000,
    ).get("lista", [])


def _listar_usuarios_todos() -> List[Dict[str, Any]]:
    """Ativos E inativos.

    Visita de corretor desligado continua sendo visita do periodo, entao o
    escopo do painel nao pode depender de `ativo` — senao o total de visitas
    diverge do painel do diretor.
    """
    return retornar_lista(
        ativo=None,
        page=1,
        per_page=100000,
    ).get("lista", [])


def _usuario_label(user: Dict[str, Any]) -> str:
    return _safe_str(user.get("nome")) or _safe_str(user.get("username")) or _safe_str(user.get("id_usuarios"))


def _usuario_lookup(incluir_inativos: bool = False) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    usuarios = _listar_usuarios_todos() if incluir_inativos else _listar_usuarios_ativos()
    por_id = {
        _safe_str(u.get("id_usuarios")): u
        for u in usuarios
        if _safe_str(u.get("id_usuarios"))
    }
    por_time: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for u in usuarios:
        team = _safe_str(u.get("team"))
        if team:
            por_time[team].append(u)
    return por_id, por_time


def _resolver_ids_corretor_gestao(
    usuario_id: str,
    permissao: str,
    team: str = "",
    escopo: str = "",
    id_corretor: str = "",
    id_gerente: str = "",
) -> Tuple[set, List[Dict[str, Any]], Dict[str, Any]]:
    usuario_id = _safe_str(usuario_id)
    permissao = _safe_str(permissao).lower()
    team = _safe_str(team)
    escopo = _safe_str(escopo).lower() or "auto"
    id_corretor = _safe_str(id_corretor)
    id_gerente = _safe_str(id_gerente)

    # Inclui inativos: visita de corretor desligado continua contando no periodo.
    usuario_map, usuarios_por_time = _usuario_lookup(incluir_inativos=True)

    if permissao in {"diretor", "administrativo"} or team.lower() == "administrativo":
        if escopo == "corretor" and id_corretor:
            ids = {id_corretor}
            modo = "corretor"
        elif escopo == "equipe" and id_gerente:
            ids = {_safe_str(u.get("id_usuarios")) for u in usuarios_por_time.get(id_gerente, []) if _safe_str(u.get("id_usuarios"))}
            modo = "equipe"
        else:
            # Visao 61 = todo mundo, sem filtrar por permissao. Visita lancada por
            # gerente/assistente/diretor tambem e visita do periodo — o painel do
            # diretor ja as conta, e os dois numeros precisam bater.
            ids = {
                _safe_str(u.get("id_usuarios"))
                for u in usuario_map.values()
                if _safe_str(u.get("id_usuarios"))
            }
            modo = "61"
    elif permissao in {"gerente", "administrador"}:
        # A equipe do gerente é o `team` dele (corretores compartilham esse team), NÃO o
        # usuario_id — ex.: Fernando id=C61134 mas team=G61017. usuarios_por_time é indexado
        # por team, então escopamos por team (fallback usuario_id p/ legado id==team).
        gerente_id = team or usuario_id
        ids_equipe = {_safe_str(u.get("id_usuarios")) for u in usuarios_por_time.get(gerente_id, []) if _safe_str(u.get("id_usuarios"))}
        if escopo == "corretor" and id_corretor and id_corretor in ids_equipe:
            ids = {id_corretor}
            modo = "corretor"
        else:
            ids = ids_equipe
            modo = "equipe"
    else:
        ids = {usuario_id} if usuario_id else set()
        modo = "corretor"

    # O DROPDOWN mostra so quem esta ativo; `ids` acima continua com os inativos.
    #
    # Sao duas perguntas diferentes que nasciam da mesma variavel: "de quem contar os
    # dados" (tem que incluir desligado — visita dele continua sendo visita do periodo,
    # e tirar da conta faria o total divergir do painel do diretor) e "quem cabe escolher
    # no filtro" (nao adianta oferecer quem nao trabalha mais aqui).
    #
    # Medido em 28/08/2026: o diretor via 267 opcoes, 175 delas de gente desligada.
    corretores = []
    for cid in sorted(ids):
        u = usuario_map.get(cid, {})
        # O ja selecionado fica na lista mesmo inativo: sem esta excecao, abrir a tela
        # com um corretor desligado escolhido deixaria o filtro valendo e o select em
        # branco — e no escopo "corretor" a lista viria vazia.
        if not u.get("ativo") and cid != id_corretor:
            continue
        corretores.append({
            "id_corretor": cid,
            "nome": _usuario_label(u),
            "team": _safe_str(u.get("team")),
            "permissao": _safe_str(u.get("permissao")),
            # A tela pode marcar o desligado que sobrou por estar selecionado.
            "ativo": bool(u.get("ativo")),
        })

    meta = {
        "modo": modo,
        "usuario_id": usuario_id,
        "permissao": permissao,
        "team": team,
        "ids_corretor": sorted(ids),
    }
    return ids, corretores, meta


def _media(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 1) if values else None


def _nota_float(value: Any) -> Optional[float]:
    s = _safe_str(value).replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def gestao_clientes_visitas(
    usuario_id: str,
    permissao: str,
    team: str = "",
    escopo: str = "",
    id_corretor: str = "",
    id_gerente: str = "",
    q: str = "",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    data = _load_visitas_base()
    maps = _build_maps(data)
    ids_corretor, corretores_disponiveis, meta = _resolver_ids_corretor_gestao(
        usuario_id=usuario_id,
        permissao=permissao,
        team=team,
        escopo=escopo,
        id_corretor=id_corretor,
        id_gerente=id_gerente,
    )

    fato_visitas = data.get("Fato_Visitas", [])
    dim_clientes = data.get("Dim_Cliente_Visita", [])
    cliente_map = maps["cliente_map"]
    cliente_visitas = maps["clientes_por_visita"]
    avaliacoes_por_visita = maps["avaliacoes_por_visita"]

    usuario_map, _ = _usuario_lookup()
    qn = _norm_key(q)

    clientes: Dict[str, Dict[str, Any]] = {}
    for row in dim_clientes:
        id_cliente = _safe_str(row.get("Id_Cliente"))
        id_cli_corretor = _safe_str(row.get("Id_Corretor"))
        if not id_cliente or id_cli_corretor not in ids_corretor:
            continue
        clientes[id_cliente] = {
            "id_cliente": id_cliente,
            "nome": _safe_str(row.get("Nome_Cliente")),
            "telefone": _safe_str(row.get("Telefone_Cliente")),
            "email": _safe_str(row.get("Email_Cliente")),
            "id_corretor": id_cli_corretor,
            "corretor": _usuario_label(usuario_map.get(id_cli_corretor, {})),
            "visitas": [],
            "notas": [],
            "propostas": Counter(),
            "motivos_talvez": [],
            "motivos_sim": [],
            "ultima_data_ord": None,
        }

    visitas_por_dia: Counter = Counter()
    propostas_total: Counter = Counter()
    clientes_com_proposta = set()
    clientes_no_periodo: set = set()
    periodo_definido = bool(start or end)

    for visita in fato_visitas:
        id_visita = _safe_str(visita.get("Id_Visita"))
        id_visit_corretor = _safe_str(visita.get("Id_Corretor"))
        if not id_visita or id_visit_corretor not in ids_corretor:
            continue

        data_visita = _fmt_date(visita.get("Data_Visita"))
        data_ord = _parse_date_any(visita.get("Data_Visita"))
        visita_no_periodo = _in_period(visita.get("Data_Visita"), start, end)
        proposta = _safe_str(visita.get("Proposta")) or "Sem informacao"
        id_imovel = _safe_str(visita.get("Id_Imovel"))
        endereco_externo = _safe_str(visita.get("Endereco_Externo"))
        motivo_talvez = (
            _safe_str(visita.get("Motivo_Talvez"))
            or _safe_str(visita.get("Motivo Talvez"))
            or _safe_str(visita.get("Motivo_Talvez_Proposta"))
        )
        motivo_sim = _safe_str(visita.get("Motivo_Sim"))
        anexo_ficha = _safe_str(visita.get("Anexo_Ficha_Visita"))
        notas_visita = _safe_str(visita.get("AudiodescricaoClienteVisita"))
        if visita_no_periodo:
            if data_ord:
                visitas_por_dia[data_ord.strftime("%Y-%m-%d")] += 1
            propostas_total[proposta] += 1

        ids_cliente = [
            _safe_str(fc.get("Id_Cliente"))
            for fc in cliente_visitas.get(id_visita, [])
            if _safe_str(fc.get("Id_Cliente"))
        ]
        fallback_cliente = _safe_str(visita.get("Id_Cliente_Assinante"))
        if fallback_cliente and fallback_cliente not in ids_cliente:
            ids_cliente.append(fallback_cliente)

        notas_por_cliente: Dict[str, List[float]] = defaultdict(list)
        avaliacoes_payload = []
        for av in avaliacoes_por_visita.get(id_visita, []):
            cid = _safe_str(av.get("Id_Cliente"))
            nota = _nota_float(av.get("Nota_Geral"))
            if nota is not None:
                notas_por_cliente[cid].append(nota)
            avaliacoes_payload.append({
                # Sem o id, `editar_visita` PULA a avaliacao (`if not id_av: continue`) —
                # editar as notas por esta tela salvava silenciosamente nada.
                "id_avaliacao": _safe_str(av.get("id_Avaliacao")),
                "id_cliente": cid,
                "cliente": _safe_str((cliente_map.get(cid) or {}).get("Nome_Cliente")),
                "notaGeral": _safe_str(av.get("Nota_Geral")),
                "localizacao": _safe_str(av.get("Localizacao")),
                "tamanho": _safe_str(av.get("Tamanho")),
                "planta": _safe_str(av.get("Planta_Imovel")),
                "acabamento": _safe_str(av.get("Qualidade_Acabamento")),
                "conservacao": _safe_str(av.get("Estado_Conservacao")),
                "condominio": _safe_str(av.get("Condominio_AreaComun")),
                "preco": _safe_str(av.get("Preco")),
                "precoNota10": _safe_str(av.get("Preco_N10")),
            })

        for cid in ids_cliente:
            cli = clientes.get(cid)
            if not cli:
                base = cliente_map.get(cid, {})
                clientes[cid] = cli = {
                    "id_cliente": cid,
                    "nome": _safe_str(base.get("Nome_Cliente")),
                    "telefone": _safe_str(base.get("Telefone_Cliente")),
                    "email": _safe_str(base.get("Email_Cliente")),
                    "id_corretor": id_visit_corretor,
                    "corretor": _usuario_label(usuario_map.get(id_visit_corretor, {})),
                    "visitas": [],
                    "notas": [],
                    "propostas": Counter(),
                    "motivos_talvez": [],
                    "motivos_sim": [],
                    "ultima_data_ord": None,
                }

            if visita_no_periodo:
                clientes_no_periodo.add(cid)

            notas_cliente = notas_por_cliente.get(cid, [])
            cli["notas"].extend(notas_cliente)
            cli["propostas"][proposta] += 1
            if proposta.strip().lower() in {"talvez", "talves"} and motivo_talvez:
                cli["motivos_talvez"].append({
                    "motivo": motivo_talvez,
                    "id_imovel": id_imovel,
                    "endereco_externo": endereco_externo,
                    "id_visita": id_visita,
                })
            if motivo_sim and proposta.strip().lower() not in {
                "", "nao", "não", "talvez", "talves", "sem informacao", "sem informação"
            }:
                cli["motivos_sim"].append({
                    "motivo": motivo_sim,
                    "id_imovel": id_imovel,
                    "endereco_externo": endereco_externo,
                    "id_visita": id_visita,
                })
            if proposta.strip().lower() not in {"", "nao", "não", "sem informacao", "sem informação"}:
                clientes_com_proposta.add(cid)
            if data_ord and (cli["ultima_data_ord"] is None or data_ord > cli["ultima_data_ord"]):
                cli["ultima_data_ord"] = data_ord

            cli["visitas"].append({
                "id_visita": id_visita,
                "data_visita": data_visita,
                # Marca se a visita cai no periodo filtrado. A lista mantem o
                # historico completo do cliente (util no detalhe), mas
                # `qtd_visitas` conta so o periodo — senao o total do painel
                # nao bate com o do diretor.
                "no_periodo": visita_no_periodo,
                "id_imovel": _safe_str(visita.get("Id_Imovel")),
                "endereco_externo": _safe_str(visita.get("Endereco_Externo")),
                "id_corretor": id_visit_corretor,
                "corretor": _usuario_label(usuario_map.get(id_visit_corretor, {})),
                "id_gerente_corretor": _safe_str((usuario_map.get(id_visit_corretor, {}) or {}).get("team")),
                "proposta": proposta,
                "motivo_talvez": motivo_talvez,
                "motivo_sim": motivo_sim,
                "anexo_ficha": anexo_ficha,
                # `Anexo_Ficha_Visita` NAO e URL: e caminho relativo herdado do AppSheet
                # ("Fato_Visitas_PDF/C61166_..._anexo.jpg") — 0 de 2.317 linhas comecam
                # com http. O anexo que abre de verdade e `Link_Imagem` (2.304 URLs do
                # Drive). Por isso a tela usa este campo para o botao "Ver anexo".
                "link_imagem": _safe_str(visita.get("Link_Imagem")),
                "link_audio": _safe_str(visita.get("Link_Audio")),
                # Derivado, nao coluna: a escrita aceita quatro valores mas grava so dois
                # estados (`Tipo_Captacao` preenchido ou `Imovel_Nao_Captado`), entao
                # CAPTACAO_61 / _PROPRIA / _PARCEIRO colapsam num so. Devolver o estado
                # real evita o modal mostrar uma escolha que o banco nao guarda.
                "situacao_imovel": ("IMOVEL_NAO_CAPTADO"
                                    if _is_true(visita.get("Imovel_Nao_Captado"))
                                    else ("CAPTACAO_61"
                                          if _safe_str(visita.get("Tipo_Captacao")) else "")),
                "anexo_ficha_visita": anexo_ficha,
                "notas": notas_visita,
                "nota_media": _media(notas_cliente),
                "avaliacoes": [a for a in avaliacoes_payload if not a["id_cliente"] or a["id_cliente"] == cid],
                "pdf_download_url": f"{API_BASE}/visitas/pdf/download?visita_id={id_visita}",
            })

    rows = []
    for cli in clientes.values():
        if periodo_definido and cli["id_cliente"] not in clientes_no_periodo:
            continue
        visitas = sorted(
            cli["visitas"],
            key=lambda v: _parse_date_any(v.get("data_visita")) or datetime.min,
            reverse=True,
        )
        row = {
            "id_cliente": cli["id_cliente"],
            "nome": cli["nome"],
            "telefone": cli["telefone"],
            "email": cli["email"],
            "id_corretor": cli["id_corretor"],
            "corretor": cli["corretor"],
            # So o periodo filtrado. Sem periodo, cai no historico inteiro.
            "qtd_visitas": sum(1 for v in visitas if v.get("no_periodo")) if periodo_definido else len(visitas),
            "qtd_visitas_historico": len(visitas),
            "ultima_visita": cli["ultima_data_ord"].strftime("%d/%m/%Y") if cli["ultima_data_ord"] else "",
            "nota_media": _media(cli["notas"]),
            "houve_proposta": any(k.strip().lower() not in {"", "nao", "não", "sem informacao", "sem informação"} for k in cli["propostas"]),
            "propostas": dict(cli["propostas"]),
            "motivos_talvez": cli["motivos_talvez"],
            "motivos_sim": cli["motivos_sim"],
            "visitas": visitas,
            "pdf_download_url": f"{API_BASE}/clientes/pdf/download?id_cliente={cli['id_cliente']}",
        }
        hay = " ".join([
            row["id_cliente"], row["nome"], row["telefone"], row["email"],
            row["corretor"], row["ultima_visita"],
        ])
        if qn and qn not in _norm_key(hay):
            continue
        rows.append(row)

    rows.sort(
        key=lambda item: (
            item.get("qtd_visitas", 0),
            _parse_date_any(item.get("ultima_visita")) or datetime.min,
            item.get("nome", ""),
        ),
        reverse=True,
    )
    if limit:
        rows = rows[: max(1, int(limit))]

    # flags de revisao do gerente por visita (importante p/ o diretor)
    try:
        from app.services.visita_vistas_service import mapa_flags_por_visitas
        ids_vis = [v["id_visita"] for r in rows for v in r.get("visitas", []) if v.get("id_visita")]
        fmap = mapa_flags_por_visitas(ids_vis)
        _default_flags = {"visto": False, "viu_anexo": False, "viu_notas": False, "add_motivo": False}
        for r in rows:
            for v in r.get("visitas", []):
                v["flags"] = fmap.get(v["id_visita"], dict(_default_flags))
    except Exception:
        pass

    serie_clientes = Counter()
    for cli in rows:
        data_ultima = _parse_date_any(cli.get("ultima_visita"))
        if data_ultima:
            serie_clientes[data_ultima.strftime("%Y-%m-%d")] += 1

    acoes_por_cliente = listar_acoes_clientes(item["id_cliente"] for item in rows)
    for row in rows:
        row["acoes"] = acoes_por_cliente.get(row["id_cliente"], [])

    # ── analises de carteira ───────────────────────────────────────────────────
    # Todas derivam de `rows` (ja recortado pelo periodo e pelo escopo), nunca dos
    # acumuladores brutos — foi assim que `clientes_com_proposta` passou a contar 178
    # de 92 clientes: ele somava o historico inteiro contra um total ja filtrado.
    ids_no_resultado = {item["id_cliente"] for item in rows}
    com_proposta_no_resultado = clientes_com_proposta & ids_no_resultado

    # Recorrencia: faixas disjuntas ("6+" e estritamente acima de 5, senao um cliente
    # com 6 visitas cairia em duas faixas e o percentual passaria de 100%).
    faixas_recorrencia = [("1 visita", 1, 1), ("2 visitas", 2, 2),
                          ("3 a 5", 3, 5), ("6 ou mais", 6, None)]
    recorrencia = []
    for rotulo, minimo, maximo in faixas_recorrencia:
        total = sum(1 for item in rows
                    if item["qtd_visitas"] >= minimo
                    and (maximo is None or item["qtd_visitas"] <= maximo))
        recorrencia.append({"faixa": rotulo, "total": total})

    # Faixas de nota do imovel. Cliente sem avaliacao fica de fora em vez de virar zero:
    # "nao avaliou" nao e a mesma coisa que "avaliou mal".
    faixas_nota = [("Ate 5", 0, 5), ("5 a 7", 5, 7), ("7 a 8,5", 7, 8.5), ("8,5 a 10", 8.5, 10.01)]
    notas = []
    for rotulo, minimo, maximo in faixas_nota:
        total = sum(1 for item in rows
                    if item.get("nota_media") is not None
                    and minimo <= float(item["nota_media"]) < maximo)
        notas.append({"faixa": rotulo, "total": total})
    sem_nota = sum(1 for item in rows if item.get("nota_media") is None)

    # Conversao por corretor: quem transforma visita em interesse (SIM ou TALVEZ).
    por_corretor: Dict[str, Dict[str, Any]] = {}
    for item in rows:
        chave = item.get("corretor") or "Sem corretor"
        alvo = por_corretor.setdefault(chave, {"corretor": chave, "clientes": 0,
                                               "visitas": 0, "com_interesse": 0})
        alvo["clientes"] += 1
        alvo["visitas"] += item["qtd_visitas"]
        if item.get("houve_proposta"):
            alvo["com_interesse"] += 1
    for alvo in por_corretor.values():
        alvo["taxa"] = round(alvo["com_interesse"] / alvo["clientes"] * 100, 1) if alvo["clientes"] else 0.0
    ranking_corretor = sorted(por_corretor.values(),
                              key=lambda x: (-x["clientes"], x["corretor"]))[:10]

    # Carteira parada: cliente cuja ultima visita ja passou do corte. E o numero que
    # vira acao — os outros sao diagnostico.
    hoje_ref = date.today()
    def _dias_desde(item):
        d = _parse_date_any(item.get("ultima_visita"))
        # _parse_date_any devolve datetime; subtrair de um date levanta TypeError.
        return (hoje_ref - d.date()).days if d else None

    cortes = [("Ate 15 dias", 0, 15), ("16 a 30", 16, 30), ("31 a 60", 31, 60), ("Mais de 60", 61, None)]
    sem_retorno = []
    for rotulo, minimo, maximo in cortes:
        total = 0
        for item in rows:
            dias = _dias_desde(item)
            if dias is None:
                continue
            if dias >= minimo and (maximo is None or dias <= maximo):
                total += 1
        sem_retorno.append({"faixa": rotulo, "total": total})

    return {
        "ok": True,
        "meta": meta,
        "corretores": corretores_disponiveis,
        "clientes": rows,
        "dashboard": {
            "total_clientes": len(rows),
            "total_visitas": sum(item["qtd_visitas"] for item in rows),
            "clientes_com_proposta": len(com_proposta_no_resultado),
            "recorrencia": recorrencia,
            "notas_faixa": notas,
            "clientes_sem_nota": sem_nota,
            "ranking_corretor": ranking_corretor,
            "sem_retorno": sem_retorno,
            "nota_media_geral": _media([n for item in clientes.values() for n in item["notas"]]),
            "propostas": dict(propostas_total),
            "clientes_por_dia": [
                {"data": key, "label": _parse_date_any(key).strftime("%d/%m") if _parse_date_any(key) else key, "total": serie_clientes[key]}
                for key in sorted(serie_clientes)
            ],
            "visitas_por_dia": [
                {"data": key, "label": _parse_date_any(key).strftime("%d/%m") if _parse_date_any(key) else key, "total": visitas_por_dia[key]}
                for key in sorted(visitas_por_dia)
            ],
        },
    }


# ---------------------------------------------------------------------------
# Construção dos mapas — chamada única por fluxo
# ---------------------------------------------------------------------------

def _build_maps(data: Dict[str, List[Dict[str, Any]]]) -> VisitasMaps:
    dim_corretor = data.get("Dim_Corretor", [])
    dim_gerente = data.get("Dim_Gerente", [])
    dim_cliente = data.get("Dim_Cliente_Visita", [])
    dim_parceiro = data.get("Dim_Parceiro_Visita", [])
    fato_cliente = data.get("Fato_Cliente_Visita", [])
    fato_parceiro = data.get("Fato_Parceiro_Visita", [])
    fato_avaliacao = data.get("Fato_Avaliacao", [])

    corretor_map = {
        _safe_str(r.get("IdCorretor")): r
        for r in dim_corretor
        if _safe_str(r.get("IdCorretor"))
    }
    gerente_map = {
        _safe_str(r.get("IdGerente")): r
        for r in dim_gerente
        if _safe_str(r.get("IdGerente"))
    }
    cliente_map = {
        _safe_str(r.get("Id_Cliente")): r
        for r in dim_cliente
        if _safe_str(r.get("Id_Cliente"))
    }
    parceiro_map = {
        _safe_str(r.get("Id_Parceiro")): r
        for r in dim_parceiro
        if _safe_str(r.get("Id_Parceiro"))
    }

    clientes_por_visita: Dict[str, List] = defaultdict(list)
    for r in fato_cliente:
        id_visita = _safe_str(r.get("Id_Visita"))
        if id_visita:
            clientes_por_visita[id_visita].append(r)

    parceiros_por_visita: Dict[str, List] = defaultdict(list)
    for r in fato_parceiro:
        id_visita = _safe_str(r.get("Id_Visita"))
        if id_visita:
            parceiros_por_visita[id_visita].append(r)

    avaliacoes_por_visita: Dict[str, List] = defaultdict(list)
    for r in fato_avaliacao:
        id_visita = _safe_str(r.get("Id_Visita"))
        if id_visita:
            avaliacoes_por_visita[id_visita].append(r)

    return VisitasMaps(
        corretor_map=corretor_map,
        gerente_map=gerente_map,
        cliente_map=cliente_map,
        parceiro_map=parceiro_map,
        clientes_por_visita=clientes_por_visita,
        parceiros_por_visita=parceiros_por_visita,
        avaliacoes_por_visita=avaliacoes_por_visita,
    )


# ---------------------------------------------------------------------------
# Helpers de PDF — fpdf2, padrão visual 61 Imóveis
# ---------------------------------------------------------------------------

_LOGO_PATH_PDF = "./app/utils/asserts/logo_61.png"
_PINK       = (225, 0, 91)
_DARK       = (40, 40, 40)
_GRAY       = (110, 110, 110)
_LIGHT_GRAY = (248, 248, 248)
_WHITE      = (255, 255, 255)

_PDF_CHAR_MAP = {
    "—": "-",   # em dash —
    "–": "-",   # en dash –
    "‘": "'",   # aspas simples esquerda
    "’": "'",   # aspas simples direita
    "“": '"',   # aspas duplas esquerda
    "”": '"',   # aspas duplas direita
    "…": "...", # reticências
    "â": "a",   # â
    "ã": "a",   # ã — fpdf2 com fonte core nao suporta
    "ç": "c",   # ç
    "é": "e",   # é
    "ê": "e",   # ê
    "í": "i",   # í
    "ó": "o",   # ó
    "ô": "o",   # ô
    "õ": "o",   # õ
    "ú": "u",   # ú
    "ü": "u",   # ü
    "Â": "A",
    "Ã": "A",
    "Ç": "C",
    "É": "E",
    "Ê": "E",
    "Ó": "O",
    "Ô": "O",
    "Õ": "O",
    "Ú": "U",
}


def _pt(text: str) -> str:
    """Converte texto para latin-1 compatível com as fontes core do fpdf2."""
    for src, dst in _PDF_CHAR_MAP.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _Pdf61:
    """Wrapper fino sobre FPDF com cabeçalho/rodapé padrão 61 Imóveis."""

    def __init__(self, titulo: str, subtitulo: str = ""):
        from fpdf import FPDF  # type: ignore

        class _Doc(FPDF):
            pass

        self._titulo    = titulo
        self._subtitulo = subtitulo
        self._fpdf: FPDF = _Doc(orientation="P", unit="mm", format="A4")
        self._fpdf.set_margins(15, 30, 15)
        self._fpdf.set_auto_page_break(auto=True, margin=18)
        # Armazena referência para que o header possa usar self
        self._fpdf._wrapper = self  # type: ignore[attr-defined]
        self._setup_callbacks()

    def _setup_callbacks(self):
        wrapper = self

        def _header(this):
            if os.path.exists(_LOGO_PATH_PDF):
                this.image(_LOGO_PATH_PDF, x=15, y=8, h=10)

            this.set_font("Arial", "B", 12)
            this.set_text_color(*_PINK)
            this.set_xy(15, 8)
            this.cell(0, 6, _pt(wrapper._titulo), align="R")

            if wrapper._subtitulo:
                this.set_font("Arial", "", 8)
                this.set_text_color(*_GRAY)
                this.set_xy(15, 15)
                this.cell(0, 5, _pt(wrapper._subtitulo), align="R")

            this.set_draw_color(*_PINK)
            this.set_line_width(0.4)
            this.line(15, 23, 195, 23)
            this.set_xy(15, 27)

        def _footer(this):
            this.set_y(-12)
            this.set_font("Arial", "", 7)
            this.set_text_color(*_GRAY)
            this.cell(
                0, 4,
                f"61 Imoveis  ·  Gerado em: {date.today().strftime('%d/%m/%Y')}  ·  Pagina {this.page_no()}",
                align="C",
            )

        import types
        self._fpdf.header = types.MethodType(_header, self._fpdf)  # type: ignore[method-assign]
        self._fpdf.footer = types.MethodType(_footer, self._fpdf)  # type: ignore[method-assign]

    def add_page(self):
        self._fpdf.add_page()

    def section(self, titulo: str):
        self._fpdf.ln(2)
        self._fpdf.set_font("Arial", "B", 9)
        self._fpdf.set_fill_color(*_PINK)
        self._fpdf.set_text_color(*_WHITE)
        self._fpdf.cell(0, 7, _pt(f"  {titulo}"), border=0, fill=True, ln=1)
        self._fpdf.ln(1)

    def info_rows(self, rows: List[List[str]]):
        """Tabela de duas colunas: label | valor."""
        pdf = self._fpdf
        pdf.set_draw_color(220, 220, 220)
        pdf.set_line_width(0.2)
        fill = False
        for label, valor in rows:
            pdf.set_font("Arial", "B", 8)
            pdf.set_fill_color(*_LIGHT_GRAY)
            pdf.set_text_color(*_GRAY)
            pdf.cell(55, 6.5, _pt(f"  {label}"), border=1, fill=fill, align="L")
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(*_DARK)
            pdf.cell(125, 6.5, _pt(f"  {valor}"), border=1, fill=fill, align="L")
            pdf.ln()
            fill = not fill
        pdf.ln(2)

    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        col_widths: List[float],
        row_h: float = 6.0,
    ):
        pdf = self._fpdf
        pdf.set_font("Arial", "B", 7.5)
        pdf.set_fill_color(*_PINK)
        pdf.set_text_color(*_WHITE)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.2)
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 7, _pt(f"  {h}"), border=1, fill=True, align="L")
        pdf.ln()

        pdf.set_font("Arial", "", 7.5)
        pdf.set_text_color(*_DARK)
        fill = False
        for row in rows:
            pdf.set_fill_color(*_LIGHT_GRAY)
            for val, w in zip(row, col_widths):
                pdf.cell(w, row_h, _pt(f"  {str(val)}"), border=1, fill=fill, align="L")
            pdf.ln()
            fill = not fill
        pdf.ln(2)

    def to_bytes(self) -> bytes:
        out = self._fpdf.output()
        if isinstance(out, (bytearray, bytes)):
            return bytes(out)
        return out.encode("latin-1")


def _pdf_upload_to_drive(
    pdf_bytes: bytes,
    file_name: str,
    subfolder_name: str,
    entity_id: str,
) -> Dict[str, str]:
    """Faz upload de um PDF para o Drive, torna público e retorna metadados."""
    from googleapiclient.http import MediaIoBaseUpload

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    reports_folder_id = _find_or_create_folder(subfolder_name, parent_id=root_folder_id)
    entity_folder_id = _find_or_create_folder(entity_id, parent_id=reports_folder_id)

    _trash_same_name_files_in_folder(entity_folder_id, file_name)

    _, drive_files, drive = _get_services()
    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False,
    )
    created = drive_files.create(
        body={"name": file_name, "parents": [entity_folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    try:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception as exc:
        logger.warning("Falha ao tornar arquivo público no Drive: %s", exc)

    drive_path = f"{DRIVE_PARENT_FOLDER_NAME}/{subfolder_name}/{entity_id}/{file_name}"
    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": drive_path,
    }


# ---------------------------------------------------------------------------
# Listagens públicas
# ---------------------------------------------------------------------------

def listar_corretores_do_gerente(
    id_gerente: str,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    usuarios_ativos = retornar_lista(
        id_gerente=id_gerente,
        ativo=True,
        page=1,
        per_page=100000,
    ).get("lista", [])

    lista = [
        {
            "IdCorretor": _safe_str(u.get("id_usuarios")),
            "Nome": _safe_str(u.get("nome")),
            "IdGerente": _safe_str(u.get("team")),
            "Ativo": u.get("ativo"),
        }
        for u in usuarios_ativos
    ]
    lista.sort(key=lambda x: _safe_str(x.get("Nome")).lower())
    return lista


def listar_visitas_do_gerente(
    id_gerente: str,
    q: str = "",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    maps: Optional[VisitasMaps] = None,
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    maps = maps or _build_maps(data)

    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    cliente_map = maps["cliente_map"]
    parceiro_map = maps["parceiro_map"]
    clientes_por_visita = maps["clientes_por_visita"]
    parceiros_por_visita = maps["parceiros_por_visita"]
    avaliacoes_por_visita = maps.get("avaliacoes_por_visita", {})

    qn = _norm_key(q)
    lista = []

    for visita in fato_visitas:
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        corretor = corretor_map.get(id_corretor)
        if not corretor:
            continue
        if _safe_str(corretor.get("IdGerente")) != _safe_str(id_gerente):
            continue
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue

        visita_id = _safe_str(visita.get("Id_Visita"))

        nomes_clientes: List[str] = []
        for fc in clientes_por_visita.get(visita_id, []):
            cli = cliente_map.get(_safe_str(fc.get("Id_Cliente")))
            nome = _safe_str((cli or {}).get("Nome_Cliente"))
            if nome and nome not in nomes_clientes:
                nomes_clientes.append(nome)

        nomes_parceiros: List[str] = []
        for fp in parceiros_por_visita.get(visita_id, []):
            par = parceiro_map.get(_safe_str(fp.get("Id_Parceiro")))
            nome = _safe_str((par or {}).get("Nome_Parceiro"))
            if nome and nome not in nomes_parceiros:
                nomes_parceiros.append(nome)

        avaliacoes = []
        for av in avaliacoes_por_visita.get(visita_id, []):
            cid = _safe_str(av.get("Id_Cliente"))
            cli = cliente_map.get(cid)
            avaliacoes.append({
                "id_avaliacao": _safe_str(av.get("Id_Avaliacao")),
                "id_cliente": cid,
                "cliente": _safe_str((cli or {}).get("Nome_Cliente")),
                "localizacao": _safe_str(av.get("Localizacao")),
                "tamanho": _safe_str(av.get("Tamanho")),
                "planta": _safe_str(av.get("Planta_Imovel")),
                "acabamento": _safe_str(av.get("Qualidade_Acabamento")),
                "conservacao": _safe_str(av.get("Estado_Conservacao")),
                "condominio": _safe_str(av.get("Condominio_AreaComun")),
                "preco": _safe_str(av.get("Preco")),
                "notaGeral": _safe_str(av.get("Nota_Geral")),
                "precoNota10": _safe_str(av.get("Preco_N10")),
            })

        motivo_talvez = (
            _safe_str(visita.get("Motivo_Talvez"))
            or _safe_str(visita.get("Motivo Talvez"))
            or _safe_str(visita.get("Motivo_Talvez_Proposta"))
        )
        motivo_sim = _safe_str(visita.get("Motivo_Sim"))
        anexo_ficha = _safe_str(visita.get("Anexo_Ficha_Visita"))
        notas_cliente_visita = _safe_str(visita.get("AudiodescricaoClienteVisita"))

        item = {
            "id_visita": visita_id,
            "id_imovel": _safe_str(visita.get("Id_Imovel")),
            "data_visita": _fmt_date(visita.get("Data_Visita")),
            "created_at": _fmt_datetime(visita.get("CreatedAt")),
            "corretor": _safe_str(corretor.get("Nome")),
            "id_corretor": id_corretor,
            "id_gerente_corretor": _safe_str(corretor.get("IdGerente")),
            "clientes": nomes_clientes,
            "parceiros": nomes_parceiros,
            "endereco_externo": _safe_str(visita.get("Endereco_Externo")),
            "tipo_captacao": _safe_str(visita.get("Tipo_Captacao")),
            "proposta": _safe_str(visita.get("Proposta")),
            "motivo_talvez": motivo_talvez,
            "motivoTalvez": motivo_talvez,
            "motivo_sim": motivo_sim,
            "motivoSim": motivo_sim,
            "anexo_ficha": anexo_ficha,
            "notas": notas_cliente_visita,
            "visita_com_parceiro": _is_true(visita.get("Visita_Com_Parceiro")),
            "imovel_nao_captado": _is_true(visita.get("Imovel_Nao_Captado")),
            "revisita": _is_true(visita.get("Revisita")),
            "avaliacoes": avaliacoes,
            "pdf_url": f"{API_BASE}/visitas/pdf?visita_id={visita_id}",
            "pdf_download_url": f"{API_BASE}/visitas/pdf/download?visita_id={visita_id}",
        }

        if qn:
            hay = " ".join([
                item["id_visita"], item["id_imovel"], item["data_visita"],
                item["corretor"], item["endereco_externo"], item["tipo_captacao"],
                item["proposta"], item["motivo_talvez"], " ".join(item["clientes"]), " ".join(item["parceiros"]),
            ])
            if qn not in _norm_key(hay):
                continue

        lista.append(item)

    lista.sort(
        key=lambda x: (
            _parse_date_any(x.get("data_visita")) or datetime.min,
            x.get("created_at", ""),
        ),
        reverse=True,
    )
    return lista[: max(1, int(limit or 100))]


def listar_clientes_do_gerente(
    id_gerente: str,
    q: str = "",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 200,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    maps: Optional[VisitasMaps] = None,
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    maps = maps or _build_maps(data)

    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    cliente_map = maps["cliente_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    visitas_validas: Dict[str, Dict] = {}
    for visita in fato_visitas:
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        corretor = corretor_map.get(id_corretor)
        if not corretor:
            continue
        if _safe_str(corretor.get("IdGerente")) != _safe_str(id_gerente):
            continue
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue
        visitas_validas[_safe_str(visita.get("Id_Visita"))] = {
            "visita": visita,
            "corretor": corretor,
        }

    agrupado: Dict[str, Dict] = {}
    for id_visita, payload in visitas_validas.items():
        visita = payload["visita"]
        corretor = payload["corretor"]

        for fc in clientes_por_visita.get(id_visita, []):
            id_cliente = _safe_str(fc.get("Id_Cliente"))
            cli = cliente_map.get(id_cliente)
            if not cli:
                continue

            if id_cliente not in agrupado:
                agrupado[id_cliente] = {
                    "id_cliente": id_cliente,
                    "nome": _safe_str(cli.get("Nome_Cliente")),
                    "telefone": _safe_str(cli.get("Telefone_Cliente")),
                    "email": _safe_str(cli.get("Email_Cliente")),
                    "corretores": set(),
                    "qtd_visitas": 0,
                    "ultima_visita": None,
                    "pdf_url": f"{API_BASE}/clientes/pdf?id_cliente={id_cliente}",
                    "pdf_download_url": f"{API_BASE}/clientes/pdf/download?id_cliente={id_cliente}",
                }

            item = agrupado[id_cliente]
            item["corretores"].add(_safe_str(corretor.get("Nome")))
            item["qtd_visitas"] += 1

            dt = _parse_date_any(visita.get("Data_Visita"))
            if dt and (item["ultima_visita"] is None or dt > item["ultima_visita"]):
                item["ultima_visita"] = dt

    qn = _norm_key(q)
    lista = []
    for item in agrupado.values():
        nomes_corretores = sorted(n for n in item["corretores"] if n)
        row = {
            "id_cliente": item["id_cliente"],
            "nome": item["nome"],
            "telefone": item["telefone"],
            "email": item["email"],
            "corretores": nomes_corretores,
            "qtd_visitas": item["qtd_visitas"],
            "ultima_visita": item["ultima_visita"].strftime("%d/%m/%Y")
            if item["ultima_visita"]
            else "",
            "pdf_url": item["pdf_url"],
            "pdf_download_url": item["pdf_download_url"],
        }

        if qn:
            hay = " ".join([
                row["id_cliente"], row["nome"], row["telefone"],
                row["email"], row["ultima_visita"], " ".join(row["corretores"]),
            ])
            if qn not in _norm_key(hay):
                continue

        lista.append(row)

    lista.sort(
        key=lambda x: (
            _parse_date_any(x.get("ultima_visita")) or datetime.min,
            x.get("nome", ""),
        ),
        reverse=True,
    )
    return lista[: max(1, int(limit or 200))]


def listar_imoveis_do_gerente(
    id_gerente: str,
    q: str = "",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 200,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    maps: Optional[VisitasMaps] = None,
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    maps = maps or _build_maps(data)

    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    cliente_map = maps["cliente_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    qn = _norm_key(q)
    agrupado: Dict[str, Dict] = {}

    for visita in fato_visitas:
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        corretor = corretor_map.get(id_corretor)
        if not corretor:
            continue
        if _safe_str(corretor.get("IdGerente")) != _safe_str(id_gerente):
            continue
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue

        id_imovel = _safe_str(visita.get("Id_Imovel"))
        if not id_imovel:
            continue

        id_visita = _safe_str(visita.get("Id_Visita"))
        data_visita = _safe_str(visita.get("Data_Visita"))
        endereco_externo = _safe_str(visita.get("Endereco_Externo"))
        nome_corretor = _safe_str(corretor.get("Nome"))

        if id_imovel not in agrupado:
            agrupado[id_imovel] = {
                "id_imovel": id_imovel,
                "qtd_visitas": 0,
                "ultima_data": "",
                "ultima_data_ord": None,
                "clientes": [],
                "corretores": [],
                "endereco_externo": endereco_externo,
                "pdf_url": f"{API_BASE}/imoveis/pdf?imovel_id={id_imovel}",
                "pdf_download_url": f"{API_BASE}/imoveis/pdf/download?imovel_id={id_imovel}",
            }

        item = agrupado[id_imovel]
        item["qtd_visitas"] += 1

        dt = _parse_date_any(data_visita)
        if dt and (item["ultima_data_ord"] is None or dt > item["ultima_data_ord"]):
            item["ultima_data_ord"] = dt
            item["ultima_data"] = dt.strftime("%d/%m/%Y")
            if endereco_externo:
                item["endereco_externo"] = endereco_externo

        if nome_corretor and nome_corretor not in item["corretores"]:
            item["corretores"].append(nome_corretor)

        for fc in clientes_por_visita.get(id_visita, []):
            id_cliente = _safe_str(fc.get("Id_Cliente"))
            cli = cliente_map.get(id_cliente)
            nome_cli = _safe_str((cli or {}).get("Nome_Cliente"))
            if nome_cli and nome_cli not in item["clientes"]:
                item["clientes"].append(nome_cli)

    lista = list(agrupado.values())

    if qn:
        lista = [
            item for item in lista
            if qn in _norm_key(" ".join([
                item["id_imovel"], item["ultima_data"], item["endereco_externo"],
                " ".join(item["clientes"]), " ".join(item["corretores"]),
            ]))
        ]

    lista.sort(
        key=lambda x: (x["ultima_data_ord"] or datetime.min, x["id_imovel"]),
        reverse=True,
    )
    for item in lista:
        item.pop("ultima_data_ord", None)

    return lista[: max(1, int(limit or 200))]


CRITERIOS_AVALIACAO_MAP = {
    "Localização": "Localizacao",
    "Tamanho": "Tamanho",
    "Planta": "Planta_Imovel",
    "Acabamento": "Qualidade_Acabamento",
    "Conservação": "Estado_Conservacao",
    "Condomínio": "Condominio_AreaComun",
    "Preço": "Preco",
    "Nota Geral": "Nota_Geral",
    "Preço Nota 10": "Preco_N10",
}


def detalhe_visita_gerente(visita_id: str) -> Dict[str, Any]:
    data = _load_visitas_base()
    maps = _build_maps(data)

    visita = _find_first_by_key(data.get("Fato_Visitas", []), "Id_Visita", visita_id)
    if not visita:
        raise ValueError(f"Visita {visita_id} não encontrada.")

    cliente_map = maps["cliente_map"]
    avals = maps["avaliacoes_por_visita"].get(visita_id, [])

    avaliacoes = []
    for a in avals:
        id_cli = _safe_str(a.get("Id_Cliente"))
        cli = cliente_map.get(id_cli, {})
        row: Dict[str, Any] = {
            "nome_cliente": _safe_str(cli.get("Nome_Cliente")),
        }
        for label, key in CRITERIOS_AVALIACAO_MAP.items():
            row[label] = _safe_str(a.get(key))
        avaliacoes.append(row)

    return {
        "ok": True,
        "visita_id": visita_id,
        "link_imagem": _safe_str(visita.get("Link_Imagem")),
        "anexo_ficha": _safe_str(visita.get("Anexo_Ficha_Visita")),
        "link_audio": _safe_str(visita.get("Link_Audio")),
        "assinatura": _safe_str(visita.get("Assinatura")),
        "revisita": _is_true(visita.get("Revisita")),
        "avaliacoes": avaliacoes,
    }


def ranking_corretores_do_gerente(
    id_gerente: str,
    tipo: str = _TIPO_RANKING_PADRAO,
    start: Optional[str] = None,
    end: Optional[str] = None,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    maps: Optional[VisitasMaps] = None,
) -> List[Dict[str, Any]]:
    tipo = _safe_str(tipo).lower().strip()
    tipo = tipo if tipo in _TIPOS_RANKING_VALIDOS else _TIPO_RANKING_PADRAO

    data = data or _load_visitas_base()
    maps = maps or _build_maps(data)
    corretores = listar_corretores_do_gerente(id_gerente, data=data)
    if not corretores:
        return []

    fato_visitas = data.get("Fato_Visitas", [])
    clientes_por_visita = maps["clientes_por_visita"]

    corretores_map = {
        _safe_str(c.get("IdCorretor")): {
            "id_corretor": _safe_str(c.get("IdCorretor")),
            "corretor": _safe_str(c.get("Nome")),
            "total": 0,
        }
        for c in corretores
    }

    # Para clientes: acumula IDs únicos por corretor (evita contar mesmo cliente N vezes)
    clientes_unicos: Dict[str, set] = {id_c: set() for id_c in corretores_map}

    for visita in fato_visitas:
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        if id_corretor not in corretores_map:
            continue
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue

        if tipo == "visitas":
            corretores_map[id_corretor]["total"] += 1
        else:
            visita_id = _safe_str(visita.get("Id_Visita"))
            for fc in clientes_por_visita.get(visita_id, []):
                id_cliente = _safe_str(fc.get("Id_Cliente"))
                if id_cliente:
                    clientes_unicos[id_corretor].add(id_cliente)

    if tipo != "visitas":
        for id_c, ids_set in clientes_unicos.items():
            corretores_map[id_c]["total"] = len(ids_set)

    ranking = sorted(
        corretores_map.values(),
        key=lambda x: (x["total"], x["corretor"]),
        reverse=True,
    )
    return [
        {
            "posicao": idx,
            "id_corretor": item["id_corretor"],
            "corretor": item["corretor"],
            "total": item["total"],
        }
        for idx, item in enumerate(ranking, start=1)
    ]


def _quartos_por_codigo(codigos: set) -> Dict[str, int]:
    """Retorna o numero de quartos do anuncio mais recente de cada codigo."""
    global _quartos_cache, _quartos_cache_expires
    codigos = {_safe_str(c) for c in codigos if _safe_str(c)}
    if not codigos:
        return {}

    with _quartos_cache_lock:
        if time.time() >= _quartos_cache_expires:
            _quartos_cache = {}
            _quartos_cache_expires = time.time() + _QUARTOS_CACHE_TTL_SECONDS
        faltantes = codigos.difference(_quartos_cache)
        if faltantes:
            session = SessionLocal()
            try:
                rows = (
                    session.query(Imovel.codigo, Imovel.quartos)
                    .filter(
                        Imovel.codigo.in_(sorted(faltantes)),
                        Imovel.quartos.isnot(None),
                        Imovel.quartos >= 0,
                        Imovel.quartos <= 20,
                    )
                    .distinct(Imovel.codigo)
                    .order_by(
                        Imovel.codigo,
                        Imovel.data_coleta.desc().nullslast(),
                        Imovel.id.desc(),
                    )
                    .all()
                )
                encontrados = {_safe_str(codigo): int(quartos) for codigo, quartos in rows}
                for codigo in faltantes:
                    _quartos_cache[codigo] = encontrados.get(codigo)
            finally:
                session.close()
        return {
            codigo: quartos
            for codigo in codigos
            if (quartos := _quartos_cache.get(codigo)) is not None
        }


def _faixa_quartos(quartos: Optional[int]) -> Tuple[str, str]:
    if quartos is None:
        return "nao_informado", "Não informado"
    if quartos >= 5:
        return "5+", "5+ quartos"
    return str(quartos), f"{quartos} quarto" if quartos == 1 else f"{quartos} quartos"


def _visitas_evolucao_base(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    carregar_quartos: bool = True,
    todas_equipes: bool = False,
) -> List[Dict[str, Any]]:
    filtros = filtros or {}
    data = _load_visitas_base()
    maps = _build_maps(data)
    corretor_map = maps["corretor_map"]
    gerente_map = maps["gerente_map"]
    cliente_map = maps["cliente_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    scoped: List[Tuple[Dict[str, Any], Dict[str, Any], datetime]] = []
    codigos = set()
    for visita in data.get("Fato_Visitas", []):
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        corretor = corretor_map.get(id_corretor)
        if not corretor:
            continue
        equipe_id = _safe_str(corretor.get("IdGerente"))
        if not todas_equipes and equipe_id != _safe_str(id_gerente):
            continue
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue
        dt = _parse_date_any(visita.get("Data_Visita"))
        if not dt:
            continue
        scoped.append((visita, corretor, dt))
        codigos.add(_safe_str(visita.get("Id_Imovel")))

    quartos_map = _quartos_por_codigo(codigos) if carregar_quartos else {}
    resultado = []
    for visita, corretor, dt in scoped:
        visita_id = _safe_str(visita.get("Id_Visita"))
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        equipe_id = _safe_str(corretor.get("IdGerente"))
        gerente = gerente_map.get(equipe_id) or {}
        equipe = _safe_str(gerente.get("Equipe")) or _safe_str(gerente.get("Nome")) or equipe_id or "Sem equipe"
        id_imovel = _safe_str(visita.get("Id_Imovel"))
        proposta = _safe_str(visita.get("Proposta")) or "Sem proposta"
        tipo_captacao = _safe_str(visita.get("Tipo_Captacao")) or "Nao informado"
        quartos = quartos_map.get(id_imovel)
        quartos_value, quartos_label = _faixa_quartos(quartos)

        clientes = []
        for ligacao in clientes_por_visita.get(visita_id, []):
            cliente_id = _safe_str(ligacao.get("Id_Cliente"))
            cliente = cliente_map.get(cliente_id) or {}
            if cliente_id and not any(c["id"] == cliente_id for c in clientes):
                clientes.append({
                    "id": cliente_id,
                    "nome": _safe_str(cliente.get("Nome_Cliente")) or cliente_id,
                })

        if filtros.get("corretor") and id_corretor != _safe_str(filtros["corretor"]):
            continue
        if filtros.get("equipe") and equipe_id != _safe_str(filtros["equipe"]):
            continue
        if filtros.get("proposta") and _norm_key(proposta) != _norm_key(filtros["proposta"]):
            continue
        if filtros.get("quartos") and quartos_value != _safe_str(filtros["quartos"]):
            continue
        if filtros.get("cliente") and not any(c["id"] == _safe_str(filtros["cliente"]) for c in clientes):
            continue
        if filtros.get("tipo_captacao") and _norm_key(tipo_captacao) != _norm_key(filtros["tipo_captacao"]):
            continue
        if filtros.get("imovel"):
            texto_imovel = " ".join([id_imovel, _safe_str(visita.get("Endereco_Externo"))])
            if _norm_key(filtros["imovel"]) not in _norm_key(texto_imovel):
                continue
        if filtros.get("com_parceiro") in {"sim", "nao"}:
            esperado = filtros["com_parceiro"] == "sim"
            if _is_true(visita.get("Visita_Com_Parceiro")) != esperado:
                continue
        if filtros.get("revisita") in {"sim", "nao"}:
            esperado = filtros["revisita"] == "sim"
            if _is_true(visita.get("Revisita")) != esperado:
                continue

        resultado.append({
            "data": dt.strftime("%Y-%m-%d"),
            "id_visita": visita_id,
            "id_corretor": id_corretor,
            "corretor": _safe_str(corretor.get("Nome")) or id_corretor,
            "equipe_id": equipe_id,
            "equipe": equipe,
            "id_imovel": id_imovel,
            "imovel": id_imovel or _safe_str(visita.get("Endereco_Externo")) or "Sem imovel",
            "proposta": proposta,
            "tipo_captacao": tipo_captacao,
            "quartos_value": quartos_value,
            "quartos_label": quartos_label,
            "clientes": clientes,
            "com_parceiro": _is_true(visita.get("Visita_Com_Parceiro")),
        })
    return resultado


def opcoes_evolucao_visitas(id_gerente: str, todas_equipes: bool = False) -> Dict[str, Any]:
    visitas = _visitas_evolucao_base(
        id_gerente,
        carregar_quartos=False,
        todas_equipes=todas_equipes,
    )
    equipes = {}
    corretores = {}
    clientes = {}
    propostas = set()
    tipos_captacao = set()
    for visita in visitas:
        equipes[visita["equipe_id"]] = visita["equipe"]
        corretores[visita["id_corretor"]] = {
            "label": visita["corretor"],
            "equipe": visita["equipe_id"],
        }
        propostas.add(visita["proposta"])
        tipos_captacao.add(visita["tipo_captacao"])
        for cliente in visita["clientes"]:
            clientes[cliente["id"]] = cliente["nome"]

    as_options = lambda values: [
        {"value": value, "label": label}
        for value, label in sorted(values.items(), key=lambda item: _norm_key(item[1]))
    ]
    return {
        "ok": True,
        "equipes": as_options(equipes),
        "corretores": [
            {"value": value, "label": meta["label"], "equipe": meta["equipe"]}
            for value, meta in sorted(corretores.items(), key=lambda item: _norm_key(item[1]["label"]))
        ],
        "clientes": as_options(clientes),
        "propostas": [{"value": v, "label": v} for v in sorted(propostas, key=_norm_key)],
        "tipos_captacao": [{"value": v, "label": v} for v in sorted(tipos_captacao, key=_norm_key)],
        "quartos": [
            {"value": "0", "label": "0 quartos"},
            {"value": "1", "label": "1 quarto"},
            {"value": "2", "label": "2 quartos"},
            {"value": "3", "label": "3 quartos"},
            {"value": "4", "label": "4 quartos"},
            {"value": "5+", "label": "5+ quartos"},
            {"value": "nao_informado", "label": "Não informado"},
        ],
    }


def _bucket_data_visita(data_iso: str, gran: str) -> str:
    """Data ISO representativa do bucket: dia=próprio, semana=segunda-feira, mês=dia 1."""
    d = date.fromisoformat(data_iso)
    if gran == "mes":
        return d.replace(day=1).isoformat()
    if gran == "semana":
        return (d - timedelta(days=d.weekday())).isoformat()
    return d.isoformat()


def _eixo_datas(primeira: date, ultima: date, gran: str) -> List[str]:
    """Eixo X completo (inclui buckets vazios) na granularidade escolhida."""
    out: List[str] = []
    if gran == "mes":
        cursor = primeira.replace(day=1)
        while cursor <= ultima:
            out.append(cursor.isoformat())
            cursor = (cursor.replace(year=cursor.year + 1, month=1)
                      if cursor.month == 12 else cursor.replace(month=cursor.month + 1))
    elif gran == "semana":
        cursor = primeira - timedelta(days=primeira.weekday())
        while cursor <= ultima:
            out.append(cursor.isoformat())
            cursor += timedelta(weeks=1)
    else:
        cursor = primeira
        while cursor <= ultima:
            out.append(cursor.isoformat())
            cursor += timedelta(days=1)
    return out


def evolucao_visitas_gerente(
    id_gerente: str,
    dimensao: str = "corretor",
    start: Optional[str] = None,
    end: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    max_series: int = 12,
    todas_equipes: bool = False,
    granularidade: str = "dia",
) -> Dict[str, Any]:
    dimensao = _safe_str(dimensao).lower() or "corretor"
    if dimensao not in _DIMENSOES_EVOLUCAO_VISITAS:
        dimensao = "corretor"
    gran = _safe_str(granularidade).lower() or "dia"
    if gran not in _AGRUPAMENTOS_VALIDOS:
        gran = "dia"
    visitas = _visitas_evolucao_base(
        id_gerente,
        start=start,
        end=end,
        filtros=filtros,
        todas_equipes=todas_equipes,
    )

    series_bucket: Dict[str, Counter] = defaultdict(Counter)
    labels: Dict[str, str] = {}
    clientes_unicos = set()
    propostas = 0
    for visita in visitas:
        clientes_unicos.update(c["id"] for c in visita["clientes"])
        if _norm_key(visita["proposta"]) not in {_norm_key("Sem proposta"), _norm_key("Nao"), _norm_key("Não")}:
            propostas += 1

        if dimensao == "total":
            grupos = [("total", "Visitas")]
        elif dimensao == "cliente":
            grupos = [(c["id"], c["nome"]) for c in visita["clientes"]] or [("sem_cliente", "Sem cliente")]
        elif dimensao == "quartos":
            grupos = [(visita["quartos_value"], visita["quartos_label"])]
        elif dimensao == "imovel":
            grupos = [(visita["imovel"], visita["imovel"])]
        else:
            valor = visita[dimensao]
            grupos = [(valor, valor)]

        bucket = _bucket_data_visita(visita["data"], gran)
        for chave, label in grupos:
            labels[chave] = label
            series_bucket[chave][bucket] += 1

    if visitas:
        primeira = _parse_date_any(start) or _parse_date_any(min(v["data"] for v in visitas))
        ultima = _parse_date_any(end) or _parse_date_any(max(v["data"] for v in visitas))
        datas = _eixo_datas(primeira.date(), ultima.date(), gran)
    else:
        datas = []

    ordenadas = sorted(series_bucket, key=lambda k: (-sum(series_bucket[k].values()), _norm_key(labels[k])))
    principais = ordenadas[:max_series]
    restantes = ordenadas[max_series:]
    series = [
        {"nome": labels[chave], "pontos": [series_bucket[chave].get(d, 0) for d in datas]}
        for chave in principais
    ]
    if restantes:
        series.append({
            "nome": "Outros",
            "pontos": [sum(series_bucket[chave].get(d, 0) for chave in restantes) for d in datas],
        })

    return {
        "ok": True,
        "dimensao": dimensao,
        "granularidade": gran,
        "datas": datas,
        "series": series,
        "resumo": {
            "total_visitas": len(visitas),
            "clientes_unicos": len(clientes_unicos),
            "visitas_com_proposta": propostas,
            "imoveis_unicos": len({v["id_imovel"] for v in visitas if v["id_imovel"]}),
        },
    }


def serie_gerente(
    id_gerente: str,
    tipo: str = "visitas",
    agrupamento: str = _AGRUPAMENTO_PADRAO,
    start: Optional[str] = None,
    end: Optional[str] = None,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    maps: Optional[VisitasMaps] = None,
) -> Dict[str, Any]:
    tipo = _safe_str(tipo).lower().strip()
    agrupamento = _safe_str(agrupamento).lower().strip()
    agrupamento = agrupamento if agrupamento in _AGRUPAMENTOS_VALIDOS else _AGRUPAMENTO_PADRAO

    data = data or _load_visitas_base()
    maps = maps or _build_maps(data)
    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    bucket: Dict[Tuple[str, str], int] = defaultdict(int)
    # Para clientes: acumula IDs únicos por bucket (evita contar mesmo cliente N vezes no período)
    clientes_por_bucket: Dict[Tuple[str, str], set] = defaultdict(set)

    for visita in fato_visitas:
        id_corretor = _safe_str(visita.get("Id_Corretor"))
        corretor = corretor_map.get(id_corretor)
        if not corretor:
            continue
        if _safe_str(corretor.get("IdGerente")) != _safe_str(id_gerente):
            continue
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue

        dt = _parse_date_any(visita.get("Data_Visita"))
        if not dt:
            continue

        if agrupamento == "mes":
            chave, label = dt.strftime("%Y-%m"), dt.strftime("%m/%Y")
        elif agrupamento == "semana":
            iso = dt.isocalendar()
            chave = f"{iso.year}-W{iso.week:02d}"
            label = f"Sem {iso.week:02d}/{iso.year}"
        else:
            chave, label = dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m")

        if tipo == "clientes":
            visita_id = _safe_str(visita.get("Id_Visita"))
            for fc in clientes_por_visita.get(visita_id, []):
                id_cliente = _safe_str(fc.get("Id_Cliente"))
                if id_cliente:
                    clientes_por_bucket[(chave, label)].add(id_cliente)
        else:
            bucket[(chave, label)] += 1

    if tipo == "clientes":
        for key, ids_set in clientes_por_bucket.items():
            bucket[key] = len(ids_set)

    ordenado = sorted(bucket.items(), key=lambda x: x[0][0])
    return {
        "ok": True,
        "labels": [label for (_, label), _ in ordenado],
        "valores": [valor for _, valor in ordenado],
        "tipo": tipo,
        "agrupamento": agrupamento,
    }


def dashboard_gerente(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, Any]:
    # Carrega dados e constrói mapas UMA única vez para todo o dashboard
    data = _load_visitas_base()
    maps = _build_maps(data)

    corretores = listar_corretores_do_gerente(id_gerente, data=data)
    visitas = listar_visitas_do_gerente(
        id_gerente, start=start, end=end, limit=100_000, data=data, maps=maps
    )
    clientes = listar_clientes_do_gerente(
        id_gerente, start=start, end=end, limit=100_000, data=data, maps=maps
    )
    imoveis = listar_imoveis_do_gerente(
        id_gerente, start=start, end=end, limit=100_000, data=data, maps=maps
    )
    ranking_visitas = ranking_corretores_do_gerente(
        id_gerente, "visitas", start, end, data=data, maps=maps
    )
    ranking_clientes = ranking_corretores_do_gerente(
        id_gerente, "clientes", start, end, data=data, maps=maps
    )

    corretores_ativos = {
        v["id_corretor"] for v in visitas if _safe_str(v.get("id_corretor"))
    }
    total_corretores = len(corretores)

    return {
        "ok": True,
        "resumo": {
            "total_corretores": total_corretores,
            "corretores_ativos": len(corretores_ativos),
            "corretores_sem_visita": max(total_corretores - len(corretores_ativos), 0),
            "total_visitas": len(visitas),
            "total_clientes": len(clientes),
            "total_imoveis": len(imoveis),
            "media_visitas_por_corretor": round(len(visitas) / total_corretores, 2)
            if total_corretores
            else 0,
        },
        "graficos": {
            "visitas_por_dia": serie_gerente(
                id_gerente, "visitas", "dia", start, end, data=data, maps=maps
            ),
            "clientes_por_dia": serie_gerente(
                id_gerente, "clientes", "dia", start, end, data=data, maps=maps
            ),
        },
        "rankings": {
            "visitas": ranking_visitas,
            "clientes": ranking_clientes,
        },
        "listas": {
            "visitas": visitas[:50],
            "clientes": clientes[:50],
            "imoveis": imoveis[:50],
        },
    }


# ---------------------------------------------------------------------------
# PDF — Corretor
# ---------------------------------------------------------------------------

def _montar_contexto_pdf_corretor(
    id_corretor: str,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    data = data or _load_visitas_base()
    maps = _build_maps(data)

    dim_corretor = data.get("Dim_Corretor", [])
    fato_visitas = data.get("Fato_Visitas", [])
    cliente_map = maps["cliente_map"]
    parceiro_map = maps["parceiro_map"]
    gerente_map = maps["gerente_map"]
    clientes_por_visita = maps["clientes_por_visita"]
    parceiros_por_visita = maps["parceiros_por_visita"]
    avaliacoes_por_visita = maps["avaliacoes_por_visita"]

    corretor = _find_first_by_key(dim_corretor, "IdCorretor", id_corretor)
    if not corretor:
        raise ValueError(f"Corretor {id_corretor} não encontrado.")

    gerente = gerente_map.get(_safe_str(corretor.get("IdGerente")), {})
    visitas = [
        v for v in fato_visitas
        if _safe_str(v.get("Id_Corretor")) == _safe_str(id_corretor)
    ]
    if not visitas:
        raise ValueError(f"Nenhuma visita encontrada para o corretor {id_corretor}.")

    visitas.sort(
        key=lambda v: (
            _parse_date_any(v.get("Data_Visita")) or datetime.min,
            _safe_str(v.get("CreatedAt")),
        ),
        reverse=True,
    )

    clientes_unicos: Dict[str, Dict] = {}
    parceiros_unicos: Dict[str, Dict] = {}
    imoveis_unicos: set = set()
    visitas_resumo = []

    for visita in visitas:
        visita_id = _safe_str(visita.get("Id_Visita"))
        id_imovel = _safe_str(visita.get("Id_Imovel"))
        if id_imovel:
            imoveis_unicos.add(id_imovel)

        nomes_clientes = []
        for fc in clientes_por_visita.get(visita_id, []):
            id_cliente = _safe_str(fc.get("Id_Cliente"))
            cli = cliente_map.get(id_cliente)
            if not cli:
                continue
            nome_cli = _safe_str(cli.get("Nome_Cliente"))
            if nome_cli:
                nomes_clientes.append(nome_cli)
            if id_cliente and id_cliente not in clientes_unicos:
                clientes_unicos[id_cliente] = {
                    "Id_Cliente": id_cliente,
                    "Nome_Cliente": nome_cli,
                    "Telefone_Cliente": _safe_str(cli.get("Telefone_Cliente")),
                    "Email_Cliente": _safe_str(cli.get("Email_Cliente")),
                }

        nomes_parceiros = []
        for fp in parceiros_por_visita.get(visita_id, []):
            id_parceiro = _safe_str(fp.get("Id_Parceiro"))
            par = parceiro_map.get(id_parceiro)
            if not par:
                continue
            nome_par = _safe_str(par.get("Nome_Parceiro"))
            if nome_par:
                nomes_parceiros.append(nome_par)
            if id_parceiro and id_parceiro not in parceiros_unicos:
                parceiros_unicos[id_parceiro] = {
                    "Id_Parceiro": id_parceiro,
                    "Nome_Parceiro": nome_par,
                    "Imobiliaria": _safe_str(par.get("Imobiliaria")),
                }

        visitas_resumo.append({
            "Id_Visita": visita_id,
            "Data_Visita": _fmt_date(visita.get("Data_Visita")),
            "Id_Imovel": id_imovel,
            "Endereco_Externo": _safe_str(visita.get("Endereco_Externo")),
            "Proposta": _safe_str(visita.get("Proposta")),
            "Tipo_Captacao": _safe_str(visita.get("Tipo_Captacao")),
            "Clientes": ", ".join(nomes_clientes),
            "Parceiros": ", ".join(nomes_parceiros),
            "Qtd_Avaliacoes": len(avaliacoes_por_visita.get(visita_id, [])),
        })

    ultima_visita = visitas[0]
    return {
        "Id_Corretor": _safe_str(corretor.get("IdCorretor")),
        "Nome_Corretor": _safe_str(corretor.get("Nome")),
        "Email": _safe_str(corretor.get("Email")),
        "Telefone": _safe_str(corretor.get("Telefone")),
        "Instagram": _safe_str(corretor.get("Instragram")),
        "Nome_Gerente": _safe_str(gerente.get("Nome")),
        "Equipe": _safe_str(gerente.get("Equipe")),
        "Total_Visitas": len(visitas),
        "Total_Clientes": len(clientes_unicos),
        "Total_Parceiros": len(parceiros_unicos),
        "Total_Imoveis": len(imoveis_unicos),
        "Ultima_Visita": _fmt_date(ultima_visita.get("Data_Visita")),
        "Clientes": list(clientes_unicos.values()),
        "Parceiros": list(parceiros_unicos.values()),
        "Visitas": visitas_resumo,
    }


def _build_pdf_corretor_bytes(ctx: Dict[str, Any]) -> bytes:
    subtitulo = _display(ctx.get("Nome_Corretor")) + "  ·  Equipe " + _display(ctx.get("Equipe"))
    doc = _Pdf61("Relatorio do Corretor", subtitulo)
    doc.add_page()

    doc.section("Informacoes do corretor")
    doc.info_rows([
        ["ID", _display(ctx.get("Id_Corretor"))],
        ["Nome", _display(ctx.get("Nome_Corretor"))],
        ["E-mail", _display(ctx.get("Email"))],
        ["Telefone", _display(ctx.get("Telefone"))],
        ["Instagram", _display(ctx.get("Instagram"))],
        ["Gerente", _display(ctx.get("Nome_Gerente"))],
        ["Equipe", _display(ctx.get("Equipe"))],
        ["Total de visitas", str(ctx.get("Total_Visitas", 0))],
        ["Total de clientes", str(ctx.get("Total_Clientes", 0))],
        ["Total de parceiros", str(ctx.get("Total_Parceiros", 0))],
        ["Total de imoveis", str(ctx.get("Total_Imoveis", 0))],
        ["Ultima visita", _display(ctx.get("Ultima_Visita"))],
    ])

    if ctx.get("Clientes"):
        doc.section("Clientes vinculados")
        doc.table(
            ["Cliente", "Telefone", "E-mail"],
            [[_display(c.get("Nome_Cliente")), _display(c.get("Telefone_Cliente")), _display(c.get("Email_Cliente"))] for c in ctx["Clientes"]],
            [75, 45, 60],
        )

    if ctx.get("Parceiros"):
        doc.section("Parceiros vinculados")
        doc.table(
            ["Parceiro", "Imobiliaria"],
            [[_display(p.get("Nome_Parceiro")), _display(p.get("Imobiliaria"))] for p in ctx["Parceiros"]],
            [95, 85],
        )

    doc.section("Historico de visitas")
    doc.table(
        ["ID Visita", "Data", "Imovel", "Proposta", "Clientes"],
        [
            [_display(v.get("Id_Visita")), _display(v.get("Data_Visita")), _display(v.get("Id_Imovel")), _display(v.get("Proposta")), _display(v.get("Clientes"))]
            for v in ctx.get("Visitas", [])
        ],
        [28, 22, 24, 26, 80],
    )

    return doc.to_bytes()


def gerar_pdf_corretor_download(id_corretor: str) -> Tuple[io.BytesIO, str]:
    data = _load_visitas_base()
    ctx = _montar_contexto_pdf_corretor(id_corretor, data=data)
    pdf_bytes = _build_pdf_corretor_bytes(ctx)
    file_name = f"Relatorio_Corretor_{id_corretor}.pdf"
    return io.BytesIO(pdf_bytes), file_name


def gerar_pdf_corretor_publico(id_corretor: str) -> Dict[str, str]:
    data = _load_visitas_base()
    ctx = _montar_contexto_pdf_corretor(id_corretor, data=data)
    pdf_bytes = _build_pdf_corretor_bytes(ctx)
    file_name = f"Relatorio_Corretor_{id_corretor}.pdf"
    return _pdf_upload_to_drive(pdf_bytes, file_name, DRIVE_CORRETOR_REPORTS_SUBFOLDER_NAME, id_corretor)


# ---------------------------------------------------------------------------
# PDF — Gerente (contexto separado da renderização)
# ---------------------------------------------------------------------------

def _montar_contexto_pdf_gerente(
    id_gerente: str,
    start: Optional[str],
    end: Optional[str],
    data: Dict[str, List[Dict[str, Any]]],
    maps: VisitasMaps,
) -> Dict[str, Any]:
    gerente = _find_first_by_key(data.get("Dim_Gerente", []), "IdGerente", id_gerente)
    if not gerente:
        raise ValueError(f"Gerente {id_gerente} não encontrado.")

    dash = dashboard_gerente(id_gerente, start, end)
    visitas = listar_visitas_do_gerente(
        id_gerente, start=start, end=end, limit=1000, data=data, maps=maps
    )
    return {
        "gerente": gerente,
        "dashboard": dash,
        "visitas": visitas,
    }


def _build_pdf_gerente_bytes(ctx: Dict[str, Any]) -> bytes:
    gerente  = ctx["gerente"]
    dashboard = ctx["dashboard"]
    visitas  = ctx["visitas"]
    resumo   = dashboard["resumo"]
    ranking  = dashboard["rankings"]["visitas"]

    nome   = _display(gerente.get("Nome"))
    equipe = _display(gerente.get("Equipe"))
    doc = _Pdf61("Relatorio Consolidado do Gerente", f"{nome}  ·  Equipe {equipe}")
    doc.add_page()

    doc.section("Resumo executivo")
    doc.info_rows([
        ["Total de corretores",    str(resumo["total_corretores"])],
        ["Corretores ativos",      str(resumo["corretores_ativos"])],
        ["Corretores sem visita",  str(resumo["corretores_sem_visita"])],
        ["Total de visitas",       str(resumo["total_visitas"])],
        ["Total de clientes",      str(resumo["total_clientes"])],
        ["Total de imoveis",       str(resumo.get("total_imoveis", 0))],
        ["Media visitas/corretor", str(resumo["media_visitas_por_corretor"])],
    ])

    doc.section("Ranking de visitas por corretor")
    doc.table(
        ["Pos.", "Corretor", "Total"],
        [[str(r["posicao"]), r["corretor"], str(r["total"])] for r in ranking],
        [14, 140, 26],
    )

    doc.section("Visitas do periodo")
    doc.table(
        ["Data", "Corretor", "Imovel", "Proposta", "Motivo talvez", "Motivo sim", "Clientes"],
        [
            [
                _display(v.get("data_visita")),
                _display(v.get("corretor")),
                _display(v.get("id_imovel")),
                _display(v.get("proposta")),
                _display(v.get("motivo_talvez")),
                _display(v.get("motivo_sim")),
                ", ".join(v.get("clientes", [])) if v.get("clientes") else "-",
            ]
            for v in visitas[:200]
        ],
        [18, 30, 16, 18, 34, 34, 30],
    )

    return doc.to_bytes()


def gerar_pdf_gerente_consolidado_bytes(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> bytes:
    data = _load_visitas_base()
    maps = _build_maps(data)
    ctx = _montar_contexto_pdf_gerente(id_gerente, start, end, data, maps)
    return _build_pdf_gerente_bytes(ctx)


def gerar_pdf_gerente_download(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Tuple[io.BytesIO, str]:
    pdf_bytes = gerar_pdf_gerente_consolidado_bytes(id_gerente, start, end)
    file_name = f"Relatorio_Gerente_{id_gerente}.pdf"
    return io.BytesIO(pdf_bytes), file_name


def gerar_pdf_gerente_publico(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, str]:
    pdf_bytes = gerar_pdf_gerente_consolidado_bytes(id_gerente, start, end)
    file_name = f"Relatorio_Gerente_{id_gerente}.pdf"
    return _pdf_upload_to_drive(pdf_bytes, file_name, DRIVE_GERENTE_REPORTS_SUBFOLDER_NAME, id_gerente)


# ---------------------------------------------------------------------------
# Dashboard e PDF — Geral por Equipe
# ---------------------------------------------------------------------------

def dashboard_equipes(
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, Any]:
    data = _load_visitas_base()
    maps = _build_maps(data)

    dim_corretor = data.get("Dim_Corretor", [])
    dim_gerente = data.get("Dim_Gerente", [])
    fato_visitas = data.get("Fato_Visitas", [])
    clientes_por_visita = maps["clientes_por_visita"]

    # IdGerente → Equipe
    gerente_equipe: Dict[str, str] = {}
    for g in dim_gerente:
        id_g = _safe_str(g.get("IdGerente"))
        equipe = _safe_str(g.get("Equipe")).strip()
        if id_g and equipe:
            gerente_equipe[id_g] = equipe

    # IdCorretor → Equipe
    corretor_equipe: Dict[str, str] = {}
    equipe_corretores: Dict[str, set] = defaultdict(set)
    for c in dim_corretor:
        id_c = _safe_str(c.get("IdCorretor"))
        id_g = _safe_str(c.get("IdGerente"))
        equipe = gerente_equipe.get(id_g, "")
        if id_c and equipe:
            corretor_equipe[id_c] = equipe
            equipe_corretores[equipe].add(id_c)

    equipe_visitas: Dict[str, int] = defaultdict(int)
    equipe_ativos: Dict[str, set] = defaultdict(set)
    equipe_clientes: Dict[str, set] = defaultdict(set)

    for visita in fato_visitas:
        if not _in_period(visita.get("Data_Visita"), start, end):
            continue
        id_c = _safe_str(visita.get("Id_Corretor"))
        equipe = corretor_equipe.get(id_c)
        if not equipe:
            continue
        visita_id = _safe_str(visita.get("Id_Visita"))
        equipe_visitas[equipe] += 1
        equipe_ativos[equipe].add(id_c)
        for fc in clientes_por_visita.get(visita_id, []):
            id_cliente = _safe_str(fc.get("Id_Cliente"))
            if id_cliente:
                equipe_clientes[equipe].add(id_cliente)

    resultado: List[Dict[str, Any]] = []
    for equipe in sorted(equipe_corretores.keys()):
        resultado.append({
            "equipe": equipe,
            "total_corretores": len(equipe_corretores[equipe]),
            "corretores_ativos": len(equipe_ativos.get(equipe, set())),
            "total_visitas": equipe_visitas.get(equipe, 0),
            "total_clientes": len(equipe_clientes.get(equipe, set())),
        })

    resultado.sort(key=lambda x: -x["total_visitas"])
    for i, r in enumerate(resultado):
        r["posicao"] = i + 1

    return {
        "ok": True,
        "start": start,
        "end": end,
        "equipes": resultado,
        "totais": {
            "total_visitas": sum(r["total_visitas"] for r in resultado),
            "total_clientes": sum(r["total_clientes"] for r in resultado),
            "total_corretores": sum(r["total_corretores"] for r in resultado),
        },
    }


def _build_pdf_equipes_bytes(ctx: Dict[str, Any]) -> bytes:
    start  = ctx.get("start") or "-"
    end    = ctx.get("end") or "-"
    totais = ctx.get("totais", {})

    doc = _Pdf61("Relatorio Geral por Equipe", f"Periodo: {start} a {end}")
    doc.add_page()

    doc.section("Totais consolidados")
    doc.info_rows([
        ["Total de visitas",       str(totais.get("total_visitas", 0))],
        ["Total de clientes unicos", str(totais.get("total_clientes", 0))],
        ["Total de corretores",    str(totais.get("total_corretores", 0))],
    ])

    doc.section("Ranking por equipe")
    doc.table(
        ["Pos.", "Equipe", "Visitas", "Clientes", "Corretores", "Ativos"],
        [
            [str(e["posicao"]), e["equipe"], str(e["total_visitas"]), str(e["total_clientes"]), str(e["total_corretores"]), str(e["corretores_ativos"])]
            for e in ctx.get("equipes", [])
        ],
        [12, 68, 24, 24, 28, 24],
    )

    return doc.to_bytes()


def gerar_pdf_equipes_download(
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Tuple[io.BytesIO, str]:
    ctx = dashboard_equipes(start, end)
    pdf_bytes = _build_pdf_equipes_bytes(ctx)
    file_name = f"Relatorio_Equipes_{start or 'completo'}_{end or 'completo'}.pdf"
    return io.BytesIO(pdf_bytes), file_name
