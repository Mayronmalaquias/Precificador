from __future__ import annotations

import io
import os
import datetime as dt
from typing import Any, Dict, List, Optional

from googleapiclient.http import MediaIoBaseUpload

from app.services.visita_service import _get_services


# ==========================================================
# CONFIG
# ==========================================================
APP_ID = "NewApp-287229161-25-08-26"
SPREADSHEET_ID = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"

APP_ROOT_PARTS = ["appsheet", "data", APP_ID]
REL_PATH_BASE = ["Relatorios", "Visitas"]


# ==========================================================
# HELPERS DE LEITURA
# ==========================================================
def _safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _rows_from_values(values: List[List[Any]]) -> List[Dict[str, Any]]:
    if not values:
        return []

    header = [str(c).strip() for c in values[0]]
    out: List[Dict[str, Any]] = []

    for row in values[1:]:
        item = {}
        for i, col in enumerate(header):
            item[col] = row[i] if i < len(row) else ""
        out.append(item)

    return out


def _batch_get_ranges(ranges: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute()

    value_ranges = res.get("valueRanges", [])
    out: Dict[str, List[Dict[str, Any]]] = {}

    for rg, vr in zip(ranges, value_ranges):
        sheet_name = rg.split("!")[0]
        out[sheet_name] = _rows_from_values(vr.get("values", []))

    return out


def _find_first(rows: List[Dict[str, Any]], key: str, value: Any) -> Optional[Dict[str, Any]]:
    val = _safe_str(value)
    for row in rows:
        if _safe_str(row.get(key)) == val:
            return row
    return None


def _find_all(rows: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]:
    val = _safe_str(value)
    return [row for row in rows if _safe_str(row.get(key)) == val]


def _fmt_date_br(v: Any) -> str:
    if v in (None, ""):
        return ""

    if isinstance(v, dt.datetime):
        return v.strftime("%d/%m/%Y")

    if isinstance(v, dt.date):
        return v.strftime("%d/%m/%Y")

    s = str(v).strip()
    if not s:
        return ""

    formatos = [
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formatos:
        try:
            return dt.datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except Exception:
            continue

    return s


def _fmt_datetime_br(v: Any) -> str:
    if v in (None, ""):
        return ""

    if isinstance(v, dt.datetime):
        return v.strftime("%d/%m/%Y %H:%M:%S")

    s = str(v).strip()
    if not s:
        return ""

    formatos = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formatos:
        try:
            d = dt.datetime.strptime(s, fmt)
            return d.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            continue

    return s


def _fmt_money_brl(v: Any) -> str:
    if v in (None, ""):
        return ""
    try:
        n = float(str(v).replace(".", "").replace(",", "."))
        return f"R$ {n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


# ==========================================================
# DRIVE
# ==========================================================
def _find_folder_by_name(drive_files, name: str, parent_id: Optional[str] = None) -> Optional[str]:
    safe_name = name.replace("'", "\\'")
    q_parts = [
        "mimeType='application/vnd.google-apps.folder'",
        f"name='{safe_name}'",
        "trashed=false",
    ]
    if parent_id:
        q_parts.append(f"'{parent_id}' in parents")

    q = " and ".join(q_parts)

    res = drive_files.list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        pageSize=20,
    ).execute()

    files = res.get("files", [])
    if not files:
        return None
    return files[0]["id"]


def _create_folder(drive_files, name: str, parent_id: Optional[str] = None) -> str:
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]

    created = drive_files.create(body=body, fields="id,name").execute()
    return created["id"]


def _get_or_create_child_folder(drive_files, parent_id: str, child_name: str) -> str:
    existing = _find_folder_by_name(drive_files, child_name, parent_id=parent_id)
    if existing:
        return existing
    return _create_folder(drive_files, child_name, parent_id=parent_id)


def _ensure_drive_path(parts: List[str]) -> str:
    """
    Garante /appsheet/data/<APP_ID>/Relatorios/Visitas/<Id_Visita>
    """
    _, drive_files, _ = _get_services()

    parent_id = None
    for part in parts:
        if parent_id is None:
            existing = _find_folder_by_name(drive_files, part, parent_id=None)
            parent_id = existing or _create_folder(drive_files, part, parent_id=None)
        else:
            parent_id = _get_or_create_child_folder(drive_files, parent_id, part)

    return parent_id


def _trash_existing_files_same_name(drive_files, folder_id: str, file_name: str) -> None:
    safe_name = file_name.replace("'", "\\'")
    q = (
        f"name='{safe_name}' and "
        f"'{folder_id}' in parents and "
        "trashed=false"
    )
    res = drive_files.list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        pageSize=50,
    ).execute()

    for f in res.get("files", []):
        drive_files.update(fileId=f["id"], body={"trashed": True}).execute()


def _upload_pdf_bytes_to_drive(folder_id: str, file_name: str, pdf_bytes: bytes) -> Dict[str, str]:
    _, drive_files, drive = _get_services()

    _trash_existing_files_same_name(drive_files, folder_id, file_name)

    bio = io.BytesIO(pdf_bytes)
    media = MediaIoBaseUpload(bio, mimetype="application/pdf", resumable=False)

    created = drive_files.create(
        body={"name": file_name, "parents": [folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    # permissão pública por link
    try:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception:
        pass

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", ""),
    }


# ==========================================================
# CONTEXTO DA VISITA
# ==========================================================
def _montar_contexto_visita(visita_id: str) -> Dict[str, Any]:
    data = _batch_get_ranges(
        [
            "Fato_Visitas!A1:R",
            "Fato_Avaliacao!A1:N",
            "Dim_Cliente_Visita!A1:F",
            "Fato_Cliente_Visita!A1:D",
            "Dim_Corretor!A1:I",
            "Dim_Parceiro_Visita!A1:D",
            "Fato_Parceiro_Visita!A1:D",
        ]
    )

    fato_visitas = data.get("Fato_Visitas", [])
    # print(fato_visitas)
    fato_avaliacao = data.get("Fato_Avaliacao", [])
    dim_cliente = data.get("Dim_Cliente_Visita", [])
    fato_cliente_visita = data.get("Fato_Cliente_Visita", [])
    dim_corretor = data.get("Dim_Corretor", [])
    dim_parceiro = data.get("Dim_Parceiro_Visita", [])
    fato_parceiro_visita = data.get("Fato_Parceiro_Visita", [])

    visita = _find_first(fato_visitas, "Id_Visita", visita_id)
    if not visita:
        raise ValueError(f"Visita {visita_id} não encontrada.")

    corretor = None
    if _safe_str(visita.get("Id_Corretor")):
        corretor = _find_first(dim_corretor, "IdCorretor", visita.get("Id_Corretor"))

    cliente_map = {
        _safe_str(c.get("Id_Cliente")): c
        for c in dim_cliente
        if _safe_str(c.get("Id_Cliente"))
    }

    parceiro_map = {
        _safe_str(p.get("Id_Parceiro")): p
        for p in dim_parceiro
        if _safe_str(p.get("Id_Parceiro"))
    }

    fatos_cliente = _find_all(fato_cliente_visita, "Id_Visita", visita_id)
    clientes: List[Dict[str, Any]] = []

    for fc in fatos_cliente:
        id_cliente = _safe_str(fc.get("Id_Cliente"))
        cli = cliente_map.get(id_cliente)
        if not cli:
            continue

        clientes.append(
            {
                "Id_Cliente": id_cliente,
                "Nome_Cliente": _safe_str(cli.get("Nome_Cliente")),
                "Telefone_Cliente": _safe_str(cli.get("Telefone_Cliente")),
                "Email_Cliente": _safe_str(cli.get("Email_Cliente")),
                "Papel_na_Visita": _safe_str(fc.get("Papel_na_Visita")),
            }
        )

    # fallback pelo assinante, se não houver relacionamento na fato
    if not clientes and _safe_str(visita.get("Id_Cliente_Assinante")):
        cli = cliente_map.get(_safe_str(visita.get("Id_Cliente_Assinante")))
        if cli:
            clientes.append(
                {
                    "Id_Cliente": _safe_str(cli.get("Id_Cliente")),
                    "Nome_Cliente": _safe_str(cli.get("Nome_Cliente")),
                    "Telefone_Cliente": _safe_str(cli.get("Telefone_Cliente")),
                    "Email_Cliente": _safe_str(cli.get("Email_Cliente")),
                    "Papel_na_Visita": "Assinante",
                }
            )

    fatos_parceiro = _find_all(fato_parceiro_visita, "Id_Visita", visita_id)
    parceiros: List[Dict[str, Any]] = []

    for fp in fatos_parceiro:
        id_parceiro = _safe_str(fp.get("Id_Parceiro"))
        par = parceiro_map.get(id_parceiro)
        if not par:
            continue

        parceiros.append(
            {
                "Id_Parceiro": id_parceiro,
                "Nome_Parceiro": _safe_str(par.get("Nome_Parceiro")),
                "Imobiliaria": _safe_str(par.get("Imobiliaria")),
                "Papel_na_Visita": _safe_str(fp.get("Papel_na_Visita")),
            }
        )

    if not parceiros and _safe_str(visita.get("Id_Parceiro")):
        par = parceiro_map.get(_safe_str(visita.get("Id_Parceiro")))
        if par:
            parceiros.append(
                {
                    "Id_Parceiro": _safe_str(par.get("Id_Parceiro")),
                    "Nome_Parceiro": _safe_str(par.get("Nome_Parceiro")),
                    "Imobiliaria": _safe_str(par.get("Imobiliaria")),
                    "Papel_na_Visita": "Parceiro",
                }
            )

    avals = _find_all(fato_avaliacao, "Id_Visita", visita_id)

    def deref_cliente_nome(id_cliente: Any) -> str:
        cli = cliente_map.get(_safe_str(id_cliente))
        if cli:
            return _safe_str(cli.get("Nome_Cliente"))
        return ""

    avaliacoes = []
    for a in avals:
        avaliacoes.append(
            {
                "Nome_Cliente": deref_cliente_nome(a.get("Id_Cliente")),
                "Localizacao": _safe_str(a.get("Localizacao")),
                "Tamanho": _safe_str(a.get("Tamanho")),
                "Planta_Imovel": _safe_str(a.get("Planta_Imovel")),
                "Qualidade_Acabamento": _safe_str(a.get("Qualidade_Acabamento")),
                "Estado_Conservacao": _safe_str(a.get("Estado_Conservacao")),
                "Condominio_AreaComun": _safe_str(a.get("Condominio_AreaComun")),
                "Preco": _safe_str(a.get("Preco")),
                "Preco_N10": _safe_str(a.get("Preco_N10")),
                "Nota_Geral": _safe_str(a.get("Nota_Geral")),
            }
        )

    ctx = {
        "Id_Visita": _safe_str(visita.get("Id_Visita")),
        "CreatedAt": _fmt_datetime_br(visita.get("CreatedAt")),
        "Data_Visita": _fmt_date_br(visita.get("Data_Visita")),
        "Proposta": _safe_str(visita.get("Proposta")),
        "Id_Imovel": _safe_str(visita.get("Id_Imovel")),
        "CorretorNome": _safe_str(corretor.get("Nome")) if corretor else "",
        "CorretorTelefone": _safe_str(corretor.get("Telefone")) if corretor else "",
        "CorretorInstagram": _safe_str(corretor.get("Instragram")) if corretor else "",
        "CorretorEmail": _safe_str(corretor.get("Email")) if corretor else "",
        "CorretorDescricao": _safe_str(corretor.get("Descricao")) if corretor else "",
        "Link_Audio": _safe_str(visita.get("Link_Audio")),
        "Link_Imagem": _safe_str(visita.get("Link_Imagem")),
        "Clientes": clientes,
        "Parceiros": parceiros,
        "Avaliacoes": avaliacoes,
        "TotAval": len(avaliacoes),
    }

    return ctx


# ==========================================================
# GERAÇÃO DO PDF
# ==========================================================
def _build_pdf_bytes_visita(ctx: Dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as e:
        raise RuntimeError(
            "A biblioteca reportlab não está instalada. Instale com: pip install reportlab"
        ) from e

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Relatorio_Visita_{ctx['Id_Visita']}",
    )

    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_h2 = styles["Heading2"]
    style_body = styles["BodyText"]
    style_small = ParagraphStyle(
        "small",
        parent=style_body,
        fontSize=8.5,
        leading=10.5,
    )

    story = []

    story.append(Paragraph("Relatório de Visita", style_title))
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            f"<b>Id da visita:</b> {ctx['Id_Visita']}<br/>"
            f"<b>Data da visita:</b> {ctx['Data_Visita'] or '-'}<br/>"
            f"<b>Criado em:</b> {ctx['CreatedAt'] or '-'}<br/>"
            f"<b>Imóvel:</b> {ctx['Id_Imovel'] or '-'}<br/>"
            f"<b>Proposta:</b> {ctx['Proposta'] or '-'}",
            style_body,
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Corretor", style_h2))
    story.append(
        Paragraph(
            f"<b>Nome:</b> {ctx['CorretorNome'] or '-'}<br/>"
            f"<b>Telefone:</b> {ctx['CorretorTelefone'] or '-'}<br/>"
            f"<b>Instagram:</b> {ctx['CorretorInstagram'] or '-'}<br/>"
            f"<b>E-mail:</b> {ctx['CorretorEmail'] or '-'}<br/>"
            f"<b>Descrição:</b> {ctx['CorretorDescricao'] or '-'}",
            style_body,
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Clientes", style_h2))
    clientes_data = [["Cliente", "Telefone", "E-mail", "Papel"]]
    if ctx["Clientes"]:
        for c in ctx["Clientes"]:
            clientes_data.append(
                [
                    c.get("Nome_Cliente") or "-",
                    c.get("Telefone_Cliente") or "-",
                    c.get("Email_Cliente") or "-",
                    c.get("Papel_na_Visita") or "-",
                ]
            )
    else:
        clientes_data.append(["Sem clientes vinculados", "-", "-", "-"])

    clientes_table = Table(clientes_data, colWidths=[55 * mm, 35 * mm, 60 * mm, 30 * mm])
    clientes_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    story.append(clientes_table)
    story.append(Spacer(1, 10))

    if ctx["Parceiros"]:
        story.append(Paragraph("Parceiros", style_h2))
        parceiros_data = [["Parceiro", "Imobiliária", "Papel"]]
        for p in ctx["Parceiros"]:
            parceiros_data.append(
                [
                    p.get("Nome_Parceiro") or "-",
                    p.get("Imobiliaria") or "-",
                    p.get("Papel_na_Visita") or "-",
                ]
            )

        parceiros_table = Table(parceiros_data, colWidths=[70 * mm, 70 * mm, 40 * mm])
        parceiros_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ]
            )
        )
        story.append(parceiros_table)
        story.append(Spacer(1, 10))

    story.append(Paragraph(f"Avaliações ({ctx['TotAval']})", style_h2))
    aval_cols = [
        "Cliente",
        "Localização",
        "Tamanho",
        "Planta",
        "Acabamento",
        "Conservação",
        "Condomínio",
        "Preço",
        "Preço Nota 10",
        "Nota Geral",
    ]
    aval_data = [aval_cols]

    if ctx["Avaliacoes"]:
        for a in ctx["Avaliacoes"]:
            aval_data.append(
                [
                    a.get("Nome_Cliente") or "-",
                    a.get("Localizacao") or "-",
                    a.get("Tamanho") or "-",
                    a.get("Planta_Imovel") or "-",
                    a.get("Qualidade_Acabamento") or "-",
                    a.get("Estado_Conservacao") or "-",
                    a.get("Condominio_AreaComun") or "-",
                    a.get("Preco") or "-",
                    _fmt_money_brl(a.get("Preco_N10")) if a.get("Preco_N10") else "-",
                    a.get("Nota_Geral") or "-",
                ]
            )
    else:
        aval_data.append(["Sem avaliações", "-", "-", "-", "-", "-", "-", "-", "-", "-"])

    aval_table = Table(
        aval_data,
        repeatRows=1,
        colWidths=[28 * mm, 18 * mm, 15 * mm, 16 * mm, 18 * mm, 18 * mm, 18 * mm, 12 * mm, 22 * mm, 13 * mm],
    )
    aval_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("LEADING", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    story.append(aval_table)
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            f"<b>Link do áudio:</b> {ctx['Link_Audio'] or '-'}<br/>"
            f"<b>Link da imagem:</b> {ctx['Link_Imagem'] or '-'}",
            style_small,
        )
    )

    doc.build(story)
    return buffer.getvalue()


# ==========================================================
# FUNÇÕES PÚBLICAS
# ==========================================================
def gerar_pdf_visita_download(visita_id: str):
    ctx = _montar_contexto_visita(visita_id)
    pdf_bytes = _build_pdf_bytes_visita(ctx)
    file_name = f"Relatorio_Visita_{visita_id}.pdf"
    return io.BytesIO(pdf_bytes), file_name


def gerar_pdf_visita_publico(visita_id: str) -> Dict[str, str]:
    ctx = _montar_contexto_visita(visita_id)
    pdf_bytes = _build_pdf_bytes_visita(ctx)

    file_name = f"Relatorio_Visita_{visita_id}.pdf"
    parts = APP_ROOT_PARTS + REL_PATH_BASE + [visita_id]
    folder_id = _ensure_drive_path(parts)

    uploaded = _upload_pdf_bytes_to_drive(folder_id, file_name, pdf_bytes)

    drive_path = "/".join(parts + [file_name])

    return {
        **uploaded,
        "drive_path": drive_path,
    }