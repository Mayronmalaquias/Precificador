from __future__ import annotations

import io
import os
from collections import defaultdict
from typing import Any, Dict, List

from app.services.visita_service import (
    _get_services,
    _find_or_create_folder,
    _trash_same_name_files_in_folder,
    _safe_str,
    _fmt_money_brl,
    _parse_ddmmyyyy_safe,
    _find_first_by_key,
    _find_all_by_key,
    _norm_key,
    SPREADSHEET_ID as VISITAS_SPREADSHEET_ID,
    DRIVE_PARENT_FOLDER_NAME,
)

DRIVE_IMOVEL_REPORTS_SUBFOLDER_NAME = os.getenv(
    "DRIVE_IMOVEL_REPORTS_SUBFOLDER_NAME",
    "Relatorios_Imovel_Gerados",
)


def _pick_from_row(row: Dict[str, Any] | None, *keys: str) -> str:
    if not row:
        return ""
    for key in keys:
        val = _safe_str(row.get(key))
        if val:
            return val
    return ""


def _display(v: Any, default: str = "—") -> str:
    s = _safe_str(v)
    return s if s else default


def _num_or_none(v: Any) -> float | None:
    s = _safe_str(v)
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return None


def _batch_get_rows_from_sheet(
    spreadsheet_id: str,
    ranges: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=spreadsheet_id,
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

        header = [str(c).strip() for c in values[0]]
        rows = []

        for raw in values[1:]:
            row = {}
            for i, h in enumerate(header):
                row[h] = raw[i] if i < len(raw) else ""
            rows.append(row)

        out[sheet_name] = rows

    return out


def _avg_scores_imovel(avaliacoes: List[Dict[str, Any]]) -> Dict[str, str]:
    campos = [
        ("Localizacao", "Localização"),
        ("Tamanho", "Tamanho"),
        ("Planta_Imovel", "Planta"),
        ("Qualidade_Acabamento", "Acabamento"),
        ("Estado_Conservacao", "Conservação"),
        ("Condominio_AreaComun", "Condomínio"),
        ("Preco", "Preço"),
        ("Nota_Geral", "Nota Geral"),
    ]

    out: Dict[str, str] = {}
    for key, label in campos:
        nums = [_num_or_none(a.get(key)) for a in avaliacoes]
        nums = [n for n in nums if n is not None]
        out[label] = f"{sum(nums) / len(nums):.1f}" if nums else "—"

    preco_n10_vals = [_num_or_none(a.get("Preco_N10")) for a in avaliacoes]
    preco_n10_vals = [n for n in preco_n10_vals if n is not None]
    out["Preço Nota 10"] = (
        _fmt_money_brl(sum(preco_n10_vals) / len(preco_n10_vals))
        if preco_n10_vals
        else "—"
    )

    return out


def _find_corretor_row_from_visita(
    visita: Dict[str, Any],
    dim_corretor: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    id_corretor = _pick_from_row(visita, "Id_Corretor")
    created_by = _pick_from_row(visita, "CreatedBy")

    corretor = None
    if id_corretor:
        corretor = _find_first_by_key(dim_corretor, "IdCorretor", id_corretor)

    if not corretor and created_by:
        corretor = _find_first_by_key(dim_corretor, "Email", created_by)

    return corretor


def _montar_contexto_pdf_imovel(imovel_id: str) -> Dict[str, Any]:
    data_visitas = _batch_get_rows_from_sheet(
        VISITAS_SPREADSHEET_ID,
        [
            "Fato_Visitas!A1:R",
            "Fato_Avaliacao!A1:N",
            "Dim_Cliente_Visita!A1:F",
            "Fato_Cliente_Visita!A1:D",
            "Dim_Corretor!A1:I",
            "Dim_Parceiro_Visita!A1:D",
            "Fato_Parceiro_Visita!A1:D",
        ],
    )

    fato_visitas = data_visitas.get("Fato_Visitas", [])
    fato_avaliacao = data_visitas.get("Fato_Avaliacao", [])
    dim_cliente = data_visitas.get("Dim_Cliente_Visita", [])
    fato_cliente_visita = data_visitas.get("Fato_Cliente_Visita", [])
    dim_corretor = data_visitas.get("Dim_Corretor", [])
    dim_parceiro = data_visitas.get("Dim_Parceiro_Visita", [])
    fato_parceiro_visita = data_visitas.get("Fato_Parceiro_Visita", [])

    visitas_do_imovel = [
        v for v in fato_visitas
        if _safe_str(v.get("Id_Imovel")) == _safe_str(imovel_id)
    ]

    if not visitas_do_imovel:
        raise ValueError(f"Nenhuma visita encontrada para o imóvel {imovel_id}.")

    visitas_do_imovel.sort(
        key=lambda v: (
            _parse_ddmmyyyy_safe(_safe_str(v.get("Data_Visita"))),
            _safe_str(v.get("CreatedAt")),
        ),
        reverse=True,
    )

    visita_mais_recente = visitas_do_imovel[0]

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

    enderecos_unicos = []
    enderecos_seen = set()
    for v in visitas_do_imovel:
        endereco = _pick_from_row(v, "Endereco_Externo")
        if endereco and endereco not in enderecos_seen:
            enderecos_unicos.append(endereco)
            enderecos_seen.add(endereco)

    todas_avaliacoes = []
    visitas_resumo = []
    clientes_unicos = []
    parceiros_unicos = []
    corretores_unicos = []

    ids_clientes_seen = set()
    ids_parceiros_seen = set()
    nomes_corretores_seen = set()

    for visita in visitas_do_imovel:
        visita_id = _pick_from_row(visita, "Id_Visita")

        corretor = _find_corretor_row_from_visita(visita, dim_corretor)
        nome_corretor = _pick_from_row(corretor, "Nome", "Nome_Corretor", "NomeCompleto")
        telefone_corretor = _pick_from_row(
            corretor,
            "Telefone",
            "Telefone_Corretor",
            "Celular",
            "WhatsApp",
        )

        if nome_corretor and nome_corretor not in nomes_corretores_seen:
            corretores_unicos.append(
                {
                    "Nome": nome_corretor,
                    "Telefone": telefone_corretor,
                    "Email": _pick_from_row(corretor, "Email") or _pick_from_row(visita, "CreatedBy"),
                    "Instagram": _pick_from_row(
                        corretor,
                        "Instragram",
                        "Instagram",
                        "Instagram_Corretor",
                    ),
                }
            )
            nomes_corretores_seen.add(nome_corretor)

        clientes_da_visita = []
        fatos_cliente = _find_all_by_key(fato_cliente_visita, "Id_Visita", visita_id)
        for fc in fatos_cliente:
            id_cliente = _pick_from_row(fc, "Id_Cliente")
            cli = cliente_map.get(id_cliente)
            if not cli:
                continue

            nome_cli = _pick_from_row(cli, "Nome_Cliente", "Nome")
            cliente_obj = {
                "Id_Cliente": id_cliente,
                "Nome_Cliente": nome_cli,
                "Telefone_Cliente": _pick_from_row(cli, "Telefone_Cliente", "Telefone"),
                "Email_Cliente": _pick_from_row(cli, "Email_Cliente", "Email"),
                "Papel_na_Visita": _pick_from_row(fc, "Papel_na_Visita", "Papel_Visita", "Papel"),
            }
            clientes_da_visita.append(cliente_obj)

            if id_cliente and id_cliente not in ids_clientes_seen:
                clientes_unicos.append(cliente_obj)
                ids_clientes_seen.add(id_cliente)

        parceiros_da_visita = []
        fatos_parceiro = _find_all_by_key(fato_parceiro_visita, "Id_Visita", visita_id)
        for fp in fatos_parceiro:
            id_parceiro = _pick_from_row(fp, "Id_Parceiro")
            par = parceiro_map.get(id_parceiro)
            if not par:
                continue

            parceiro_obj = {
                "Id_Parceiro": id_parceiro,
                "Nome_Parceiro": _pick_from_row(par, "Nome_Parceiro", "Nome"),
                "Imobiliaria": _pick_from_row(par, "Imobiliaria"),
                "Papel_na_Visita": _pick_from_row(fp, "Papel_na_Visita", "Papel_Visita", "Papel"),
            }
            parceiros_da_visita.append(parceiro_obj)

            if id_parceiro and id_parceiro not in ids_parceiros_seen:
                parceiros_unicos.append(parceiro_obj)
                ids_parceiros_seen.add(id_parceiro)

        avals_visita = _find_all_by_key(fato_avaliacao, "Id_Visita", visita_id)
        for a in avals_visita:
            id_cliente_aval = _pick_from_row(a, "Id_Cliente")
            cli = cliente_map.get(id_cliente_aval)
            todas_avaliacoes.append(
                {
                    "Nome_Cliente": _pick_from_row(cli, "Nome_Cliente", "Nome"),
                    "Localizacao": _pick_from_row(a, "Localizacao"),
                    "Tamanho": _pick_from_row(a, "Tamanho"),
                    "Planta_Imovel": _pick_from_row(a, "Planta_Imovel"),
                    "Qualidade_Acabamento": _pick_from_row(a, "Qualidade_Acabamento"),
                    "Estado_Conservacao": _pick_from_row(a, "Estado_Conservacao"),
                    "Condominio_AreaComun": _pick_from_row(a, "Condominio_AreaComun"),
                    "Preco": _pick_from_row(a, "Preco"),
                    "Preco_N10": _pick_from_row(a, "Preco_N10"),
                    "Nota_Geral": _pick_from_row(a, "Nota_Geral"),
                }
            )

        visitas_resumo.append(
            {
                "Id_Visita": visita_id,
                "Data_Visita": _pick_from_row(visita, "Data_Visita"),
                "Proposta": _pick_from_row(visita, "Proposta"),
                "Corretor": nome_corretor,
                "Clientes": ", ".join(
                    [c["Nome_Cliente"] for c in clientes_da_visita if c["Nome_Cliente"]]
                ),
                "Parceiros": ", ".join(
                    [p["Nome_Parceiro"] for p in parceiros_da_visita if p["Nome_Parceiro"]]
                ),
                "Endereco_Externo": _pick_from_row(visita, "Endereco_Externo"),
                "Tipo_Captacao": _pick_from_row(visita, "Tipo_Captacao"),
            }
        )

    return {
        "Id_Imovel": _safe_str(imovel_id),
        "Endereco": _pick_from_row(visita_mais_recente, "Endereco_Externo"),
        "Enderecos_Encontrados": enderecos_unicos,
        "Tipo_Captacao": _pick_from_row(visita_mais_recente, "Tipo_Captacao"),
        "Imovel_Nao_Captado": _pick_from_row(visita_mais_recente, "Imovel_Nao_Captado"),
        "Visita_Com_Parceiro": _pick_from_row(visita_mais_recente, "Visita_Com_Parceiro"),
        "Total_Visitas": len(visitas_do_imovel),
        "Data_Ultima_Visita": _pick_from_row(visita_mais_recente, "Data_Visita"),
        "Corretores": corretores_unicos,
        "Clientes": clientes_unicos,
        "Parceiros": parceiros_unicos,
        "Avaliacoes": todas_avaliacoes,
        "TotAval": len(todas_avaliacoes),
        "Visitas": visitas_resumo,
    }


def _build_pdf_imovel_bytes(ctx: Dict[str, Any]) -> bytes:
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
        title=f"Relatorio_Imovel_{ctx['Id_Imovel']}",
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "imovel_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    style_subtitle = ParagraphStyle(
        "imovel_subtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=10,
    )

    style_section = ParagraphStyle(
        "imovel_section",
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

    story.append(Paragraph("Relatório do Imóvel", style_title))
    story.append(
        Paragraph(
            "Histórico consolidado de visitas, clientes, corretores e avaliações do imóvel.",
            style_subtitle,
        )
    )

    resumo_rows = [
        ["Id do imóvel", _display(ctx.get("Id_Imovel"))],
        ["Endereço principal", _display(ctx.get("Endereco"))],
        ["Tipo de captação", _display(ctx.get("Tipo_Captacao"))],
        ["Visita com parceiro", _display(ctx.get("Visita_Com_Parceiro"))],
        ["Imóvel não captado", _display(ctx.get("Imovel_Nao_Captado"))],
        ["Total de visitas", _display(ctx.get("Total_Visitas"))],
        ["Última visita", _display(ctx.get("Data_Ultima_Visita"))],
    ]
    story.append(make_info_table(resumo_rows))
    story.append(Spacer(1, 10))

    if ctx.get("Enderecos_Encontrados"):
        story.append(Paragraph("Endereços encontrados nas visitas", style_section))
        enderecos_data = [["Endereço"]]
        for endereco in ctx["Enderecos_Encontrados"]:
            enderecos_data.append([_display(endereco)])
        story.append(make_grid_table(enderecos_data, [172 * mm]))
        story.append(Spacer(1, 10))

    if ctx["Corretores"]:
        story.append(Paragraph("Corretores envolvidos", style_section))
        corretores_data = [["Nome", "Telefone", "E-mail", "Instagram"]]
        for c in ctx["Corretores"]:
            corretores_data.append(
                [
                    _display(c.get("Nome")),
                    _display(c.get("Telefone")),
                    _display(c.get("Email")),
                    _display(c.get("Instagram")),
                ]
            )
        story.append(make_grid_table(corretores_data, [55 * mm, 35 * mm, 60 * mm, 24 * mm]))
        story.append(Spacer(1, 10))

    if ctx["Clientes"]:
        story.append(Paragraph("Clientes vinculados", style_section))
        clientes_data = [["Cliente", "Telefone", "E-mail", "Papel"]]
        for c in ctx["Clientes"]:
            clientes_data.append(
                [
                    _display(c.get("Nome_Cliente")),
                    _display(c.get("Telefone_Cliente")),
                    _display(c.get("Email_Cliente")),
                    _display(c.get("Papel_na_Visita")),
                ]
            )
        story.append(make_grid_table(clientes_data, [52 * mm, 34 * mm, 62 * mm, 26 * mm]))
        story.append(Spacer(1, 10))

    if ctx["Parceiros"]:
        story.append(Paragraph("Parceiros", style_section))
        parceiros_data = [["Parceiro", "Imobiliária", "Papel"]]
        for p in ctx["Parceiros"]:
            parceiros_data.append(
                [
                    _display(p.get("Nome_Parceiro")),
                    _display(p.get("Imobiliaria")),
                    _display(p.get("Papel_na_Visita")),
                ]
            )
        story.append(make_grid_table(parceiros_data, [65 * mm, 75 * mm, 34 * mm]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Resumo das avaliações", style_section))
    medias = _avg_scores_imovel(ctx["Avaliacoes"])
    resumo_avaliacoes_data = [["Critério", "Resultado"]]
    for label, value in medias.items():
        resumo_avaliacoes_data.append([label, value])
    story.append(make_grid_table(resumo_avaliacoes_data, [95 * mm, 79 * mm]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Histórico de visitas", style_section))
    visitas_data = [["Id da visita", "Data", "Corretor", "Clientes", "Proposta"]]
    for v in ctx["Visitas"]:
        visitas_data.append(
            [
                _display(v.get("Id_Visita")),
                _display(v.get("Data_Visita")),
                _display(v.get("Corretor")),
                _display(v.get("Clientes")),
                _display(v.get("Proposta")),
            ]
        )

    story.append(
        make_grid_table(
            visitas_data,
            [26 * mm, 20 * mm, 36 * mm, 58 * mm, 34 * mm],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_imovel_download(imovel_id: str):
    ctx = _montar_contexto_pdf_imovel(imovel_id)
    pdf_bytes = _build_pdf_imovel_bytes(ctx)
    file_name = f"Relatorio_Imovel_{imovel_id}.pdf"
    return io.BytesIO(pdf_bytes), file_name


def gerar_pdf_imovel_publico(imovel_id: str) -> Dict[str, str]:
    ctx = _montar_contexto_pdf_imovel(imovel_id)
    pdf_bytes = _build_pdf_imovel_bytes(ctx)
    file_name = f"Relatorio_Imovel_{imovel_id}.pdf"

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    reports_folder_id = _find_or_create_folder(
        DRIVE_IMOVEL_REPORTS_SUBFOLDER_NAME,
        parent_id=root_folder_id,
    )
    imovel_folder_id = _find_or_create_folder(imovel_id, parent_id=reports_folder_id)

    _trash_same_name_files_in_folder(imovel_folder_id, file_name)

    _, drive_files, drive = _get_services()

    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False,
    )

    created = drive_files.create(
        body={"name": file_name, "parents": [imovel_folder_id]},
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
        f"{DRIVE_IMOVEL_REPORTS_SUBFOLDER_NAME}/"
        f"{imovel_id}/"
        f"{file_name}"
    )

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": drive_path,
    }


def listar_imoveis_do_corretor(
    id_corretor: str,
    q: str = "",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    id_corretor = (id_corretor or "").strip()
    qn = _norm_key(q)

    if not id_corretor:
        return []

    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=VISITAS_SPREADSHEET_ID,
        ranges=[
            "Fato_Visitas!A1:R",
            "Fato_Cliente_Visita!A1:D",
            "Dim_Cliente_Visita!A1:F",
        ],
    ).execute()

    value_ranges = res.get("valueRanges", [])

    def to_rows(vr):
        vals = vr.get("values", [])
        if not vals:
            return []
        header = vals[0]
        rows = []
        for raw in vals[1:]:
            obj = {}
            for i, h in enumerate(header):
                obj[h] = raw[i] if i < len(raw) else ""
            rows.append(obj)
        return rows

    visitas_rows = to_rows(value_ranges[0]) if len(value_ranges) > 0 else []
    fato_cliente_rows = to_rows(value_ranges[1]) if len(value_ranges) > 1 else []
    dim_cliente_rows = to_rows(value_ranges[2]) if len(value_ranges) > 2 else []

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
            "ultima_data_ord": None,
            "clientes": [],
            "visitas_ids": [],
            "endereco_externo": "",
        }
    )

    for r in visitas_rows:
        id_cor_row = _safe_str(r.get("Id_Corretor"))
        if id_cor_row != id_corretor:
            continue

        id_imovel = _safe_str(r.get("Id_Imovel"))
        id_visita = _safe_str(r.get("Id_Visita"))
        data_visita = _safe_str(r.get("Data_Visita"))
        endereco_externo = _safe_str(r.get("Endereco_Externo"))

        if not id_imovel:
            continue

        data_ord = _parse_ddmmyyyy_safe(data_visita)
        item = agrupado[id_imovel]
        item["id_imovel"] = id_imovel
        item["qtd_visitas"] += 1
        item["visitas_ids"].append(id_visita)

        if item["ultima_data_ord"] is None or data_ord >= item["ultima_data_ord"]:
            item["ultima_data_ord"] = data_ord
            item["ultima_data"] = data_visita
            if endereco_externo:
                item["endereco_externo"] = endereco_externo

        for nome_cli in clientes_por_visita.get(id_visita, []):
            if nome_cli not in item["clientes"]:
                item["clientes"].append(nome_cli)

    lista = []
    for _, item in agrupado.items():
        label_parts = [
            item["id_imovel"],
            f"{item['qtd_visitas']} visita(s)",
        ]
        if item["ultima_data"]:
            label_parts.append(f"Última: {item['ultima_data']}")
        if item["endereco_externo"]:
            label_parts.append(item["endereco_externo"])

        label = " - ".join(label_parts).strip()

        hay = " ".join(
            [
                item["id_imovel"],
                item["ultima_data"],
                label,
                item["endereco_externo"],
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
                "endereco_externo": item["endereco_externo"],
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