import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from app import SessionLocal
from sqlalchemy.orm import sessionmaker
from app import engine, cache
from typing import Optional

from flask import Response, jsonify, current_app
from fpdf import FPDF, HTMLMixin

# Pillow opcional p/ medir imagem
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Session = sessionmaker(bind=engine)
db = SessionLocal()
from app.models.relatorio import PerformeImoveis

# -------- utils --------
def num_or_zero(x):
    try:
        v = float(x)
        if not np.isfinite(v):
            return 0.0
        return v
    except Exception:
        return 0.0

def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

class PDF(FPDF, HTMLMixin):
    def __init__(self, orientation='P', unit='mm', format='A4', logo_file=None):
        super().__init__(orientation, unit, format)
        self.logo_file = logo_file
        self.set_left_margin(15)
        self.set_right_margin(15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Fundo cinza suave
        self.set_fill_color(242, 242, 242)  # #f2f2f2
        self.rect(0, 0, self.w, self.h, 'F')

        # Logo
        if self.logo_file and os.path.exists(self.logo_file):
            self.image(self.logo_file, x=15, y=8, h=12)

        # Título
        self.set_font('Arial', 'B', 15)
        self.set_text_color(225, 0, 91)  # #e1005b
        self.cell(0, 10, 'Relatório de Desempenho de Imóvel', 0, 1, 'C')
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
        self.set_text_color(0, 0, 0)

    def chapter_title(self, title):
        self.ln(2)
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 220, 220)  # cinza p/ barra do título
        self.set_text_color(225, 0, 91)     # #e1005b
        self.cell(0, 9, title, 0, 1, 'L', 1)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, body)
        self.ln(1)

def add_image_auto(pdf: PDF, img_path: str, max_w: float = 180, max_h: float = 100, center: bool = True):
    if not (img_path and os.path.exists(img_path)):
        return
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    max_w = min(max_w, usable_w)

    if PIL_AVAILABLE:
        try:
            with PILImage.open(img_path) as im:
                iw, ih = im.size
            aspect = ih / iw if iw else 0.5
        except Exception:
            aspect = 0.5
    else:
        aspect = 0.5

    target_w = max_w
    target_h = target_w * aspect
    if target_h > max_h:
        target_h = max_h
        target_w = target_h / aspect if aspect else max_w

    if pdf.get_y() + target_h > pdf.page_break_trigger:
        pdf.add_page()

    x = pdf.l_margin
    if center:
        x = pdf.l_margin + (usable_w - target_w) / 2.0

    pdf.image(img_path, x=x, y=pdf.get_y(), w=target_w, h=target_h)
    pdf.ln(target_h + 6)

def gerar_pdf_relatorio(rowdict: dict) -> bytes:
    # Paleta para gráficos
    cor_principal = "#e1005b"
    cores_views = ["#e1005b", "#f59ab5"]
    cores_leads = ["#e1005b", "#ff7f50", "#a64ca6"]
    cores_pizza = cores_leads

    # Extrai dados
    views_values = [
        num_or_zero(rowdict.get("Views DF", 0)),
        num_or_zero(rowdict.get("Views OLX/ZAP", 0)),
    ]
    views_labels = ["Views DF", "Views OLX/ZAP"]

    # Define as listas iniciais de leads
    leads_values_inicial = [
        num_or_zero(rowdict.get("Leads DF", 0)),
        num_or_zero(rowdict.get("Leads OLX/ZAP", 0)),
        num_or_zero(rowdict.get("Leads C2S - Imoview", 0)),
    ]
    leads_labels_inicial = ["Leads DF", "Leads OLX/ZAP", "Leads C2S - Imoview"]

    # Agrupa, filtra os pares com valor 0, e depois "descompacta" em novas listas
    pares_filtrados = [
        (valor, label)
        for valor, label in zip(leads_values_inicial, leads_labels_inicial)
        if valor != 0
    ]

    # Trata o caso de a lista filtrada ficar vazia
    if pares_filtrados:
        # A função zip retorna tuplas, então convertemos de volta para listas
        leads_values, leads_labels = map(list, zip(*pares_filtrados))
    else:
        leads_values, leads_labels = [], []


    # Gera figuras temporárias
    views_chart_path = "views_chart.jpg"
    leads_chart_path = "leads_chart.jpg"
    pie_chart_path = None

    try:
        # Views
        plt.figure(figsize=(8, 4))
        plt.bar(views_labels, views_values, color=cores_views)
        plt.ylabel("Quantidade de Views")
        plt.title("Comparativo de Visualizações por Portal")
        for i, v in enumerate(views_values):
            plt.text(i, v + 0.5, str(int(v)), ha="center", fontweight="bold")
        plt.tight_layout()
        plt.savefig(views_chart_path, format="jpg", dpi=150)
        plt.close()

        # Leads
        plt.figure(figsize=(8, 4))
        plt.bar(leads_labels, leads_values, color=cores_leads)
        plt.ylabel("Quantidade de Leads")
        plt.title("Comparativo de Leads por Fonte")
        for i, v in enumerate(leads_values):
            plt.text(i, v + 0.5, str(int(v)), ha="center", fontweight="bold")
        plt.tight_layout()
        plt.savefig(leads_chart_path, format="jpg", dpi=150)
        plt.close()

        # Pizza (se houver dados)
        if sum(leads_values) > 0:
            pie_chart_path = "pie_chart.jpg"
            plt.figure(figsize=(7, 7))
            plt.pie(leads_values, labels=leads_labels, autopct="%1.1f%%", startangle=90, colors=cores_pizza)
            plt.title("Distribuição de Leads por Fonte")
            plt.axis("equal")
            plt.tight_layout()
            plt.savefig(pie_chart_path, format="jpg", dpi=150)
            plt.close()

        # Montagem do PDF
        logo_file = current_app.config.get("LOGO_FILE", "../utils/asserts/img/Logo 61 Vazado (1).png")
        pdf = PDF(logo_file=logo_file)
        pdf.add_page()

        codigo = rowdict.get("Código do Imóvel", "")
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, f"Detalhamento do Imóvel {codigo}", 0, 1, "C")
        pdf.ln(2)

        # Informações
        pdf.chapter_title("Informações do Imóvel")
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(50, 50, 50)

        # escreve pares 'Coluna: valor' (excluindo as que viram gráfico)
        excluir = {"Views DF", "Views OLX/ZAP", "Leads DF", "Leads OLX/ZAP", "Leads C2S"}
        for col, value in rowdict.items():
            if col in excluir:
                continue
            if pdf.get_y() + 7 > pdf.page_break_trigger:
                pdf.add_page()
                pdf.set_font("Arial", "", 10)
                pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 7, f"{col}: {value}", 0, "L")

        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # Seção Views
        pdf.chapter_title("Análise de Visualizações (Views)")
        add_image_auto(pdf, views_chart_path, max_w=180, max_h=90, center=True)
        pdf.chapter_body("Comparação de visualizações nos portais disponíveis.")

        # Seção Leads
        pdf.chapter_title("Análise de Contatos (Leads)")
        add_image_auto(pdf, leads_chart_path, max_w=180, max_h=90, center=True)
        pdf.chapter_body("Leads gerados por fonte, indicando canais com melhor desempenho.")

        # Pizza
        if pie_chart_path and os.path.exists(pie_chart_path):
            pdf.chapter_title("Distribuição Percentual de Leads")
            add_image_auto(pdf, pie_chart_path, max_w=160, max_h=100, center=True)
            pdf.chapter_body("Proporção relativa de cada fonte de lead.")

        out = pdf.output(dest="S")
        if isinstance(out, str):
            out = out.encode("latin-1", "ignore")
        return out

    finally:
        safe_remove(views_chart_path)
        safe_remove(leads_chart_path)
        safe_remove(pie_chart_path)

# -------- orchestration --------
def get_imovel_by_codigo(codigo: str) -> Optional[dict]:
    reg = (
        db.query(PerformeImoveis)
        .filter(PerformeImoveis.codigo_imovel == codigo)
        .order_by(PerformeImoveis.id.desc())
        .first()
    )
    return reg.to_rowdict() if reg else None

def gerar_relatorio_imovel(codigo: str):
    if not codigo:
        return jsonify({"error": "Parâmetro 'codigo' é obrigatório"}), 400

    rowdict = get_imovel_by_codigo(codigo)
    if not rowdict:
        return jsonify({"error": f"Imóvel com código '{codigo}' não encontrado."}), 404

    pdf_bytes = gerar_pdf_relatorio(rowdict)
    filename = f"relatorio_imovel_{codigo}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
