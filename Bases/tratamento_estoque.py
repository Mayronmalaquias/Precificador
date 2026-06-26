import pandas as pd
import numpy as np
from datetime import datetime

# =========================
# CONFIG
# =========================
INPUT_XLS = "./imoveis-2026-06-19.xls" # seu export do Imoview (HTML disfarçado de .xls)
OUTPUT_XLSX = "./Fato_Estoque_IMPORTAR.xlsx"   # ESTE é o arquivo que você vai importar no App Script

# Data do estoque como data real (célula de Excel)
DATA_ESTOQUE = datetime.now().date()

# =========================
# HELPERS
# =========================
def clean_str(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s

def split_captadores(valor: str):
    """
    No Imoview, 'Captadores' costuma vir assim:
      "Nome 1 | Nome 2 | Nome 3"
    Vamos gerar Captador1..3 (nomes).
    """
    s = clean_str(valor)
    if not s:
        return "", "", ""
    parts = [p.strip() for p in s.split("|")]
    parts = [p for p in parts if p]
    parts = (parts + ["", "", ""])[:3]
    return parts[0], parts[1], parts[2]

# =========================
# LEITURA DO "XLS" (HTML)
# =========================
tables = pd.read_html(INPUT_XLS, flavor="lxml")
if not tables:
    raise ValueError("Não encontrei nenhuma tabela dentro do arquivo .xls (HTML).")

# Pega a maior tabela (geralmente é a do estoque)
df = max(tables, key=lambda t: t.shape[0] * t.shape[1]).copy()

# =========================
# VALIDAR COLUNAS DO EXPORT
# =========================
# Código pode vir como "Codigo" (sem acento) no export
if "Codigo" not in df.columns and "Código" not in df.columns:
    raise ValueError(f"Não encontrei coluna de código. Colunas disponíveis: {list(df.columns)}")

col_codigo = "Codigo" if "Codigo" in df.columns else "Código"

# Captadores pode vir como "Captadores" ou outra variação
if "Captadores" not in df.columns:
    # se não existir, cria vazio (não quebra)
    df["Captadores"] = ""

# =========================
# GERAR Captador1..3 (NOMES)
# =========================
caps = df["Captadores"].apply(split_captadores)
df["Captador1"] = caps.apply(lambda x: x[0])
df["Captador2"] = caps.apply(lambda x: x[1])
df["Captador3"] = caps.apply(lambda x: x[2])

# =========================
# SAÍDA EXATA PARA processFile(data)
# (6 COLUNAS, com DataEstoque na COLUNA F)
# =========================
out = pd.DataFrame({
    "Codigo": df[col_codigo].apply(clean_str),   # A
    "Captador1": df["Captador1"],                # B (nome)
    "Captador2": df["Captador2"],                # C (nome)
    "Captador3": df["Captador3"],                # D (nome)
    "Gerente": "",                               # E (pode vazio; GAS preenche)
    "DataEstoque": DATA_ESTOQUE,                 # F (data real no Excel)
})

# (Opcional) remover linhas sem código
out = out[out["Codigo"].astype(str).str.strip().ne("")].copy()

# Salvar XLSX (com data como célula de data)
out.to_excel(OUTPUT_XLSX, index=False)

print("OK! XLSX compatível gerado:", OUTPUT_XLSX)
print(out.head(10))
