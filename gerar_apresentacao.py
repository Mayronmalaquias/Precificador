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

# ── Cores 61 Imóveis ──────────────────────────────────────────────────────────
PINK      = HexColor("#C8185A")
PINK_LIGHT= HexColor("#F5D0E0")
DARK      = HexColor("#1A1A1A")
GRAY      = HexColor("#555555")
GRAY_LIGHT= HexColor("#F4F4F4")
WHITE     = colors.white
BORDER    = HexColor("#E0E0E0")

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
LOGO   = os.path.join(BASE, "front-end", "src", "assets", "img", "LOGO 61 PNG (3).png")
OUTPUT = os.path.join(BASE, "Apresentacao_Renata_61Imoveis.pdf")

W, H = A4  # 595.28 x 841.89 pts

# ── Header / Footer em cada página ────────────────────────────────────────────
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
        # Título no header
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(62, H - 22, "61 IMÓVEIS")
        c.setFont("Helvetica", 9)
        c.drawString(62, H - 36, "Apresentação — Assistente Virtual Renata")
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
        c.drawString(18, 10, "Documento interno — 61 Imóveis | Tecnologia & Inovação")
        c.drawRightString(W - 18, 10, f"Página {doc.page}")
        c.restoreState()

    def __call__(self, c, doc):
        self.header(c, doc)
        self.footer(c, doc)


# ── Estilos ───────────────────────────────────────────────────────────────────
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


# ── Utilitários ───────────────────────────────────────────────────────────────
def section_header(text, S):
    """Bloco rosa com título de seção."""
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
    """Tabela com ícone ✓/✗ na primeira coluna."""
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
    """Tabela de fluxo em linha única."""
    cells = []
    for i, s in enumerate(steps):
        cells.append(Paragraph(s, ParagraphStyle("fc",
            fontName="Helvetica", fontSize=8.5, textColor=DARK,
            alignment=TA_CENTER, leading=12)))
        if i < len(steps) - 1:
            cells.append(Paragraph("→", ParagraphStyle("arrow",
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


# ── Conteúdo ──────────────────────────────────────────────────────────────────
def build_story(S):
    story = []
    sp = lambda n=1: Spacer(1, n * 0.3 * cm)

    # ── Capa ──────────────────────────────────────────────────────────────────
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
            "Documento de apresentação para gerentes — Como funciona, o que ela sabe "
            "e as novidades visuais do site.",
            S["subtitle"]),
        sp(0.5),
        info_box(
            "<b>61 Imóveis · Brasília/DF</b> &nbsp;|&nbsp; Tecnologia &amp; Inovação "
            "&nbsp;|&nbsp; Maio de 2026",
            S),
        sp(3),
    ]

    # ── 1. O que é a Renata ───────────────────────────────────────────────────
    story += [section_header("1. O que é a Renata?", S), sp()]
    story += [
        Paragraph(
            "A <b>Renata</b> é uma assistente virtual inteligente desenvolvida "
            "especificamente para a <b>61 Imóveis</b>. Ela funciona como uma atendente "
            "disponível <b>24h por dia, 7 dias por semana</b>, diretamente no site público "
            "da imobiliária.", S["body"]),
        sp(0.5),
        Paragraph(
            "Ela foi desenvolvida pela <b>Inteligência 61 Imóveis</b> utilizando tecnologia "
            "de linguagem de última geração — o mesmo tipo de IA por trás de ferramentas "
            "como o ChatGPT, porém 100% configurada e personalizada para a 61 Imóveis.", S["body"]),
        sp(0.5),
        Paragraph(
            "A Renata <b>não é uma IA genérica</b>: ela recebe um contexto específico da "
            "61 Imóveis e só responde sobre temas relacionados ao mercado imobiliário de "
            "Brasília/DF.", S["body"]),
        sp(),
    ]

    # ── 2. Como funciona ──────────────────────────────────────────────────────
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
            "A Renata <b>mantém o histórico da conversa</b> durante a sessão do usuário — "
            "se o cliente disse &ldquo;quero 2 quartos&rdquo; no início, ela lembra nas perguntas "
            "seguintes. O histórico é apagado ao fechar o navegador.", S["body"]),
        sp(),
    ]

    # ── 3. O que ela tem acesso ───────────────────────────────────────────────
    story += [section_header("3. O que a Renata tem acesso?", S), sp()]
    story += [
        Paragraph(
            "A Renata acessa <b>diretamente o banco de dados da plataforma</b> em tempo real:",
            S["body"]),
        sp(0.3),
        two_col_table([
            ["Dado", "Descrição"],
            ["Imóveis à venda",    "Apartamentos, casas, comerciais — últimos 12 meses"],
            ["Imóveis para aluguel", "Incluindo temporada"],
            ["Preços de mercado",  "Valor/m² por bairro e tipo de imóvel"],
            ["Links dos anúncios", "Link direto para o portal (ex: DFImóveis)"],
            ["Dados do imóvel",    "Quartos, vagas, área útil, bairro, quadra, anunciante"],
            ["Análises de mercado","Agrupamentos estatísticos para precificação"],
        ], S),
        sp(0.5),
        Paragraph(
            "<b>Bairros cobertos:</b> Asa Sul, Asa Norte, Noroeste, Sudoeste, Lago Norte, "
            "Lago Sul, Águas Claras — e demais regiões cadastradas no banco.", S["body"]),
        Paragraph(
            "<b>Os dados têm no máximo 365 dias</b> — a Renata nunca exibe imóveis desatualizados.",
            S["body"]),
        sp(),
    ]

    # ── 4. Capacidades ────────────────────────────────────────────────────────
    story += [section_header("4. O que a Renata pode responder?", S), sp()]
    story += [Paragraph("A Renata possui <b>3 capacidades principais</b>:", S["body"]), sp(0.3)]

    caps = [
        ("4.1 Buscar Imóveis Disponíveis",
         "Quando o cliente quer ver opções para comprar ou alugar.",
         [
             "Tem apartamento de 2 quartos no Sudoeste para alugar?",
             "Quero comprar uma casa no Lago Norte até R$ 800.000",
             "Mostre imóveis para temporada na Asa Sul",
         ],
         "Retorna até <b>5 imóveis</b> com tipo, bairro, quartos, vagas, área, preço "
         "e <b>link direto para o anúncio no portal</b>."),
        ("4.2 Precificar um Imóvel",
         "Quando o cliente (ou proprietário) quer saber quanto vale um imóvel.",
         [
             "Quanto vale um apartamento de 3 quartos no Noroeste?",
             "Qual o valor de mercado de uma casa de 200m² no Lago Sul?",
             "Quero alugar meu apto na Asa Norte — qual o preço justo?",
         ],
         "Retorna <b>valor médio/m²</b>, estimativa total, tamanho da amostra e "
         "indicadores de confiança baseados em dados reais."),
        ("4.3 Dicas para Anunciar",
         "Quando o proprietário quer saber como anunciar melhor o imóvel.",
         [
             "Como devo anunciar meu apartamento para vender mais rápido?",
             "Qual o perfil dos imóveis mais procurados no Sudoeste?",
         ],
         "Retorna dados reais: preço médio, quartos mais procurados, % com vaga, "
         "recomendações específicas por bairro."),
    ]

    for title_cap, when, examples, returns in caps:
        tbl = Table([
            [Paragraph(f"<b>{title_cap}</b>", S["bold_body"])],
            [Paragraph(f"<b>Quando usar:</b> {when}", S["body"])],
            [Paragraph("<b>Exemplos de perguntas:</b>", S["body"])],
        ] + [
            [Paragraph(f"&nbsp;&nbsp;• {ex}", S["bullet"])] for ex in examples
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

    # ── 5. Limitações ─────────────────────────────────────────────────────────
    story += [section_header("5. O que a Renata NÃO faz", S), sp()]
    story += [
        Paragraph(
            "É importante alinhar com a equipe as limitações da ferramenta:", S["body"]),
        sp(0.3),
        two_col_table([
            ["Limitação", "Explicação"],
            ["Não agenda visitas",         "Não tem acesso à agenda dos corretores"],
            ["Não processa pagamentos",    "Sem integração com sistemas financeiros"],
            ["Não cria/edita anúncios",    "Acesso somente leitura ao banco de dados"],
            ["Não responde outros temas",  "Fora do imobiliário, redireciona educadamente"],
            ["Sem histórico entre sessões","Ao fechar o navegador, o histórico é perdido"],
            ["Sem consultoria jurídica",   "Está fora do escopo definido"],
            ["Sem acesso ao CRM",          "Não tem vínculo com dados de clientes cadastrados"],
        ], S),
        sp(),
    ]

    # ── 6. Segurança ──────────────────────────────────────────────────────────
    story += [section_header("6. Segurança e Privacidade", S), sp()]
    items = [
        "A Renata <b>não coleta dados pessoais</b> dos clientes durante o chat",
        "As mensagens são processadas em tempo real e não são armazenadas permanentemente",
        "O histórico de conversa existe apenas na <b>memória temporária da sessão</b>",
        "O banco consultado contém apenas <b>dados de imóveis públicos</b> (já anunciados nos portais)",
        "A chave de acesso ao modelo de IA é gerenciada com segurança no servidor",
    ]
    for it in items:
        story.append(Paragraph(f"✔ &nbsp;{it}", S["bullet"]))
    story.append(sp())

    # ── 7. Mudanças visuais ───────────────────────────────────────────────────
    story += [section_header("7. Mudanças Visuais do Site", S), sp()]
    story += [
        Paragraph(
            "Junto com a Renata foram realizadas atualizações visuais modernas no widget de chat:",
            S["body"]),
        sp(0.3),
    ]

    visual_items = [
        ("Botão Flutuante",
         "Canto inferior direito da tela · 64×64px com gradiente roxo · "
         "efeito de pulso animado · avatar da Renata quando fechado, ícone X quando aberto."),
        ("Janela do Chat",
         "380×560px no desktop e tela cheia no mobile · bordas arredondadas com sombra suave · "
         "animação de abertura com efeito de mola."),
        ("Header",
         "Gradiente roxo com avatar da Renata em moldura circular · indicador verde de status online."),
        ("Balões de Mensagem",
         "Mensagens da Renata: fundo branco, borda esquerda roxa. "
         "Mensagens do cliente: gradiente roxo, texto branco."),
        ("Indicador de Digitação",
         "3 pontos roxos animados enquanto a Renata processa a resposta."),
        ("Responsividade Mobile",
         "Abaixo de 490px o chat ocupa tela inteira, botão de fechar aparece no header."),
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
            ["Principal (roxo médio)",  "#724ae8"],
            ["Escuro (roxo escuro)",    "#5a35c8"],
            ["Claro (roxo claro)",      "#9b6ef5"],
            ["Fundo chat",              "#f5f3ff (roxo muito claro)"],
            ["Texto",                   "#2d2d2d (cinza escuro)"],
            ["Online",                  "#4ade80 (verde)"],
        ], S),
        sp(),
    ]

    # ── 8. Resumo Executivo ───────────────────────────────────────────────────
    story += [section_header("8. Resumo Executivo", S), sp()]
    story += [
        two_col_table([
            ["Item", "Detalhe"],
            ["Tecnologia",       "Inteligência 61 Imóveis — IA de última geração"],
            ["Disponibilidade",  "24/7 no site público"],
            ["Dados em tempo real", "Sim — consulta o banco da plataforma"],
            ["Idioma",           "Português brasileiro"],
            ["Capacidades",      "Busca de imóveis, precificação e dicas de anúncio"],
            ["Limitações",       "Somente imobiliário, somente leitura, sem agenda"],
            ["Privacidade",      "Sem coleta de dados pessoais"],
            ["Visual",           "Widget moderno, animado, responsivo, identidade 61"],
        ], S),
        sp(2),
        info_box(
            "A Renata representa o primeiro passo da <b>61 Imóveis rumo à automação "
            "inteligente do atendimento</b>, oferecendo ao cliente uma experiência "
            "personalizada e baseada em dados reais de mercado — disponível sempre, "
            "sem custo de horas extras.",
            S),
    ]

    return story


# ── Geração do PDF ────────────────────────────────────────────────────────────
def main():
    doc_canvas = DocCanvas(LOGO)

    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm,
        title="Apresentação Renata — 61 Imóveis",
        author="61 Imóveis",
    )

    S = make_styles()
    story = build_story(S)

    doc.build(story,
              onFirstPage=doc_canvas,
              onLaterPages=doc_canvas)

    print(f"PDF gerado: {OUTPUT}")


if __name__ == "__main__":
    main()
