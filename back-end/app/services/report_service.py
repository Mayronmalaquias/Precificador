import os
import re
import csv
import time
import logging
import unicodedata
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except Exception:
    GSHEETS_AVAILABLE = False

from typing import Optional, Tuple, Dict, List
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


# ===================== cache da base de avaliações =====================

_AVAL_CACHE = {
    "source": None,     # "csv" ou "gsheet"
    "key": None,        # csv: caminho; gsheet: (sheet_id, range_resolvido)
    "mtime": None,      # csv: mtime; gsheet: None
    "rows": None,
    "headers": None,
    "last_fetch": 0.0,  # timestamp do último fetch (para TTL)
}
_AVAL_TTL_SECONDS = 60  # evite bater na API a cada chamada


# ===================== Código: normalização e match robustos =====================

def _normalize_codigo(v) -> str:
    """
    Normaliza códigos para comparação:
    - Remove tudo que não é [0-9A-Za-z]
    - Se ficar só dígitos: int -> str (padroniza 3346.0, 03.346 => "3346")
    - Caso contrário, retorna upper() (para códigos alfanuméricos)
    """
    if v is None:
        return ""
    s = str(v).strip()
    s = re.sub(r"[^0-9A-Za-z]", "", s)  # tira separadores, espaços, pontuação
    if not s:
        return ""
    if re.fullmatch(r"\d+", s):
        try:
            return str(int(s))
        except Exception:
            return s
    return s.upper()

def _only_digits(v) -> str:
    """Extrai somente dígitos (pode ser vazio)."""
    return re.sub(r"\D", "", str(v) if v is not None else "")

def _codigo_matches(a, b) -> bool:
    """
    Critério robusto:
    1) compara normalizado (_normalize_codigo)
    2) se ambos têm dígitos, compara apenas os dígitos
    Isso cobre "3346", "3346.0", "03.346", "COD-3346" etc.
    """
    an = _normalize_codigo(a)
    bn = _normalize_codigo(b)
    if an and bn and an == bn:
        return True

    ad = _only_digits(a)
    bd = _only_digits(b)
    if ad and bd and ad == bd:
        return True

    return False


# ===================== Google Sheets helpers =====================

def _gs_build_service(cred_file: str):
    creds = Credentials.from_service_account_file(
        cred_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    # cache_discovery=False evita warnings/erros de cache
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def _gs_list_sheet_titles(service, sheet_id: str) -> List[str]:
    meta = service.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets(properties(title))").execute()
    sheets = meta.get("sheets", [])
    return [s["properties"]["title"] for s in sheets if "properties" in s and "title" in s["properties"]]

def _quote_sheet_title(title: str) -> str:
    # Sheets A1 notation: aspas simples ao redor; aspas internas duplicadas
    return "'" + str(title).replace("'", "''") + "'"

def _normalize_title_for_match(s: str) -> str:
    s = _strip_accents(s or "")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()

def _resolve_range(service, sheet_id: str, range_name: str) -> str:
    """
    Garante um range A1 válido:
    - Se incluir '!' separa em (aba, intervalo).
    - Coloca a aba entre aspas simples.
    - Se a aba não existir, tenta casar por normalização; se mesmo assim não, usa a primeira aba.
    - Se o intervalo vier vazio, usa 'A:Z'.
    """
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
    """
    Lê valores de um Google Sheet e retorna (rows, headers), sendo rows uma lista de dicts por linha.
    A primeira linha do intervalo é considerada o cabeçalho.
    Faz resolução robusta do nome da aba.
    """
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


# ===================== Carregamento base (Sheets com fallback CSV) =====================

def load_avaliacoes_base():
    log = _get_logger()

    # Preferir Google Sheets via config; fallback para seus valores
    try:
        sheet_id = current_app.config.get("AVALIACOES_SHEET_ID")
        range_name = current_app.config.get("AVALIACOES_SHEET_RANGE")
        cred_file = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    except Exception:
        sheet_id = None
        range_name = None
        cred_file = None

    if not sheet_id:
        sheet_id = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"  # fallback do seu exemplo
    if not range_name:
        range_name = "Fato_Avaliacao!A1:Z"
    if not cred_file:
        cred_file = "./app/utils/asserts/credenciais.json"

    now = time.time()

    # Tenta Sheets
    if sheet_id:
        cache_key = ("gsheet", sheet_id, range_name, cred_file)
        if (
            _AVAL_CACHE["source"] == "gsheet"
            and _AVAL_CACHE["key"] == cache_key
            and (now - float(_AVAL_CACHE.get("last_fetch") or 0)) < _AVAL_TTL_SECONDS
            and _AVAL_CACHE["rows"] is not None
        ):
            log.debug("[load_avaliacoes_base] Cache gsheet válido.")
            return

        try:
            rows, headers = _read_gsheet_values(sheet_id, range_name, cred_file)
            if not rows or not headers:
                log.warning("[load_avaliacoes_base] Google Sheet sem dados (rows/headers vazios). Mantendo cache anterior.")
            else:
                _AVAL_CACHE.update({
                    "source": "gsheet",
                    "key": cache_key,
                    "mtime": None,
                    "rows": rows,
                    "headers": headers,
                    "last_fetch": now,
                })
                log.info(f"[load_avaliacoes_base] (Google Sheets) Carregado. Linhas={len(rows)} | Colunas={len(headers)}")
                log.info(f"[load_avaliacoes_base] Headers: {headers}")  # INFO para ver no log
                return
        except Exception as e:
            log.exception(f"[load_avaliacoes_base] Erro lendo Google Sheets: {e}")
            # fallback para CSV

    # CSV fallback
    default_path = "./app/utils/asserts/Cópia de Modelo_Visitas - Fato_Avaliacao.csv"
    try:
        csv_path = current_app.config.get("AVALIACOES_CSV", default_path)
    except Exception:
        csv_path = default_path

    log.debug(f"[load_avaliacoes_base] csv_path={csv_path}")

    if not csv_path or not os.path.exists(csv_path):
        log.warning(f"[load_avaliacoes_base] CSV não encontrado: {csv_path}")
        _AVAL_CACHE.update({"source": None, "key": None, "mtime": None, "rows": None, "headers": None})
        return

    mtime = os.path.getmtime(csv_path)
    if (
        _AVAL_CACHE["source"] == "csv"
        and _AVAL_CACHE["key"] == csv_path
        and _AVAL_CACHE["mtime"] == mtime
        and _AVAL_CACHE["rows"] is not None
    ):
        log.debug("[load_avaliacoes_base] Cache CSV válido.")
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
                rows.append({(k.strip() if isinstance(k, str) else k): (r.get(k, "").strip() if isinstance(r.get(k, ""), str) else r.get(k, ""))
                             for k in (reader.fieldnames or [])})
    except Exception as e:
        log.exception(f"[load_avaliacoes_base] Erro lendo CSV: {e}")
        _AVAL_CACHE.update({"source": None, "key": None, "mtime": None, "rows": None, "headers": None})
        return

    _AVAL_CACHE.update({
        "source": "csv",
        "key": csv_path,
        "mtime": mtime,
        "rows": rows,
        "headers": headers,
        "last_fetch": now,
    })
    log.info(f"[load_avaliacoes_base] (CSV) Carregado. Linhas={len(rows)} | Colunas={len(headers)}")
    log.debug(f"[load_avaliacoes_base] Headers: {headers}")


# ===================== heurísticas de colunas =====================

def _normalize_header_key(h: str) -> str:
    h = _strip_accents(h or "").lower()
    h = re.sub(r"[^a-z0-9]+", " ", h)
    return re.sub(r"\s+", " ", h).strip()

def _score_codigo_header(h_norm: str) -> int:
    """
    Atribui score para headers que parecem 'código do imóvel'.
    """
    score = 0
    exacts = {
        "codigo do imovel", "codigo_imovel", "codigo", "cod imovel", "cod_imovel",
        "id imovel", "id_imovel", "imovel", "imovel id", "codigo do imóvel", "id imóvel"
    }
    if h_norm in exacts:
        score += 5
    if "cod" in h_norm:
        score += 3
    if "codigo" in h_norm:
        score += 2
    if "imovel" in h_norm or "imovel" in h_norm:  # redundância proposital
        score += 1
    if h_norm.startswith("id"):
        score += 1
    return score

def _guess_codigo_column(headers):
    """
    Escolhe a melhor coluna de código:
    - Respeita override via config AVALIACOES_COL_CODIGO (case-insensitive)
    - Usa pontuação para decidir entre múltiplas candidatas
    - Fallback: primeira coluna que contenha 'cod'
    """
    # Override via config
    try:
        cfg = current_app.config.get("AVALIACOES_COL_CODIGO")
    except Exception:
        cfg = None
    if cfg:
        # match case-insensitive
        for h in headers:
            if _normalize_header_key(h) == _normalize_header_key(cfg) or h.strip().lower() == cfg.strip().lower():
                return h

    # Scoring
    best_h = None
    best_score = -1
    for h in headers:
        hn = _normalize_header_key(h)
        s = _score_codigo_header(hn)
        if s > best_score:
            best_h, best_score = h, s

    if best_h and best_score > 0:
        return best_h

    # Fallback 1: contém "cod"
    for h in headers:
        if re.search(r"cod", h, re.IGNORECASE):
            return h

    # Fallback 2: contém "id"
    for h in headers:
        if re.search(r"\bid\b", _normalize_header_key(h)):
            return h

    return None


# ===================== AGREGADORES DE AVALIAÇÃO =====================

def _log_codigo_samples(rows, col_codigo, codigo):
    log = _get_logger()
    try:
        sample_raw = [rows[i].get(col_codigo, "") for i in range(min(20, len(rows)))]
        sample_norm = list({_normalize_codigo(x) for x in sample_raw if str(x).strip() != ""})
        sample_digits = list({_only_digits(x) for x in sample_raw if str(x).strip() != ""})
        log.info(f"[codigo] col='{col_codigo}' | exemplos_raw={sample_raw[:10]}")
        log.info(f"[codigo] exemplos_norm={sample_norm[:10]} | exemplos_digits={sample_digits[:10]} | "
                 f"codigo_busca='{codigo}' norm='{_normalize_codigo(codigo)}' digits='{_only_digits(codigo)}'")
    except Exception:
        pass

def _find_matches(rows, col_codigo: str, codigo: str) -> List[int]:
    """
    Retorna índices das linhas cujo código casa.
    Se der 0, tenta colunas alternativas que pareçam código.
    """
    idxs = [i for i, r in enumerate(rows) if _codigo_matches(r.get(col_codigo), codigo)]
    if idxs:
        return idxs

    # tentar colunas alternativas
    headers = list(rows[0].keys()) if rows else []
    candidates = []
    for h in headers:
        if h == col_codigo:
            continue
        hn = _normalize_header_key(h)
        s = _score_codigo_header(hn)
        if s > 0 or "cod" in hn or hn.startswith("id"):
            candidates.append(h)

    alt_idxs = []
    for h in candidates:
        hits = [i for i, r in enumerate(rows) if _codigo_matches(r.get(h), codigo)]
        if hits:
            alt_idxs = hits
            _get_logger().info(f"[match] Sem match em '{col_codigo}'. Casou pela coluna alternativa '{h}' (hits={len(hits)}).")
            return alt_idxs

    return idxs  # vazio


def _per_registro_medias_e_cols(codigo: str) -> Tuple[List[float], List[str], int]:
    log = _get_logger()
    load_avaliacoes_base()
    rows = _AVAL_CACHE["rows"]; headers = _AVAL_CACHE["headers"]
    if not rows or not headers:
        return [], [], 0

    col_codigo = _guess_codigo_column(headers)
    if not col_codigo:
        log.info("[_per_registro_medias_e_cols] Nenhuma coluna de código identificada.")
        return [], [], 0

    log.info(f"[_per_registro_medias_e_cols] col_codigo='{col_codigo}' | headers={headers}")
    _log_codigo_samples(rows, col_codigo, codigo)

    cand_cols = _candidate_avaliacao_columns(headers)
    if not cand_cols:
        numeric_cols = []
        for h in headers:
            if h == col_codigo:
                continue
            cnt_num = 0; cnt_tot = 0
            for r in rows[:50]:
                v = r.get(h, "")
                if v not in (None, ""):
                    cnt_tot += 1
                    if _is_number(v):
                        cnt_num += 1
            if cnt_tot > 0 and cnt_num / max(cnt_tot, 1) > 0.6:
                numeric_cols.append(h)
        cand_cols = numeric_cols

    lista = []

    match_idxs = _find_matches(rows, col_codigo, codigo)
    match = len(match_idxs)

    for i in match_idxs:
        r = rows[i]
        notas = []
        for c in cand_cols:
            v = r.get(c, "")
            if v not in (None, "") and _is_number(v):
                notas.append(_to_float(v))
        if notas:
            lista.append(float(np.nanmean(notas)))

    log.info(f"[_per_registro_medias_e_cols] codigo={codigo} | match={match} | colunas={cand_cols} | registros_com_nota={len(lista)}")
    return lista, cand_cols, match

def get_media_avaliacao_por_codigo(codigo: str) -> Optional[Tuple[float, int, List[float]]]:
    lista, _, _ = _per_registro_medias_e_cols(codigo)
    if not lista:
        return None
    media = float(np.nanmean(lista))
    return (media, len(lista), lista)

def get_media_por_campo(codigo: str) -> Optional[Dict[str, Tuple[float, int]]]:
    log = _get_logger()
    load_avaliacoes_base()
    rows = _AVAL_CACHE["rows"]; headers = _AVAL_CACHE["headers"]
    if not rows or not headers:
        return None

    col_codigo = _guess_codigo_column(headers)
    if not col_codigo:
        log.info("[get_media_por_campo] Nenhuma coluna de código identificada.")
        return None

    cand_cols = _candidate_avaliacao_columns(headers)
    if not cand_cols:
        cand_cols = []
        for h in headers:
            if h == col_codigo:
                continue
            cnt_num = 0; cnt_tot = 0
            for r in rows[:50]:
                v = r.get(h, "")
                if v not in (None, ""):
                    cnt_tot += 1
                    if _is_number(v):
                        cnt_num += 1
            if cnt_tot > 0 and cnt_num / max(cnt_tot, 1) > 0.6:
                cand_cols.append(h)

    if not cand_cols:
        return None

    dados = {c: [] for c in cand_cols}

    match_idxs = _find_matches(rows, col_codigo, codigo)
    match = len(match_idxs)

    for i in match_idxs:
        r = rows[i]
        for c in cand_cols:
            v = r.get(c, "")
            if v not in (None, "") and _is_number(v):
                dados[c].append(_to_float(v))

    log.info(f"[get_media_por_campo] codigo={codigo} | match={match} | cols={cand_cols}")

    out = {}
    ok = False
    for c, vals in dados.items():
        if vals:
            out[c] = (float(np.nanmean(vals)), len(vals))
            ok = True
    return out if ok else None


# ===================== PREÇO N10 & CAMPOS ESPECÍFICOS =====================

def _detect_preco_n10_column(headers: List[str]) -> Optional[str]:
    norm = {h: _normalize_header_key(h) for h in headers}
    for h, n in norm.items():
        if n == "preco_n10" or n == "preco n10":
            return h
    for h, n in norm.items():
        if "preco" in n and "n10" in n:
            return h
    for h in headers:
        n = _normalize_header_key(h.replace("ç", "c").replace("Ç", "C"))
        if "preco" in n and "n10" in n:
            return h
    return None

def _detect_preco_column(headers: List[str]) -> Optional[str]:
    norm = {h: _normalize_header_key(h) for h in headers}
    candidates = []
    for h, n in norm.items():
        if "preco" in n and "n10" not in n:
            candidates.append(h)
    exact = [h for h in candidates if _normalize_header_key(h) in ("preco",)]
    if exact:
        return exact[0]
    return candidates[0] if candidates else None

def _detect_by_tokens(headers: List[str], *tokens: str) -> Optional[str]:
    """
    Encontra uma coluna cujo nome normalizado contenha TODOS os tokens.
    """
    norm = {h: _normalize_header_key(h) for h in headers}
    for h, n in norm.items():
        if all(tok in n for tok in tokens):
            return h
    return None

_CAMPOS_SOLICITADOS = [
    ("Localizacao",          ["localizacao"]),
    ("Tamanho",              ["tamanho"]),
    ("Planta_Imovel",        ["planta", "imovel"]),
    ("Qualidade_Acabamento", ["qualidade", "acabamento"]),
    ("Estado_Conservacao",   ["estado", "conservacao"]),
    ("Condominio_AreaComun", ["condominio", "area", "com"]),
    ("Preco",                ["preco"]),
    ("Preco_N10",            ["preco", "n10"]),
]

def get_medias_especificas(codigo: str) -> List[Tuple[str, Optional[float], int]]:
    """
    Retorna lista na ordem dos campos solicitados:
    [(rotulo, media_or_None, qtd), ...]
    """
    log = _get_logger()
    load_avaliacoes_base()
    rows = _AVAL_CACHE["rows"]; headers = _AVAL_CACHE["headers"]
    if not rows or not headers:
        return [(lbl, None, 0) for (lbl, _) in _CAMPOS_SOLICITADOS]

    col_codigo = _guess_codigo_column(headers)
    if not col_codigo:
        log.info("[get_medias_especificas] Nenhuma coluna de código identificada.")
        return [(lbl, None, 0) for (lbl, _) in _CAMPOS_SOLICITADOS]

    # mapear headers encontrados
    encontrados: Dict[str, Optional[str]] = {}
    for lbl, toks in _CAMPOS_SOLICITADOS:
        if lbl == "Preco_N10":
            encontrados[lbl] = _detect_preco_n10_column(headers)
        elif lbl == "Preco":
            encontrados[lbl] = _detect_preco_column(headers)
        else:
            encontrados[lbl] = _detect_by_tokens(headers, *toks)

    log.info("[get_medias_especificas] mapeamento: " + ", ".join(f"{k}=>{v}" for k,v in encontrados.items()))
    log.info(f"[get_medias_especificas] col_codigo='{col_codigo}'")

    resultados: List[Tuple[str, Optional[float], int]] = []

    match_idxs = _find_matches(rows, col_codigo, codigo)
    log.info(f"[get_medias_especificas] codigo={codigo} | match={len(match_idxs)}")

    for lbl, _toks in _CAMPOS_SOLICITADOS:
        col = encontrados.get(lbl)
        if not col:
            resultados.append((lbl, None, 0))
            continue
        vals = []
        for i in match_idxs:
            v = rows[i].get(col, "")
            if v not in (None, "") and _is_number(v):
                vals.append(_to_float(v))
        if vals:
            resultados.append((lbl, float(np.nanmean(vals)), len(vals)))
        else:
            resultados.append((lbl, None, 0))
        _get_logger().debug(f"[get_medias_especificas] {lbl}: col='{col}' com_valor={len(vals)}")
    return resultados


# ===================== PDF base =====================

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


# ===================== helpers p/ texto & imagens =====================

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


# ===================== visuais de avaliação =====================

def desenhar_barra_nota(pdf: PDF, nota: float, minimo: float = 0.0, maximo: float = 10.0,
                        largura: float = 120.0, altura: float = 6.0):
    nota = max(minimo, min(maximo, float(nota)))
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    pdf.set_draw_color(180, 180, 180)
    pdf.rect(x0, y0, largura, altura)
    propor = 0 if maximo == minimo else (nota - minimo) / (maximo - minimo)
    pdf.set_fill_color(225, 0, 91)
    pdf.rect(x0, y0, largura * propor, altura, 'F')

    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(80, 80, 80)
    for m in range(int(minimo), int(maximo) + 1):
        tx = x0 + (largura * (m - minimo) / (maximo - minimo))
        pdf.line(tx, y0 + altura, tx, y0 + altura + 1.5)
        if m % 2 == 0:
            pdf.set_xy(tx - 1.5, y0 + altura + 2)
            pdf.cell(3, 3, str(m), 0, 0, "C")
    pdf.ln(altura + 7)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(0, 0, 0)
    _safe_multicell(pdf, f"Média geral: {nota:.2f} (escala 0-10)", h=6, align="L")

def desenhar_tabela(pdf: PDF, rows: List[Tuple[str, Optional[float], int]],
                    header=("Campo", "Média", "Qtd."), widths=(90, 30, 25)):
    """
    rows: [(label, media or None, qtd)]
    """
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

        nome = label
        if len(nome) > 60:
            nome = nome[:57] + "..."
        val = "N/A" if media is None or (isinstance(media, float) and not np.isfinite(media)) else f"{media:.2f}"
        pdf.cell(widths[0], 7, latin1_safe(nome, "tabela.campo"), 1, 0, "L")
        pdf.cell(widths[1], 7, latin1_safe(val, "tabela.media"), 1, 0, "C")
        pdf.cell(widths[2], 7, latin1_safe(str(qtd), "tabela.qtd"), 1, 1, "C")


# ===================== geração do PDF =====================

def gerar_pdf_relatorio(rowdict: dict) -> bytes:
    log = _get_logger()

    cores_views = ["#e1005b", "#f59ab5"]
    cores_leads = ["#e1005b", "#ff7f50", "#a64ca6"]
    cores_pizza = cores_leads

    views_values = [
        num_or_zero(rowdict.get("Views DF", 0)),
        num_or_zero(rowdict.get("Views OLX/ZAP", 0)),
    ]
    views_labels = ["Views DF", "Views OLX/ZAP"]

    leads_values_inicial = [
        num_or_zero(rowdict.get("Leads DF", 0)),
        num_or_zero(rowdict.get("Leads OLX/ZAP", 0)),
        num_or_zero(rowdict.get("Leads C2S - Imoview", 0)),
    ]
    leads_labels_inicial = ["Leads DF", "Leads OLX/ZAP", "Leads C2S - Imoview"]

    pares_filtrados = [
        (valor, label)
        for valor, label in zip(leads_values_inicial, leads_labels_inicial)
        if valor != 0
    ]
    if pares_filtrados:
        leads_values, leads_labels = map(list, zip(*pares_filtrados))
    else:
        leads_values, leads_labels = [], []

    views_chart_path = "views_chart.jpg"
    leads_chart_path = "leads_chart.jpg"
    pie_chart_path = None

    try:
        # gráficos
        plt.figure(figsize=(8, 4))
        plt.bar(views_labels, views_values, color=cores_views)
        plt.ylabel("Quantidade de Views")
        plt.title("Comparativo de Visualizações por Portal")
        for i, v in enumerate(views_values):
            plt.text(i, v + 0.5, str(int(v)), ha="center", fontweight="bold")
        plt.tight_layout()
        plt.savefig(views_chart_path, format="jpg", dpi=150)
        plt.close()

        plt.figure(figsize=(8, 4))
        plt.bar(leads_labels, leads_values, color=cores_leads)
        plt.ylabel("Quantidade de Leads")
        plt.title("Comparativo de Leads por Fonte")
        for i, v in enumerate(leads_values):
            plt.text(i, v + 0.5, str(int(v)), ha="center", fontweight="bold")
        plt.tight_layout()
        plt.savefig(leads_chart_path, format="jpg", dpi=150)
        plt.close()

        if sum(leads_values) > 0:
            pie_chart_path = "pie_chart.jpg"
            plt.figure(figsize=(7, 7))
            plt.pie(leads_values, labels=leads_labels, autopct="%1.1f%%", startangle=90, colors=cores_pizza)
            plt.title("Distribuição de Leads por Fonte")
            plt.axis("equal")
            plt.tight_layout()
            plt.savefig(pie_chart_path, format="jpg", dpi=150)
            plt.close()

        # PDF
        logo_file = current_app.config.get("LOGO_FILE", "../utils/asserts/img/Logo 61 Vazado (1).png")
        pdf = PDF(logo_file=logo_file)
        pdf.add_page()

        codigo = rowdict.get("Código do Imóvel", "")
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
                    _safe_multicell(pdf, f"Base: {qtd} avaliação(ões) registrada(s) para este imóvel.")
                    desenhar_barra_nota(pdf, float(media_geral), minimo=0.0, maximo=10.0, largura=130.0, altura=6.0)
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

        # ===================== INFORMAÇÕES =====================
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

        # ===================== VIEWS / LEADS =====================
        pdf.chapter_title("Análise de Visualizações (Views)")
        add_image_auto(pdf, views_chart_path, max_w=180, max_h=90, center=True)
        pdf.chapter_body("Comparação de visualizações nos portais disponíveis.")

        pdf.chapter_title("Análise de Contatos (Leads)")
        add_image_auto(pdf, leads_chart_path, max_w=180, max_h=90, center=True)
        pdf.chapter_body("Leads gerados por fonte, indicando canais com melhor desempenho.")

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
    Erro/validação: dict + status (Flask-RESTX serializa).
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
