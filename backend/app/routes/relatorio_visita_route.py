from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any, Dict, List

from flask import request
from flask_restx import Namespace, Resource



relatorio_visita = Namespace(
    "relatorio_visita",
    description="Relatório de visita em PDF (o documento assinado pelo cliente)",
)


def _safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _norm_key(s: str) -> str:
    return " ".join(str(s or "").strip().lower().split())


def _parse_ddmmyyyy_safe(s: str) -> dt.date:
    try:
        return dt.datetime.strptime((s or "").strip(), "%d/%m/%Y").date()
    except Exception:
        return dt.date.min


def listar_imoveis_do_corretor(
    id_corretor: str,
    q: str = "",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    id_corretor = (id_corretor or "").strip()
    qn = _norm_key(q)

    if not id_corretor:
        return []

    from app.services import db_loaders

    visitas_rows = db_loaders.carregar_aba("Fato_Visitas")
    fato_cliente_rows = db_loaders.carregar_aba("Fato_Cliente_Visita")
    dim_cliente_rows = db_loaders.carregar_aba("Dim_Cliente_Visita")

    cliente_map = {
        _safe_str(r.get("Id_Cliente")): _safe_str(r.get("Nome_Cliente"))
        for r in dim_cliente_rows
        if _safe_str(r.get("Id_Cliente"))
    }

    clientes_por_visita = defaultdict(list)
    for r in fato_cliente_rows:
        id_visita = _safe_str(r.get("Id_Visita"))
        id_cliente = _safe_str(r.get("Id_Cliente"))
        nome = cliente_map.get(id_cliente, "")

        if not id_visita or not nome:
            continue

        if nome not in clientes_por_visita[id_visita]:
            clientes_por_visita[id_visita].append(nome)

    agrupado = defaultdict(
        lambda: {
            "id_imovel": "",
            "qtd_visitas": 0,
            "ultima_data": "",
            "ultima_data_ord": dt.date.min,
            "clientes": [],
            "visitas_ids": [],
        }
    )

    for r in visitas_rows:
        id_cor_row = _safe_str(r.get("Id_Corretor"))
        if id_cor_row != id_corretor:
            continue

        id_imovel = _safe_str(r.get("Id_Imovel"))
        id_visita = _safe_str(r.get("Id_Visita"))
        data_visita = _safe_str(r.get("Data_Visita"))

        if not id_imovel:
            continue

        data_ord = _parse_ddmmyyyy_safe(data_visita)
        item = agrupado[id_imovel]
        item["id_imovel"] = id_imovel
        item["qtd_visitas"] += 1
        item["visitas_ids"].append(id_visita)

        if data_ord >= item["ultima_data_ord"]:
            item["ultima_data_ord"] = data_ord
            item["ultima_data"] = data_visita

        for nome_cli in clientes_por_visita.get(id_visita, []):
            if nome_cli not in item["clientes"]:
                item["clientes"].append(nome_cli)

    lista = []
    for _, item in agrupado.items():
        label = " - ".join(
            [
                item["id_imovel"],
                f"{item['qtd_visitas']} visita(s)",
                f"Última: {item['ultima_data']}" if item["ultima_data"] else "",
            ]
        ).strip()

        hay = " ".join(
            [
                item["id_imovel"],
                item["ultima_data"],
                label,
                " ".join(item["clientes"]),
            ]
        )

        if qn and qn not in _norm_key(hay):
            continue

        lista.append(
            {
                "id_imovel": item["id_imovel"],
                "qtd_visitas": item["qtd_visitas"],
                "ultima_data": item["ultima_data"],
                "clientes": item["clientes"][:5],
                "label": label,
            }
        )

    lista.sort(
        key=lambda x: (
            _parse_ddmmyyyy_safe(x.get("ultima_data", "")),
            x.get("id_imovel", ""),
        ),
        reverse=True,
    )

    return lista[: max(1, int(limit or 50))]


@relatorio_visita.route("/corretores/<string:id_corretor>/imoveis")
class ImoveisDoCorretorResource(Resource):
    def get(self, id_corretor: str):
        """
        Lista os imóveis visitados por um corretor.
        Ex:
        /api/corretores/123/imoveis?q=joao&limit=20
        """
        try:
            q = (request.args.get("q") or "").strip()

            try:
                limit = int(request.args.get("limit", 50))
            except Exception:
                limit = 50

            data = listar_imoveis_do_corretor(
                id_corretor=id_corretor,
                q=q,
                limit=limit,
            )

            return {
                "ok": True,
                "id_corretor": id_corretor,
                "q": q,
                "limit": limit,
                "total": len(data),
                "items": data,
            }, 200

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }, 500