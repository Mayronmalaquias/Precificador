import matplotlib
matplotlib.use('Agg')  # backend sem GUI
import pandas as pd
from flask import Flask, request, Response, jsonify
from fpdf import FPDF, HTMLMixin
import os
import matplotlib.pyplot as plt
import numpy as np

# Tente usar Pillow para medir imagens; se não houver, seguimos com fallback
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# --- Configuração ---
app = Flask(__name__)
CSV_FILE = 'Relatorio_Consolidado.csv'
LOGO_FILE = 'Logo 61 Vazado (1).png'

# --- Util ---
def num_or_zero(x):
    try:
        if pd.isna(x):
            return 0
        if isinstance(x, str):
            x = x.replace(',', '.')
        v = float(x)
        if not np.isfinite(v):
            return 0
        return v
    except Exception:
        return 0

def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# --- Classe PDF Personalizada ---
class PDF(FPDF, HTMLMixin):
    def __init__(self, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
        # Margens e quebra de página automática para texto
        self.set_left_margin(15)
        self.set_right_margin(15)
        self.set_text_color(225, 0, 91) 
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(242, 242, 242)  # #f2f2f2  
        self.rect(0, 0, self.w, self.h, 'F')  # preenche página inteira

        if os.path.exists(LOGO_FILE):
            # logo: altura ~12mm para não “empurrar” demais
            self.image(LOGO_FILE, x=15, y=8, w=0, h=12)
        self.set_font('Arial', 'B', 15)
        self.set_text_color(50, 50, 150)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, 'Relatório de Desempenho de Imóvel', 0, 1, 'C')
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
        self.set_text_color(0, 0, 0)

    def chapter_title(self, title):
        # Garante espaço antes do título
        self.ln(2)
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(247, 196, 216)  # #f7c4d8 (rosa claro)
        self.set_text_color(225, 0, 91)     # #e1005b (magenta forte)
        self.cell(0, 9, title, 0, 1, 'L', 1)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, body)
        self.ln(1)

def add_image_auto(pdf: PDF, img_path: str, max_w: float = 180, max_h: float = 100, center: bool = True):
    """
    Insere imagem respeitando margens, calcula tamanho para caber em max_w x max_h,
    faz quebra de página se necessário e avança o cursor após a imagem.
    """
    if not (img_path and os.path.exists(img_path)):
        return

    # Largura útil da página (entre margens)
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    max_w = min(max_w, usable_w)

    # Descobrir proporção da imagem
    if PIL_AVAILABLE:
        try:
            with PILImage.open(img_path) as im:
                iw, ih = im.size
            aspect = ih / iw if iw else 0.5
        except Exception:
            aspect = 0.5  # fallback 2:1 (ex.: gráficos 8x4)
    else:
        aspect = 0.5

    # Calcula w/h finais mantendo proporção e respeitando limites
    # Primeiro tenta limitar por largura
    target_w = max_w
    target_h = target_w * aspect
    # Se estourar a altura máxima, limita pela altura
    if target_h > max_h:
        target_h = max_h
        target_w = target_h / aspect if aspect else max_w

    # Verifica quebra de página
    current_y = pdf.get_y()
    if current_y + target_h > pdf.page_break_trigger:
        pdf.add_page()

    # X alinhado
    x = pdf.l_margin
    if center:
        x = pdf.l_margin + (usable_w - target_w) / 2.0

    # Desenha imagem e avança cursor
    pdf.image(img_path, x=x, y=pdf.get_y(), w=target_w, h=target_h)
    pdf.ln(target_h + 6)  # espaço abaixo da figura

# --- Endpoint ---
@app.route('/relatorio', methods=['GET'])
def gerar_relatorio():
    codigo_imovel = request.args.get('codigo')
    if not codigo_imovel:
        return jsonify({"error": "Parâmetro 'codigo' é obrigatório"}), 400

    if not os.path.exists(CSV_FILE):
        return jsonify({"error": f"Arquivo de dados '{CSV_FILE}' não encontrado."}), 500

    views_chart_path = None
    leads_chart_path = None
    pie_chart_path = None

    try:
        df = pd.read_csv(CSV_FILE, dtype={'Código do Imóvel': str})
        imovel_data = df.loc[df['Código do Imóvel'] == codigo_imovel]

        if imovel_data.empty:
            return jsonify({"error": f"Imóvel com código '{codigo_imovel}' não encontrado."}), 404

        row_data = imovel_data.iloc[0]

        # --- Gráficos: sanear dados ---
        # Views
        views_labels = ['Views DF', 'Views OLX/ZAP']
        views_values_raw = [row_data.get('Views DF', 0), row_data.get('Views OLX/ZAP', 0)]
        views_values = [num_or_zero(v) for v in views_values_raw]

        plt.figure(figsize=(8, 4))
        views_colors = ['#e1005b', '#f59ab5']
        plt.bar(views_labels, views_values, color=views_colors)
        plt.ylabel('Quantidade de Views')
        plt.title('Comparativo de Visualizações por Portal')
        for i, v in enumerate(views_values):
            plt.text(i, v + 0.5, str(int(v)), ha='center', fontweight='bold')
        plt.tight_layout()
        views_chart_path = 'views_chart.jpg'
        plt.savefig(views_chart_path, format='jpg', dpi=150)
        plt.close()

        # Leads
        leads_labels = ['Leads DF', 'Leads OLX/ZAP', 'Leads C2S']
        leads_values_raw = [
            row_data.get('Leads DF', 0),
            row_data.get('Leads OLX/ZAP', 0),
            row_data.get('Leads C2S', 0),
        ]
        leads_values = [num_or_zero(v) for v in leads_values_raw]

        plt.figure(figsize=(8, 4))
        leads_colors = ['#e1005b', '#ff7f50', '#a64ca6']  
        plt.bar(leads_labels, leads_values, color=leads_colors)
        plt.ylabel('Quantidade de Leads')
        plt.title('Comparativo de Leads por Fonte')
        for i, v in enumerate(leads_values):
            plt.text(i, v + 0.5, str(int(v)), ha='center', fontweight='bold')
        plt.tight_layout()
        leads_chart_path = 'leads_chart.jpg'
        plt.savefig(leads_chart_path, format='jpg', dpi=150)
        plt.close()

        # Pizza (se houver dados)
        if sum(leads_values) > 0:
            plt.figure(figsize=(7, 7))
            pie_colors = ['#e1005b', '#ff7f50', '#a64ca6']
            plt.pie(leads_values, labels=leads_labels, autopct='%1.1f%%', startangle=90, colors=pie_colors)
            plt.title('Distribuição de Leads por Fonte')
            plt.axis('equal')
            pie_chart_path = 'pie_chart.jpg'
            plt.savefig(pie_chart_path, format='jpg', dpi=150)
            plt.close()

        # --- Montagem do PDF ---
        pdf = PDF()
        pdf.add_page()

        # Título do documento (já há um título no header, mas mantemos um subtítulo)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 8, f'Detalhamento do Imóvel {codigo_imovel}', 0, 1, 'C')
        pdf.ln(2)

        # Informações do Imóvel
        pdf.chapter_title('Informações do Imóvel')
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(50, 50, 50)

        # Renderiza pares "Coluna: valor" com MultiCell (quebra automática) e checagem de página entre blocos
        for col, value in row_data.items():
            if col not in ['Views DF', 'Views OLX/ZAP', 'Leads DF', 'Leads OLX/ZAP', 'Leads C2S']:
                # antes de escrever, verifique se precisamos de nova página (linha ~7mm)
                if pdf.get_y() + 7 > pdf.page_break_trigger:
                    pdf.add_page()
                    pdf.set_font('Arial', '', 10)
                    pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 7, f'{col}: {value}', 0, 'L')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # Visualizações
        pdf.chapter_title('Análise de Visualizações (Views)')
        add_image_auto(pdf, views_chart_path, max_w=180, max_h=90, center=True)
        pdf.chapter_body('Comparação de visualizações do imóvel em diferentes portais, destacando a performance de cada plataforma.')

        # Leads
        pdf.chapter_title('Análise de Contatos (Leads)')
        add_image_auto(pdf, leads_chart_path, max_w=180, max_h=90, center=True)
        pdf.chapter_body('Quantidade de leads gerados por cada fonte, indicando os canais com maior conversão ou interesse.')

        # Distribuição de Leads (Pizza)
        if pie_chart_path and os.path.exists(pie_chart_path):
            pdf.chapter_title('Distribuição Percentual de Leads')
            add_image_auto(pdf, pie_chart_path, max_w=160, max_h=100, center=True)
            pdf.chapter_body('Proporção de leads por canal, permitindo leitura rápida da contribuição relativa de cada fonte.')

        # --- Saída do PDF ---
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            pdf_output = pdf_output.encode('latin-1', 'ignore')

        return Response(
            pdf_output,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=relatorio_imovel_{codigo_imovel}.pdf'}
        )

    except Exception as e:
        return jsonify({"error": "Ocorreu um erro interno ao processar o arquivo", "details": str(e)}), 500

    finally:
        # Limpa arquivos temporários
        safe_remove(views_chart_path)
        safe_remove(leads_chart_path)
        safe_remove(pie_chart_path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
