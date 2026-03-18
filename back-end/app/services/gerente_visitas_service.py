# app/services/gerente_visita_service.py
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Set, Tuple

from app.services.visita_service import _get_services


# ==========================================================
# CONFIG
# ==========================================================
SPREADSHEET_ID = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"


# ==========================================================
# HELPERS GERAIS
# ==========================================================
def _safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _norm(s: Any) -> str:
    return _safe_str(s).strip().lower()


def _parse_date(value: Any) -> dt.date | None:
    """
    Tenta interpretar datas vindas do Sheets.
    Aceita:
    - dd/MM/yyyy
    - yyyy-MM-dd
    - yyyy-MM-ddTHH:MM:SS
    - datetime/date já prontos
    """
    if value is None or value == "":
        return None

    if isinstance(value, dt.datetime):
        return value.date()

    if isinstance(value, dt.date):
        return value

    s = _safe_str(value)
    if not s:
        return None

    formatos = [
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formatos:
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            continue

    return None


def _inicio_semana(ref: dt.date | None = None) -> dt.date:
    """
    Considera semana iniciando na segunda-feira.
    """
    ref = ref or dt.date.today()
    return ref - dt.timedelta(days=ref.weekday())


def _is_data_na_semana(data_value: Any, ref: dt.date | None = None) -> bool:
    data = _parse_date(data_value)
    if not data:
        return False

    inicio = _inicio_semana(ref)
    fim = inicio + dt.timedelta(days=6)
    return inicio <= data <= fim


def _batch_get_as_dicts(ranges: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Lê múltiplas abas com cabeçalho na primeira linha e devolve:
    {
      "NomeAba": [ {coluna: valor, ...}, ... ]
    }
    """
    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute()

    value_ranges = res.get("valueRanges", [])
    out: Dict[str, List[Dict[str, Any]]] = {}

    for rg, vr in zip(ranges, value_ranges):
        values = vr.get("values", [])
        sheet_name = rg.split("!")[0]

        if not values:
            out[sheet_name] = []
            continue

        header = [_safe_str(c) for c in values[0]]
        rows_dict = []

        for raw in values[1:]:
            item = {}
            for i, col in enumerate(header):
                item[col] = raw[i] if i < len(raw) else ""
            rows_dict.append(item)

        out[sheet_name] = rows_dict

    return out


def _sort_ranking_desc(itens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        itens,
        key=lambda x: (
            int(x.get("visitas", 0) or 0),
            _norm(x.get("nome")),
        ),
        reverse=True,
    )


def _sort_relatorio_corretor(itens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        itens,
        key=lambda x: (
            int(x.get("visitasTotais", 0) or 0),
            int(x.get("visitasSemana", 0) or 0),
            int(x.get("clientesTotais", 0) or 0),
            _norm(x.get("nome")),
        ),
        reverse=True,
    )


def _sort_relatorio_drive(itens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        itens,
        key=lambda x: (
            _parse_date(x.get("dataVisita")) or dt.date.min,
            _norm(x.get("corretor")),
            _norm(x.get("cliente")),
        ),
        reverse=True,
    )


# ==========================================================
# HELPERS DE DOMÍNIO
# ==========================================================
def _buscar_corretores_do_gerente(
    dim_corretor_rows: List[Dict[str, Any]],
    id_gerente: str,
) -> List[Dict[str, Any]]:
    id_gerente = _safe_str(id_gerente)
    return [
        row
        for row in dim_corretor_rows
        if _safe_str(row.get("IdGerente")) == id_gerente
    ]


def _mapa_corretores(corretores_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapa: Dict[str, Dict[str, Any]] = {}
    for row in corretores_rows:
        id_corretor = _safe_str(row.get("IdCorretor"))
        if id_corretor:
            mapa[id_corretor] = row
    return mapa


def _mapa_clientes(dim_cliente_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapa: Dict[str, Dict[str, Any]] = {}
    for row in dim_cliente_rows:
        id_cliente = _safe_str(row.get("Id_Cliente"))
        if id_cliente:
            mapa[id_cliente] = row
    return mapa


def _clientes_por_visita(
    fato_cliente_visita_rows: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """
    Retorna:
    {
      id_visita: [id_cliente1, id_cliente2, ...]
    }
    """
    mapa: Dict[str, List[str]] = {}

    for row in fato_cliente_visita_rows:
        id_visita = _safe_str(row.get("Id_Visita"))
        id_cliente = _safe_str(row.get("Id_Cliente"))

        if not id_visita or not id_cliente:
            continue

        mapa.setdefault(id_visita, [])
        if id_cliente not in mapa[id_visita]:
            mapa[id_visita].append(id_cliente)

    return mapa


def _nome_cliente_principal_da_visita(
    visita_row: Dict[str, Any],
    clientes_por_visita: Dict[str, List[str]],
    cliente_map: Dict[str, Dict[str, Any]],
) -> str:
    """
    Tenta descobrir o cliente principal da visita.
    Prioridade:
    1) Fato_Cliente_Visita
    2) Id_Cliente_Assinante em Fato_Visitas
    """
    id_visita = _safe_str(visita_row.get("Id_Visita"))
    ids_cliente = clientes_por_visita.get(id_visita, [])

    if ids_cliente:
        primeiro = ids_cliente[0]
        cli = cliente_map.get(primeiro, {})
        return _safe_str(cli.get("Nome_Cliente"))

    id_cliente_assinante = _safe_str(visita_row.get("Id_Cliente_Assinante"))
    if id_cliente_assinante:
        cli = cliente_map.get(id_cliente_assinante, {})
        return _safe_str(cli.get("Nome_Cliente"))

    return ""


def _extrair_link_ficha(visita_row: Dict[str, Any]) -> str:
    """
    Define qual link será enviado para o front como 'link da ficha'.
    Prioridade:
    1) Anexo_Ficha_Visita
    2) Link_Imagem
    """
    anexo = _safe_str(visita_row.get("Anexo_Ficha_Visita"))
    if anexo:
        return anexo

    link_imagem = _safe_str(visita_row.get("Link_Imagem"))
    if link_imagem:
        return link_imagem

    return ""


# ==========================================================
# MÉTRICAS PRINCIPAIS
# ==========================================================
def obter_visitas_totais_gerente(
    fato_visitas_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
) -> int:
    return sum(
        1
        for row in fato_visitas_rows
        if _safe_str(row.get("Id_Corretor")) in ids_corretores
           and _safe_str(row.get("Id_Visita"))
    )


def obter_visitas_semana_gerente(
    fato_visitas_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
) -> int:
    return sum(
        1
        for row in fato_visitas_rows
        if _safe_str(row.get("Id_Corretor")) in ids_corretores
           and _safe_str(row.get("Id_Visita"))
           and _is_data_na_semana(row.get("Data_Visita"))
    )


def obter_clientes_totais_gerente(
    dim_cliente_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
) -> int:
    clientes_unicos: Set[str] = set()

    for row in dim_cliente_rows:
        id_cliente = _safe_str(row.get("Id_Cliente"))
        id_corretor = _safe_str(row.get("Id_Corretor"))

        if id_cliente and id_corretor in ids_corretores:
            clientes_unicos.add(id_cliente)

    return len(clientes_unicos)


def obter_ranking_total_gerente(
    corretores_rows: List[Dict[str, Any]],
    fato_visitas_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
) -> List[Dict[str, Any]]:
    contador: Dict[str, int] = {cid: 0 for cid in ids_corretores}

    for row in fato_visitas_rows:
        cid = _safe_str(row.get("Id_Corretor"))
        if cid in ids_corretores and _safe_str(row.get("Id_Visita")):
            contador[cid] = contador.get(cid, 0) + 1

    out = []
    for cor in corretores_rows:
        cid = _safe_str(cor.get("IdCorretor"))
        if cid not in ids_corretores:
            continue

        out.append({
            "id_corretor": cid,
            "nome": _safe_str(cor.get("Nome")),
            "visitas": contador.get(cid, 0),
        })

    return _sort_ranking_desc(out)


def obter_ranking_semana_gerente(
    corretores_rows: List[Dict[str, Any]],
    fato_visitas_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
) -> List[Dict[str, Any]]:
    contador: Dict[str, int] = {cid: 0 for cid in ids_corretores}

    for row in fato_visitas_rows:
        cid = _safe_str(row.get("Id_Corretor"))
        if (
            cid in ids_corretores
            and _safe_str(row.get("Id_Visita"))
            and _is_data_na_semana(row.get("Data_Visita"))
        ):
            contador[cid] = contador.get(cid, 0) + 1

    out = []
    for cor in corretores_rows:
        cid = _safe_str(cor.get("IdCorretor"))
        if cid not in ids_corretores:
            continue

        out.append({
            "id_corretor": cid,
            "nome": _safe_str(cor.get("Nome")),
            "visitas": contador.get(cid, 0),
        })

    return _sort_ranking_desc(out)


def obter_relatorio_corretores_gerente(
    corretores_rows: List[Dict[str, Any]],
    fato_visitas_rows: List[Dict[str, Any]],
    dim_cliente_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
) -> List[Dict[str, Any]]:
    visitas_total_por_corretor: Dict[str, int] = {cid: 0 for cid in ids_corretores}
    visitas_semana_por_corretor: Dict[str, int] = {cid: 0 for cid in ids_corretores}
    clientes_por_corretor: Dict[str, Set[str]] = {cid: set() for cid in ids_corretores}

    for row in fato_visitas_rows:
        cid = _safe_str(row.get("Id_Corretor"))
        if cid not in ids_corretores:
            continue

        if _safe_str(row.get("Id_Visita")):
            visitas_total_por_corretor[cid] = visitas_total_por_corretor.get(cid, 0) + 1

            if _is_data_na_semana(row.get("Data_Visita")):
                visitas_semana_por_corretor[cid] = visitas_semana_por_corretor.get(cid, 0) + 1

    for row in dim_cliente_rows:
        cid = _safe_str(row.get("Id_Corretor"))
        id_cliente = _safe_str(row.get("Id_Cliente"))

        if cid in ids_corretores and id_cliente:
            clientes_por_corretor.setdefault(cid, set()).add(id_cliente)

    out = []
    for cor in corretores_rows:
        cid = _safe_str(cor.get("IdCorretor"))
        if cid not in ids_corretores:
            continue

        out.append({
            "id_corretor": cid,
            "nome": _safe_str(cor.get("Nome")),
            "email": _safe_str(cor.get("Email")),
            "telefone": _safe_str(cor.get("Telefone")),
            "instagram": _safe_str(cor.get("Instragram")) or _safe_str(cor.get("Instagram")),
            "visitasTotais": visitas_total_por_corretor.get(cid, 0),
            "visitasSemana": visitas_semana_por_corretor.get(cid, 0),
            "clientesTotais": len(clientes_por_corretor.get(cid, set())),
        })

    return _sort_relatorio_corretor(out)


def obter_relatorio_drive_gerente(
    fato_visitas_rows: List[Dict[str, Any]],
    ids_corretores: Set[str],
    corretor_map: Dict[str, Dict[str, Any]],
    cliente_map: Dict[str, Dict[str, Any]],
    clientes_por_visita: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    out = []

    for row in fato_visitas_rows:
        id_visita = _safe_str(row.get("Id_Visita"))
        id_corretor = _safe_str(row.get("Id_Corretor"))

        if not id_visita or id_corretor not in ids_corretores:
            continue

        corretor = corretor_map.get(id_corretor, {})
        nome_corretor = _safe_str(corretor.get("Nome"))
        cliente_principal = _nome_cliente_principal_da_visita(
            row,
            clientes_por_visita,
            cliente_map,
        )
        link_ficha = _extrair_link_ficha(row)

        out.append({
            "id_visita": id_visita,
            "id_corretor": id_corretor,
            "corretor": nome_corretor,
            "cliente": cliente_principal,
            "dataVisita": _safe_str(row.get("Data_Visita")),
            "imovelId": _safe_str(row.get("Id_Imovel")),
            "proposta": _safe_str(row.get("Proposta")),
            "tipoCaptacao": _safe_str(row.get("Tipo_Captacao")),
            "enderecoExterno": _safe_str(row.get("Endereco_Externo")),
            "anexoFichaVisita": _safe_str(row.get("Anexo_Ficha_Visita")),
            "linkImagem": _safe_str(row.get("Link_Imagem")),
            "drive_url": link_ficha,
        })

    return _sort_relatorio_drive(out)


# ==========================================================
# FUNÇÃO PRINCIPAL
# ==========================================================
def gerar_json_corretores(id_gerente: str) -> Dict[str, Any]:
    """
    Retorna todos os dados necessários para a tela do gerente.
    """
    id_gerente = _safe_str(id_gerente)
    if not id_gerente:
        raise ValueError("id_gerente é obrigatório")

    data = _batch_get_as_dicts(
        [
            "Dim_Corretor!A1:I",
            "Dim_Gerente!A1:D",
            "Dim_Cliente_Visita!A1:F",
            "Fato_Cliente_Visita!A1:D",
            "Fato_Visitas!A1:R",
        ]
    )

    dim_corretor_rows = data.get("Dim_Corretor", [])
    dim_gerente_rows = data.get("Dim_Gerente", [])
    dim_cliente_rows = data.get("Dim_Cliente_Visita", [])
    fato_cliente_visita_rows = data.get("Fato_Cliente_Visita", [])
    fato_visitas_rows = data.get("Fato_Visitas", [])

    gerente = next(
        (g for g in dim_gerente_rows if _safe_str(g.get("IdGerente")) == id_gerente),
        None,
    )
    if not gerente:
        raise ValueError(f"Gerente {id_gerente} não encontrado na Dim_Gerente")

    corretores_rows = _buscar_corretores_do_gerente(dim_corretor_rows, id_gerente)
    ids_corretores = {
        _safe_str(row.get("IdCorretor"))
        for row in corretores_rows
        if _safe_str(row.get("IdCorretor"))
    }

    corretor_map = _mapa_corretores(corretores_rows)
    cliente_map = _mapa_clientes(dim_cliente_rows)
    clientes_por_visita = _clientes_por_visita(fato_cliente_visita_rows)

    visitas_totais = obter_visitas_totais_gerente(
        fato_visitas_rows,
        ids_corretores,
    )

    clientes_totais = obter_clientes_totais_gerente(
        dim_cliente_rows,
        ids_corretores,
    )

    visitas_semana = obter_visitas_semana_gerente(
        fato_visitas_rows,
        ids_corretores,
    )

    ranking_total = obter_ranking_total_gerente(
        corretores_rows,
        fato_visitas_rows,
        ids_corretores,
    )

    ranking_semana = obter_ranking_semana_gerente(
        corretores_rows,
        fato_visitas_rows,
        ids_corretores,
    )

    relatorio_corretor = obter_relatorio_corretores_gerente(
        corretores_rows,
        fato_visitas_rows,
        dim_cliente_rows,
        ids_corretores,
    )

    relatorio_drive = obter_relatorio_drive_gerente(
        fato_visitas_rows,
        ids_corretores,
        corretor_map,
        cliente_map,
        clientes_por_visita,
    )

    return {
        "gerente": {
            "id_gerente": _safe_str(gerente.get("IdGerente")),
            "nome": _safe_str(gerente.get("Nome")),
            "equipe": _safe_str(gerente.get("Equipe")),
            "email": _safe_str(gerente.get("email")),
            "qtdCorretores": len(ids_corretores),
        },
        "visitasTotais": visitas_totais,
        "clientesTotais": clientes_totais,
        "visitasSemana": visitas_semana,
        "rankingTotal": ranking_total,
        "rankingSemana": ranking_semana,
        "relatorioCorretor": relatorio_corretor,
        "relatorioDrive": relatorio_drive,
    }