import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from app.database import SessionLocal
from app.models.estoque_legado import LeadLegado
from app.models.fato_bases import FatoEstoque
from app.models.usuarios import Usuarios
from app.models.equipe import Equipe


CONTACT2SALE_URL = "https://api.contact2sale.com/integration/leads"
# A API leva 5-10 s por pagina; 45 s estourava no cron. Com a espera do 429 ja
# existente, uma pagina lenta nao derruba mais a rodada.
TIMEOUT_C2S = 120
MAX_TENTATIVAS_PAGINA = 3
RECEPCAO_CREATED_BY_ID = "d6cd52d3d32cefcc24245ce5aa46e48a"
RECEPCAO_CREATED_BY_NAME = "Atendimento/Recepcao"

FONTE_MAP = {
    "ImovelWeb": "WI",
    "Grupo Zap": "OLX",
    "DF imoveis": "DF",
    "DF imóveis": "DF",
    "Telefone": "61",
    "(Site Proprio)": "61",
    "(Site Próprio)": "61",
    "Site Proprio": "Site",
    "Site Próprio": "Site",
    "Facebook Leads": "99Web",
    "Instagram Leads": "99Web",
    "C2Sbot": "DF",
}

CONTATO_MAP = {
    "Internet": "I",
    "WhatsApp": "W",
    "Telefone": "L",
    "Rede Social": "I",
}

GERENTE_POR_EQUIPE = {
    "NOVA UNIAO": "Marcelo Pincinato",
    "NOVA UNIÃO": "Marcelo Pincinato",
    "AGUIA": "Marcelo Souza",
    "ÁGUIA": "Marcelo Souza",
    "LOTUS": "Thais Tannus",
    "LÓTUS": "Thais Tannus",
    "AGEF": "Jose Marques",
    "PRIME": "Luana Salvinski",
    "SENNA": "Helio Junio",
}

MOTIVOS_RESPOSTA = {
    "Compra adiada",
    "Apenas pesquisando",
    "Avaliacao baixa na troca",
    "Avaliação baixa na troca",
    "Ja foi vendido",
    "Já foi vendido",
    "Localizacao nao agradou",
    "Localização não agradou",
    "Nao possui renda",
    "Não possui renda",
    "Preco alto",
    "Preço alto",
    "Produto nao agradou",
    "Produto não agradou",
    "Proposta do cliente com valor baixo",
    "Proposta inviavel",
    "Proposta inviável",
}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    replacements = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Õ": "O", "Ô": "O",
        "Ú": "U",
        "Ç": "C",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text)


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text[:len(fmt.replace("%z", "+0000"))], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _iso_start(day: date) -> str:
    return f"{day.isoformat()}T00:00:00Z"


def _iso_end(day: date) -> str:
    return f"{day.isoformat()}T23:59:59Z"


def _normalize_codigo(value: Any) -> str:
    text = _clean(value).replace("'", "")
    if re.fullmatch(r"\d+(\.0+)?", text):
        return str(int(float(text)))
    return text


def _lead_attr(lead: Dict[str, Any]) -> Dict[str, Any]:
    return lead.get("attributes") or {}


def _source_name(attributes: Dict[str, Any]) -> str:
    return _clean((attributes.get("lead_source") or {}).get("name"))


def _channel_name(attributes: Dict[str, Any]) -> str:
    return _clean((attributes.get("channel") or {}).get("name"))


def _company_team(attributes: Dict[str, Any]) -> str:
    name = _clean((attributes.get("company") or {}).get("name"))
    if "Equipe" in name:
        return name.split("Equipe")[-1].strip()
    return name


def _extract_code_from_messages(messages: Any) -> str:
    if not messages:
        return ""
    raw = " ".join(str(m.get("body") if isinstance(m, dict) else m) for m in messages)
    patterns = [
        r"(?:cod(?:igo)?\.?|c[oó]d\.?)\s*[:#-]?\s*(\d{3,})",
        r"\bim[oó]vel\s*(\d{3,})\b",
        r"\b(\d{5,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _motivo_from_logs(logs: Any) -> Optional[str]:
    if not isinstance(logs, list):
        return None
    for item in logs:
        body = item.get("body") if isinstance(item, dict) else None
        if not isinstance(body, str):
            continue
        match = re.search(r"Motivo\(s\):\s*(.*?)\s*\| \| Detalhes:", body)
        if match:
            return match.group(1).strip()
    return None


def _tem_motivo_resposta(logs: Any) -> bool:
    if not isinstance(logs, list):
        return False
    motivos_norm = {_norm(m) for m in MOTIVOS_RESPOSTA}
    for item in logs:
        body = item.get("body") if isinstance(item, dict) else ""
        body_norm = _norm(body)
        if any(m in body_norm for m in motivos_norm):
            return True
    return False


def _relatorio(attributes: Dict[str, Any]) -> str:
    archived = bool((attributes.get("archive_details") or {}).get("archived"))
    relatorio = "D" if archived else "C"
    if attributes.get("archive_details") is not None:
        motivo = _motivo_from_logs(attributes.get("log") or [])
        if motivo and _norm(motivo) == "CORRETOR PARCEIRO":
            return "P"
        if _tem_motivo_resposta(attributes.get("log") or []):
            return "C"
        if motivo and _norm(motivo) == "NAO CONSEGUI CONTATAR":
            return "R"
    return relatorio


def _carregar_mapas(session) -> Dict[str, Dict[str, str]]:
    corretor_nome_id = {}
    gerente_nome_id = {}
    equipe_nome_id = {}

    for usuario in session.query(Usuarios).filter(Usuarios.id_usuarios.isnot(None)).all():
        nome_key = _norm(usuario.nome or usuario.username)
        if nome_key:
            corretor_nome_id[nome_key] = usuario.id_usuarios
            if usuario.permissao == "gerente":
                gerente_nome_id[nome_key] = usuario.id_usuarios

    for equipe in session.query(Equipe).all():
        if equipe.nome:
            equipe_nome_id[_norm(equipe.nome)] = equipe.id_equipe

    return {
        "corretor_nome_id": corretor_nome_id,
        "gerente_nome_id": gerente_nome_id,
        "equipe_nome_id": equipe_nome_id,
    }


def _resolver_corretor_id(mapas: Dict[str, Dict[str, str]], nome_ou_id: str) -> str:
    value = _clean(nome_ou_id)
    return mapas["corretor_nome_id"].get(_norm(value), value)


def _resolver_gerente_id(mapas: Dict[str, Dict[str, str]], equipe_ou_nome: str) -> str:
    value = _clean(equipe_ou_nome)
    mapped_name = GERENTE_POR_EQUIPE.get(value) or GERENTE_POR_EQUIPE.get(_norm(value)) or value
    return (
        mapas["gerente_nome_id"].get(_norm(mapped_name))
        or mapas["equipe_nome_id"].get(_norm(value))
        or mapas["equipe_nome_id"].get(_norm(mapped_name))
        or value
    )


def _estoque_por_codigo(session, codigo: str) -> Tuple[str, str]:
    codigo = _normalize_codigo(codigo)
    if not codigo:
        return "", ""
    estoque = (
        session.query(FatoEstoque)
        .filter(FatoEstoque.codigo_imovel == codigo)
        .order_by(FatoEstoque.data_estoque.desc(), FatoEstoque.id.desc())
        .first()
    )
    if not estoque:
        return "", ""
    return _clean(estoque.captador1), _clean(estoque.id_gerente)


def _linha_de_lead(session, mapas: Dict[str, Dict[str, str]], lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    attributes = _lead_attr(lead)
    if not attributes:
        return None

    fonte_original = _source_name(attributes)
    created_by = attributes.get("created_by") or {}
    created_id = created_by.get("id")
    created_name = _clean(created_by.get("name"))
    created_is_recepcao = created_id == RECEPCAO_CREATED_BY_ID and _norm(created_name) == _norm(RECEPCAO_CREATED_BY_NAME)

    if fonte_original not in {"Faixa", "Indicação", "Indicacao"}:
        if not created_is_recepcao and not (created_id is None and not created_name):
            return None

    equipe_nome = _company_team(attributes)
    if _norm(equipe_nome) == "LOCACAO":
        return None

    seller_name = _clean((attributes.get("seller") or {}).get("name"))
    responsavel = seller_name or created_name
    if _norm(responsavel) == "LIXEIRA":
        return None

    customer = attributes.get("customer") or {}
    product = attributes.get("product") or {}
    codigo = _normalize_codigo(product.get("prop_ref") or _extract_code_from_messages(attributes.get("messages")))

    atendimento = seller_name
    equipe = equipe_nome
    if codigo and _norm(atendimento) in {_norm("Atendimento/Recepcao"), _norm("Helio Junio Martins Rodrigues")}:
        estoque_captador, _ = _estoque_por_codigo(session, codigo)
        if estoque_captador:
            atendimento = estoque_captador

    if codigo and _norm(equipe) == _norm("61 Imoveis"):
        _, estoque_gerente = _estoque_por_codigo(session, codigo)
        if estoque_gerente:
            equipe = estoque_gerente

    fonte = FONTE_MAP.get(fonte_original, fonte_original)
    contato_original = _channel_name(attributes)
    contato = CONTATO_MAP.get(contato_original, contato_original)

    return {
        "data": _parse_date(attributes.get("created_at")),
        "fonte": fonte,
        "contato": contato,
        "relatorio": _relatorio(attributes),
        "cliente": _clean(customer.get("name")),
        "telefone": _clean(customer.get("phone")),
        "codigo_imovel": codigo,
        "atendimento": _resolver_corretor_id(mapas, atendimento),
        "equipe": _resolver_gerente_id(mapas, equipe),
        "observacao": "",
        "san_observacao": "",
    }


def _dedupe_key(row: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        _norm(row.get("cliente")),
        _norm(row.get("telefone")),
        _normalize_codigo(row.get("codigo_imovel")),
        _norm(row.get("fonte")),
    )


def _existe_lead(session, row: Dict[str, Any]) -> bool:
    return session.query(LeadLegado.id).filter(
        LeadLegado.cliente == row.get("cliente"),
        LeadLegado.telefone == row.get("telefone"),
        LeadLegado.codigo_imovel == row.get("codigo_imovel"),
        LeadLegado.fonte == row.get("fonte"),
    ).first() is not None


def inserir_leads(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    resumo = {"inseridos": 0, "ignorados_duplicados": 0, "ignorados_invalidos": 0, "preview": []}
    session = SessionLocal()
    try:
        mapas = _carregar_mapas(session)
        seen = set()
        for raw in rows:
            if isinstance(raw, (list, tuple)):
                row = {
                    "data": raw[0] if len(raw) > 0 else None,
                    "fonte": raw[1] if len(raw) > 1 else "",
                    "contato": raw[2] if len(raw) > 2 else "",
                    "relatorio": raw[3] if len(raw) > 3 else "",
                    "cliente": raw[4] if len(raw) > 4 else "",
                    "telefone": raw[5] if len(raw) > 5 else "",
                    "codigo_imovel": raw[6] if len(raw) > 6 else "",
                    "atendimento": raw[7] if len(raw) > 7 else "",
                    "equipe": raw[8] if len(raw) > 8 else "",
                    "observacao": raw[9] if len(raw) > 9 else "",
                    "san_observacao": raw[10] if len(raw) > 10 else "",
                }
            else:
                row = dict(raw)
            if not row.get("cliente"):
                resumo["ignorados_invalidos"] += 1
                continue
            row["data"] = _parse_date(row.get("data"))
            row["codigo_imovel"] = _normalize_codigo(row.get("codigo_imovel") or row.get("codigo"))
            row["atendimento"] = _resolver_corretor_id(mapas, row.get("atendimento"))
            row["equipe"] = _resolver_gerente_id(mapas, row.get("equipe"))
            key = _dedupe_key(row)
            if key in seen or _existe_lead(session, row):
                resumo["ignorados_duplicados"] += 1
                continue
            seen.add(key)
            session.add(LeadLegado(**{
                field: row.get(field)
                for field in (
                    "data", "fonte", "contato", "relatorio", "cliente", "telefone",
                    "codigo_imovel", "atendimento", "equipe", "observacao", "san_observacao",
                )
            }))
            resumo["inseridos"] += 1
            if len(resumo["preview"]) < 10:
                resumo["preview"].append(row.get("codigo_imovel") or row.get("cliente"))
        session.commit()
        return resumo
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def importar_contact2sale(data_de: Any = None, data_ate: Any = None, per_page: int = 50) -> Dict[str, Any]:
    token = os.getenv("CONTACT2SALE_TOKEN") or os.getenv("C2S_TOKEN")
    if not token:
        raise RuntimeError("Configure CONTACT2SALE_TOKEN no ambiente para importar leads.")

    inicio = _parse_date(data_de) or (date.today() - timedelta(days=1))
    fim = _parse_date(data_ate) or inicio
    # Teto da API e 50: acima disso o /leads devolve 403 "'perpage' must be less than or equal to 50".
    per_page = min(max(int(per_page or 50), 1), 50)

    session = SessionLocal()
    try:
        mapas = _carregar_mapas(session)
        page = 1
        total_api = 0
        processados = 0
        ignorados = 0
        inseridos = 0
        duplicados = 0
        seen = set()
        tentativas_pagina = {}

        while True:
            try:
                response = requests.get(
                    CONTACT2SALE_URL,
                    headers={"Authorization": token, "Content-Type": "application/json"},
                    params={
                        "page": page,
                        "perpage": per_page,
                        "created_lt": _iso_end(fim),
                        "created_gte": _iso_start(inicio),
                    },
                    timeout=TIMEOUT_C2S,
                )
            except requests.Timeout:
                # A API do C2S responde entre 5 e 10 s por pagina e piora nas paginas
                # profundas. Com `timeout=45` o cron das 3h10 caiu em 19 e 20/08 e, como
                # o commit era so no fim, perdeu tudo que ja tinha lido.
                tentativas_pagina[page] = tentativas_pagina.get(page, 0) + 1
                if tentativas_pagina[page] > MAX_TENTATIVAS_PAGINA:
                    raise RuntimeError(
                        f"Contact2Sale nao respondeu na pagina {page} apos "
                        f"{MAX_TENTATIVAS_PAGINA} tentativas."
                    )
                time.sleep(10)
                continue
            if response.status_code == 429:
                # Teto documentado: 10 req/min. Backfill de varios meses estoura isso
                # em poucas paginas — espera a janela resetar e repete a mesma pagina.
                time.sleep(65)
                continue
            if response.status_code >= 400:
                raise RuntimeError(f"Contact2Sale HTTP {response.status_code}: {response.text[:800]}")

            leads = (response.json() or {}).get("data") or []
            total_api += len(leads)
            if not leads:
                break

            for lead in leads:
                row = _linha_de_lead(session, mapas, lead)
                if not row or not row.get("cliente"):
                    ignorados += 1
                    continue
                key = _dedupe_key(row)
                if key in seen or _existe_lead(session, row):
                    duplicados += 1
                    continue
                seen.add(key)
                session.add(LeadLegado(**row))
                inseridos += 1
                processados += 1

            # Commit por pagina. Antes havia um unico commit no fim, entao qualquer
            # falha no meio (timeout, 500 da API) descartava a importacao inteira. Como
            # o dedupe compara contra o que ja esta gravado, reprocessar e inofensivo.
            session.commit()

            if len(leads) < per_page:
                break
            page += 1

        session.commit()
        return {
            "total_api": total_api,
            "processados": processados,
            "inseridos": inseridos,
            "ignorados": ignorados,
            "ignorados_duplicados": duplicados,
            "data_de": inicio.isoformat(),
            "data_ate": fim.isoformat(),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_leads(page: int = 1, per_page: int = 50) -> Dict[str, Any]:
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 50), 1), 200)
    session = SessionLocal()
    try:
        query = session.query(LeadLegado).order_by(LeadLegado.data.desc(), LeadLegado.id.desc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [
                {
                    "id": item.id,
                    "data": item.data.isoformat() if item.data else None,
                    "fonte": item.fonte,
                    "contato": item.contato,
                    "relatorio": item.relatorio,
                    "cliente": item.cliente,
                    "telefone": item.telefone,
                    "codigo_imovel": item.codigo_imovel,
                    "atendimento": item.atendimento,
                    "equipe": item.equipe,
                    "observacao": item.observacao,
                    "san_observacao": item.san_observacao,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    finally:
        session.close()


def listar_leads_do_corretor(id_corretor: str, q: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    id_corretor = _clean(id_corretor)
    if not id_corretor:
        return []

    q_norm = _norm(q)
    limit = min(max(int(limit or 50), 1), 200)
    session = SessionLocal()
    try:
        owner_values = {id_corretor}
        usuario = (
            session.query(Usuarios)
            .filter(Usuarios.id_usuarios == id_corretor)
            .first()
        )
        if usuario:
            owner_values.update(
                value
                for value in (usuario.nome, usuario.username)
                if _clean(value)
            )

        candidates = (
            session.query(LeadLegado)
            .filter(LeadLegado.atendimento.in_(list(owner_values)))
            .order_by(LeadLegado.data.desc(), LeadLegado.id.desc())
            .limit(1000)
            .all()
        )

        items = []
        owner_norms = {_norm(value) for value in owner_values if _clean(value)}
        for item in candidates:
            if _norm(item.atendimento) not in owner_norms:
                continue
            haystack = _norm(
                " ".join(
                    _clean(value)
                    for value in (
                        item.cliente,
                        item.telefone,
                        item.codigo_imovel,
                        item.fonte,
                        item.contato,
                    )
                )
            )
            if q_norm and q_norm not in haystack:
                continue
            items.append({
                "id": item.id,
                "data": item.data.isoformat() if item.data else None,
                "fonte": item.fonte,
                "contato": item.contato,
                "relatorio": item.relatorio,
                "cliente": item.cliente,
                "telefone": item.telefone,
                "codigo_imovel": item.codigo_imovel,
                "atendimento": item.atendimento,
                "equipe": item.equipe,
            })
            if len(items) >= limit:
                break
        return items
    finally:
        session.close()
