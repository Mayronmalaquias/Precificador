from __future__ import annotations

import io
import os
import time
from collections import defaultdict
from datetime import datetime, date
from threading import Lock
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from googleapiclient.errors import HttpError

load_dotenv()
API_BASE = (os.getenv("API_BASE") or "").rstrip("/")

CORRETORES_ATIVOS = {
    "C61180",
    "C61162",
    "C61186",
    "C61147",
    "C61086",
    "C61165",
    "C61175",
    "C61188",
    "C61096",
    "C61059",
    "C61054",
    "C61066",
    "C61095",
    "C61090",
    "C61041",
    "C61184",
    "C61182",
    "C61185",
    "C61179",
    "C61153",
    "C61189",
    "C61010",
    "C61178",
    "C61151",
    "C61174",
    "C61110",
    "C61181",
    "C61086",
    "C61092",
    "C61183",
    "C61114",
    "C61039",
    "C61134",
    "C61158",
    "C61166",
    "C61051",
    "C61171",
    "C61161",
    "C61144",

}

def _is_corretor_id_ativo(id_corretor: Any) -> bool:
    return _safe_str(id_corretor) in CORRETORES_ATIVOS


from app.services.visita_service import (
    _get_services,
    _find_or_create_folder,
    _trash_same_name_files_in_folder,
    _safe_str,
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

_VISITAS_CACHE = {
    "data": None,
    "expires_at": 0.0,
}
_VISITAS_CACHE_LOCK = Lock()


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
    if not dt:
        return _safe_str(v)
    return dt.strftime("%d/%m/%Y")


def _fmt_datetime(v: Any) -> str:
    dt = _parse_date_any(v)
    if not dt:
        return _safe_str(v)
    return dt.strftime("%d/%m/%Y %H:%M")


def _display(v: Any, default: str = "—") -> str:
    s = _safe_str(v)
    return s if s else default


def _batch_get_rows_from_sheet(
    spreadsheet_id: str,
    ranges: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    sheets, _, _ = _get_services()

    last_error = None
    res = None

    for attempt in range(3):
        try:
            res = sheets.values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges,
                majorDimension="ROWS",
            ).execute()
            break
        except HttpError as e:
            last_error = e
            status = getattr(getattr(e, "resp", None), "status", None)

            if status == 429 and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise

    if res is None and last_error:
        raise last_error

    value_ranges = res.get("valueRanges", [])
    out: Dict[str, List[Dict[str, Any]]] = {}

    for rg, vr in zip(ranges, value_ranges):
        values = vr.get("values", [])
        sheet_name = rg.split("!")[0]

        if not values:
            out[sheet_name] = []
            continue

        header = [str(c).strip() for c in values[0]]
        rows = []

        for raw in values[1:]:
            row = {}
            for i, h in enumerate(header):
                row[h] = raw[i] if i < len(raw) else ""
            rows.append(row)

        out[sheet_name] = rows

    return out


def _in_period(row_date: Any, start: Optional[str], end: Optional[str]) -> bool:
    dt = _parse_date_any(row_date)
    if not dt:
        return False

    start_dt = _parse_date_any(start) if start else None
    end_dt = _parse_date_any(end) if end else None

    if start_dt and dt.date() < start_dt.date():
        return False
    if end_dt and dt.date() > end_dt.date():
        return False
    return True


def _load_visitas_base(force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    now = time.time()

    with _VISITAS_CACHE_LOCK:
        if (
            not force_refresh
            and _VISITAS_CACHE["data"] is not None
            and now < _VISITAS_CACHE["expires_at"]
        ):
            return _VISITAS_CACHE["data"]

    data = _batch_get_rows_from_sheet(
        VISITAS_SPREADSHEET_ID,
        [
            "Dim_Corretor!A1:I",
            "Dim_Gerente!A1:D",
            "Dim_Cliente_Visita!A1:F",
            "Dim_Parceiro_Visita!A1:D",
            "Fato_Visitas!A1:R",
            "Fato_Cliente_Visita!A1:D",
            "Fato_Parceiro_Visita!A1:D",
            "Fato_Avaliacao!A1:N",
        ],
    )

    with _VISITAS_CACHE_LOCK:
        _VISITAS_CACHE["data"] = data
        _VISITAS_CACHE["expires_at"] = time.time() + 30

    return data


def _build_maps(data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
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

    clientes_por_visita = defaultdict(list)
    for r in fato_cliente:
        id_visita = _safe_str(r.get("Id_Visita"))
        if id_visita:
            clientes_por_visita[id_visita].append(r)

    parceiros_por_visita = defaultdict(list)
    for r in fato_parceiro:
        id_visita = _safe_str(r.get("Id_Visita"))
        if id_visita:
            parceiros_por_visita[id_visita].append(r)

    avaliacoes_por_visita = defaultdict(list)
    for r in fato_avaliacao:
        id_visita = _safe_str(r.get("Id_Visita"))
        if id_visita:
            avaliacoes_por_visita[id_visita].append(r)

    return {
        "corretor_map": corretor_map,
        "gerente_map": gerente_map,
        "cliente_map": cliente_map,
        "parceiro_map": parceiro_map,
        "clientes_por_visita": clientes_por_visita,
        "parceiros_por_visita": parceiros_por_visita,
        "avaliacoes_por_visita": avaliacoes_por_visita,
    }


def listar_corretores_do_gerente(
    id_gerente: str,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    dim_corretor = data.get("Dim_Corretor", [])

    id_gerente = _safe_str(id_gerente)
    if not id_gerente:
        return []

    lista = [
        r
        for r in dim_corretor
        if _safe_str(r.get("IdGerente")) == id_gerente
        and _is_corretor_id_ativo(r.get("IdCorretor"))
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
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    maps = _build_maps(data)

    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    cliente_map = maps["cliente_map"]
    parceiro_map = maps["parceiro_map"]
    clientes_por_visita = maps["clientes_por_visita"]
    parceiros_por_visita = maps["parceiros_por_visita"]

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

        nomes_clientes = []
        for fc in clientes_por_visita.get(visita_id, []):
            cli = cliente_map.get(_safe_str(fc.get("Id_Cliente")))
            nome_cli = _safe_str((cli or {}).get("Nome_Cliente"))
            if nome_cli and nome_cli not in nomes_clientes:
                nomes_clientes.append(nome_cli)

        nomes_parceiros = []
        for fp in parceiros_por_visita.get(visita_id, []):
            par = parceiro_map.get(_safe_str(fp.get("Id_Parceiro")))
            nome_par = _safe_str((par or {}).get("Nome_Parceiro"))
            if nome_par and nome_par not in nomes_parceiros:
                nomes_parceiros.append(nome_par)

        item = {
            "id_visita": visita_id,
            "id_imovel": _safe_str(visita.get("Id_Imovel")),
            "data_visita": _fmt_date(visita.get("Data_Visita")),
            "created_at": _fmt_datetime(visita.get("CreatedAt")),
            "corretor": _safe_str(corretor.get("Nome")),
            "id_corretor": id_corretor,
            "clientes": nomes_clientes,
            "parceiros": nomes_parceiros,
            "endereco_externo": _safe_str(visita.get("Endereco_Externo")),
            "tipo_captacao": _safe_str(visita.get("Tipo_Captacao")),
            "proposta": _safe_str(visita.get("Proposta")),
            "visita_com_parceiro": bool(_safe_str(visita.get("Visita_Com_Parceiro"))),
            "imovel_nao_captado": bool(_safe_str(visita.get("Imovel_Nao_Captado"))),
            "pdf_url": f"{API_BASE}/visitas/pdf?visita_id={visita_id}",
            "pdf_download_url": f"{API_BASE}/visitas/pdf/download?visita_id={visita_id}",
        }

        hay = " ".join(
            [
                item["id_visita"],
                item["id_imovel"],
                item["data_visita"],
                item["corretor"],
                item["endereco_externo"],
                item["tipo_captacao"],
                item["proposta"],
                " ".join(item["clientes"]),
                " ".join(item["parceiros"]),
            ]
        )

        if qn and qn not in _norm_key(hay):
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
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    maps = _build_maps(data)

    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    cliente_map = maps["cliente_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    visitas_validas = {}
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

    agrupado = {}

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
        nomes_corretores = sorted([n for n in item["corretores"] if n])

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

        hay = " ".join(
            [
                row["id_cliente"],
                row["nome"],
                row["telefone"],
                row["email"],
                row["ultima_visita"],
                " ".join(row["corretores"]),
            ]
        )

        if qn and qn not in _norm_key(hay):
            continue

        lista.append(row)

    lista.sort(
        key=lambda x: (_parse_date_any(x.get("ultima_visita")) or datetime.min, x.get("nome", "")),
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
) -> List[Dict[str, Any]]:
    data = data or _load_visitas_base()
    maps = _build_maps(data)

    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    cliente_map = maps["cliente_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    qn = _norm_key(q)
    agrupado = {}

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
        id_visita = _safe_str(visita.get("Id_Visita"))
        data_visita = _safe_str(visita.get("Data_Visita"))
        endereco_externo = _safe_str(visita.get("Endereco_Externo"))
        nome_corretor = _safe_str(corretor.get("Nome"))

        if not id_imovel:
            continue

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
            item
            for item in lista
            if qn
            in _norm_key(
                " ".join(
                    [
                        item["id_imovel"],
                        item["ultima_data"],
                        item["endereco_externo"],
                        " ".join(item["clientes"]),
                        " ".join(item["corretores"]),
                    ]
                )
            )
        ]

    lista.sort(
        key=lambda x: (x["ultima_data_ord"] or datetime.min, x["id_imovel"]),
        reverse=True,
    )

    for item in lista:
        item.pop("ultima_data_ord", None)

    return lista[: max(1, int(limit or 200))]


def ranking_corretores_do_gerente(
    id_gerente: str,
    tipo: str = "visitas",
    start: Optional[str] = None,
    end: Optional[str] = None,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    tipo = _safe_str(tipo).lower().strip()
    if tipo not in {"visitas", "clientes"}:
        tipo = "visitas"

    data = data or _load_visitas_base()
    corretores = listar_corretores_do_gerente(id_gerente, data=data)
    if not corretores:
        return []

    maps = _build_maps(data)
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
            corretores_map[id_corretor]["total"] += len(clientes_por_visita.get(visita_id, []))

    ranking = list(corretores_map.values())
    ranking.sort(key=lambda x: (x["total"], x["corretor"]), reverse=True)

    out = []
    for idx, item in enumerate(ranking, start=1):
        out.append(
            {
                "posicao": idx,
                "id_corretor": item["id_corretor"],
                "corretor": item["corretor"],
                "total": item["total"],
            }
        )
    return out


def serie_gerente(
    id_gerente: str,
    tipo: str = "visitas",
    agrupamento: str = "dia",
    start: Optional[str] = None,
    end: Optional[str] = None,
    data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    tipo = _safe_str(tipo).lower().strip()
    agrupamento = _safe_str(agrupamento).lower().strip()

    data = data or _load_visitas_base()
    maps = _build_maps(data)
    fato_visitas = data.get("Fato_Visitas", [])
    corretor_map = maps["corretor_map"]
    clientes_por_visita = maps["clientes_por_visita"]

    bucket = defaultdict(int)

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
            chave = dt.strftime("%Y-%m")
            label = dt.strftime("%m/%Y")
        elif agrupamento == "semana":
            iso = dt.isocalendar()
            chave = f"{iso.year}-W{iso.week:02d}"
            label = f"Sem {iso.week:02d}/{iso.year}"
        else:
            chave = dt.strftime("%Y-%m-%d")
            label = dt.strftime("%d/%m")

        if tipo == "clientes":
            visita_id = _safe_str(visita.get("Id_Visita"))
            bucket[(chave, label)] += len(clientes_por_visita.get(visita_id, []))
        else:
            bucket[(chave, label)] += 1

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
    data = _load_visitas_base()

    corretores = listar_corretores_do_gerente(id_gerente, data=data)
    visitas = listar_visitas_do_gerente(
        id_gerente,
        start=start,
        end=end,
        limit=100000,
        data=data,
    )
    clientes = listar_clientes_do_gerente(
        id_gerente,
        start=start,
        end=end,
        limit=100000,
        data=data,
    )
    imoveis = listar_imoveis_do_gerente(
        id_gerente,
        start=start,
        end=end,
        limit=100000,
        data=data,
    )

    ranking_visitas = ranking_corretores_do_gerente(
        id_gerente,
        "visitas",
        start,
        end,
        data=data,
    )
    ranking_clientes = ranking_corretores_do_gerente(
        id_gerente,
        "clientes",
        start,
        end,
        data=data,
    )

    corretores_ativos = {
        v["id_corretor"]
        for v in visitas
        if _safe_str(v.get("id_corretor"))
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
            "media_visitas_por_corretor": round((len(visitas) / total_corretores), 2)
            if total_corretores
            else 0,
        },
        "graficos": {
            "visitas_por_dia": serie_gerente(
                id_gerente,
                "visitas",
                "dia",
                start,
                end,
                data=data,
            ),
            "clientes_por_dia": serie_gerente(
                id_gerente,
                "clientes",
                "dia",
                start,
                end,
                data=data,
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
        v for v in fato_visitas if _safe_str(v.get("Id_Corretor")) == _safe_str(id_corretor)
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

    clientes_unicos = {}
    parceiros_unicos = {}
    imoveis_unicos = set()
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

        visitas_resumo.append(
            {
                "Id_Visita": visita_id,
                "Data_Visita": _fmt_date(visita.get("Data_Visita")),
                "Id_Imovel": id_imovel,
                "Endereco_Externo": _safe_str(visita.get("Endereco_Externo")),
                "Proposta": _safe_str(visita.get("Proposta")),
                "Tipo_Captacao": _safe_str(visita.get("Tipo_Captacao")),
                "Clientes": ", ".join(nomes_clientes),
                "Parceiros": ", ".join(nomes_parceiros),
                "Qtd_Avaliacoes": len(avaliacoes_por_visita.get(visita_id, [])),
            }
        )

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
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise RuntimeError(
            "A biblioteca reportlab não está instalada. Instale com: pip install reportlab"
        ) from e

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title=f"Relatorio_Corretor_{ctx['Id_Corretor']}",
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "corretor_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    style_subtitle = ParagraphStyle(
        "corretor_subtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=10,
    )

    style_section = ParagraphStyle(
        "corretor_section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )

    def make_info_table(rows, col_widths=(46 * mm, 126 * mm)):
        tbl = Table(rows, colWidths=list(col_widths))
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
                ]
            )
        )
        return tbl

    def make_grid_table(data, widths):
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                    ("LEADING", (0, 0), (-1, -1), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return tbl

    story = []

    story.append(Paragraph("Relatório do Corretor", style_title))
    story.append(
        Paragraph(
            "Histórico consolidado de visitas, clientes, parceiros e imóveis atendidos.",
            style_subtitle,
        )
    )

    resumo_rows = [
        ["Id do corretor", _display(ctx.get("Id_Corretor"))],
        ["Nome", _display(ctx.get("Nome_Corretor"))],
        ["E-mail", _display(ctx.get("Email"))],
        ["Telefone", _display(ctx.get("Telefone"))],
        ["Instagram", _display(ctx.get("Instagram"))],
        ["Gerente", _display(ctx.get("Nome_Gerente"))],
        ["Equipe", _display(ctx.get("Equipe"))],
        ["Total de visitas", _display(ctx.get("Total_Visitas"))],
        ["Total de clientes", _display(ctx.get("Total_Clientes"))],
        ["Total de parceiros", _display(ctx.get("Total_Parceiros"))],
        ["Total de imóveis", _display(ctx.get("Total_Imoveis"))],
        ["Última visita", _display(ctx.get("Ultima_Visita"))],
    ]
    story.append(make_info_table(resumo_rows))
    story.append(Spacer(1, 10))

    if ctx["Clientes"]:
        story.append(Paragraph("Clientes vinculados", style_section))
        clientes_data = [["Cliente", "Telefone", "E-mail"]]
        for c in ctx["Clientes"]:
            clientes_data.append(
                [
                    _display(c.get("Nome_Cliente")),
                    _display(c.get("Telefone_Cliente")),
                    _display(c.get("Email_Cliente")),
                ]
            )
        story.append(make_grid_table(clientes_data, [62 * mm, 42 * mm, 68 * mm]))
        story.append(Spacer(1, 10))

    if ctx["Parceiros"]:
        story.append(Paragraph("Parceiros vinculados", style_section))
        parceiros_data = [["Parceiro", "Imobiliária"]]
        for p in ctx["Parceiros"]:
            parceiros_data.append(
                [
                    _display(p.get("Nome_Parceiro")),
                    _display(p.get("Imobiliaria")),
                ]
            )
        story.append(make_grid_table(parceiros_data, [82 * mm, 90 * mm]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Histórico de visitas", style_section))
    visitas_data = [["Id da visita", "Data", "Imóvel", "Proposta", "Clientes"]]
    for v in ctx["Visitas"]:
        visitas_data.append(
            [
                _display(v.get("Id_Visita")),
                _display(v.get("Data_Visita")),
                _display(v.get("Id_Imovel")),
                _display(v.get("Proposta")),
                _display(v.get("Clientes")),
            ]
        )
    story.append(make_grid_table(visitas_data, [28 * mm, 24 * mm, 24 * mm, 28 * mm, 68 * mm]))

    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_corretor_download(id_corretor: str):
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

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    reports_folder_id = _find_or_create_folder(
        DRIVE_CORRETOR_REPORTS_SUBFOLDER_NAME,
        parent_id=root_folder_id,
    )
    corretor_folder_id = _find_or_create_folder(id_corretor, parent_id=reports_folder_id)

    _trash_same_name_files_in_folder(corretor_folder_id, file_name)

    _, drive_files, drive = _get_services()
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False,
    )

    created = drive_files.create(
        body={"name": file_name, "parents": [corretor_folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    try:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception:
        pass

    drive_path = (
        f"{DRIVE_PARENT_FOLDER_NAME}/"
        f"{DRIVE_CORRETOR_REPORTS_SUBFOLDER_NAME}/"
        f"{id_corretor}/"
        f"{file_name}"
    )

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": drive_path,
    }


def gerar_pdf_gerente_consolidado_bytes(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise RuntimeError(
            "A biblioteca reportlab não está instalada. Instale com: pip install reportlab"
        ) from e

    data = _load_visitas_base()
    gerente = _find_first_by_key(data.get("Dim_Gerente", []), "IdGerente", id_gerente)
    if not gerente:
        raise ValueError(f"Gerente {id_gerente} não encontrado.")

    dashboard = dashboard_gerente(id_gerente, start, end)
    ranking = dashboard["rankings"]["visitas"]
    visitas = listar_visitas_do_gerente(
        id_gerente,
        start=start,
        end=end,
        limit=1000,
        data=data,
    )

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title=f"Relatorio_Gerente_{id_gerente}",
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "ger_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    style_subtitle = ParagraphStyle(
        "ger_subtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=10,
    )

    style_section = ParagraphStyle(
        "ger_section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )

    def make_grid_table(data_rows, widths):
        tbl = Table(data_rows, colWidths=widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return tbl

    story = []

    story.append(Paragraph("Relatório Consolidado do Gerente", style_title))
    story.append(
        Paragraph(
            f"{_display(gerente.get('Nome'))} • Equipe {_display(gerente.get('Equipe'))}",
            style_subtitle,
        )
    )

    resumo = dashboard["resumo"]
    resumo_data = [
        ["Indicador", "Valor"],
        ["Total de corretores", str(resumo["total_corretores"])],
        ["Corretores ativos", str(resumo["corretores_ativos"])],
        ["Corretores sem visita", str(resumo["corretores_sem_visita"])],
        ["Total de visitas", str(resumo["total_visitas"])],
        ["Total de clientes", str(resumo["total_clientes"])],
        ["Total de imóveis", str(resumo.get("total_imoveis", 0))],
        ["Média visitas/corretor", str(resumo["media_visitas_por_corretor"])],
    ]
    story.append(Paragraph("Resumo executivo", style_section))
    story.append(make_grid_table(resumo_data, [85 * mm, 87 * mm]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Ranking de visitas por corretor", style_section))
    ranking_data = [["Posição", "Corretor", "Total"]]
    for r in ranking:
        ranking_data.append([str(r["posicao"]), r["corretor"], str(r["total"])])
    story.append(make_grid_table(ranking_data, [24 * mm, 110 * mm, 38 * mm]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Visitas do período", style_section))
    visitas_data = [["Data", "Corretor", "Imóvel", "Proposta", "Clientes"]]
    for v in visitas[:200]:
        visitas_data.append(
            [
                _display(v.get("data_visita")),
                _display(v.get("corretor")),
                _display(v.get("id_imovel")),
                _display(v.get("proposta")),
                ", ".join(v.get("clientes", [])) if v.get("clientes") else "—",
            ]
        )
    story.append(make_grid_table(visitas_data, [22 * mm, 42 * mm, 24 * mm, 24 * mm, 64 * mm]))

    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_gerente_download(
    id_gerente: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
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

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    reports_folder_id = _find_or_create_folder(
        DRIVE_GERENTE_REPORTS_SUBFOLDER_NAME,
        parent_id=root_folder_id,
    )
    gerente_folder_id = _find_or_create_folder(id_gerente, parent_id=reports_folder_id)

    _trash_same_name_files_in_folder(gerente_folder_id, file_name)

    _, drive_files, drive = _get_services()
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False,
    )

    created = drive_files.create(
        body={"name": file_name, "parents": [gerente_folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    try:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception:
        pass

    drive_path = (
        f"{DRIVE_PARENT_FOLDER_NAME}/"
        f"{DRIVE_GERENTE_REPORTS_SUBFOLDER_NAME}/"
        f"{id_gerente}/"
        f"{file_name}"
    )

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": drive_path,
    }