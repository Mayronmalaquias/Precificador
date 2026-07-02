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
    ABA_GERENTES: str


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
            ABA_GERENTES=os.getenv("GSHEET_ABA_GERENTES", "Dim_Gerente"),
        )

        self.gsa_json_path = "./app/utils/asserts/credenciais.json"
        self.gsa_json_inline = os.getenv("GSA_JSON", "")

        # Lista de exclusão por ENV:
        RANKING_EXCLUDED_NAMES=os.getenv("RANKING_EXCLUDED_NAMES","")
        #RANKING_EXCLUDED_IDS="C61010,C99999"
        self.excluded_names: Set[str] = self._parse_csv_env_to_set("RANKING_EXCLUDED_NAMES")
        self.excluded_ids: Set[str] = self._parse_csv_env_to_set("RANKING_EXCLUDED_IDS")

        # Ocultos manuais (persistidos no banco, via olhinho no front)
        try:
            from app.services.ranking_ocultos_service import ids_e_nomes_ocultos
            ids_db, nomes_db = ids_e_nomes_ocultos()
            self.excluded_ids |= ids_db
            self.excluded_names |= nomes_db
        except Exception:
            pass

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

    def read_sheet_df(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        """Le do Postgres (substitui a leitura via gspread). spreadsheet_id
        ignorado - so existe pra nao mudar a assinatura de quem chama isso."""
        from app.services import db_loaders

        rows = db_loaders.carregar_aba(sheet_name)
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

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
    def _rank_list(df: pd.DataFrame, total_col: str, id_col: str, name_col: str) -> List[Dict[str, Any]]:
        if df.empty:
            return []

        df = df.sort_values([total_col, name_col], ascending=[False, True]).reset_index(drop=True)

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
    def get_gerentes_df(self) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_CORRETORES_ID, self.cfg.ABA_GERENTES)
        if df.empty:
            return pd.DataFrame(columns=["Id_Gerente", "Equipe"])

        id_col = next((c for c in ["IdGerente", "Id_Gerente", "id_gerente"] if c in df.columns), None)
        equipe_col = next((c for c in ["Equipe", "equipe", "Team", "team"] if c in df.columns), None)

        if not id_col or not equipe_col:
            return pd.DataFrame(columns=["Id_Gerente", "Equipe"])

        out = df[[id_col, equipe_col]].copy()
        out.columns = ["Id_Gerente", "Equipe"]
        out["Id_Gerente"] = out["Id_Gerente"].astype(str).str.strip().str.upper()
        out["Equipe"] = out["Equipe"].astype(str).str.strip()
        out = out[out["Id_Gerente"].ne("") & out["Id_Gerente"].ne("NAN")]
        return out.drop_duplicates(subset=["Id_Gerente"])

    def get_corretores_df(self) -> pd.DataFrame:
        df = self.read_sheet_df(self.cfg.SHEET_CORRETORES_ID, self.cfg.ABA_CORRETORES)
        if df.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "Team"])

        id_col = next(
            (c for c in ["IdCorretor", "Id_Corretor", "id_corretor", "ID_CORRETOR", "ID", "Codigo", "Código", "Cod", "cod"] if c in df.columns),
            None,
        )
        name_col = next(
            (c for c in ["Nome_Corretor", "nome_corretor", "Nome", "nome", "Corretor", "corretor"] if c in df.columns),
            None,
        )

        if not id_col or not name_col:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "Team"])

        out = df.copy()
        out["Id_Corretor"] = out[id_col].astype(str).str.strip().str.upper()
        out["Nome_Corretor"] = out[name_col].astype(str).str.strip().str.upper()

        # Tenta pegar equipe diretamente da Dim_Corretor (coluna Team/Equipe)
        team_col = next((c for c in ["Team", "team", "Equipe", "equipe"] if c in out.columns), None)
        if team_col:
            out["Team"] = out[team_col].astype(str).str.strip()
        else:
            out["Team"] = ""

        # Se não tiver equipe direta mas tiver IdGerente, resolve via Dim_Gerente
        gerente_col = next((c for c in ["IdGerente", "Id_Gerente", "id_gerente"] if c in out.columns), None)
        if gerente_col and out["Team"].eq("").all():
            out["_IdGerente"] = out[gerente_col].astype(str).str.strip().str.upper()
            gerentes_df = self.get_gerentes_df()
            if not gerentes_df.empty:
                gerente_map = dict(zip(gerentes_df["Id_Gerente"], gerentes_df["Equipe"]))
                out["Team"] = out["_IdGerente"].map(gerente_map).fillna("")
            out = out.drop(columns=["_IdGerente"])

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
        - vendedores dividem Valor_Negocio entre si
        - captadores dividem Valor_Negocio entre si (independente dos vendedores)
        - 1v+1c: ambos recebem 1x Valor_Negocio
        - 2v+1c: cada vendedor recebe 1/2, captador recebe 1x
        - 1v+2c: vendedor recebe 1x, cada captador recebe 1/2
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

            if vendedores:
                por_vendedor = valor_imovel / len(vendedores)
                for nome in vendedores:
                    acc[nome] = acc.get(nome, 0.0) + por_vendedor

            if captadores:
                por_captador = valor_imovel / len(captadores)
                for nome in captadores:
                    acc[nome] = acc.get(nome, 0.0) + por_captador

        return self._finalize_rank_df(acc)

    def _calc_vgc_geral_algoritmo(self, vendas: pd.DataFrame, apply_factor: bool = False) -> pd.DataFrame:
        """
        REGRA OFICIAL:
        - usa Valor_Total_61 BRUTO
        - vendedores dividem Valor_Total_61 entre si (mesma logica do VGV)
        - captadores dividem Valor_Total_61 entre si (mesma logica do VGV)
        - 1v+1c: ambos recebem 1x Valor_Total_61
        - 2v+1c: cada vendedor recebe 1/2, captador recebe 1x
        - 1v+2c: vendedor recebe 1x, cada captador recebe 1/2
        - NÃO divide por 0.06 por padrão; se apply_factor=True divide cada valor por 0.06
        """
        if vendas.empty:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        acc: Dict[str, float] = {}

        for _, row in vendas.iterrows():
            valor_total = float(row.get("Valor_Total_61", 0.0) or 0.0)
            if valor_total <= 0:
                continue

            if apply_factor:
                valor_total = valor_total / 0.06

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

            n_lados = (1 if vendedores else 0) + (1 if captadores else 0)
            if n_lados == 0:
                continue

            valor_por_lado = valor_total / n_lados

            if vendedores:
                por_vendedor = valor_por_lado / len(vendedores)
                for nome in vendedores:
                    acc[nome] = acc.get(nome, 0.0) + por_vendedor

            if captadores:
                por_captador = valor_por_lado / len(captadores)
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

        id_to_name, name_to_id = self._maps_corretores()
        rows = []

        def _resolve_captador(value: Any) -> Dict[str, str]:
            raw = str(value or "").strip()
            key = raw.upper()
            if not key or key in {"-", "NAN", "NONE"}:
                return {}

            if key in id_to_name:
                return {
                    "Id_Corretor": key,
                    "Nome_Corretor": id_to_name[key],
                }

            nome = self._limpar_nome(raw)
            if not nome:
                return {}

            return {
                "Id_Corretor": name_to_id.get(nome, ""),
                "Nome_Corretor": nome,
            }

        for c in ["Captador1", "Captador2", "Captador3"]:
            if c not in df.columns:
                continue

            for value in df[c].tolist():
                captador = _resolve_captador(value)
                if captador:
                    rows.append(captador)

        if not rows:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        x = pd.DataFrame(rows)
        agg = (
            x.groupby(["Id_Corretor", "Nome_Corretor"], as_index=False)
            .size()
            .rename(columns={"size": "total"})
        )

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
    def get_ranking(
        self,
        kind: str,
        start: Optional[str],
        end: Optional[str],
        include_pending: bool = False,
        apply_factor: bool = False,
    ) -> List[Dict[str, Any]]:
        kind = (kind or "").lower().strip()

        if kind in {"vgv_geral", "vgc_geral"}:
            vendas = self.load_vendas(start, end)
            if kind == "vgv_geral":
                rank_df = self._calc_vgv_geral_algoritmo(vendas)
            else:
                rank_df = self._calc_vgc_geral_algoritmo(vendas, apply_factor=apply_factor)
        elif kind == "captacao":
            rank_df = self._calc_captacao_rank(start, end)
        elif kind == "visitas":
            rank_df = self._calc_visitas_rank(start, end)
        else:
            raise ValueError("kind invalido")

        return self._rank_list(rank_df, "total", "Id_Corretor", "Nome_Corretor")

    def get_all_rankings(
        self,
        start: Optional[str],
        end: Optional[str],
        include_pending: bool = False,
        apply_factor: bool = False,
    ) -> Dict[str, Any]:
        vendas = self.load_vendas(start, end)

        warnings: List[str] = []

        if vendas.empty:
            warnings.append("Base de vendas vazia para o período.")

        df_vgv = self._calc_vgv_geral_algoritmo(vendas) if not vendas.empty else pd.DataFrame(
            columns=["Id_Corretor", "Nome_Corretor", "total"]
        )
        df_vgc = self._calc_vgc_geral_algoritmo(vendas, apply_factor=apply_factor) if not vendas.empty else pd.DataFrame(
            columns=["Id_Corretor", "Nome_Corretor", "total"]
        )
        df_capt = self._calc_captacao_rank(start, end)
        df_vis = self._calc_visitas_rank(start, end)

        vgv_list = self._rank_list(df_vgv, "total", "Id_Corretor", "Nome_Corretor")
        vgc_list = self._rank_list(df_vgc, "total", "Id_Corretor", "Nome_Corretor")
        capt_list = self._rank_list(df_capt, "total", "Id_Corretor", "Nome_Corretor")
        vis_list = self._rank_list(df_vis, "total", "Id_Corretor", "Nome_Corretor")

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
    # Público: detalhe corretor
    # =========================================================
    def _detalhe_de_vendas(
        self,
        nome_corretor: str,
        kind: str,
        start: Optional[str],
        end: Optional[str],
        apply_factor: bool,
        vendas: "pd.DataFrame",
    ) -> Dict[str, Any]:
        """Calcula o detalhe de um corretor a partir de um DataFrame já carregado."""
        nome_norm = self._limpar_nome(nome_corretor)
        negociacoes: List[Dict[str, Any]] = []
        total = 0.0
        total_vgv = 0.0
        total_vgc_bruto = 0.0
        total_vgc_fator = 0.0
        total_v61_cheio = 0.0
        total_parte_vn = 0.0
        total_parte_v61 = 0.0

        for _, row in vendas.iterrows():
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

            is_vend = nome_norm in vendedores
            is_cap = nome_norm in captadores

            if not is_vend and not is_cap:
                continue

            if is_vend and is_cap:
                papel = "VENDA + CAPTAÇÃO"
            elif is_vend:
                papel = "VENDA"
            else:
                papel = "CAPTAÇÃO"

            n_lados = (1 if vendedores else 0) + (1 if captadores else 0)
            if n_lados == 0:
                continue

            vn = float(row.get("Valor_Negocio", 0.0) or 0.0)
            v61 = float(row.get("Valor_Total_61", 0.0) or 0.0)

            # Acumula porção de cada lado em que o corretor aparece
            vgv_corretor = 0.0
            vgc_bruto_corretor = 0.0
            vgc_fator_corretor = 0.0

            if is_vend and len(vendedores) > 0:
                vgv_corretor += vn / len(vendedores)
                if v61 > 0:
                    vgc_bruto_corretor += (v61 / n_lados) / len(vendedores)
                    vgc_fator_corretor += (v61 / 0.06 / n_lados) / len(vendedores)

            if is_cap and len(captadores) > 0:
                vgv_corretor += vn / len(captadores)
                if v61 > 0:
                    vgc_bruto_corretor += (v61 / n_lados) / len(captadores)
                    vgc_fator_corretor += (v61 / 0.06 / n_lados) / len(captadores)

            # VGV (parte): NAO duplica quando a pessoa e vendedor E captador no mesmo
            # contrato -> conta 1x (max dos lados). Ex: 1M vendedor+captador = 1M.
            share_vend_vn = (vn / len(vendedores)) if (is_vend and vendedores) else 0.0
            share_cap_vn = (vn / len(captadores)) if (is_cap and captadores) else 0.0
            vgv_part = max(share_vend_vn, share_cap_vn)

            # VGC (parte): SOMA de todas as partes da pessoa (venda + captacao).
            # Ex: vendedor+captador sozinho = (v61/2) + (v61/2) = v61 cheio.
            vgc_part = vgc_bruto_corretor

            # Relatorio UNIFICADO (sem diferenciar VGV/VGC): inclui se a pessoa
            # participou de qualquer lado. valor_corretor mantido p/ compatibilidade.
            valor_corretor = vgc_bruto_corretor if kind == "vgc_geral" else vgv_corretor
            if vgv_part <= 0 and vgc_part <= 0:
                continue

            outros = sorted((vendedores | captadores) - {nome_norm})

            empreend_cols = ["Empreendimento", "empreendimento", "Endereco", "Endereco_Imovel", "Descricao"]
            empreendimento = ""
            for c in empreend_cols:
                v = str(row.get(c, "")).strip()
                if v and v.lower() not in ("nan", "none", ""):
                    empreendimento = v
                    break

            # formata data sem timestamp
            raw_date = str(row.get("Data_Contrato", "")).strip()
            date_only = raw_date.split(" ")[0].split("T")[0]

            contrato_nome = str(row.get("Contrato", "")).strip()

            negociacoes.append({
                "id_contrato": str(row.get("Id_Contrato", "")).strip(),
                "contrato": contrato_nome,
                "data_contrato": date_only,
                "empreendimento": empreendimento,
                "valor_negocio": vn,
                "valor_total_61": v61,
                "parte_valor_negocio": round(vgv_part, 2),   # VGV (parte, sem duplicar)
                "parte_valor_total_61": round(vgc_part, 2),  # VGC (parte, sem duplicar)
                "papel": papel,
                "valor_corretor": round(valor_corretor, 2),
                "outros_envolvidos": outros,
            })
            total += valor_corretor
            total_vgv += vn
            total_v61_cheio += v61
            total_parte_vn += vgv_part
            total_parte_v61 += vgc_part
            total_vgc_bruto += vgc_bruto_corretor
            total_vgc_fator += vgc_fator_corretor

        negociacoes.sort(key=lambda x: x["data_contrato"])

        return {
            "corretor": nome_norm,
            "kind": kind,
            "start": start,
            "end": end,
            "apply_factor": apply_factor,
            "total": round(total, 2),
            "total_vgv": round(total_vgv, 2),
            "total_vgc_bruto": round(total_vgc_bruto, 2),
            "total_vgc_fator": round(total_vgc_fator, 2),
            # cheios x partes (relatorio unificado)
            "total_vn_cheio": round(total_vgv, 2),
            "total_parte_vn": round(total_parte_vn, 2),
            "total_v61_cheio": round(total_v61_cheio, 2),
            "total_parte_v61": round(total_parte_v61, 2),
            "negociacoes": negociacoes,
        }

    def _contadores_periodo(self, start: Optional[str], end: Optional[str]):
        """Mapas nome(UPPER) -> qtd de captacoes e de visitas no periodo."""
        def _to_map(df):
            m: Dict[str, int] = {}
            if df is not None and not df.empty and "Nome_Corretor" in df.columns:
                for _, r in df.iterrows():
                    k = str(r.get("Nome_Corretor", "")).strip().upper()
                    if k:
                        m[k] = int(round(float(r.get("total", 0) or 0)))
            return m
        try:
            capt = _to_map(self._calc_captacao_rank(start, end))
        except Exception:
            capt = {}
        try:
            vis = _to_map(self._calc_visitas_rank(start, end))
        except Exception:
            vis = {}
        return capt, vis

    def get_corretor_detalhe(
        self,
        nome_corretor: str,
        kind: str,
        start: Optional[str],
        end: Optional[str],
        apply_factor: bool = False,
    ) -> Dict[str, Any]:
        vendas = self.load_vendas(start, end)
        detalhe = self._detalhe_de_vendas(nome_corretor, kind, start, end, apply_factor, vendas)
        capt_map, vis_map = self._contadores_periodo(start, end)
        chave = str(detalhe.get("corretor", "")).strip().upper()
        detalhe["qtd_captacoes"] = capt_map.get(chave, 0)
        detalhe["qtd_visitas"] = vis_map.get(chave, 0)
        return detalhe

    def get_todos_detalhe(
        self,
        kind: str,
        start: Optional[str],
        end: Optional[str],
        apply_factor: bool = False,
    ) -> List[Dict[str, Any]]:
        """Carrega a planilha UMA vez e gera detalhe de todos os corretores do ranking."""
        vendas = self.load_vendas(start, end)

        if kind == "vgc_geral":
            rank_df = self._calc_vgc_geral_algoritmo(vendas, apply_factor=apply_factor) if not vendas.empty else pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])
        else:
            rank_df = self._calc_vgv_geral_algoritmo(vendas) if not vendas.empty else pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        ranking = self._rank_list(rank_df, "total", "Id_Corretor", "Nome_Corretor")
        capt_map, vis_map = self._contadores_periodo(start, end)

        detalhes = []
        for item in ranking:
            nome = item.get("corretor", "")
            if not nome:
                continue
            detalhe = self._detalhe_de_vendas(nome, kind, start, end, apply_factor, vendas)
            if detalhe.get("negociacoes"):
                chave = str(detalhe.get("corretor", "")).strip().upper()
                detalhe["qtd_captacoes"] = capt_map.get(chave, 0)
                detalhe["qtd_visitas"] = vis_map.get(chave, 0)
                detalhes.append(detalhe)

        return detalhes

    def get_ranking_equipe(
        self,
        kind: str,
        start: Optional[str],
        end: Optional[str],
        include_pending: bool = False,
        apply_factor: bool = False,
    ) -> List[Dict[str, Any]]:
        rank_items = self.get_ranking(kind, start, end, include_pending, apply_factor)

        corretores_df = self.get_corretores_df()
        nome_to_team: Dict[str, str] = {}
        if not corretores_df.empty:
            for _, r in corretores_df.iterrows():
                nome = str(r["Nome_Corretor"]).strip().upper()
                team = str(r.get("Team", "")).strip()
                if nome:
                    nome_to_team[nome] = team if team and team.lower() not in ("nan", "none", "") else "Sem Equipe"

        team_totals: Dict[str, float] = {}
        for item in rank_items:
            nome = str(item.get("corretor", "")).strip().upper()
            team = nome_to_team.get(nome, "Sem Equipe")
            team_totals[team] = team_totals.get(team, 0.0) + float(item.get("total", 0.0))

        result = sorted(team_totals.items(), key=lambda x: -x[1])
        return [
            {"posicao": i + 1, "id_corretor": "", "corretor": team, "total": round(total, 2)}
            for i, (team, total) in enumerate(result)
        ]

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

        agora = datetime.utcnow()

        from app.database import SessionLocal
        from app.models.contrato import DivisaoComissao

        session = SessionLocal()
        try:
            for x in norm:
                comissao_valor = 0.0
                if valor_comissao_total > 0:
                    comissao_valor = valor_comissao_total * (x["percentual"] / 100.0)

                session.add(DivisaoComissao(
                    id_contrato=id_contrato,
                    papel=x["papel"],
                    id_corretor=x["id_corretor"],
                    nome_corretor=x["nome"],
                    percentual=x["percentual"],
                    comissao_valor=comissao_valor,
                    observacao=x["obs"],
                    atualizado_em=agora,
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return {
            "ok": True,
            "id_contrato": id_contrato,
            "linhas_inseridas": len(norm),
            "valor_comissao_total": valor_comissao_total
        }
