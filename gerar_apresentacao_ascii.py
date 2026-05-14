# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import PageTemplate, Frame
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import os

# \u2500\u2500 Cores 61 Im\u00f3veis \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
PINK      = HexColor("#C8185A")
PINK_LIGHT= HexColor("#F5D0E0")
DARK      = HexColor("#1A1A1A")
GRAY      = HexColor("#555555")
GRAY_LIGHT= HexColor("#F4F4F4")
WHITE     = colors.white
BORDER    = HexColor("#E0E0E0")

# \u2500\u2500 Caminhos \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
BASE   = os.path.dirname(os.path.abspath(__file__))
LOGO   = os.path.join(BASE, "front-end", "src", "assets", "img", "LOGO 61 PNG (3).png")
OUTPUT = os.path.join(BASE, "Apresentacao_Renata_61Imoveis.pdf")

W, H = A4  # 595.28 x 841.89 pts

# \u2500\u2500 Header / Footer em cada p\u00e1gina \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
class DocCanvas:
    def __init__(self, logo_path):
        self.logo = logo_path

    def header(self, c, doc):
        c.saveState()
        # Barra superior rosa
        c.setFillColor(PINK)
        c.rect(0, H - 52, W, 52, fill=1, stroke=0)
        # Logo
        if os.path.exists(self.logo):
            c.drawImage(self.logo, 10, H - 50, width=44, height=44,
                        mask="auto", preserveAspectRatio=True)
        # T\u00edtulo no header
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(62, H - 22, "61 IM\u00d3VEIS")
        c.setFont("Helvetica", 9)
        c.drawString(62, H - 36, "Apresenta\u00e7\u00e3o \u2014 Assistente Virtual Renata")
        # Data direita
        c.setFont("Helvetica", 8)
        c.drawRightString(W - 18, H - 30, "Maio de 2026")
        c.restoreState()

    def footer(self, c, doc):
        c.saveState()
        c.setFillColor(GRAY_LIGHT)
        c.rect(0, 0, W, 28, fill=1, stroke=0)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        c.drawString(18, 10, "Documento interno \u2014 61 Im\u00f3veis | Tecnologia & Inova\u00e7\u00e3o")
        c.drawRightString(W - 18, 10, f"P\u00e1gina {doc.page}")
        c.restoreState()

    def __call__(self, c, doc):
        self.header(c, doc)
        self.footer(c, doc)


# \u2500\u2500 Estilos \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def make_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle("title",
        fontName="Helvetica-Bold", fontSize=22, textColor=PINK,
        spaceAfter=4, alignment=TA_LEFT)

    subtitle = ParagraphStyle("subtitle",
        fontName="Helvetica", fontSize=11, textColor=GRAY,
        spaceAfter=16, alignment=TA_LEFT)

    section = ParagraphStyle("section",
        fontName="Helvetica-Bold", fontSize=13, textColor=WHITE,
        spaceBefore=14, spaceAfter=6, leftIndent=0)

    body = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9.5, textColor=DARK,
        leading=15, spaceAfter=4, leftIndent=0)

    bullet = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=9.5, textColor=DARK,
        leading=15, spaceAfter=3, leftIndent=14, firstLineIndent=-10)

    bold_body = ParagraphStyle("bold_body",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK,
        leading=15, spaceAfter=3)

    caption = ParagraphStyle("caption",
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=GRAY,
        spaceAfter=4)

    note = ParagraphStyle("note",
        fontName="Helvetica", fontSize=8.5, textColor=GRAY,
        leading=13, spaceAfter=4)

    return dict(title=title, subtitle=subtitle, section=section,
                body=body, bullet=bullet, bold_body=bold_body,
                caption=caption, note=note)


# \u2500\u2500 Utilit\u00e1rios \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def section_header(text, S):
    """Bloco rosa com t\u00edtulo de se\u00e7\u00e3o."""
    tbl = Table([[Paragraph(text, S["section"])]], colWidths=[W - 4*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PINK),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return tbl

def two_col_table(rows, S):
    """Tabela de 2 colunas com zebra."""
    data = [[Paragraph(f"<b>{h}</b>", S["bold_body"]) for h in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(str(c), S["body"]) for c in r])

    col1 = (W - 4*cm) * 0.38
    col2 = (W - 4*cm) * 0.62
    tbl = Table(data, colWidths=[col1, col2], repeatRows=1)

    style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  PINK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9.5),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl

def check_table(rows, S, col_widths=None):
    """Tabela com \u00edcone \u2713/\u2717 na primeira coluna."""
    data = [[Paragraph(f"<b>{h}</b>", S["bold_body"]) for h in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(str(c), S["body"]) for c in r])

    if col_widths is None:
        total = W - 4*cm
        col_widths = [total * 0.12, total * 0.30, total * 0.58]

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  PINK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl

def info_box(text, S, bg=None):
    """Caixa de destaque com fundo."""
    bg = bg or PINK_LIGHT
    tbl = Table([[Paragraph(text, S["body"])]], colWidths=[W - 4*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("BOX",           (0, 0), (-1, -1), 1, PINK),
    ]))
    return tbl

def flow_table(steps, S):
    """Tabela de fluxo em linha \u00fanica."""
    cells = []
    for i, s in enumerate(steps):
        cells.append(Paragraph(s, ParagraphStyle("fc",
            fontName="Helvetica", fontSize=8.5, textColor=DARK,
            alignment=TA_CENTER, leading=12)))
        if i < len(steps) - 1:
            cells.append(Paragraph("\u2192", ParagraphStyle("arrow",
                fontName="Helvetica-Bold", fontSize=14, textColor=PINK,
                alignment=TA_CENTER)))

    n = len(steps)
    total = W - 4*cm
    arrow_w = 18
    step_w  = (total - arrow_w * (n - 1)) / n
    col_w   = []
    for i in range(n):
        col_w.append(step_w)
        if i < n - 1:
            col_w.append(arrow_w)

    tbl = Table([cells], colWidths=col_w)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0),   PINK_LIGHT),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [GRAY_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    return tbl


# \u2500\u2500 Conte\u00fado \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def build_story(S):
    story = []
    sp = lambda n=1: Spacer(1, n * 0.3 * cm)

    # \u2500\u2500 Capa \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [sp(3)]
    if os.path.exists(LOGO):
        img = Image(LOGO, width=5.5*cm, height=5.5*cm)
        img.hAlign = "LEFT"
        story.append(img)
    story += [sp(1),
        Paragraph("Assistente Virtual", S["subtitle"]),
        Paragraph("Renata", S["title"]),
        Spacer(1, 0.4*cm),
        HRFlowable(width="100%", thickness=2, color=PINK, spaceAfter=10),
        Paragraph(
            "Documento de apresenta\u00e7\u00e3o para gerentes \u2014 Como funciona, o que ela sabe "
            "e as novidades visuais do site.",
            S["subtitle"]),
        sp(0.5),
        info_box(
            "<b>61 Im\u00f3veis \u00b7 Bras\u00edlia/DF</b> &nbsp;|&nbsp; Tecnologia &amp; Inova\u00e7\u00e3o "
            "&nbsp;|&nbsp; Maio de 2026",
            S),
        sp(3),
    ]

    # \u2500\u2500 1. O que \u00e9 a Renata \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("1. O que \u00e9 a Renata?", S), sp()]
    story += [
        Paragraph(
            "A <b>Renata</b> \u00e9 uma assistente virtual inteligente desenvolvida "
            "especificamente para a <b>61 Im\u00f3veis</b>. Ela funciona como uma atendente "
            "dispon\u00edvel <b>24h por dia, 7 dias por semana</b>, diretamente no site p\u00fablico "
            "da imobili\u00e1ria.", S["body"]),
        sp(0.5),
        Paragraph(
            "Ela foi desenvolvida pela <b>Intelig\u00eancia 61 Im\u00f3veis</b> utilizando tecnologia "
            "de linguagem de \u00faltima gera\u00e7\u00e3o \u2014 o mesmo tipo de IA por tr\u00e1s de ferramentas "
            "como o ChatGPT, por\u00e9m 100% configurada e personalizada para a 61 Im\u00f3veis.", S["body"]),
        sp(0.5),
        Paragraph(
            "A Renata <b>n\u00e3o \u00e9 uma IA gen\u00e9rica</b>: ela recebe um contexto espec\u00edfico da "
            "61 Im\u00f3veis e s\u00f3 responde sobre temas relacionados ao mercado imobili\u00e1rio de "
            "Bras\u00edlia/DF.", S["body"]),
        sp(),
    ]

    # \u2500\u2500 2. Como funciona \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("2. Como ela funciona?", S), sp()]
    steps = [
        "Cliente digita\numa mensagem",
        "Enviado ao\nservidor 61",
        "IA escolhe\na ferramenta",
        "Consulta o\nbanco de dados",
        "IA monta\na resposta",
        "Resposta exibida\nno chat",
    ]
    story += [flow_table(steps, S), sp(0.5),
        Paragraph(
            "A Renata <b>mant\u00e9m o hist\u00f3rico da conversa</b> durante a sess\u00e3o do usu\u00e1rio \u2014 "
            "se o cliente disse &ldquo;quero 2 quartos&rdquo; no in\u00edcio, ela lembra nas perguntas "
            "seguintes. O hist\u00f3rico \u00e9 apagado ao fechar o navegador.", S["body"]),
        sp(),
    ]

    # \u2500\u2500 3. O que ela tem acesso \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("3. O que a Renata tem acesso?", S), sp()]
    story += [
        Paragraph(
            "A Renata acessa <b>diretamente o banco de dados da plataforma</b> em tempo real:",
            S["body"]),
        sp(0.3),
        two_col_table([
            ["Dado", "Descri\u00e7\u00e3o"],
            ["Im\u00f3veis \u00e0 venda",    "Apartamentos, casas, comerciais \u2014 \u00faltimos 12 meses"],
            ["Im\u00f3veis para aluguel", "Incluindo temporada"],
            ["Pre\u00e7os de mercado",  "Valor/m\u00b2 por bairro e tipo de im\u00f3vel"],
            ["Links dos an\u00fancios", "Link direto para o portal (ex: DFIm\u00f3veis)"],
            ["Dados do im\u00f3vel",    "Quartos, vagas, \u00e1rea \u00fatil, bairro, quadra, anunciante"],
            ["An\u00e1lises de mercado","Agrupamentos estat\u00edsticos para precifica\u00e7\u00e3o"],
        ], S),
        sp(0.5),
        Paragraph(
            "<b>Bairros cobertos:</b> Asa Sul, Asa Norte, Noroeste, Sudoeste, Lago Norte, "
            "Lago Sul, \u00c1guas Claras \u2014 e demais regi\u00f5es cadastradas no banco.", S["body"]),
        Paragraph(
            "<b>Os dados t\u00eam no m\u00e1ximo 365 dias</b> \u2014 a Renata nunca exibe im\u00f3veis desatualizados.",
            S["body"]),
        sp(),
    ]

    # \u2500\u2500 4. Capacidades \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("4. O que a Renata pode responder?", S), sp()]
    story += [Paragraph("A Renata possui <b>3 capacidades principais</b>:", S["body"]), sp(0.3)]

    caps = [
        ("4.1 Buscar Im\u00f3veis Dispon\u00edveis",
         "Quando o cliente quer ver op\u00e7\u00f5es para comprar ou alugar.",
         [
             "Tem apartamento de 2 quartos no Sudoeste para alugar?",
             "Quero comprar uma casa no Lago Norte at\u00e9 R$ 800.000",
             "Mostre im\u00f3veis para temporada na Asa Sul",
         ],
         "Retorna at\u00e9 <b>5 im\u00f3veis</b> com tipo, bairro, quartos, vagas, \u00e1rea, pre\u00e7o "
         "e <b>link direto para o an\u00fancio no portal</b>."),
        ("4.2 Precificar um Im\u00f3vel",
         "Quando o cliente (ou propriet\u00e1rio) quer saber quanto vale um im\u00f3vel.",
         [
             "Quanto vale um apartamento de 3 quartos no Noroeste?",
             "Qual o valor de mercado de uma casa de 200m\u00b2 no Lago Sul?",
             "Quero alugar meu apto na Asa Norte \u2014 qual o pre\u00e7o justo?",
         ],
         "Retorna <b>valor m\u00e9dio/m\u00b2</b>, estimativa total, tamanho da amostra e "
         "indicadores de confian\u00e7a baseados em dados reais."),
        ("4.3 Dicas para Anunciar",
         "Quando o propriet\u00e1rio quer saber como anunciar melhor o im\u00f3vel.",
         [
             "Como devo anunciar meu apartamento para vender mais r\u00e1pido?",
             "Qual o perfil dos im\u00f3veis mais procurados no Sudoeste?",
         ],
         "Retorna dados reais: pre\u00e7o m\u00e9dio, quartos mais procurados, % com vaga, "
         "recomenda\u00e7\u00f5es espec\u00edficas por bairro."),
    ]

    for title_cap, when, examples, returns in caps:
        tbl = Table([
            [Paragraph(f"<b>{title_cap}</b>", S["bold_body"])],
            [Paragraph(f"<b>Quando usar:</b> {when}", S["body"])],
            [Paragraph("<b>Exemplos de perguntas:</b>", S["body"])],
        ] + [
            [Paragraph(f"&nbsp;&nbsp;\u2022 {ex}", S["bullet"])] for ex in examples
        ] + [
            [Paragraph(f"<b>O que retorna:</b> {returns}", S["body"])],
        ], colWidths=[W - 4*cm])

        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), PINK_LIGHT),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("BOX",           (0, 0), (-1, -1), 1, PINK),
            ("LINEBELOW",     (0, 0), (-1, 0), 1, PINK),
        ]))
        story += [KeepTogether([tbl]), sp(0.5)]

    story.append(sp(0.5))

    # \u2500\u2500 5. Limita\u00e7\u00f5es \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("5. O que a Renata N\u00c3O faz", S), sp()]
    story += [
        Paragraph(
            "\u00c9 importante alinhar com a equipe as limita\u00e7\u00f5es da ferramenta:", S["body"]),
        sp(0.3),
        two_col_table([
            ["Limita\u00e7\u00e3o", "Explica\u00e7\u00e3o"],
            ["N\u00e3o agenda visitas",         "N\u00e3o tem acesso \u00e0 agenda dos corretores"],
            ["N\u00e3o processa pagamentos",    "Sem integra\u00e7\u00e3o com sistemas financeiros"],
            ["N\u00e3o cria/edita an\u00fancios",    "Acesso somente leitura ao banco de dados"],
            ["N\u00e3o responde outros temas",  "Fora do imobili\u00e1rio, redireciona educadamente"],
            ["Sem hist\u00f3rico entre sess\u00f5es","Ao fechar o navegador, o hist\u00f3rico \u00e9 perdido"],
            ["Sem consultoria jur\u00eddica",   "Est\u00e1 fora do escopo definido"],
            ["Sem acesso ao CRM",          "N\u00e3o tem v\u00ednculo com dados de clientes cadastrados"],
        ], S),
        sp(),
    ]

    # \u2500\u2500 6. Seguran\u00e7a \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("6. Seguran\u00e7a e Privacidade", S), sp()]
    items = [
        "A Renata <b>n\u00e3o coleta dados pessoais</b> dos clientes durante o chat",
        "As mensagens s\u00e3o processadas em tempo real e n\u00e3o s\u00e3o armazenadas permanentemente",
        "O hist\u00f3rico de conversa existe apenas na <b>mem\u00f3ria tempor\u00e1ria da sess\u00e3o</b>",
        "O banco consultado cont\u00e9m apenas <b>dados de im\u00f3veis p\u00fablicos</b> (j\u00e1 anunciados nos portais)",
        "A chave de acesso ao modelo de IA \u00e9 gerenciada com seguran\u00e7a no servidor",
    ]
    for it in items:
        story.append(Paragraph(f"\u2714 &nbsp;{it}", S["bullet"]))
    story.append(sp())

    # \u2500\u2500 7. Mudan\u00e7as visuais \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("7. Mudan\u00e7as Visuais do Site", S), sp()]
    story += [
        Paragraph(
            "Junto com a Renata foram realizadas atualiza\u00e7\u00f5es visuais modernas no widget de chat:",
            S["body"]),
        sp(0.3),
    ]

    visual_items = [
        ("Bot\u00e3o Flutuante",
         "Canto inferior direito da tela \u00b7 64\u00d764px com gradiente roxo \u00b7 "
         "efeito de pulso animado \u00b7 avatar da Renata quando fechado, \u00edcone X quando aberto."),
        ("Janela do Chat",
         "380\u00d7560px no desktop e tela cheia no mobile \u00b7 bordas arredondadas com sombra suave \u00b7 "
         "anima\u00e7\u00e3o de abertura com efeito de mola."),
        ("Header",
         "Gradiente roxo com avatar da Renata em moldura circular \u00b7 indicador verde de status online."),
        ("Bal\u00f5es de Mensagem",
         "Mensagens da Renata: fundo branco, borda esquerda roxa. "
         "Mensagens do cliente: gradiente roxo, texto branco."),
        ("Indicador de Digita\u00e7\u00e3o",
         "3 pontos roxos animados enquanto a Renata processa a resposta."),
        ("Responsividade Mobile",
         "Abaixo de 490px o chat ocupa tela inteira, bot\u00e3o de fechar aparece no header."),
    ]

    for titulo, desc in visual_items:
        row = [
            Paragraph(f"<b>{titulo}</b>", S["bold_body"]),
            Paragraph(desc, S["body"]),
        ]
        tbl = Table([row], colWidths=[(W-4*cm)*0.28, (W-4*cm)*0.72])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0), PINK_LIGHT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tbl)

    story.append(sp(0.5))

    # Tabela de cores
    story += [
        Paragraph("<b>Paleta de cores utilizada:</b>", S["bold_body"]),
        sp(0.2),
        two_col_table([
            ["Elemento", "Cor"],
            ["Principal (roxo m\u00e9dio)",  "#724ae8"],
            ["Escuro (roxo escuro)",    "#5a35c8"],
            ["Claro (roxo claro)",      "#9b6ef5"],
            ["Fundo chat",              "#f5f3ff (roxo muito claro)"],
            ["Texto",                   "#2d2d2d (cinza escuro)"],
            ["Online",                  "#4ade80 (verde)"],
        ], S),
        sp(),
    ]

    # \u2500\u2500 8. Resumo Executivo \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    story += [section_header("8. Resumo Executivo", S), sp()]
    story += [
        two_col_table([
            ["Item", "Detalhe"],
            ["Tecnologia",       "Intelig\u00eancia 61 Im\u00f3veis \u2014 IA de \u00faltima gera\u00e7\u00e3o"],
            ["Disponibilidade",  "24/7 no site p\u00fablico"],
            ["Dados em tempo real", "Sim \u2014 consulta o banco da plataforma"],
            ["Idioma",           "Portugu\u00eas brasileiro"],
            ["Capacidades",      "Busca de im\u00f3veis, precifica\u00e7\u00e3o e dicas de an\u00fancio"],
            ["Limita\u00e7\u00f5es",       "Somente imobili\u00e1rio, somente leitura, sem agenda"],
            ["Privacidade",      "Sem coleta de dados pessoais"],
            ["Visual",           "Widget moderno, animado, responsivo, identidade 61"],
        ], S),
        sp(2),
        info_box(
            "A Renata representa o primeiro passo da <b>61 Im\u00f3veis rumo \u00e0 automa\u00e7\u00e3o "
            "inteligente do atendimento</b>, oferecendo ao cliente uma experi\u00eancia "
            "personalizada e baseada em dados reais de mercado \u2014 dispon\u00edvel sempre, "
            "sem custo de horas extras.",
            S),
    ]

    return story


# \u2500\u2500 Gera\u00e7\u00e3o do PDF \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def main():
    doc_canvas = DocCanvas(LOGO)

    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm,
        title="Apresenta\u00e7\u00e3o Renata \u2014 61 Im\u00f3veis",
        author="61 Im\u00f3veis",
    )

    S = make_styles()
    story = build_story(S)

    doc.build(story,
              onFirstPage=doc_canvas,
              onLaterPages=doc_canvas)

    print(f"PDF gerado: {OUTPUT}")


if __name__ == "__main__":
    main()
