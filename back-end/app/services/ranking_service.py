# app/services/ranking_service.py
import os
import json
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any, Set


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
    Regras oficiais:

    VGV:
      - por contrato: junta VENDA + CAPTACAO
      - remove duplicidade de nome no mesmo contrato
      - cada corretor recebe 1x o Valor_Negocio

    VGC:
      - usa Valor_Total_61 BRUTO
      - se houver venda e captação: 50% para cada lado
      - se houver só um lado: 100% para esse lado
      - divide igualmente entre os nomes de cada lado
      - NÃO divide por 0.06 no ranking

    Captação:
      - conta ocorrências em Fato_Captacao (Captador1/2/3)

    Visitas:
      - conta ocorrências em Fato_Visitas

    Exclusão:
      - corretores podem ser excluídos por nome e/ou id
      - excluídos não entram em nenhum ranking
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

        self.gsa_json_path = "./app/utils/asserts/credenciais.json"
        self.gsa_json_inline = os.getenv("GSA_JSON", "")

        # Lista de exclusão por ENV:
        RANKING_EXCLUDED_NAMES=os.getenv("RANKING_EXCLUDED_NAMES","")
        #RANKING_EXCLUDED_IDS="C61010,C99999"
        self.excluded_names: Set[str] = self._parse_csv_env_to_set("RANKING_EXCLUDED_NAMES")
        self.excluded_ids: Set[str] = self._parse_csv_env_to_set("RANKING_EXCLUDED_IDS")

    # =========================================================
    # ENV helpers
    # =========================================================
    @staticmethod
    def _parse_csv_env_to_set(env_name: str) -> Set[str]:
        raw = os.getenv(env_name, "")
        if not raw.strip():
            return set()
        return {
            str(x).strip().upper()
            for x in raw.split(",")
            if str(x).strip()
        }

    # =========================================================
    # Google Sheets client
    # =========================================================
    def _get_gspread_client(self, readonly: bool = True):
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
                raise RuntimeError("Defina GSA_JSON ou configure o caminho do JSON de credenciais.")
            creds = Credentials.from_service_account_file(self.gsa_json_path, scopes=scopes)

        return gspread.authorize(creds)

    def read_sheet_df(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
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
    # Helpers base
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
        except Exception:
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

        for fmt in (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d/%m/%y",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                return pd.to_datetime(datetime.strptime(s, fmt))
            except Exception:
                pass

        try:
            dt = pd.to_datetime(s, errors="coerce")
            if pd.isna(dt):
                return None
            return dt
        except Exception:
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
    def _limpar_nome(n: Any) -> str:
        if pd.isna(n) or str(n).strip() in ["", "-", "nan", "NAN", "None", "NONE"]:
            return ""
        return str(n).strip().upper()

    def _is_excluded(self, nome: str = "", id_corretor: str = "") -> bool:
        nome_norm = self._limpar_nome(nome)
        id_norm = str(id_corretor or "").strip().upper()

        if nome_norm and nome_norm in self.excluded_names:
            return True
        if id_norm and id_norm in self.excluded_ids:
            return True

        return False

    @staticmethod
    def _rank_list(df: pd.DataFrame, total_col: str, id_col: str, name_col: str, limit: int) -> List[Dict[str, Any]]:
        if df.empty:
            return []

        df = df.sort_values([total_col, name_col], ascending=[False, True]).head(limit).reset_index(drop=True)

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
    # Corretores (mapa ID<->Nome)
    # =========================================================
    def get_corretores_df(self) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_CORRETORES_ID, self.cfg.ABA_CORRETORES)
        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "Team"])

        id_col = None
        name_col = None

        for c in ["IdCorretor", "Id_Corretor", "id_corretor", "ID_CORRETOR", "ID", "Codigo", "Código", "Cod", "cod"]:
            if c in df.columns:
                id_col = c
                break

        for c in ["Nome_Corretor", "nome_corretor", "Nome", "nome", "Corretor", "corretor"]:
            if c in df.columns:
                name_col = c
                break

        if not id_col or not name_col:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "Team"])

        out = df.copy()
        out["Id_Corretor"] = out[id_col].astype(str).str.strip().str.upper()
        out["Nome_Corretor"] = out[name_col].astype(str).str.strip().str.upper()

        team_col = next((c for c in ["Team", "team", "Equipe", "equipe"] if c in out.columns), None)
        if team_col:
            out["Team"] = out[team_col].astype(str).str.strip()
        else:
            out["Team"] = ""

        out = out[out["Id_Corretor"].ne("") & out["Nome_Corretor"].ne("")]
        out = out.drop_duplicates(subset=["Id_Corretor"])

        return out[["Id_Corretor", "Nome_Corretor", "Team"]]

    def get_corretores(self) -> List[Dict[str, Any]]:
        df = self.get_corretores_df()
        if df.empty:
            return []

        out = []
        for _, r in df.iterrows():
            item = {
                "id_corretor": str(r["Id_Corretor"]).strip(),
                "nome_corretor": str(r["Nome_Corretor"]).strip(),
            }
            if str(r.get("Team", "")).strip():
                item["team"] = str(r.get("Team", "")).strip()
            out.append(item)

        out.sort(key=lambda x: x["nome_corretor"])
        return out

    def _maps_corretores(self):
        df = self.get_corretores_df()
        if df.empty:
            return {}, {}

        id_to_name = {
            str(r["Id_Corretor"]).strip().upper(): str(r["Nome_Corretor"]).strip().upper()
            for _, r in df.iterrows()
        }
        name_to_id = {
            str(r["Nome_Corretor"]).strip().upper(): str(r["Id_Corretor"]).strip().upper()
            for _, r in df.iterrows()
        }
        return id_to_name, name_to_id

    # =========================================================
    # Divisão Comissão (mantido)
    # =========================================================
    def _ensure_divisao_sheet(self, sh):
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

        # normalizar colunas esperadas
        expected_people_cols = [
            "Corretor_Venda_1_Nome",
            "Corretor_Venda_2_Nome",
            "Corretor_Captador_1_Nome",
            "Corretor_Captador_2_Nome",
        ]
        for c in expected_people_cols:
            if c not in df.columns:
                df[c] = ""
            df[c] = df[c].astype(str).fillna("").str.strip()

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
        df["Nome_Corretor"] = df["Nome_Corretor"].astype(str).str.strip().str.upper()

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
            df[c] = df[c].astype(str).fillna("").str.strip()

        return df

    def load_visitas(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_VISITAS_ID, self.cfg.ABA_VISITAS)
        if df.empty:
            return df

        df = df.copy()

        date_col = None
        for c in ["Data_Visita", "Data", "data", "DATA", "CreatedAt"]:
            if c in df.columns:
                date_col = c
                break
        if not date_col:
            return pd.DataFrame()

        df = self._filter_date_range(df, date_col, start, end)

        id_col = None
        for c in ["Id_Corretor", "id_corretor", "ID_CORRETOR", "IdCorretor", "idCorretor"]:
            if c in df.columns:
                id_col = c
                break

        name_col = None
        for c in ["Nome_Corretor", "nome_corretor", "Corretor", "corretor", "Nome", "nome", "Corretor_Nome"]:
            if c in df.columns:
                name_col = c
                break

        if id_col:
            df["Id_Corretor"] = df[id_col].astype(str).fillna("").str.strip().str.upper()
        else:
            df["Id_Corretor"] = ""

        if name_col:
            df["Nome_Corretor"] = df[name_col].astype(str).fillna("").str.strip().str.upper()
        else:
            df["Nome_Corretor"] = ""

        id_to_name, _ = self._maps_corretores()

        def _resolve_nome(row):
            nome = str(row.get("Nome_Corretor", "")).strip().upper()
            if nome and nome != "NAN":
                return nome
            cid = str(row.get("Id_Corretor", "")).strip().upper()
            return id_to_name.get(cid, "")

        df["Nome_Corretor"] = df.apply(_resolve_nome, axis=1)

        return df

    # =========================================================
    # Regras de exclusão / normalização do resultado
    # =========================================================
    def _finalize_rank_df(self, acc: Dict[str, float]) -> pd.DataFrame:
        """
        acc: dict Nome_Corretor -> total
        Resolve Id_Corretor via Dim_Corretor e remove excluídos.
        """
        if not acc:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        _, name_to_id = self._maps_corretores()

        rows = []
        for nome, total in acc.items():
            nome_norm = self._limpar_nome(nome)
            if not nome_norm:
                continue

            id_corretor = name_to_id.get(nome_norm, "")

            if self._is_excluded(nome=nome_norm, id_corretor=id_corretor):
                continue

            rows.append({
                "Id_Corretor": id_corretor,
                "Nome_Corretor": nome_norm,
                "total": float(total or 0.0),
            })

        if not rows:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = pd.DataFrame(rows)
        df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0)
        df = df.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False)["total"].sum()

        return df

    # =========================================================
    # Cálculos oficiais: VGV / VGC
    # =========================================================
    def _calc_vgv_geral_algoritmo(self, vendas: pd.DataFrame) -> pd.DataFrame:
        """
        REGRA OFICIAL:
        - por contrato: junta vendedores e captadores
        - remove duplicidade
        - cada nome recebe 1x o Valor_Negocio
        """
        if vendas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        acc: Dict[str, float] = {}

        for _, row in vendas.iterrows():
            valor_imovel = float(row.get("Valor_Negocio", 0.0) or 0.0)
            if valor_imovel <= 0:
                continue

            vendedores = {
                self._limpar_nome(row.get("Corretor_Venda_1_Nome")),
                self._limpar_nome(row.get("Corretor_Venda_2_Nome")),
            }
            captadores = {
                self._limpar_nome(row.get("Corretor_Captador_1_Nome")),
                self._limpar_nome(row.get("Corretor_Captador_2_Nome")),
            }

            vendedores = {n for n in vendedores if n}
            captadores = {n for n in captadores if n}

            todos = vendedores | captadores

            for nome in todos:
                acc[nome] = acc.get(nome, 0.0) + valor_imovel

        return self._finalize_rank_df(acc)

    def _calc_vgc_geral_algoritmo(self, vendas: pd.DataFrame) -> pd.DataFrame:
        """
        REGRA OFICIAL:
        - usa Valor_Total_61 BRUTO
        - se houver venda + captação => 50% / 50%
        - se só houver um lado => 100% para aquele lado
        - divide igualmente entre os nomes do lado
        - NÃO divide por 0.06
        """
        if vendas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        acc: Dict[str, float] = {}

        for _, row in vendas.iterrows():
            valor_comissao_total = float(row.get("Valor_Total_61", 0.0) or 0.0)
            if valor_comissao_total <= 0:
                continue

            vendedores = {
                self._limpar_nome(row.get("Corretor_Venda_1_Nome")),
                self._limpar_nome(row.get("Corretor_Venda_2_Nome")),
            }
            captadores = {
                self._limpar_nome(row.get("Corretor_Captador_1_Nome")),
                self._limpar_nome(row.get("Corretor_Captador_2_Nome")),
            }

            vendedores = {n for n in vendedores if n}
            captadores = {n for n in captadores if n}

            tem_venda = len(vendedores) > 0
            tem_capt = len(captadores) > 0

            if tem_venda and tem_capt:
                parcela_venda = valor_comissao_total * 0.5
                parcela_capt = valor_comissao_total * 0.5
            elif tem_venda:
                parcela_venda = valor_comissao_total
                parcela_capt = 0.0
            elif tem_capt:
                parcela_venda = 0.0
                parcela_capt = valor_comissao_total
            else:
                parcela_venda = 0.0
                parcela_capt = 0.0

            if tem_venda and parcela_venda > 0:
                por_vendedor = parcela_venda / len(vendedores)
                for nome in vendedores:
                    acc[nome] = acc.get(nome, 0.0) + por_vendedor

            if tem_capt and parcela_capt > 0:
                por_captador = parcela_capt / len(captadores)
                for nome in captadores:
                    acc[nome] = acc.get(nome, 0.0) + por_captador

        return self._finalize_rank_df(acc)

    # =========================================================
    # Captação e visitas
    # =========================================================
    def _calc_captacao_rank(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        df = self.load_captacao(start, end)
        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        _, name_to_id = self._maps_corretores()
        rows = []

        for c in ["Captador1", "Captador2", "Captador3"]:
            if c not in df.columns:
                continue

            tmp = df[[c]].copy()
            tmp["Nome_Corretor"] = tmp[c].astype(str).fillna("").str.strip().str.upper()
            tmp = tmp[tmp["Nome_Corretor"].ne("") & tmp["Nome_Corretor"].ne("NAN")]

            if not tmp.empty:
                rows.append(tmp[["Nome_Corretor"]])

        if not rows:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        x = pd.concat(rows, ignore_index=True)
        agg = x.groupby("Nome_Corretor", as_index=False).size().rename(columns={"size": "total"})
        agg["Id_Corretor"] = agg["Nome_Corretor"].map(lambda n: name_to_id.get(str(n).strip().upper(), ""))

        # excluir
        agg = agg[
            ~agg.apply(
                lambda r: self._is_excluded(
                    nome=str(r["Nome_Corretor"]).strip().upper(),
                    id_corretor=str(r["Id_Corretor"]).strip().upper()
                ),
                axis=1
            )
        ].copy()

        agg["total"] = pd.to_numeric(agg["total"], errors="coerce").fillna(0).astype(float)

        return agg[["Id_Corretor", "Nome_Corretor", "total"]]

    def _calc_visitas_rank(self, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        df = self.load_visitas(start, end)
        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        df = df.copy()
        df["Id_Corretor"] = df["Id_Corretor"].astype(str).fillna("").str.strip().str.upper()
        df["Nome_Corretor"] = df["Nome_Corretor"].astype(str).fillna("").str.strip().str.upper()

        df = df[df["Nome_Corretor"].ne("") & df["Nome_Corretor"].ne("NAN")]

        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        # excluir
        df = df[
            ~df.apply(
                lambda r: self._is_excluded(
                    nome=str(r["Nome_Corretor"]).strip().upper(),
                    id_corretor=str(r["Id_Corretor"]).strip().upper()
                ),
                axis=1
            )
        ].copy()

        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        if (df["Id_Corretor"].ne("")).any():
            agg = df.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False).size()
        else:
            agg = df.groupby(["Nome_Corretor"], as_index=False).size()
            agg["Id_Corretor"] = ""

        agg = agg.rename(columns={"size": "total"})
        agg["total"] = pd.to_numeric(agg["total"], errors="coerce").fillna(0).astype(float)

        return agg[["Id_Corretor", "Nome_Corretor", "total"]]

    # =========================================================
    # Público: rankings
    # =========================================================
    def get_all_rankings(
        self,
        start: Optional[str],
        end: Optional[str],
        limit: int = 100,
        include_pending: bool = False
    ) -> Dict[str, Any]:
        vendas = self.load_vendas(start, end)

        warnings: List[str] = []

        if vendas.empty:
            warnings.append("Base de vendas vazia para o período.")

        df_vgv = self._calc_vgv_geral_algoritmo(vendas) if not vendas.empty else pd.DataFrame(
            columns=["Id_Corretor", "Nome_Corretor", "total"]
        )
        df_vgc = self._calc_vgc_geral_algoritmo(vendas) if not vendas.empty else pd.DataFrame(
            columns=["Id_Corretor", "Nome_Corretor", "total"]
        )
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

            "captacao": capt_list,
            "captacoes": capt_list,

            "visitas": vis_list,
            "visitas_rank": vis_list,

            "corretores_excluidos": {
                "nomes": sorted(list(self.excluded_names)),
                "ids": sorted(list(self.excluded_ids)),
            },

            "meta": {
                "start": start,
                "end": end,
                "limit": limit,
                "include_pending": include_pending,
                "base_counts": {
                    "vendas": int(len(vendas)) if isinstance(vendas, pd.DataFrame) else 0,
                    "captacao": int(df_capt["total"].sum()) if not df_capt.empty else 0,
                    "visitas": int(df_vis["total"].sum()) if not df_vis.empty else 0,
                },
                "warnings": warnings,
            }
        }

    # =========================================================
    # Público: contratos 2026
    # =========================================================
    def get_contratos_2026(self) -> List[Dict[str, Any]]:
        vendas = self.load_vendas(start="2026-01-01", end="2026-12-31")
        if vendas.empty:
            return []

        df = vendas.copy()
        if "Id_Contrato" not in df.columns:
            return []

        df["Id_Contrato"] = df["Id_Contrato"].astype(str).str.strip()

        if "Contrato" in df.columns:
            df["display"] = df["Id_Contrato"] + " - " + df["Contrato"].astype(str).str.strip()
        else:
            df["display"] = df["Id_Contrato"] + " - VGV " + df["Valor_Negocio"].astype(float).map(
                lambda x: f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

        df = df.drop_duplicates(subset=["Id_Contrato"])
        if "Data_Contrato" in df.columns:
            df = df.sort_values("Data_Contrato", ascending=False)

        return df[["Id_Contrato", "display"]].to_dict(orient="records")

    # =========================================================
    # Público: grava divisão comissão
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
            except Exception:
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