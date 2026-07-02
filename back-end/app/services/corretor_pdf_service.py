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
# Assinatura e rodapé fixos no rodapé da página
Y_DECL        = 258
Y_SIG_LINE    = 268
Y_FOOTER      = 290

COL_WIDTHS  = [44, 18, 26, 26, 24, 22, 20]   # total = 180mm
COL_HEADERS = ["Contrato (endereço)", "Data", "V. Negócio", "VGV", "V. Total 61", "VGC", "Papel"]

PAPEL_ABREV = {"VENDA + CAPTAÇÃO": "V + C", "VENDA": "Venda", "CAPTAÇÃO": "Capt."}


def _trunc(s: str, n: int) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[: n - 3] + "..."


def _lat(s) -> str:
    """Garante compatibilidade com a fonte latin-1 do fpdf (troca chars fora do range)."""
    return str(s if s is not None else "").encode("latin-1", "replace").decode("latin-1")


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

    nome_title  = _lat(detalhe["corretor"].title())
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
    qtd_vis = detalhe.get("qtd_visitas", 0)
    pdf.cell(
        0, 4,
        _lat(f"Período: {start_fmt} a {end_fmt}   |   {len(negs)} negociação(ões)"
             f"   |   Visitas: {qtd_vis}"),
        ln=False,
    )

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
        contrato_txt = neg.get("contrato") or neg.get("empreendimento") or neg.get("id_contrato", "")
        papel_txt = PAPEL_ABREV.get(neg.get("papel", ""), neg.get("papel", ""))
        row_data = [
            _trunc(contrato_txt, 30),
            _fmt_date(neg["data_contrato"]),
            _fmt_br(neg["valor_negocio"]),
            _fmt_br(neg.get("parte_valor_negocio", 0.0)),   # VGV
            _fmt_br(neg["valor_total_61"]),
            _fmt_br(neg.get("parte_valor_total_61", 0.0)),  # VGC
            papel_txt,
        ]
        pdf.set_xy(15, y_row)
        pdf.set_fill_color(*LIGHT_GRAY)
        pdf.set_text_color(*DARK)
        for w, v in zip(COL_WIDTHS, row_data):
            pdf.cell(w, ROW_H, _lat(v), border=1, fill=fill, align="C")
        y_row += ROW_H
        fill = not fill

    # Nota de truncamento (se houver)
    if truncado > 0:
        pdf.set_xy(15, y_row + 1)
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 4, f"* {truncado} contrato(s) não exibido(s) por limite de espaço.", ln=False)

    # ── Bloco de resumo (logo após a tabela) ──────────────────
    y_sum = y_row + (6 if truncado == 0 else 8)
    pdf.set_xy(15, y_sum)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 5, "Resumo do Período", ln=False)

    totais = [
        ("Valor Negócio (cheio)",  detalhe.get("total_vn_cheio", detalhe.get("total_vgv", 0.0))),
        ("VGV (parte)",            detalhe.get("total_parte_vn", 0.0)),
        ("Valor Total 61 (cheio)", detalhe.get("total_v61_cheio", 0.0)),
        ("VGC (parte)",            detalhe.get("total_parte_v61", detalhe.get("total_vgc_bruto", 0.0))),
    ]
    lw, vw = 120, 60
    y_res = y_sum + 6
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

    # ── Observação (posição fixa no rodapé) ───────────────────
    pdf.set_xy(15, Y_DECL - 4)
    pdf.set_font("Arial", "I", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(
        180, 4,
        "Observação: os dados apresentados são para fins de ranking e premiação e "
        "NÃO representam os valores efetivamente recebidos.",
        align="C",
    )

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

def _pdf_to_bytes(pdf) -> bytes:
    """Extrai o conteúdo do PDF como bytes, compatível com fpdf2 2.x e pyfpdf 1.x."""
    try:
        out = pdf.output()  # fpdf2 2.x → bytearray
        if isinstance(out, str):
            return out.encode("latin-1")
        return bytes(out)
    except Exception:
        # pyfpdf 1.x: output() sem dest tenta print(); usar dest='S' para string
        out = pdf.output(dest="S")  # type: ignore[call-arg]
        return out.encode("latin-1") if isinstance(out, str) else bytes(out)


def gerar_pdf_corretor(detalhe: Dict[str, Any]) -> BytesIO:
    """PDF de um único corretor (usado pelo modal individual)."""
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    _render_page(pdf, detalhe)

    buf = BytesIO(_pdf_to_bytes(pdf))
    buf.seek(0)
    return buf


def _render_rank_block(pdf, x: float, y: float, titulo: str, linhas: List[Dict[str, Any]], nome_key: str) -> None:
    W_POS, W_NOME, W_VAL = 10, 48, 30   # 88mm
    pdf.set_xy(x, y)
    pdf.set_font("Arial", "B", 8.5)
    pdf.set_text_color(*PINK)
    pdf.cell(W_POS + W_NOME + W_VAL, 5, _lat(titulo), ln=False)

    yy = y + 6
    pdf.set_xy(x, yy)
    pdf.set_fill_color(*PINK)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Arial", "B", 7)
    pdf.cell(W_POS, 5, "#", border=1, fill=True, align="C")
    pdf.cell(W_NOME, 5, "Nome" if nome_key == "corretor" else "Equipe", border=1, fill=True, align="L")
    pdf.cell(W_VAL, 5, "Total", border=1, fill=True, align="C")
    yy += 5

    top = (linhas or [])[:10]
    fill = False
    pdf.set_font("Arial", "", 7)
    for i, l in enumerate(top, 1):
        pdf.set_xy(x, yy)
        pdf.set_fill_color(*LIGHT_GRAY)
        pdf.set_text_color(*DARK)
        nome_val = l.get(nome_key) or l.get("corretor") or l.get("equipe") or ""
        pdf.cell(W_POS, 5, str(i), border=1, fill=fill, align="C")
        pdf.cell(W_NOME, 5, _lat(_trunc(str(nome_val).title(), 30)), border=1, fill=fill, align="L")
        pdf.cell(W_VAL, 5, _lat(_fmt_br(l.get("total", 0.0))), border=1, fill=fill, align="R")
        yy += 5
        fill = not fill
    if not top:
        pdf.set_xy(x, yy)
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(*GRAY)
        pdf.cell(W_POS + W_NOME + W_VAL, 5, "Sem dados.", border=1, align="C")


def _render_ranking_page(pdf, rankings: Dict[str, Any]) -> None:
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=15, y=Y_LOGO, h=11)
    pdf.set_xy(15, Y_TITLE)
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(*PINK)
    pdf.cell(0, 6, "Ranking do Período (Top 10)", ln=False)
    pdf.set_draw_color(*PINK)
    pdf.set_line_width(0.5)
    pdf.line(15, Y_DIVIDER, 195, Y_DIVIDER)

    x_esq, x_dir = 15, 107
    y_top, y_bot = 50, 150
    _render_rank_block(pdf, x_esq, y_top, "VGV - Corretores", rankings.get("vgv_corretor"), "corretor")
    _render_rank_block(pdf, x_dir, y_top, "VGC - Corretores", rankings.get("vgc_corretor"), "corretor")
    _render_rank_block(pdf, x_esq, y_bot, "VGV - Equipes", rankings.get("vgv_equipe"), "equipe")
    _render_rank_block(pdf, x_dir, y_bot, "VGC - Equipes", rankings.get("vgc_equipe"), "equipe")

    pdf.set_xy(15, Y_DECL)
    pdf.set_font("Arial", "I", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(
        180, 4,
        "Observação: os dados apresentados são para fins de ranking e premiação e "
        "NÃO representam os valores efetivamente recebidos.",
        align="C",
    )


def gerar_pdf_todos(detalhes: List[Dict[str, Any]], rankings: Dict[str, Any] = None) -> BytesIO:
    """PDF com 1 página por corretor + (opcional) página final de ranking Top 10."""
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)

    for detalhe in detalhes:
        pdf.add_page()
        _render_page(pdf, detalhe)

    if rankings:
        pdf.add_page()
        _render_ranking_page(pdf, rankings)

    buf = BytesIO(_pdf_to_bytes(pdf))
    buf.seek(0)
    return buf
