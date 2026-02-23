# app/services/ranking_service.py
import os
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any


@dataclass
class SheetsConfig:
    SHEET_VENDAS_ID: str
    SHEET_BASE_INTELIGENCIA_ID: str
    SHEET_VISITAS_ID: str

    ABA_VENDAS: str
    ABA_DIVISAO_COMISSAO: str
    ABA_CAPTACAO: str
    ABA_VISITAS: str

    SHEET_CORRETORES_ID: str
    ABA_CORRETORES: str


class RankingService:
    """
    Rankings:
      - VGV: por participação na venda (apareceu em Venda OU Captador na mesma venda conta 1 vez)
      - VGC: soma(Comissao_Valor/0.06) por corretor (depende da Divisao_Comissao manual)
      - Captação: contagem por corretor (explode Captador1/2/3)
      - Visitas: contagem por corretor

    Extras:
      - GET contratos de 2026 (para dropdown no front)
      - POST divisão de comissão (N corretores por contrato) gravando na aba Divisao_Comissao
    """

    def __init__(self):
        self.cfg = SheetsConfig(
            SHEET_VENDAS_ID=os.getenv("GSHEET_VENDAS_ID", ""),
            SHEET_BASE_INTELIGENCIA_ID=os.getenv("GSHEET_BASE_INTELIGENCIA_ID", ""),
            SHEET_VISITAS_ID=os.getenv("GSHEET_VISITAS_ID", ""),

            ABA_VENDAS=os.getenv("GSHEET_ABA_VENDAS", "Vendas"),
            ABA_DIVISAO_COMISSAO=os.getenv("GSHEET_ABA_DIVISAO", "Divisao_Comissao"),
            ABA_CAPTACAO=os.getenv("GSHEET_ABA_CAPTACAO", "Fato_Captacao"),
            ABA_VISITAS=os.getenv("GSHEET_ABA_VISITAS", "Fato_Visitas"),

            SHEET_CORRETORES_ID=os.getenv(
                "GSHEET_CORRETORES_ID",
                os.getenv("GSHEET_BASE_INTELIGENCIA_ID", "")
            ),
            ABA_CORRETORES=os.getenv("GSHEET_ABA_CORRETORES", "Dim_Corretor"),
        )

        # service account JSON (caminho) OU JSON inline
        self.gsa_json_path = "./app/utils/asserts/credenciais.json"
        self.gsa_json_inline = os.getenv("GSA_JSON", "")

        self.VGC_RATE = float(os.getenv("VGC_TAXA", "0.06"))

    # =========================================================
    # Google Sheets client
    # =========================================================
    def _get_gspread_client(self, readonly: bool = True):
        import json
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"] if readonly else [
            "https://www.googleapis.com/auth/spreadsheets"
        ]

        if self.gsa_json_inline:
            info = json.loads(self.gsa_json_inline)
            creds = Credentials.from_service_account_info(info, scopes=scopes)
        else:
            if not self.gsa_json_path:
                raise RuntimeError("Defina GOOGLE_APPLICATION_CREDENTIALS ou GSA_JSON.")
            creds = Credentials.from_service_account_file(self.gsa_json_path, scopes=scopes)

        return gspread.authorize(creds)

    def read_sheet_df(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        """
        Lê uma aba do Google Sheets e devolve DataFrame.
        Se a aba não existir, retorna DataFrame vazio (não quebra a API).
        """
        from gspread.exceptions import WorksheetNotFound

        if not spreadsheet_id:
            return pd.DataFrame()

        gc = self._get_gspread_client(readonly=True)
        sh = gc.open_by_key(spreadsheet_id)

        try:
            ws = sh.worksheet(sheet_name)
        except WorksheetNotFound:
            return pd.DataFrame()

        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame()

        headers = [str(h).strip() for h in values[0]]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)

    # =========================================================
    # Corretores (dropdown / mapa ID->Nome)
    # =========================================================
    def get_corretores(self) -> List[Dict[str, Any]]:
        """
        Retorna lista de corretores para dropdown:
        [{ "id_corretor": "C61010", "nome_corretor": "Fulano", "team": "..." }, ...]
        """
        df = self.read_sheet_df(self.cfg.SHEET_CORRETORES_ID, self.cfg.ABA_CORRETORES)
        if df.empty:
            return []

        id_col = None
        name_col = None

        for c in ["IdCorretor", "id_corretor", "ID_CORRETOR", "ID", "Codigo", "Código", "Cod", "cod"]:
            if c in df.columns:
                id_col = c
                break

        for c in ["Nome_Corretor", "nome_corretor", "Nome", "nome", "Corretor", "corretor"]:
            if c in df.columns:
                name_col = c
                break

        if not id_col or not name_col:
            return []

        df = df.copy()
        df[id_col] = df[id_col].astype(str).str.strip()
        df[name_col] = df[name_col].astype(str).str.strip()

        df = df[df[id_col].ne("") & df[name_col].ne("")]
        df = df.drop_duplicates(subset=[id_col])

        team_col = next((c for c in ["Team", "team", "Equipe", "equipe"] if c in df.columns), None)

        out: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            item: Dict[str, Any] = {
                "id_corretor": str(r[id_col]).strip(),
                "nome_corretor": str(r[name_col]).strip(),
            }
            if team_col:
                item["team"] = str(r.get(team_col, "")).strip()
            out.append(item)

        out.sort(key=lambda x: x["nome_corretor"].lower())
        return out

    # =========================================================
    # Divisão Comissão (garantir aba + header)
    # =========================================================
    def _ensure_divisao_sheet(self, sh):
        """
        Garante que a worksheet Divisao_Comissao existe e tem cabeçalho padrão.
        Se a aba já existir com header diferente, corrige A1:H1.
        """
        from gspread.exceptions import WorksheetNotFound

        sheet_name = self.cfg.ABA_DIVISAO_COMISSAO
        try:
            ws = sh.worksheet(sheet_name)
        except WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_name, rows=2000, cols=20)

        header = [
            "Id_Contrato",
            "Papel",
            "Id_Corretor",
            "Nome_Corretor",
            "Percentual",
            "Comissao_Valor",
            "Observacao",
            "UpdatedAt",
        ]

        values = ws.get_all_values()
        if not values:
            ws.append_row(header, value_input_option="RAW")
            return ws

        first = [str(x).strip() for x in values[0]]
        if first[:len(header)] != header:
            ws.update("A1:H1", [header], value_input_option="RAW")

        return ws

    # =========================================================
    # Helpers
    # =========================================================
    @staticmethod
    def _to_float_br(x) -> float:
        if x is None:
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip()
        if not s:
            return 0.0
        s = s.replace("R$", "").strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")
        s = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
        try:
            return float(s)
        except:
            return 0.0

    @staticmethod
    def _parse_date(x) -> Optional[pd.Timestamp]:
        if x is None:
            return None
        if isinstance(x, (datetime, pd.Timestamp)):
            return pd.to_datetime(x)
        s = str(x).strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y", "%d/%m/%Y %H:%M:%S"):
            try:
                return pd.to_datetime(datetime.strptime(s, fmt))
            except:
                pass
        try:
            return pd.to_datetime(s, errors="coerce")
        except:
            return None

    def _filter_date_range(self, df: pd.DataFrame, col: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        if df.empty or col not in df.columns:
            return df
        df = df.copy()
        df[col] = df[col].apply(self._parse_date)
        df = df[df[col].notna()]
        if start:
            df = df[df[col] >= pd.to_datetime(start)]
        if end:
            df = df[df[col] <= pd.to_datetime(end)]
        return df

    @staticmethod
    def _rank_list(df: pd.DataFrame, total_col: str, id_col: str, name_col: str, limit: int) -> List[Dict[str, Any]]:
        if df.empty:
            return []
        df = df.sort_values(total_col, ascending=False).head(limit).reset_index(drop=True)
        out = []
        for i, row in df.iterrows():
            out.append({
                "posicao": int(i + 1),
                "id_corretor": str(row.get(id_col, "")).strip(),
                "corretor": str(row.get(name_col, "")).strip(),
                "total": float(row.get(total_col, 0.0) or 0.0),
            })
        return out

    # =========================================================
    # Load bases
    # =========================================================
    def load_vendas(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_VENDAS_ID, self.cfg.ABA_VENDAS)
        if df.empty:
            return df

        must = ["Id_Contrato", "Data_Contrato", "Valor_Negocio"]
        for c in must:
            if c not in df.columns:
                return pd.DataFrame()

        df = df.copy()
        df["Id_Contrato"] = df["Id_Contrato"].astype(str).str.strip()
        df["Valor_Negocio"] = df["Valor_Negocio"].apply(self._to_float_br)

        if "Valor_Total_61" in df.columns:
            df["Valor_Total_61"] = df["Valor_Total_61"].apply(self._to_float_br)
        else:
            df["Valor_Total_61"] = 0.0

        df = self._filter_date_range(df, "Data_Contrato", start, end)
        return df

    def load_divisoes(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_VENDAS_ID, self.cfg.ABA_DIVISAO_COMISSAO)
        if df.empty:
            return pd.DataFrame(columns=[
                "Id_Contrato", "Papel", "Id_Corretor", "Nome_Corretor", "Percentual", "Comissao_Valor"
            ])

        must = ["Id_Contrato", "Papel", "Nome_Corretor"]
        for c in must:
            if c not in df.columns:
                return pd.DataFrame(columns=[
                    "Id_Contrato", "Papel", "Id_Corretor", "Nome_Corretor", "Percentual", "Comissao_Valor"
                ])

        df = df.copy()
        df["Id_Contrato"] = df["Id_Contrato"].astype(str).str.strip()
        df["Papel"] = df["Papel"].astype(str).str.strip().str.upper()
        df["Nome_Corretor"] = df["Nome_Corretor"].astype(str).str.strip()

        if "Percentual" in df.columns:
            df["Percentual"] = df["Percentual"].apply(self._to_float_br)
        else:
            df["Percentual"] = 0.0

        if "Comissao_Valor" in df.columns:
            df["Comissao_Valor"] = df["Comissao_Valor"].apply(self._to_float_br)
        else:
            df["Comissao_Valor"] = 0.0

        if "Id_Corretor" not in df.columns:
            df["Id_Corretor"] = ""

        if "UpdatedAt" in df.columns:
            df = self._filter_date_range(df, "UpdatedAt", start, end)

        return df

    def load_captacao(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_BASE_INTELIGENCIA_ID, self.cfg.ABA_CAPTACAO)
        if df.empty:
            return df

        if "DataEntrada" not in df.columns:
            return pd.DataFrame()

        df = df.copy()
        df = self._filter_date_range(df, "DataEntrada", start, end)

        for c in ["Captador1", "Captador2", "Captador3"]:
            if c not in df.columns:
                df[c] = ""
            df[c] = df[c].astype(str).str.strip()

        return df

    def load_visitas(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        """
        IMPORTANTÍSSIMO:
        - Se Fato_Visitas tiver Id_Corretor (como no seu modelo), resolve Nome_Corretor via Dim_Corretor.
        - Assim o ranking de visitas sempre mostra o nome correto no front.
        """
        df = self.read_sheet_df(self.cfg.SHEET_VISITAS_ID, self.cfg.ABA_VISITAS)
        if df.empty:
            return df

        df = df.copy()

        # 1) achar coluna de data
        date_col = None
        for c in ["Data_Visita", "Data", "data", "DATA", "CreatedAt"]:
            if c in df.columns:
                date_col = c
                break
        if not date_col:
            return pd.DataFrame()

        df = self._filter_date_range(df, date_col, start, end)

        # 2) achar coluna de ID do corretor
        id_col = None
        for c in ["Id_Corretor", "id_corretor", "ID_CORRETOR", "IdCorretor", "idCorretor"]:
            if c in df.columns:
                id_col = c
                break

        # fallback (se não existir id)
        if not id_col:
            # tenta usar nome direto
            name_col = None
            for c in ["Nome_Corretor", "nome_corretor", "Corretor", "corretor", "Nome", "nome"]:
                if c in df.columns:
                    name_col = c
                    break
            if not name_col:
                return pd.DataFrame()

            df["Id_Corretor"] = ""
            df["Nome_Corretor"] = df[name_col].astype(str).str.strip()
            return df

        # normaliza ID
        df["Id_Corretor"] = df[id_col].astype(str).str.strip().str.upper()

        # 3) nome na própria fato (se existir)
        name_col = None
        for c in ["Nome_Corretor", "nome_corretor", "Corretor", "corretor", "Nome", "nome", "Corretor_Nome", "corretor_nome"]:
            if c in df.columns:
                name_col = c
                break

        if name_col:
            df["Nome_Corretor"] = df[name_col].astype(str).str.strip()
        else:
            df["Nome_Corretor"] = ""

        # 4) resolve nome pelo ID via Dim_Corretor (mesmo esquema da captação)
        corretores = self.get_corretores()  # [{id_corretor, nome_corretor, ...}]
        id_to_name = {
            str(c.get("id_corretor", "")).strip().upper(): str(c.get("nome_corretor", "")).strip()
            for c in corretores
            if str(c.get("id_corretor", "")).strip() and str(c.get("nome_corretor", "")).strip()
        }

        def _resolve_nome(row):
            nome = str(row.get("Nome_Corretor", "")).strip()
            if nome and nome.lower() != "nan":
                return nome
            _id = str(row.get("Id_Corretor", "")).strip().upper()
            return id_to_name.get(_id, "")

        df["Nome_Corretor"] = df.apply(_resolve_nome, axis=1)

        return df

    # =========================================================
    # Calculations
    # =========================================================
    def _calc_vgc(self, divs: pd.DataFrame) -> pd.DataFrame:
        if divs.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = divs.copy()
        df["Comissao_Valor"] = pd.to_numeric(df["Comissao_Valor"], errors="coerce").fillna(0.0)
        df["VGC"] = df["Comissao_Valor"] / float(self.VGC_RATE)

        out = (
            df.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False)["VGC"]
            .sum()
            .rename(columns={"VGC": "total"})
        )
        return out

    def _calc_vgv(self, vendas: pd.DataFrame, divs: pd.DataFrame, include_pending: bool) -> pd.DataFrame:
        if vendas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = vendas.copy()

        cols_corretor = [
            "Corretor_Venda_1_Nome",
            "Corretor_Venda_2_Nome",
            "Corretor_Captador_1_Nome",
            "Corretor_Captador_2_Nome",
        ]
        for c in cols_corretor:
            if c not in df.columns:
                df[c] = ""
            df[c] = df[c].astype(str).str.strip()

        if "Id_Contrato" not in df.columns or "Valor_Negocio" not in df.columns:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df["Id_Contrato"] = df["Id_Contrato"].astype(str).str.strip()
        df["Valor_Negocio"] = pd.to_numeric(df["Valor_Negocio"], errors="coerce").fillna(0.0)

        rows = []
        for _, r in df.iterrows():
            id_contrato = str(r["Id_Contrato"]).strip()
            if not id_contrato:
                continue

            vgv = float(r["Valor_Negocio"] or 0.0)
            if vgv <= 0:
                continue

            corretores = set()
            for c in cols_corretor:
                nome = str(r.get(c, "")).strip()
                if not nome or nome.lower() == "nan":
                    continue
                corretores.add(nome)

            for nome in corretores:
                rows.append([id_contrato, nome, vgv])

        if not rows:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        exploded = pd.DataFrame(rows, columns=["Id_Contrato", "Nome_Corretor", "Valor_Negocio"])
        out = (
            exploded.groupby("Nome_Corretor", as_index=False)["Valor_Negocio"]
            .sum()
            .rename(columns={"Valor_Negocio": "total"})
        )
        out["Id_Corretor"] = ""
        return out[["Id_Corretor", "Nome_Corretor", "total"]]

    def _calc_captacao(
        self,
        capt: pd.DataFrame,
        id_to_name: Optional[Dict[str, str]] = None,
        name_to_id: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        if capt.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        id_to_name = id_to_name or {}
        name_to_id = name_to_id or {}

        rows = []
        for _, r in capt.iterrows():
            for c in ["Captador1", "Captador2", "Captador3"]:
                raw = str(r.get(c, "")).strip()
                if not raw or raw.lower() == "nan":
                    continue

                raw_norm = raw.strip().upper()

                if raw_norm in id_to_name:
                    _id = raw_norm
                    _nome = id_to_name[raw_norm]
                else:
                    _nome = raw
                    _id = name_to_id.get(raw, "")

                rows.append((_id, _nome))

        if not rows:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = pd.DataFrame(rows, columns=["Id_Corretor", "Nome_Corretor"])

        out = (
            df.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False)
            .size()
            .rename(columns={"size": "total"})
        )

        out["Id_Corretor"] = out["Id_Corretor"].astype(str).fillna("").str.strip()
        out["Nome_Corretor"] = out["Nome_Corretor"].astype(str).fillna("").str.strip()

        return out[["Id_Corretor", "Nome_Corretor", "total"]]

    def _calc_visitas(self, visitas: pd.DataFrame) -> pd.DataFrame:
        if visitas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = visitas.copy()

        if "Id_Corretor" not in df.columns:
            df["Id_Corretor"] = ""
        if "Nome_Corretor" not in df.columns:
            df["Nome_Corretor"] = ""

        # padroniza (evita chave duplicada por espaço/caixa)
        df["Id_Corretor"] = df["Id_Corretor"].astype(str).str.strip().str.upper()
        df["Nome_Corretor"] = df["Nome_Corretor"].astype(str).str.strip()

        # se ainda tiver nome vazio, tenta resolver pelo ID (de novo, como segurança)
        if (df["Nome_Corretor"].eq("") | df["Nome_Corretor"].str.lower().eq("nan")).any():
            corretores = self.get_corretores()
            id_to_name = {
                str(c.get("id_corretor", "")).strip().upper(): str(c.get("nome_corretor", "")).strip()
                for c in corretores
                if str(c.get("id_corretor", "")).strip() and str(c.get("nome_corretor", "")).strip()
            }
            def _fix_name(row):
                n = str(row.get("Nome_Corretor", "")).strip()
                if n and n.lower() != "nan":
                    return n
                return id_to_name.get(str(row.get("Id_Corretor", "")).strip().upper(), "")
            df["Nome_Corretor"] = df.apply(_fix_name, axis=1)

        out = (
            df.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False)
            .size()
            .rename(columns={"size": "total"})
        )
        return out

    # =========================================================
    # Public: Rankings
    # =========================================================
    def get_all_rankings(
        self,
        start: Optional[str],
        end: Optional[str],
        limit: int = 100,
        include_pending: bool = False
    ) -> Dict[str, Any]:
        vendas = self.load_vendas(start, end)
        divs = self.load_divisoes(start, end)
        capt = self.load_captacao(start, end)
        visitas = self.load_visitas(start, end)

        # Se tiver Percentual e a Comissao_Valor estiver vazia, calcula usando Valor_Total_61 da venda (quando existir)
        if not divs.empty and not vendas.empty:
            vendas_map = vendas.set_index("Id_Contrato")["Valor_Total_61"].to_dict()

            mask = (pd.to_numeric(divs["Comissao_Valor"], errors="coerce").fillna(0.0) <= 0) & (
                pd.to_numeric(divs["Percentual"], errors="coerce").fillna(0.0) > 0
            )

            if mask.any():
                def _calc_row(r):
                    total = float(vendas_map.get(str(r["Id_Contrato"]).strip(), 0.0) or 0.0)
                    perc = float(r["Percentual"] or 0.0)
                    return total * (perc / 100.0)

                divs = divs.copy()
                divs.loc[mask, "Comissao_Valor"] = divs.loc[mask].apply(_calc_row, axis=1)

        df_vgc = self._calc_vgc(divs)
        df_vgv = self._calc_vgv(vendas, divs, include_pending=include_pending)

        corretores = self.get_corretores()
        id_to_name: Dict[str, str] = {}
        name_to_id: Dict[str, str] = {}
        for c in corretores:
            _id = str(c.get("id_corretor", "")).strip().upper()
            _nome = str(c.get("nome_corretor", "")).strip()
            if _id and _nome:
                id_to_name[_id] = _nome
                name_to_id[_nome] = _id

        df_cap = self._calc_captacao(capt, id_to_name=id_to_name, name_to_id=name_to_id)
        df_vis = self._calc_visitas(visitas)

        for df in [df_vgc, df_vgv, df_cap, df_vis]:
            if not df.empty:
                df["Id_Corretor"] = df["Id_Corretor"].astype(str).fillna("").str.strip().str.upper()
                df["Nome_Corretor"] = df["Nome_Corretor"].astype(str).fillna("").str.strip()
                df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0)

        result = {
            "vgv": self._rank_list(df_vgv, "total", "Id_Corretor", "Nome_Corretor", limit),
            "vgc": self._rank_list(df_vgc, "total", "Id_Corretor", "Nome_Corretor", limit),
            "captacao": self._rank_list(df_cap, "total", "Id_Corretor", "Nome_Corretor", limit),
            "visitas": self._rank_list(df_vis, "total", "Id_Corretor", "Nome_Corretor", limit),
            "meta": {
                "start": start,
                "end": end,
                "limit": limit,
                "include_pending": include_pending,
                "base_counts": {
                    "vendas": int(len(vendas)) if isinstance(vendas, pd.DataFrame) else 0,
                    "divisoes": int(len(divs)) if isinstance(divs, pd.DataFrame) else 0,
                    "captacao": int(len(capt)) if isinstance(capt, pd.DataFrame) else 0,
                    "visitas": int(len(visitas)) if isinstance(visitas, pd.DataFrame) else 0,
                },
                "warnings": []
            }
        }

        if divs.empty:
            result["meta"]["warnings"].append(
                f"Aba '{self.cfg.ABA_DIVISAO_COMISSAO}' não encontrada ou vazia. Ranking VGC ficará vazio até existir divisão."
            )

        return result

    # =========================================================
    # Public: Dropdown contratos 2026
    # =========================================================
    def get_contratos_2026(self) -> List[Dict[str, Any]]:
        vendas = self.load_vendas(start="2026-01-01", end="2026-12-31")
        if vendas.empty:
            return []

        df = vendas.copy()
        if "Id_Contrato" not in df.columns:
            return []

        df["Id_Contrato"] = df["Id_Contrato"].astype(str).str.strip()

        parts = []
        for col in ["Contrato", "Valor_Negocio", "Codigo_Imovel", "Endereco", "codigo", "Código"]:
            if col in df.columns:
                parts.append(df[col].astype(str).str.strip())

        if parts:
            df["display"] = df["Id_Contrato"] + " - " + parts[0]
        else:
            df["display"] = df["Id_Contrato"] + " - VGV " + df["Valor_Negocio"].astype(float).map(
                lambda x: f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

        df = df.drop_duplicates(subset=["Id_Contrato"])
        if "Data_Contrato" in df.columns:
            df = df.sort_values("Data_Contrato", ascending=False)

        return df[["Id_Contrato", "display"]].to_dict(orient="records")

    # =========================================================
    # Public: POST divisão comissão (linhas com %)
    # =========================================================
    def add_divisao_comissao(self, payload: dict) -> dict:
        id_contrato = str(payload.get("id_contrato", "")).strip()
        linhas = payload.get("linhas", [])

        if not id_contrato:
            raise ValueError("id_contrato é obrigatório.")
        if not isinstance(linhas, list) or len(linhas) == 0:
            raise ValueError("linhas deve ser uma lista com pelo menos 1 item.")

        corretores = self.get_corretores()
        name_to_id_lower = {
            str(c.get("nome_corretor", "")).strip().lower(): str(c.get("id_corretor", "")).strip().upper()
            for c in corretores
            if str(c.get("nome_corretor", "")).strip() and str(c.get("id_corretor", "")).strip()
        }

        norm = []
        for i, l in enumerate(linhas, start=1):
            papel = str(l.get("papel", "")).strip().upper()
            nome = str(l.get("nome_corretor", "")).strip()
            id_corretor = str(l.get("id_corretor", "")).strip().upper()
            obs = str(l.get("observacao", "")).strip()

            if papel not in {"VENDA", "CAPTACAO"}:
                raise ValueError(f"Linha {i}: papel inválido (use VENDA ou CAPTACAO).")
            if not nome:
                raise ValueError(f"Linha {i}: nome_corretor é obrigatório.")

            if not id_corretor and nome:
                id_corretor = name_to_id_lower.get(nome.strip().lower(), "")

            try:
                percentual = float(l.get("percentual", 0))
            except:
                raise ValueError(f"Linha {i}: percentual inválido.")

            if percentual <= 0 or percentual > 100:
                raise ValueError(f"Linha {i}: percentual deve estar entre 0 e 100.")

            norm.append({
                "papel": papel,
                "id_corretor": id_corretor,
                "nome": nome,
                "percentual": percentual,
                "obs": obs
            })

        soma_venda = sum(x["percentual"] for x in norm if x["papel"] == "VENDA")
        soma_capt = sum(x["percentual"] for x in norm if x["papel"] == "CAPTACAO")

        if soma_venda and abs(soma_venda - 100.0) > 0.0001:
            raise ValueError(f"Soma dos percentuais de VENDA deve ser 100. Atual: {soma_venda:.2f}")
        if soma_capt and abs(soma_capt - 100.0) > 0.0001:
            raise ValueError(f"Soma dos percentuais de CAPTACAO deve ser 100. Atual: {soma_capt:.2f}")

        vendas = self.load_vendas(start=None, end=None)
        valor_comissao_total = 0.0
        if not vendas.empty and "Valor_Total_61" in vendas.columns:
            row = vendas[vendas["Id_Contrato"].astype(str).str.strip() == id_contrato]
            if not row.empty:
                valor_comissao_total = float(row.iloc[0]["Valor_Total_61"] or 0.0)

        now_iso = datetime.utcnow().isoformat()

        to_append = []
        for x in norm:
            comissao_valor = 0.0
            if valor_comissao_total > 0:
                comissao_valor = valor_comissao_total * (x["percentual"] / 100.0)

            to_append.append([
                id_contrato,
                x["papel"],
                x["id_corretor"],
                x["nome"],
                x["percentual"],
                comissao_valor,
                x["obs"],
                now_iso
            ])

        gc = self._get_gspread_client(readonly=False)
        sh = gc.open_by_key(self.cfg.SHEET_VENDAS_ID)
        ws = self._ensure_divisao_sheet(sh)

        ws.append_rows(to_append, value_input_option="USER_ENTERED")

        return {
            "ok": True,
            "id_contrato": id_contrato,
            "linhas_inseridas": len(to_append),
            "valor_comissao_total": valor_comissao_total
        }