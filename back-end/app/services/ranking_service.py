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

        # 4) resolve nome pelo ID via Dim_Corretor
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
    # Calculations (VGV/VGC algoritmo + Captacao/Visitas)
    # =========================================================
    def _limpar_nome(self, n: Any) -> str:
        if pd.isna(n) or str(n).strip() in ["", "-", "nan", "NAN", "None"]:
            return ""
        return str(n).strip().upper()

    def _calc_vgv_geral_algoritmo(self, vendas: pd.DataFrame) -> pd.DataFrame:
        """
        VGV geral:
        - por contrato: junta venda + captação (nomes únicos)
        - cada pessoa conta 1 vez no contrato com Valor_Negocio
        """
        if vendas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = vendas.copy()

        cols = [
            "Corretor_Venda_1_Nome",
            "Corretor_Venda_2_Nome",
            "Corretor_Captador_1_Nome",
            "Corretor_Captador_2_Nome",
        ]
        for c in cols:
            if c not in df.columns:
                df[c] = ""

        if "Valor_Negocio" not in df.columns:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df["Valor_Negocio"] = pd.to_numeric(df["Valor_Negocio"], errors="coerce").fillna(0.0)

        acc: Dict[str, float] = {}

        for _, r in df.iterrows():
            v_imovel = float(r.get("Valor_Negocio", 0.0) or 0.0)
            if v_imovel <= 0:
                continue

            v_nomes = {
                self._limpar_nome(r.get("Corretor_Venda_1_Nome")),
                self._limpar_nome(r.get("Corretor_Venda_2_Nome")),
            }
            c_nomes = {
                self._limpar_nome(r.get("Corretor_Captador_1_Nome")),
                self._limpar_nome(r.get("Corretor_Captador_2_Nome")),
            }

            v_nomes = {n for n in v_nomes if n}
            c_nomes = {n for n in c_nomes if n}
            todos = v_nomes | c_nomes

            for n in todos:
                acc[n] = acc.get(n, 0.0) + v_imovel

        if not acc:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        out = pd.DataFrame(
            [{"Id_Corretor": "", "Nome_Corretor": k, "total": float(v)} for k, v in acc.items()]
        )
        return out

    def _calc_vgc_geral_algoritmo(self, vendas: pd.DataFrame) -> pd.DataFrame:
        """
        VGC geral:
        - usa Valor_Total_61
        - converte para VGC (divide por 0.06)
        - divide 50/50 entre venda/captação se ambos existirem
        - se só um lado existir, 100% para aquele lado
        - divide igualmente entre pessoas de cada lado
        """
        if vendas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = vendas.copy()

        cols = [
            "Corretor_Venda_1_Nome",
            "Corretor_Venda_2_Nome",
            "Corretor_Captador_1_Nome",
            "Corretor_Captador_2_Nome",
            "Valor_Total_61",
        ]
        for c in cols:
            if c not in df.columns:
                df[c] = 0.0 if c == "Valor_Total_61" else ""

        df["Valor_Total_61"] = pd.to_numeric(df["Valor_Total_61"], errors="coerce").fillna(0.0)

        acc: Dict[str, float] = {}

        for _, r in df.iterrows():
            v_comissao_total = float(r.get("Valor_Total_61", 0.0) or 0.0)

            # converte para "VGC" (mesma regra que você pediu)
            v_comissao_total = v_comissao_total / 0.06

            if v_comissao_total <= 0:
                continue

            v_nomes = {
                self._limpar_nome(r.get("Corretor_Venda_1_Nome")),
                self._limpar_nome(r.get("Corretor_Venda_2_Nome")),
            }
            c_nomes = {
                self._limpar_nome(r.get("Corretor_Captador_1_Nome")),
                self._limpar_nome(r.get("Corretor_Captador_2_Nome")),
            }

            v_nomes = {n for n in v_nomes if n}
            c_nomes = {n for n in c_nomes if n}

            tem_venda = len(v_nomes) > 0
            tem_capt = len(c_nomes) > 0

            if tem_venda and tem_capt:
                parcela_venda = v_comissao_total * 0.5
                parcela_capt = v_comissao_total * 0.5
            elif tem_venda and not tem_capt:
                parcela_venda = v_comissao_total
                parcela_capt = 0.0
            elif tem_capt and not tem_venda:
                parcela_venda = 0.0
                parcela_capt = v_comissao_total
            else:
                parcela_venda = 0.0
                parcela_capt = 0.0

            if tem_venda and parcela_venda:
                por_vendedor = parcela_venda / len(v_nomes)
                for n in v_nomes:
                    acc[n] = acc.get(n, 0.0) + por_vendedor

            if tem_capt and parcela_capt:
                por_captador = parcela_capt / len(c_nomes)
                for n in c_nomes:
                    acc[n] = acc.get(n, 0.0) + por_captador

        if not acc:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        out = pd.DataFrame(
            [{"Id_Corretor": "", "Nome_Corretor": k, "total": float(v)} for k, v in acc.items()]
        )
        return out

    def _calc_captacao_rank(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        """
        Ranking de captação:
          - lê Fato_Captacao
          - explode Captador1/2/3
          - conta 1 por linha (captação) por captador
        Saída: DataFrame com colunas [Id_Corretor, Nome_Corretor, total]
        """
        df = self.load_captacao(start, end)
        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        corretores = self.get_corretores()
        name_to_id = {
            str(c.get("nome_corretor", "")).strip().upper(): str(c.get("id_corretor", "")).strip().upper()
            for c in corretores
            if str(c.get("nome_corretor", "")).strip() and str(c.get("id_corretor", "")).strip()
        }

        rows = []
        for c in ["Captador1", "Captador2", "Captador3"]:
            if c in df.columns:
                tmp = df[[c]].copy()
                tmp["Nome_Corretor"] = tmp[c].astype(str).str.strip()
                tmp = tmp[tmp["Nome_Corretor"].ne("") & tmp["Nome_Corretor"].str.lower().ne("nan")]
                if not tmp.empty:
                    rows.append(tmp[["Nome_Corretor"]])

        if not rows:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        x = pd.concat(rows, ignore_index=True)
        x["Nome_Corretor"] = x["Nome_Corretor"].astype(str).str.strip()
        x["Nome_Corretor_UP"] = x["Nome_Corretor"].str.upper()

        agg = x.groupby("Nome_Corretor_UP", as_index=False).size()
        agg = agg.rename(columns={"Nome_Corretor_UP": "Nome_Corretor", "size": "total"})
        agg["Id_Corretor"] = agg["Nome_Corretor"].map(lambda n: name_to_id.get(str(n).strip().upper(), ""))

        agg["Nome_Corretor"] = agg["Nome_Corretor"].astype(str).str.strip()
        agg["total"] = pd.to_numeric(agg["total"], errors="coerce").fillna(0).astype(float)
        return agg[["Id_Corretor", "Nome_Corretor", "total"]]

    def _calc_visitas_rank(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        """
        Ranking de visitas:
          - lê Fato_Visitas
          - usa Id_Corretor quando existir, senão agrupa por Nome_Corretor
        Saída: DataFrame com colunas [Id_Corretor, Nome_Corretor, total]
        """
        df = self.load_visitas(start, end)
        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = df.copy()
        df["Id_Corretor"] = df.get("Id_Corretor", "").astype(str).fillna("").str.strip().str.upper()
        df["Nome_Corretor"] = df.get("Nome_Corretor", "").astype(str).fillna("").str.strip()

        if (df["Id_Corretor"].ne("")).any():
            agg = df.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False).size()
            agg = agg.rename(columns={"size": "total"})
        else:
            df = df[df["Nome_Corretor"].ne("") & df["Nome_Corretor"].str.lower().ne("nan")]
            if df.empty:
                return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])
            agg = df.groupby(["Nome_Corretor"], as_index=False).size()
            agg = agg.rename(columns={"size": "total"})
            agg["Id_Corretor"] = ""

        agg["total"] = pd.to_numeric(agg["total"], errors="coerce").fillna(0).astype(float)
        return agg[["Id_Corretor", "Nome_Corretor", "total"]]

    # =========================================================
    # Public: Rankings (AGORA COM CAPTAÇÃO E VISITAS)
    # =========================================================
    def get_all_rankings(
        self,
        start: Optional[str],
        end: Optional[str],
        limit: int = 100,
        include_pending: bool = False
    ) -> Dict[str, Any]:
        """
        Retorna rankings principais (geral AC+PP juntos):
        - vgv / vgv_geral
        - vgc / vgc_geral
        - captacao / captacoes
        - visitas / visitas_rank
        """
        vendas = self.load_vendas(start, end)

        df_vgv = pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])
        df_vgc = pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        warnings: List[str] = []

        if vendas.empty:
            warnings.append("Base de vendas vazia para o período.")
        else:
            df_vgv = self._calc_vgv_geral_algoritmo(vendas)
            df_vgc = self._calc_vgc_geral_algoritmo(vendas)

            for df in (df_vgv, df_vgc):
                if not df.empty:
                    df["Id_Corretor"] = df["Id_Corretor"].astype(str).fillna("").str.strip().str.upper()
                    df["Nome_Corretor"] = df["Nome_Corretor"].astype(str).fillna("").str.strip()
                    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0)

        # NOVO: captação e visitas
        df_capt = self._calc_captacao_rank(start, end)
        df_vis = self._calc_visitas_rank(start, end)

        vgv_list = self._rank_list(df_vgv, "total", "Id_Corretor", "Nome_Corretor", limit)
        vgc_list = self._rank_list(df_vgc, "total", "Id_Corretor", "Nome_Corretor", limit)
        capt_list = self._rank_list(df_capt, "total", "Id_Corretor", "Nome_Corretor", limit)
        vis_list = self._rank_list(df_vis, "total", "Id_Corretor", "Nome_Corretor", limit)

        return {
            "vgv": vgv_list,
            "vgc": vgc_list,

            "vgv_geral": vgv_list,
            "vgc_geral": vgc_list,

            # captação
            "captacao": capt_list,
            "captacoes": capt_list,  # alias (caso o front use plural)

            # visitas
            "visitas": vis_list,
            "visitas_rank": vis_list,  # alias (caso o front use outro nome)

            "meta": {
                "start": start,
                "end": end,
                "limit": limit,
                "include_pending": include_pending,
                "base_counts": {
                    "vendas": int(len(vendas)) if isinstance(vendas, pd.DataFrame) else 0,
                    "divisoes": 0,
                    "captacao": int(df_capt["total"].sum()) if not df_capt.empty else 0,
                    "visitas": int(df_vis["total"].sum()) if not df_vis.empty else 0,
                },
                "warnings": warnings,
            }
        }

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