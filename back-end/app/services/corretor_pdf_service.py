import os
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List

LOGO_PATH = "./app/utils/asserts/logo_61.png"

PINK       = (225, 0, 91)
DARK       = (40, 40, 40)
GRAY       = (110, 110, 110)
LIGHT_GRAY = (248, 248, 248)
WHITE      = (255, 255, 255)
PINK_LIGHT = (255, 235, 243)

KIND_LABELS = {"vgc_geral": "VGC", "vgv_geral": "VGV"}

# Layout fixo (A4 = 297mm)
Y_LOGO        = 10
Y_TITLE       = 24
Y_NAME        = 31
Y_META        = 37
Y_DIVIDER     = 42
Y_TABLE_HEAD  = 46
Y_ROWS_START  = 53
ROW_H         = 5.5
MAX_ROWS      = 29          # linhas visíveis máximas para caber na página
Y_SUMMARY     = 242         # início do bloco de resumo
Y_DECL        = 268
Y_SIG_LINE    = 276
Y_FOOTER      = 290

COL_WIDTHS  = [27, 20, 30, 27, 36, 40]   # total = 180mm
COL_HEADERS = ["Contrato", "Data", "V. Negócio", "V. Total 61", "Papel", "Comissão"]


def _fmt_br(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(raw: str) -> str:
    clean = str(raw or "").strip().split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean, fmt).strftime("%d/%m/%Y")
        except Exception:
            pass
    return clean


def _render_page(pdf, detalhe: Dict[str, Any]) -> None:
    """Desenha uma página completa (1 corretor). pdf.add_page() já foi chamado."""

    nome_title  = detalhe["corretor"].title()
    kind_label  = KIND_LABELS.get(detalhe.get("kind", ""), detalhe.get("kind", "").upper())
    start_fmt   = _fmt_date(detalhe.get("start") or "")
    end_fmt     = _fmt_date(detalhe.get("end") or "")
    af_note     = " (com fator ÷0,06)" if detalhe.get("apply_factor") else ""
    negs        = detalhe.get("negociacoes", [])

    # ── Logo ──────────────────────────────────────────────────
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=15, y=Y_LOGO, h=11)

    # ── Título ────────────────────────────────────────────────
    pdf.set_xy(15, Y_TITLE)
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(*PINK)
    pdf.cell(0, 6, "Relatório de Comissões", ln=False)

    # ── Nome (alinhado à direita do título) ───────────────────
    pdf.set_xy(15, Y_NAME)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 5, nome_title, ln=False)

    # ── Metadados ─────────────────────────────────────────────
    pdf.set_xy(15, Y_META)
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, f"Categoria: {kind_label}{af_note}   |   Período: {start_fmt} a {end_fmt}   |   {len(negs)} negociação(ões)", ln=False)

    # ── Divisória ─────────────────────────────────────────────
    pdf.set_draw_color(*PINK)
    pdf.set_line_width(0.5)
    pdf.line(15, Y_DIVIDER, 195, Y_DIVIDER)

    # ── Cabeçalho da tabela ───────────────────────────────────
    pdf.set_xy(15, Y_TABLE_HEAD)
    pdf.set_fill_color(*PINK)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Arial", "B", 7.5)
    for w, h in zip(COL_WIDTHS, COL_HEADERS):
        pdf.cell(w, 6, h, border=1, fill=True, align="C")

    # ── Linhas de dados ───────────────────────────────────────
    visible  = negs[:MAX_ROWS]
    truncado = len(negs) - MAX_ROWS if len(negs) > MAX_ROWS else 0

    y_row = Y_ROWS_START
    fill  = False
    pdf.set_font("Arial", "", 7)
    for neg in visible:
        row_data = [
            neg["id_contrato"],
            _fmt_date(neg["data_contrato"]),
            _fmt_br(neg["valor_negocio"]),
            _fmt_br(neg["valor_total_61"]),
            neg["papel"],
            _fmt_br(neg["valor_corretor"]),
        ]
        pdf.set_xy(15, y_row)
        pdf.set_fill_color(*LIGHT_GRAY)
        pdf.set_text_color(*DARK)
        for w, v in zip(COL_WIDTHS, row_data):
            pdf.cell(w, ROW_H, str(v), border=1, fill=fill, align="C")
        y_row += ROW_H
        fill = not fill

    # Linha de total da comissão
    pdf.set_xy(15, y_row)
    pdf.set_fill_color(*PINK)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Arial", "B", 7.5)
    total_label_w = sum(COL_WIDTHS[:-1])
    pdf.cell(total_label_w, ROW_H, "TOTAL COMISSÃO", border=1, fill=True, align="R")
    pdf.cell(COL_WIDTHS[-1], ROW_H, _fmt_br(detalhe["total"]), border=1, fill=True, align="C")
    y_row += ROW_H

    # Nota de truncamento (se houver)
    if truncado > 0:
        pdf.set_xy(15, y_row + 1)
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 4, f"* {truncado} contrato(s) não exibido(s) por limite de espaço.", ln=False)

    # ── Bloco de resumo (posição fixa) ────────────────────────
    pdf.set_xy(15, Y_SUMMARY)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 5, "Resumo do Período", ln=True)

    totais = [
        ("VGV Total (Valor Negócio)",            detalhe.get("total_vgv", 0.0)),
        ("VGC sem ÷0,06 (porção Valor Total 61)", detalhe.get("total_vgc_bruto", 0.0)),
        ("VGC com ÷0,06",                         detalhe.get("total_vgc_fator", 0.0)),
    ]
    lw, vw = 120, 60
    y_res = Y_SUMMARY + 6
    for label, valor in totais:
        pdf.set_xy(15, y_res)
        pdf.set_font("Arial", "", 8)
        pdf.set_fill_color(*LIGHT_GRAY)
        pdf.set_text_color(*DARK)
        pdf.cell(lw, 6.5, f"  {label}", border=1, fill=True, align="L")
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(*PINK)
        pdf.cell(vw, 6.5, _fmt_br(valor), border=1, fill=False, align="C")
        y_res += 6.5

    # ── Declaração ────────────────────────────────────────────
    pdf.set_xy(15, Y_DECL)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, "Declaro que estou de acordo com os valores apresentados acima.", align="C")

    # ── Linha de assinatura ───────────────────────────────────
    sig_x, sig_w = 60, 90
    pdf.set_draw_color(*DARK)
    pdf.set_line_width(0.25)
    pdf.line(sig_x, Y_SIG_LINE, sig_x + sig_w, Y_SIG_LINE)

    pdf.set_xy(15, Y_SIG_LINE + 2)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 4, nome_title, align="C")

    pdf.set_xy(15, Y_SIG_LINE + 7)
    pdf.set_font("Arial", "", 7)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, "Assinatura do Corretor", align="C")

    # ── Rodapé ────────────────────────────────────────────────
    pdf.set_xy(15, Y_FOOTER)
    pdf.set_font("Arial", "", 6.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, f"Gerado em: {date.today().strftime('%d/%m/%Y')}", align="R")


# ─────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────

def gerar_pdf_corretor(detalhe: Dict[str, Any]) -> BytesIO:
    """PDF de um único corretor (usado pelo modal individual)."""
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    _render_page(pdf, detalhe)

    buf = BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return buf


def gerar_pdf_todos(detalhes: List[Dict[str, Any]]) -> BytesIO:
    """PDF com 1 página por corretor (usado pelo botão 'Baixar Todos')."""
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)

    for detalhe in detalhes:
        pdf.add_page()
        _render_page(pdf, detalhe)

    buf = BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return buf
