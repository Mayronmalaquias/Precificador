import os
import re
import csv
import time
import logging
import unicodedata
import numpy as np

try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except Exception:
    GSHEETS_AVAILABLE = False

from typing import Optional, Tuple, Dict, List, Set
from flask import current_app, make_response, has_app_context
from fpdf import FPDF, HTMLMixin

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from app import SessionLocal
from app.models.relatorio import PerformeImoveis


# ===================== LOGGING =====================

_module_logger = logging.getLogger(__name__)
if not _module_logger.handlers:
    _module_logger.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s"))
    _module_logger.addHandler(_h)

def _get_logger():
    logger = _module_logger
    try:
        if has_app_context():
            logger = current_app.logger or _module_logger
            lvl_name = str(current_app.config.get("AVALIACOES_LOG_LEVEL", "INFO")).upper()
            lvl = getattr(logging, lvl_name, logging.INFO)
            logger.setLevel(lvl)
            log_file = current_app.config.get("AVALIACOES_LOG_FILE")
            if log_file:
                already = any(isinstance(h, logging.FileHandler) and getattr(h, "_aval_file", False)
                              for h in logger.handlers)
                if not already:
                    os.makedirs(os.path.dirname(log_file), exist_ok=True)
                    fh = logging.FileHandler(log_file, encoding="utf-8")
                    fh.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s"))
                    fh._aval_file = True
                    logger.addHandler(fh)
    except Exception:
        pass
    return logger


# ===================== utils =====================

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

def _strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _clean_number_token(s) -> str:
    return re.sub(r"[^0-9,\.\-]", "", str(s))

def _is_number(s) -> bool:
    try:
        t = _clean_number_token(s)
        float(t.replace(",", "."))
        return True
    except Exception:
        return False

def _to_float(s) -> float:
    try:
        t = _clean_number_token(s)
        return float(t.replace(",", "."))
    except Exception:
        return float("nan")

def format_brl(v: float) -> str:
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ---- Sanitização latin-1 para FPDF ----

_LATIN1_REPLACEMENTS = {
    "\u2013": "-", "\u2014": "-", "\u2212": "-",  # dashes
    "\u2018": "'", "\u2019": "'",                 # single quotes
    "\u201C": '"', "\u201D": '"',                 # double quotes
    "\u00A0": " ",                                # nbsp
}

def latin1_safe(s: str, ctx: str = "") -> str:
    if s is None:
        return ""
    log = _get_logger()
    original = s
    for bad, good in _LATIN1_REPLACEMENTS.items():
        if bad in s:
            s = s.replace(bad, good)
    try:
        s.encode("latin-1")
        return s
    except UnicodeEncodeError:
        fixed = s.encode("latin-1", "replace").decode("latin-1")
        log.warning(f"[latin1_safe] Substituições em '{ctx}'.")
        log.debug(f"[latin1_safe] ORIGINAL: {original}\n[latin1_safe] SANIT: {fixed}")
        return fixed


# ===================== caches (duas páginas) =====================

_AVAL_CACHE = {  # Fato_Avaliacao
    "source": None, "key": None, "mtime": None,
    "rows": None, "headers": None, "last_fetch": 0.0,
}
_VIS_CACHE = {   # Fato_Visitas
    "source": None, "key": None, "mtime": None,
    "rows": None, "headers": None, "last_fetch": 0.0,
}
_TTL_SECONDS = 60


# ===================== Google Sheets helpers =====================

def _gs_build_service(cred_file: str):
    creds = Credentials.from_service_account_file(
        cred_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def _gs_list_sheet_titles(service, sheet_id: str) -> List[str]:
    meta = service.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets(properties(title))").execute()
    sheets = meta.get("sheets", [])
    return [s["properties"]["title"] for s in sheets if "properties" in s and "title" in s["properties"]]

def _quote_sheet_title(title: str) -> str:
    return "'" + str(title).replace("'", "''") + "'"

def _normalize_title_for_match(s: str) -> str:
    s = _strip_accents(s or "")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()

def _resolve_range(service, sheet_id: str, range_name: str) -> str:
    tab = None
    rng = None
    if "!" in range_name:
        parts = range_name.split("!", 1)
        tab = parts[0].strip().strip("'").strip('"')
        rng = parts[1].strip()
    else:
        rng = range_name.strip()

    if not rng:
        rng = "A:Z"

    titles = _gs_list_sheet_titles(service, sheet_id)
    if not titles:
        return rng

    chosen = None
    if tab:
        if tab in titles:
            chosen = tab
        else:
            tab_norm = _normalize_title_for_match(tab)
            norm_map = {_normalize_title_for_match(t): t for t in titles}
            if tab_norm in norm_map:
                chosen = norm_map[tab_norm]
            else:
                for t in titles:
                    if tab_norm in _normalize_title_for_match(t):
                        chosen = t
                        break

    if not chosen:
        chosen = titles[0]
        _get_logger().warning(f"[_resolve_range] Aba '{tab}' não encontrada. Usando a primeira aba: '{chosen}'.")

    quoted = _quote_sheet_title(chosen)
    return f"{quoted}!{rng}"

def _read_gsheet_values(sheet_id: str, range_name: str, cred_file: str) -> Tuple[List[Dict[str, str]], List[str]]:
    if not GSHEETS_AVAILABLE:
        raise RuntimeError("Dependências do Google Sheets não instaladas.")

    service = _gs_build_service(cred_file)
    resolved_range = _resolve_range(service, sheet_id, range_name)

    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=resolved_range,
        majorDimension="ROWS"
    ).execute()
    values = result.get("values", [])

    if not values:
        return [], []

    headers_raw = [str(h).strip() for h in values[0]]
    headers = []
    for i, h in enumerate(headers_raw):
        headers.append(h if h else f"col{i+1}")

    rows: List[Dict[str, str]] = []
    for raw in values[1:]:
        row_dict = {}
        for i, h in enumerate(headers):
            val = raw[i] if i < len(raw) else ""
            row_dict[h] = str(val).strip() if val is not None else ""
        rows.append(row_dict)

    return rows, headers


# ===================== Carregamento bases (Sheets com fallback CSV) =====================

def _load_sheet_or_csv(cache, default_csv_path: str, sheet_id: Optional[str], range_name: Optional[str], cred_file: Optional[str]):
    log = _get_logger()
    now = time.time()

    # Google Sheets
    if sheet_id:
        cache_key = ("gsheet", sheet_id, range_name, cred_file)
        if (
            cache["source"] == "gsheet"
            and cache["key"] == cache_key
            and (now - float(cache.get("last_fetch") or 0)) < _TTL_SECONDS
            and cache["rows"] is not None
        ):
            return

        try:
            rows, headers = _read_gsheet_values(sheet_id, range_name, cred_file)
            if rows and headers:
                cache.update({
                    "source": "gsheet", "key": cache_key, "mtime": None,
                    "rows": rows, "headers": headers, "last_fetch": now,
                })
                log.info(f"[load] (Google Sheets) {range_name} Linhas={len(rows)} | Colunas={len(headers)}")
                return
            else:
                log.warning(f"[load] Google Sheet vazio em {range_name}.")
        except Exception as e:
            log.exception(f"[load] Erro lendo Google Sheets ({range_name}): {e}")

    # CSV fallback
    csv_path = default_csv_path
    try:
        csv_path = current_app.config.get("AVALIACOES_CSV" if "Avaliacao" in (range_name or "") else "VISITAS_CSV", csv_path)
    except Exception:
        pass

    if not csv_path or not os.path.exists(csv_path):
        log.warning(f"[load] CSV não encontrado: {csv_path}")
        cache.update({"source": None, "key": None, "mtime": None, "rows": None, "headers": None})
        return

    mtime = os.path.getmtime(csv_path)
    if cache["source"] == "csv" and cache["key"] == csv_path and cache["mtime"] == mtime and cache["rows"] is not None:
        return

    rows, headers = [], []
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096); f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=";,")
            except Exception:
                class _D: delimiter = ','
                dialect = _D()
            reader = csv.DictReader(f, dialect=dialect)
            headers = [h.strip() for h in (reader.fieldnames or [])]
            for r in reader:
                rows.append({(k.strip() if isinstance(k, str) else k): (r.get(k, "").strip() if isinstance(r.get(k, ""), str) else r.get(k, "")) for k in (reader.fieldnames or [])})
    except Exception as e:
        log.exception(f"[load] Erro lendo CSV: {e}")
        cache.update({"source": None, "key": None, "mtime": None, "rows": None, "headers": None})
        return

    cache.update({
        "source": "csv", "key": csv_path, "mtime": mtime,
        "rows": rows, "headers": headers, "last_fetch": now,
    })
    log.info(f"[load] (CSV) {csv_path} Linhas={len(rows)} | Colunas={len(headers)}")


def load_bases():
    """Carrega Fato_Avaliacao e Fato_Visitas com fallback para CSV."""
    # Preferir configs do app; se faltarem, usar defaults do seu exemplo
    try:
        sheet_id = current_app.config.get("AVALIACOES_SHEET_ID")
        cred_file = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        range_aval = current_app.config.get("AVALIACOES_SHEET_RANGE") or "Fato_Avaliacao!A1:Z"
        range_vis  = current_app.config.get("VISITAS_SHEET_RANGE")    or "Fato_Visitas!A1:Z"
        if not sheet_id:
            sheet_id = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"
        if not cred_file:
            cred_file = "./app/utils/asserts/credenciais.json"
    except Exception:
        sheet_id = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"
        cred_file = "./app/utils/asserts/credenciais.json"
        range_aval = "Fato_Avaliacao!A1:Z"
        range_vis = "Fato_Visitas!A1:Z"

    _load_sheet_or_csv(
        _AVAL_CACHE,
        default_csv_path="./app/utils/asserts/Copia_Fato_Avaliacao.csv",
        sheet_id=sheet_id, range_name=range_aval, cred_file=cred_file
    )
    _load_sheet_or_csv(
        _VIS_CACHE,
        default_csv_path="./app/utils/asserts/Copia_Fato_Visitas.csv",
        sheet_id=sheet_id, range_name=range_vis, cred_file=cred_file
    )


# ===================== heurísticas de colunas =====================

def _normalize_header_key(h: str) -> str:
    h = _strip_accents(h or "").lower()
    h = re.sub(r"[^a-z0-9]+", " ", h)
    return re.sub(r"\s+", " ", h).strip()

def _only_digits(v) -> str:
    return re.sub(r"\D", "", str(v) if v is not None else "")

def _normalize_codigo(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    s = re.sub(r"[^0-9A-Za-z]", "", s)
    if not s:
        return ""
    if re.fullmatch(r"\d+", s):
        try:
            return str(int(s))
        except Exception:
            return s
    return s.upper()

def _codigo_matches(a, b) -> bool:
    an = _normalize_codigo(a)
    bn = _normalize_codigo(b)
    if an and bn and an == bn:
        return True
    ad = _only_digits(a)
    bd = _only_digits(b)
    return bool(ad and bd and ad == bd)

def _guess_column(headers: List[str], candidates_exact: List[str], tokens_any: List[str] = None):
    # tenta match exato por nomes normalizados; depois por tokens (qualquer)
    norm = {h: _normalize_header_key(h) for h in headers}
    exact_norms = {_normalize_header_key(x) for x in candidates_exact}
    for h, n in norm.items():
        if n in exact_norms:
            return h
    if tokens_any:
        for h, n in norm.items():
            if all(tok in n for tok in tokens_any):
                return h
    return None


# ===================== JOIN: Id_Imovel -> (Fato_Visitas) -> Id_Visita -> (Fato_Avaliacao) =====================

def _get_visita_ids_por_codigo(codigo_imovel: str) -> Set[str]:
    """
    Busca em Fato_Visitas todas as linhas cujo Id_Imovel casa com 'codigo_imovel'
    e retorna o conjunto de Id_Visita (como strings normalizadas).
    """
    load_bases()
    rows = _VIS_CACHE["rows"] or []
    headers = _VIS_CACHE["headers"] or []
    if not rows or not headers:
        return set()

    col_id_imovel = _guess_column(headers, ["Id_Imovel", "id imovel", "imovel id"], tokens_any=["imovel"])
    col_id_visita = _guess_column(headers, ["Id_Visita", "id visita"], tokens_any=["visita"])
    if not col_id_imovel or not col_id_visita:
        _get_logger().warning("[_get_visita_ids_por_codigo] Colunas Id_Imovel/Id_Visita não encontradas em Fato_Visitas.")
        return set()

    alvo = _normalize_codigo(codigo_imovel)
    out: Set[str] = set()
    for r in rows:
        if _codigo_matches(r.get(col_id_imovel, ""), alvo):
            vid = r.get(col_id_visita, "")
            if str(vid).strip() != "":
                out.add(_normalize_codigo(vid))
    return out


# ===================== CAMPOS de avaliação =====================

_CAMPOS_SOLICITADOS = [
    ("Localizacao",          ["localizacao"]),
    ("Tamanho",              ["tamanho"]),
    ("Planta_Imovel",        ["planta", "imovel"]),
    ("Qualidade_Acabamento", ["qualidade", "acabamento"]),
    ("Estado_Conservacao",   ["estado", "conservacao"]),
    ("Condominio_AreaComun", ["condominio", "area", "com"]),
    ("Preco",                ["preco"]),
    ("Nota_Geral",           ["nota", "geral"]),
    ("Preco_N10",            ["preco", "n10"]),
]

def _detect_by_tokens(headers: List[str], *tokens: str) -> Optional[str]:
    norm = {h: _normalize_header_key(h) for h in headers}
    for h, n in norm.items():
        if all(tok in n for tok in tokens):
            return h
    return None

def _detect_preco_n10_column(headers: List[str]) -> Optional[str]:
    # casos comuns de variação
    norm = {h: _normalize_header_key(h) for h in headers}
    for h, n in norm.items():
        if n in ("preco_n10", "preco n10"):
            return h
    for h, n in norm.items():
        if "preco" in n and "n10" in n:
            return h
    for h in headers:
        n = _normalize_header_key(h.replace("ç", "c").replace("Ç", "C"))
        if "preco" in n and "n10" in n:
            return h
    return None


# ===================== AGREGADORES (agora via Id_Visita) =====================

def _candidate_avaliacao_columns(headers: List[str]) -> List[str]:
    """Seleciona automaticamente colunas numéricas (fallback, se necessário)."""
    cand = []
    for h in headers:
        cnt_num = 0; cnt_tot = 0
        for r in (_AVAL_CACHE["rows"] or [])[:50]:
            v = r.get(h, "")
            if v not in (None, ""):
                cnt_tot += 1
                if _is_number(v):
                    cnt_num += 1
        if cnt_tot > 0 and cnt_num / max(cnt_tot, 1) > 0.6:
            cand.append(h)
    return cand

def _map_campos_solicitados(headers: List[str]) -> Dict[str, Optional[str]]:
    encontrados: Dict[str, Optional[str]] = {}
    for lbl, toks in _CAMPOS_SOLICITADOS:
        if lbl == "Preco_N10":
            encontrados[lbl] = _detect_preco_n10_column(headers)
        else:
            encontrados[lbl] = _detect_by_tokens(headers, *toks)
    return encontrados

def _rows_avaliacao_para_visitas(visita_ids: Set[str]) -> List[Dict[str, str]]:
    """Filtra Fato_Avaliacao mantendo apenas linhas cujo Id_Visita ∈ visita_ids."""
    rows = _AVAL_CACHE["rows"] or []
    headers = _AVAL_CACHE["headers"] or []
    if not rows or not headers or not visita_ids:
        return []
    col_id_visita = _guess_column(headers, ["Id_Visita", "id visita"], tokens_any=["visita"])
    if not col_id_visita:
        _get_logger().warning("[_rows_avaliacao_para_visitas] Coluna Id_Visita não encontrada em Fato_Avaliacao.")
        return []
    out = []
    for r in rows:
        vid = _normalize_codigo(r.get(col_id_visita, ""))
        if vid and vid in visita_ids:
            out.append(r)
    return out

def _per_registro_medias_e_cols_via_visitas(codigo: str) -> Tuple[List[float], List[str], int]:
    """Médias por registro de avaliação (linhas) associadas ao código via Id_Visita."""
    log = _get_logger()
    load_bases()

    rows_aval = _AVAL_CACHE["rows"] or []
    headers_aval = _AVAL_CACHE["headers"] or []
    if not rows_aval or not headers_aval:
        return [], [], 0

    visita_ids = _get_visita_ids_por_codigo(codigo)
    match_rows = _rows_avaliacao_para_visitas(visita_ids)
    match = len(match_rows)

    cand_cols = _map_campos_solicitados(headers_aval).values()
    cand_cols = [c for c in cand_cols if c]  # apenas as que existirem
    if not cand_cols:
        cand_cols = _candidate_avaliacao_columns(headers_aval)

    lista = []
    for r in match_rows:
        notas = []
        for c in cand_cols:
            v = r.get(c, "")
            if v not in (None, "") and _is_number(v):
                notas.append(_to_float(v))
        if notas:
            lista.append(float(np.nanmean(notas)))

    log.info(f"[_per_registro_medias_e_cols_via_visitas] codigo={codigo} | match={match} | cols={cand_cols} | regs_com_nota={len(lista)}")
    return lista, list(cand_cols), match

def get_media_avaliacao_por_codigo(codigo: str) -> Optional[Tuple[float, int, List[float]]]:
    lista, _, _ = _per_registro_medias_e_cols_via_visitas(codigo)
    if not lista:
        return None
    media = float(np.nanmean(lista))
    return (media, len(lista), lista)

def get_media_por_campo(codigo: str) -> Optional[Dict[str, Tuple[float, int]]]:
    load_bases()
    rows_aval = _AVAL_CACHE["rows"] or []
    headers_aval = _AVAL_CACHE["headers"] or []
    if not rows_aval or not headers_aval:
        return None

    visita_ids = _get_visita_ids_por_codigo(codigo)
    match_rows = _rows_avaliacao_para_visitas(visita_ids)

    encontrados = _map_campos_solicitados(headers_aval)
    cand_cols = [c for c in encontrados.values() if c]
    if not cand_cols:
        cand_cols = _candidate_avaliacao_columns(headers_aval)
    if not cand_cols:
        return None

    dados = {c: [] for c in cand_cols}
    for r in match_rows:
        for c in cand_cols:
            v = r.get(c, "")
            if v not in (None, "") and _is_number(v):
                dados[c].append(_to_float(v))

    out = {}
    ok = False
    for c, vals in dados.items():
        if vals:
            out[c] = (float(np.nanmean(vals)), len(vals))
            ok = True
    return out if ok else None

def get_medias_especificas(codigo: str) -> List[Tuple[str, Optional[float], int]]:
    """Retorna [(rótulo, média, qtd)] na ordem de _CAMPOS_SOLICITADOS, via Id_Visita."""
    load_bases()
    rows_aval = _AVAL_CACHE["rows"] or []
    headers_aval = _AVAL_CACHE["headers"] or []
    if not rows_aval or not headers_aval:
        return [(lbl, None, 0) for (lbl, _) in _CAMPOS_SOLICITADOS]

    visita_ids = _get_visita_ids_por_codigo(codigo)
    match_rows = _rows_avaliacao_para_visitas(visita_ids)

    encontrados = _map_campos_solicitados(headers_aval)
    resultados: List[Tuple[str, Optional[float], int]] = []

    for lbl, _toks in _CAMPOS_SOLICITADOS:
        col = encontrados.get(lbl)
        if lbl == "Preco_N10" and not col:
            col = _detect_preco_n10_column(headers_aval)
        if not col:
            resultados.append((lbl, None, 0))
            continue
        vals = []
        for r in match_rows:
            v = r.get(col, "")
            if v not in (None, "") and _is_number(v):
                vals.append(_to_float(v))
        if vals:
            resultados.append((lbl, float(np.nanmean(vals)), len(vals)))
        else:
            resultados.append((lbl, None, 0))
    return resultados


# ===================== PDF base (sem gráficos) =====================

class PDF(FPDF, HTMLMixin):
    def __init__(self, orientation='P', unit='mm', format='A4', logo_file=None):
        super().__init__(orientation, unit, format)
        self.logo_file = logo_file
        self.set_left_margin(15)
        self.set_right_margin(15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(242, 242, 242)
        self.rect(0, 0, self.w, self.h, 'F')

        if self.logo_file and os.path.exists(self.logo_file):
            self.image(self.logo_file, x=15, y=8, h=12)

        title = latin1_safe('Relatório de Desempenho de Imóvel', ctx="header.title")
        self.set_font('Arial', 'B', 15)
        self.set_text_color(225, 0, 91)
        self.cell(0, 10, title, 0, 1, 'C')
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(120, 120, 120)
        txt = latin1_safe(f'Página {self.page_no()}', ctx="footer.page")
        self.cell(0, 10, txt, 0, 0, 'C')
        self.set_text_color(0, 0, 0)

    def chapter_title(self, title):
        self.ln(2)
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 220, 220)
        self.set_text_color(225, 0, 91)
        self.cell(0, 9, latin1_safe(title, ctx="chapter_title"), 0, 1, 'L', 1)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        w = self.w - self.l_margin - self.r_margin
        self.set_x(self.l_margin)
        self.multi_cell(w, 6, latin1_safe(body, ctx="chapter_body"))
        self.ln(1)


def _break_long_tokens(text: str, every: int = 60) -> str:
    if text is None:
        return ""
    s = str(text)
    return re.sub(r'(\S{' + str(every) + r'})', r'\1 ', s)

def _safe_multicell(pdf: PDF, txt: str, h: float = 7, align: str = "L"):
    pdf.set_x(pdf.l_margin)
    w = pdf.w - pdf.l_margin - pdf.r_margin
    txt = _break_long_tokens(txt, every=60)
    txt = latin1_safe(txt, ctx="multicell")
    if w <= pdf.get_string_width("W"):
        size_pt = int(pdf.font_size_pt)
        while size_pt > 6 and w <= pdf.get_string_width("W"):
            size_pt -= 1
            pdf.set_font(pdf.font_family, pdf.font_style, size_pt)
    pdf.multi_cell(w, h, txt, border=0, align=align)

def desenhar_tabela(pdf: PDF, rows: List[Tuple[str, Optional[float], int]],
                    header=("Campo", "Média", "Qtd."), widths=(90, 30, 25)):
    if not rows:
        return
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(widths[0], 7, latin1_safe(header[0], "tabela.header"), 1, 0, "C", fill=True)
    pdf.cell(widths[1], 7, latin1_safe(header[1], "tabela.header"), 1, 0, "C", fill=True)
    pdf.cell(widths[2], 7, latin1_safe(header[2], "tabela.header"), 1, 1, "C", fill=True)

    pdf.set_font("Arial", "", 10)
    for (label, media, qtd) in rows:
        if pdf.get_y() + 7 > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(widths[0], 7, latin1_safe(header[0], "tabela.header"), 1, 0, "C", fill=True)
            pdf.cell(widths[1], 7, latin1_safe(header[1], "tabela.header"), 1, 0, "C", fill=True)
            pdf.cell(widths[2], 7, latin1_safe(header[2], "tabela.header"), 1, 1, "C", fill=True)
            pdf.set_font("Arial", "", 10)

        nome = label if len(label) <= 60 else (label[:57] + "...")
        val = "N/A" if media is None or (isinstance(media, float) and not np.isfinite(media)) else f"{media:.2f}"
        pdf.cell(widths[0], 7, latin1_safe(nome, "tabela.campo"), 1, 0, "L")
        pdf.cell(widths[1], 7, latin1_safe(val, "tabela.media"), 1, 0, "C")
        pdf.cell(widths[2], 7, latin1_safe(str(qtd), "tabela.qtd"), 1, 1, "C")


# ===================== geração do PDF (sem seção de gráficos) =====================

def gerar_pdf_relatorio(rowdict: dict) -> bytes:
    log = _get_logger()
    logo_file = current_app.config.get("LOGO_FILE", "../utils/asserts/img/Logo 61 Vazado (1).png")
    pdf = PDF(logo_file=logo_file)
    pdf.add_page()

    codigo = rowdict.get("Código do Imóvel", "") or rowdict.get("Codigo do Imovel", "") or rowdict.get("codigo_imovel", "")
    titulo = latin1_safe(f"Detalhamento do Imóvel {codigo}", ctx="titulo.principal")
    pdf.set_font("Arial", "B", 14)
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin, 8, titulo, 0, 1, "C")
    pdf.ln(2)

    # ===================== AVALIAÇÕES =====================
    try:
        media_qtd_lista = get_media_avaliacao_por_codigo(str(codigo))
        log.info(f"[PDF] codigo={codigo} | media_qtd_lista={media_qtd_lista}")
        if media_qtd_lista:
            media_geral, qtd, lista_medias = media_qtd_lista
            if np.isfinite(media_geral) and qtd > 0:
                pdf.chapter_title("Avaliações do imóvel")
                pdf.set_font("Arial", "", 10)
                pdf.set_text_color(50, 50, 50)
                _safe_multicell(pdf, f"Base: {qtd} avaliação(ões) registrada(s) para as visitas deste imóvel.")
                pdf.set_text_color(0, 0, 0)

                _safe_multicell(pdf, "Médias por avaliação (cada registro):", h=6, align="L")
                rows = [("Avaliação #{}".format(i), m, 1) for i, m in enumerate(lista_medias, start=1)]
                desenhar_tabela(pdf, rows, header=("Avaliação", "Média", "Qtd."), widths=(60, 30, 25))
                pdf.ln(2)
    except Exception as e:
        log.exception(f"[PDF] Erro na seção de avaliações: {e}")

    # ===================== MÉDIAS INDIVIDUAIS (CAMPOS SOLICITADOS) =====================
    try:
        lista_especificas = get_medias_especificas(str(codigo))
        pdf.chapter_title("Médias individuais (itens e preços)")
        desenhar_tabela(pdf, lista_especificas, header=("Campo", "Média", "Qtd."), widths=(90, 30, 25))
        pdf.ln(2)
    except Exception as e:
        log.exception(f"[PDF] Erro na seção de médias individuais: {e}")

    # ===================== INFORMAÇÕES DO IMÓVEL (mantida) =====================
    pdf.chapter_title("Informações do Imóvel")
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(50, 50, 50)

    excluir = {"Views DF", "Views OLX/ZAP", "Leads DF", "Leads OLX/ZAP", "Leads C2S", "Leads C2S - Imoview"}
    for col, value in rowdict.items():
        if col in excluir:
            continue
        if pdf.get_y() + 7 > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(50, 50, 50)
        linha = f"{col}: {'' if value is None else value}"
        _safe_multicell(pdf, linha, h=7, align="L")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1", "ignore")
    return out


# ===================== orquestração =====================

def get_imovel_by_codigo(codigo: str) -> Optional[dict]:
    log = _get_logger()
    with SessionLocal() as session:
        reg = (
            session.query(PerformeImoveis)
            .filter(PerformeImoveis.codigo_imovel == codigo)
            .order_by(PerformeImoveis.id.desc())
            .first()
        )
    if not reg:
        log.warning(f"[get_imovel_by_codigo] Imóvel não encontrado: {codigo}")
    return reg.to_rowdict() if reg else None


def gerar_relatorio_imovel(codigo: str):
    """
    Sucesso: Response (PDF).
    Erro/validação: dict + status.
    """
    log = _get_logger()
    if not codigo:
        return {"error": "Parâmetro 'codigo' é obrigatório"}, 400

    rowdict = get_imovel_by_codigo(codigo)
    if not rowdict:
        return {"error": f"Imóvel com código '{codigo}' não encontrado."}, 404

    try:
        pdf_bytes = gerar_pdf_relatorio(rowdict)
    except Exception as e:
        log.exception(f"[gerar_relatorio_imovel] Erro ao gerar PDF para codigo={codigo}: {e}")
        return {"error": "Falha ao gerar o relatório em PDF."}, 500

    filename = f"relatorio_imovel_{codigo}.pdf"
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
