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
        """Ranking de captação lê de `fato_captacao` (BANCO), não mais da planilha de
        estoque. Cada linha da tabela = 1 imóvel captado, com até 3 captadores por
        `id_usuarios` — devolve UMA linha por (código, captador).

        Por que mudou: a planilha tinha 1 corretor por linha (2º captador se perdia) e
        casava por NOME. A tabela guarda `C61xxx`, então não depende do de-para. A
        planilha continua sendo escrita no lançamento, só com o corretor principal, p/
        não conflitar com o AppSheet.

        Dedup por (código do imóvel, captador): import repetido não conta duas vezes.
        """
        from app.database import SessionLocal
        from app.models.fato_bases import FatoCaptacao

        s_dt = self._parse_date(start) if start else None
        e_dt = self._parse_date(end) if end else None

        session = SessionLocal()
        try:
            registros = session.query(
                FatoCaptacao.codigo_imovel,
                FatoCaptacao.captador1,
                FatoCaptacao.captador2,
                FatoCaptacao.captador3,
                FatoCaptacao.data_entrada,
            ).all()
        except Exception:
            return pd.DataFrame()
        finally:
            session.close()

        _INVALIDOS = {"", "0", "-", "NAN", "NONE"}
        vistos = set()
        linhas = []

        for codigo, cap1, cap2, cap3, data in registros:
            if data is None:
                # Sem data não dá p/ posicionar no período — só entra em ranking sem filtro.
                if s_dt is not None or e_dt is not None:
                    continue
            else:
                dts = pd.Timestamp(data)
                if s_dt is not None and dts < s_dt:
                    continue
                if e_dt is not None and dts > e_dt:
                    continue

            cod = str(codigo or "").strip()
            for cap in (cap1, cap2, cap3):
                c = str(cap or "").strip().upper()
                if c in _INVALIDOS:
                    continue
                chave = (cod, c)
                if cod and chave in vistos:
                    continue
                vistos.add(chave)
                linhas.append({"Codigo_Imovel": cod, "Captador": c, "Data": data})

        return pd.DataFrame(linhas, columns=["Codigo_Imovel", "Captador", "Data"])

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
        - cada lado divide o Valor_Negocio CHEIO entre seus membros
        - venda e captacao sao independentes (sem split 50/50 entre lados)
        - quem e vendedor E captador no mesmo contrato conta 1x (max das partes)
        - 1v+1c (distintos): cada um recebe o valor cheio
        - 2v+1c: cada vendedor recebe 1/2, captador recebe cheio
        - 1v+2c: vendedor recebe cheio, cada captador recebe 1/2
        - valor NAO e conservado: soma pode chegar a 2x o Valor_Negocio
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

            # Cada lado divide o Valor_Negocio CHEIO entre seus membros; venda e
            # captacao sao independentes (nao ha split 50/50). Quem esta nos dois
            # lados conta 1x (max das partes). Ex: 3M, 1v+2c => vend 3M, cada
            # captador 1.5M. Valor NAO e conservado (pode somar ate 2x).
            if not (vendedores or captadores):
                continue

            por_vendedor = (valor_imovel / len(vendedores)) if vendedores else 0.0
            por_captador = (valor_imovel / len(captadores)) if captadores else 0.0

            for nome in (vendedores | captadores):
                share_v = por_vendedor if nome in vendedores else 0.0
                share_c = por_captador if nome in captadores else 0.0
                acc[nome] = acc.get(nome, 0.0) + max(share_v, share_c)

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
        if df.empty or "Captador" not in df.columns:
            return pd.DataFrame(columns=["Id_Corretor", "Nome_Corretor", "total"])

        id_to_name, name_to_id = self._maps_corretores()
        rows = []

        # `fato_captacao` guarda o captador por id_usuarios (C61xxx). Cada captador de
        # cada imóvel = 1 captação (2º captador conta igual ao 1º). Se o id não estiver
        # no cadastro, mantém o valor bruto como nome — não some do ranking.
        for value in df["Captador"].tolist():
            captador = str(value or "").strip().upper()
            if not captador or captador in {"-", "NAN", "NONE"}:
                continue
            nome = id_to_name.get(captador)
            if nome:
                rows.append({"Id_Corretor": captador, "Nome_Corretor": nome})
            else:
                # Linha antiga gravada por nome em vez de id: resolve o caminho inverso.
                rows.append({
                    "Id_Corretor": name_to_id.get(captador, ""),
                    "Nome_Corretor": captador,
                })

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
    # Texto de fechamento do mês (por equipe) p/ o grupo
    # =========================================================
    @staticmethod
    def _chave_captador(nome: Any) -> str:
        """Chave de casamento entre `fato_captacao` e o cadastro.

        Sem acento e sem caixa. `_limpar_nome` so faz `upper()`, e por isso a captacao de
        "PATRICIA MOREIRA" (como veio do Imoview) nunca casava com "Patrícia Moreira" do
        cadastro — cinco captacoes de agosto/2026 ficavam orfas por causa disso.

        Nao substitui `_limpar_nome`: aquele e usado para AGRUPAR o ranking e para exibir,
        e mexer nele mudaria numeros de outras telas. Este serve so ao casamento.
        """
        import unicodedata
        texto = RankingService._limpar_nome(nome)
        if not texto:
            return ""
        sem_acento = unicodedata.normalize("NFKD", texto)
        limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
        # Colapsa espaco repetido: o Imoview devolve "RODRIGO  PAVONI" com dois espacos, e
        # sem isto a igualdade com "Rodrigo Pavoni" falha por um caractere invisivel.
        # Eram 145 imoveis so nesse nome, 95 em "SERGIO  CARDOSO".
        return " ".join(limpo.split())

    def _indice_captadores(self):
        """Índice nome-do-Imoview -> id do cadastro, construído uma vez por chamada.

        O catálogo devolve o nome COMPLETO ("IONNARA VIEIRA DE ARAÚJO"); o cadastro tem o
        curto ("Ionnara Vieira"). Casar por igualdade perdia 20,5 captações de agosto/2026
        em nomes que são de gente ativa — Ionnara, Paolla, Kaio, Heloisa, Marcelo Ribeiro.

        E-mail seria a chave certa, mas só 17 dos 92 usuários ativos têm um preenchido.

        Regra: normaliza sem acento, tenta igualdade, depois **prefixo por tokens** com no
        mínimo dois tokens. Um token só ("Patrícia") casaria com pessoas diferentes.

        Entre homônimos, **o ativo vence**: o cadastro tem a mesma pessoa em contas
        antigas desativadas, e creditar a captação na conta morta a tira da equipe.
        """
        from app.database import SessionLocal
        from app.models.usuarios import Usuarios

        session = SessionLocal()
        try:
            usuarios = session.query(
                Usuarios.id_usuarios, Usuarios.nome, Usuarios.ativo
            ).all()
        finally:
            session.close()

        # Ativo por último para sobrescrever o inativo de mesmo nome.
        exato, por_tokens = {}, {}
        for uid, nome, ativo in sorted(usuarios, key=lambda u: bool(u[2])):
            chave = self._chave_captador(nome)
            if not chave:
                continue
            exato[chave] = uid
            por_tokens[tuple(chave.split())] = uid
        return exato, por_tokens

    def _resolver_captador(self, nome: str, indice) -> str:
        """Nome do catálogo -> id do cadastro. Devolve o nome normalizado se não achar."""
        exato, por_tokens = indice
        chave = self._chave_captador(nome)
        if not chave:
            return ""
        if chave in exato:
            return exato[chave]

        tokens = tuple(chave.split())
        # Do mais específico para o menos: "IONNARA VIEIRA DE ARAUJO" tenta a tupla
        # inteira, depois (IONNARA,VIEIRA,DE), depois (IONNARA,VIEIRA). Para em 2 — um
        # token casaria pessoas diferentes.
        #
        # O limite superior e `len(tokens)`, nao `len(tokens)-1`: com o anterior, nome de
        # DOIS tokens gerava um range vazio e nunca chegava a tentar o casamento.
        for corte in range(len(tokens), 1, -1):
            achado = por_tokens.get(tokens[:corte])
            if achado:
                return achado
        return chave

    def _mes_para_intervalo(self, mes: str):
        from calendar import monthrange
        try:
            ano, m = int(str(mes)[:4]), int(str(mes)[5:7])
            assert 1 <= m <= 12
        except Exception:
            raise ValueError("mes deve ser 'YYYY-MM'")
        return ano, m, f"{ano}-{m:02d}-01", f"{ano}-{m:02d}-{monthrange(ano, m)[1]:02d}"

    def _captacoes_rateadas(self, start: str, end: str) -> Dict[str, float]:
        """Captacoes do periodo por captador, com credito RATEADO.

        Cada imovel vale 1, dividido pelo **percentual que o CRM registra** para cada
        captador (`imovel_area.percentual1..3`, vindo da API do Imoview com
        `exibircaptadores=true`). E a regra que a operacao usa no texto do grupo
        ("Armando: 1,5/4"), e a que faz a soma das equipes fechar com o numero de imoveis.

        **O percentual nao e sempre meio a meio.** No imovel 10911 o captador marcado
        como principal esta com 0% e o outro com 100%. Dividir por `1/n` — como esta
        funcao fazia ate 27/08/2026 — erraria exatamente nesses casos, dando 0,5 a quem o
        CRM nao credita nada.

        Sem percentual no catalogo (imovel que a varredura ainda nao alcancou, ou captador
        que so existe em `fato_captacao`), cai no rateio igual. E aproximacao declarada,
        nao silencio: `_captacoes_rateadas` devolve tambem quantas linhas usaram cada
        caminho.

        O ranking geral (`_calc_captacao_rank`) conta diferente de proposito — la o 2o
        captador vale 1 inteiro, como esta documentado naquele metodo. Sao perguntas
        diferentes: "quantos imoveis esta pessoa ajudou a captar" contra "quantos imoveis
        a equipe captou". Em agosto/2026 a diferenca era de 79 contra 75, com Armando e
        Renata levando 4 cada pelas MESMAS 4 captacoes conjuntas.

        A chave e o id (`C61xxx`), que e o que `fato_captacao` grava; nome so entra para
        linha antiga gravada com nome.
        """
        from app.database import SessionLocal
        from app.models.fato_bases import FatoCaptacao

        from app.models.imovel_area import ImovelArea

        session = SessionLocal()
        try:
            linhas = session.query(
                FatoCaptacao.codigo_imovel,
                FatoCaptacao.captador1, FatoCaptacao.captador2, FatoCaptacao.captador3
            ).filter(
                FatoCaptacao.data_entrada >= start, FatoCaptacao.data_entrada <= end
            ).all()

            # Percentuais do catalogo, so dos codigos do periodo: uma consulta em vez de
            # uma por imovel.
            codigos = {str(c or "").strip() for c, *_ in linhas if str(c or "").strip()}
            percentuais: Dict[str, List[tuple]] = {}
            if codigos:
                for area in session.query(
                    ImovelArea.codigo,
                    ImovelArea.captador1, ImovelArea.captador2, ImovelArea.captador3,
                    ImovelArea.percentual1, ImovelArea.percentual2, ImovelArea.percentual3,
                ).filter(ImovelArea.codigo.in_(codigos)).all():
                    pares = [
                        (str(n).strip(), float(p))
                        for n, p in ((area[1], area[4]), (area[2], area[5]), (area[3], area[6]))
                        if str(n or "").strip() and p is not None
                    ]
                    # Soma zero significa CRM sem rateio definido: nao serve de divisor.
                    if pares and sum(p for _, p in pares) > 0:
                        percentuais[str(area[0])] = pares
        finally:
            session.close()

        def valido(v) -> bool:
            t = str(v or "").strip()
            return bool(t) and t.upper() not in {"-", "NAN", "NONE"}

        indice = self._indice_captadores()
        por_captador: Dict[str, float] = {}
        origem = {"percentual": 0, "igual": 0, "estoque": 0}

        for cod, c1, c2, c3 in linhas:
            codigo = str(cod or "").strip()
            donos = [str(v).strip().upper() for v in (c1, c2, c3) if valido(v)]
            if not donos:
                # Captacao sem captador na linha: o responsavel vem do estoque do
                # Imoview, que e a fonte de quem cuida do imovel hoje.
                do_estoque = self._responsavel_no_estoque(cod)
                if not do_estoque:
                    continue
                donos = [do_estoque]
                origem["estoque"] += 1

            pares = percentuais.get(codigo)
            if pares:
                # Rateio do CRM. As chaves do catalogo sao NOMES completos; as da captacao
                # sao ids. Sem resolver, o credito ia para uma chave que ninguem consome e
                # a captacao aparecia como "sem dono".
                total_pct = sum(p for _, p in pares)
                for nome, pct in pares:
                    chave = self._resolver_captador(nome, indice)
                    por_captador[chave] = por_captador.get(chave, 0.0) + (pct / total_pct)
                origem["percentual"] += 1
                continue

            fatia = 1.0 / len(donos)
            for dono in donos:
                por_captador[dono] = por_captador.get(dono, 0.0) + fatia
            origem["igual"] += 1

        self._origem_rateio = origem
        return por_captador

    def _responsavel_no_estoque(self, codigo: Any) -> str:
        """Captador do imovel no estoque do Imoview (`fato_estoque`), o mais recente.

        Ultimo recurso: so entra quando a captacao nao diz de quem e. **O estoque fica
        para tras** — em 25/08/2026 a `data_estoque` mais recente era 03/08, e nenhum
        imovel captado depois disso estava la. Serve para linha antiga, nao para o mes
        corrente.
        """
        from app.database import SessionLocal
        from app.models.fato_bases import FatoEstoque

        cod = str(codigo or "").strip()
        if not cod:
            return ""
        session = SessionLocal()
        try:
            linha = session.query(FatoEstoque.captador1).filter(
                FatoEstoque.codigo_imovel == cod
            ).order_by(FatoEstoque.data_estoque.desc(), FatoEstoque.id.desc()).first()
        finally:
            session.close()
        return str((linha[0] if linha else "") or "").strip().upper()

    @staticmethod
    def _formatar_total(valor: float) -> str:
        """3 -> "3"; 1.5 -> "1,5". O grupo le virgula, e "1.5" parece outro numero."""
        arredondado = round(float(valor or 0), 2)
        if abs(arredondado - round(arredondado)) < 0.01:
            return str(int(round(arredondado)))
        return f"{arredondado:.1f}".replace(".", ",")

    def fechamento(self, mes: str, meta: int = 4) -> Dict[str, Any]:
        """Dados do fechamento do mes por equipe.

        Fonte unica do texto E do dashboard: com dois calculos, o numero colado no grupo
        e o numero da tela divergiriam no primeiro ajuste feito em um so.

        Tres correcoes sobre a versao anterior, todas medidas em agosto/2026:

          1. Casamento sem acento (`_chave_captador`) — cinco captacoes ficavam orfas.
          2. Cada captacao conta UMA vez. O cadastro tem contas duplicadas, e como o
             casamento e por nome, dois usuarios com o mesmo nome recebiam a contagem
             inteira cada um: o texto somava 78 atribuidas MAIS 5 orfas de um total de 78.
          3. Membro que nao e corretor nem gerente entra quando tem captacao. Jose Marques
             encabeca a AGEF sem a permissao formal, e sumia do texto junto com a
             captacao dele.
        """
        from app.database import SessionLocal
        from app.models.equipe import Equipe
        from app.models.usuarios import Usuarios

        ano, m, start, end = self._mes_para_intervalo(mes)

        # Por ID, com rateio. Casar por nome era a origem de dois defeitos: captacao orfa
        # por diferenca de acento, e contagem dobrada quando o cadastro tem a mesma pessoa
        # em duas contas. O id e o que `fato_captacao` grava.
        por_id = self._captacoes_rateadas(start, end)
        id_to_name, name_to_id = self._maps_corretores()

        counts: Dict[str, float] = {}
        rotulo_original: Dict[str, str] = {}
        for chave, valor in por_id.items():
            # Linha antiga pode ter nome no lugar do id; resolve o caminho inverso.
            alvo = chave if chave in id_to_name else name_to_id.get(chave, chave)
            counts[alvo] = counts.get(alvo, 0.0) + valor
            rotulo_original.setdefault(alvo, id_to_name.get(alvo) or chave)

        session = SessionLocal()
        try:
            equipes = session.query(Equipe).filter(
                Equipe.ativo.is_(True)
            ).order_by(Equipe.nome.asc()).all()
            # TODOS, nao so os ativos. O roster de cada equipe continua sendo os ativos —
            # e o que "sincronizar com os ativos do sistema" quer dizer —, mas quem captou
            # e depois foi desativado nao pode sumir com a captacao junto: em agosto/2026
            # eram quatro pessoas (Patricia Moreira, Sergio Camargo, Andre Brusk e Marcela
            # Bagli), todas com equipe definida no cadastro, e as quatro captacoes
            # apareciam como "sem dono".
            usuarios = session.query(Usuarios).all()
        finally:
            session.close()

        ativos = [u for u in usuarios if u.ativo]
        inativos_com_captacao = [
            u for u in usuarios
            if not u.ativo and counts.get(str(u.id_usuarios or "").strip().upper(), 0)
        ]

        por_time: Dict[str, List[Any]] = {}
        for u in ativos + inativos_com_captacao:
            por_time.setdefault(str(u.team or ""), []).append(u)

        # Consome pelo ID do usuario. Cada chave e consumida uma vez — conta duplicada no
        # cadastro tem id diferente, entao nao ha mais o risco de dobrar.
        usadas: set = set()

        def consumir(u) -> float:
            k = str(u.id_usuarios or "").strip().upper()
            if not k or k in usadas:
                return 0.0
            usadas.add(k)
            return round(counts.get(k, 0.0), 2)

        times: List[Dict[str, Any]] = []
        for eq in equipes:
            membros = por_time.get(str(eq.id_equipe), [])
            if not membros:
                continue

            # Roster = quem esta ATIVO hoje. Quem saiu aparece a parte, abaixo.
            corretores = sorted(
                [u for u in membros
                 if u.ativo and str(u.permissao or "").lower() == "corretor"],
                key=lambda u: (u.nome or "").lower(),
            )
            gerentes = [u for u in membros
                        if u.ativo and str(u.permissao or "").lower() == "gerente"]
            # Quem nao e nem um nem outro so entra se captou — assistente sem captacao
            # nao tem por que ocupar linha no texto do grupo.
            outros = sorted(
                [u for u in membros
                 if u.ativo
                 and str(u.permissao or "").lower() not in ("corretor", "gerente")
                 and counts.get(str(u.id_usuarios or "").strip().upper(), 0)],
                key=lambda u: (u.nome or "").lower(),
            )
            # Desativado que captou no mes: conta para a equipe, mas fica marcado — o
            # gerente precisa saber que aquele numero nao volta no mes que vem.
            saiu = sorted(
                [u for u in membros if not u.ativo],
                key=lambda u: (u.nome or "").lower(),
            )

            linhas = []
            for u in corretores:
                linhas.append({"nome": u.nome, "papel": "corretor", "total": consumir(u)})
            for u in gerentes:
                linhas.append({"nome": u.nome, "papel": "gerente", "total": consumir(u)})
            for u in outros:
                linhas.append({"nome": u.nome, "papel": "outro", "total": consumir(u)})
            for u in saiu:
                linhas.append({"nome": u.nome, "papel": "inativo", "total": consumir(u)})

            total = round(sum(x["total"] for x in linhas), 2)
            com_captacao = sum(1 for x in linhas if x["total"])
            bateram = sum(1 for x in linhas if x["papel"] == "corretor" and x["total"] >= meta)
            times.append({
                "id_equipe": eq.id_equipe,
                "nome": eq.nome,
                "linhas": linhas,
                "total": total,
                "membros": len(linhas),
                "corretores": len(corretores),
                "com_captacao": com_captacao,
                "sem_captacao": len(linhas) - com_captacao,
                "bateram_meta": bateram,
                "meta_equipe": len(corretores) * meta,
                "pct_meta": round(total / (len(corretores) * meta) * 100, 1) if corretores else None,
            })

        # O que sobrou sem dono. Aparece no retorno de proposito: sem isso a soma das
        # equipes fica menor que o ranking e ninguem sabe por que.
        orfas = sorted(
            ({"nome": rotulo_original.get(k, k), "total": v}
             for k, v in counts.items() if k not in usadas and v),
            key=lambda x: -x["total"],
        )

        total_geral = round(sum(t["total"] for t in times), 2)
        return {
            "ok": True,
            "mes": f"{ano}-{m:02d}",
            "meta": meta,
            "equipes": sorted(times, key=lambda t: -t["total"]),
            "orfas": orfas,
            "resumo": {
                "total_captacoes": total_geral,
                "total_ranking": round(sum(counts.values()), 2),
                "sem_dono": round(sum(x["total"] for x in orfas), 2),
                "equipes": len(times),
                "corretores": sum(t["corretores"] for t in times),
                "com_captacao": sum(t["com_captacao"] for t in times),
                "bateram_meta": sum(t["bateram_meta"] for t in times),
                "meta_total": sum(t["meta_equipe"] for t in times),
                # De onde saiu o rateio de cada captacao. `igual` e aproximacao: imovel
                # que a varredura do catalogo ainda nao alcancou.
                "rateio": getattr(self, "_origem_rateio", {}),
            },
        }

    def gerar_texto_fechamento(self, mes: str, meta: int = 4) -> str:
        """Texto do fechamento para colar no grupo. Renderiza `fechamento()`."""
        MESES = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
                 "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
        dados = self.fechamento(mes, meta)
        ano, m = int(dados["mes"][:4]), int(dados["mes"][5:7])

        linhas = [f"*{MESES[m]}/{str(ano)[2:]}*", ""]
        for eq in dados["equipes"]:
            # Asteriscos: o texto e colado no WhatsApp, que os le como negrito.
            linhas.append(f"*Equipe {eq['nome']}*")
            for item in eq["linhas"]:
                n = self._formatar_total(item["total"])
                if item["papel"] == "corretor":
                    linhas.append(f"{item['nome']}: {n if item['total'] else ''}/{meta}")
                elif item["papel"] == "gerente":
                    linhas.append(f"{item['nome']} Gerente: {n}")
                elif item["papel"] == "inativo":
                    linhas.append(f"{item['nome']} (saiu): {n}")
                else:
                    linhas.append(f"{item['nome']}: {n}")
            linhas.append(f"*TOTAL Equipe {eq['nome']} - {self._formatar_total(eq['total'])}*")
            linhas.append("")

        # Captacao cujo captador nao esta no cadastro fica visivel no fim, em vez de
        # simplesmente sumir da conta.
        if dados["orfas"]:
            linhas.append("Sem equipe identificada:")
            for o in dados["orfas"]:
                linhas.append(f"{o['nome']}: {self._formatar_total(o['total'])}")
            linhas.append("")

        linhas.append(f"*TOTAL 61 - {self._formatar_total(dados['resumo']['total_ranking'])}*")
        return "\n".join(linhas).rstrip()

    # =========================================================
    # Relatório VGC (captador) por foco — regra por ano (DAX Power BI)
    # =========================================================
    def _foco_por_codigo(self) -> Dict[str, bool]:
        """Mapa código do imóvel -> tem foco (foco_pp OU foco_ac), da Dim_Imovel
        (`imoveis_legado`). O código tem duplicatas (reanúncios) -> True prevalece."""
        from app.database import SessionLocal
        from app.models.legado_diversos import ImovelLegado

        session = SessionLocal()
        try:
            rows = session.query(
                ImovelLegado.codigo, ImovelLegado.foco_pp, ImovelLegado.foco_ac
            ).all()
        finally:
            session.close()

        mapa: Dict[str, bool] = {}
        for codigo, pp, ac in rows:
            cod = str(codigo or "").strip()
            if not cod:
                continue
            foco = bool(pp) or bool(ac)
            if foco or cod not in mapa:
                mapa[cod] = foco
        return mapa

    @staticmethod
    def _codigo_limpo(valor) -> str:
        """Normaliza o código do imóvel.

        `contratos.codigo_imovel` vem da planilha como número formatado ("10.961,00"),
        enquanto a Dim_Imovel guarda "10961" — sem isso o cruzamento de foco dá zero.
        """
        texto = str(valor or "").strip()
        if not texto:
            return ""
        return "".join(ch for ch in texto.split(",")[0] if ch.isdigit())

    def _foco_por_codigo_captacao(self) -> Dict[str, bool]:
        """Foco vindo de `fato_captacao` — cobre imóvel que ainda não está na Dim_Imovel."""
        from app.database import SessionLocal
        from app.models.fato_bases import FatoCaptacao

        session = SessionLocal()
        try:
            rows = session.query(
                FatoCaptacao.codigo_imovel, FatoCaptacao.foco_pp, FatoCaptacao.foco_ac
            ).all()
        finally:
            session.close()

        mapa: Dict[str, bool] = {}
        for codigo, pp, ac in rows:
            cod = self._codigo_limpo(codigo)
            if not cod:
                continue
            foco = bool(pp) or bool(ac)
            if foco or cod not in mapa:
                mapa[cod] = foco
        return mapa

    def _captacoes_foco_por_captador(
        self, start: Optional[str], end: Optional[str]
    ) -> Dict[str, Dict[str, int]]:
        """Captações por captador em TODO o período, da base histórica de captação —
        NÃO da venda. Fonte: `eventos_imovel_legado` (tipo_evento='captacao', importada
        da planilha Base Inteligência, ~5,4k desde 2022) UNIÃO `fato_captacao`
        (lançamentos correntes do site). Cada captador1/2/3 conta 1 captação. O foco de
        cada captação vem da Dim_Imovel (`imoveis_legado`) pelo código; se o código não
        existir lá, cai no snapshot de foco do próprio registro (quando houver, caso do
        fato_captacao).

        Dedup por **(código, captador)** — SEM a data. As duas fontes descrevem os mesmos
        imóveis com datas divergentes (o import da planilha bate com `eventos_imovel_legado`
        em 2643 pares, e 2588 deles têm data diferente — dias ou meses). Com a data na
        chave, esses 2588 contariam duas vezes. Mesmo imóvel + mesmo captador = 1 captação,
        independente de qual fonte registrou qual data.

        Se o banco estiver vazio nessas tabelas, o resultado vem vazio — a Base
        Inteligência (Google Sheet) seria o fallback a implementar."""
        from app.database import SessionLocal
        from app.models.eventos_imovel_legado import EventoImovelLegado
        from app.models.fato_bases import FatoCaptacao

        s_dt = self._parse_date(start) if start else None
        e_dt = self._parse_date(end) if end else None
        foco_map = self._foco_por_codigo()

        acc: Dict[str, Dict[str, int]] = {}
        seen = set()
        _INVALIDOS = {"", "0", "-", "NAN", "NONE"}

        def _dentro(d) -> Optional[bool]:
            # None se sem data E há filtro de período (descarta); senão True/False.
            if d is None:
                return None if (s_dt is not None or e_dt is not None) else True
            dts = pd.Timestamp(d)
            if s_dt is not None and dts < s_dt:
                return False
            if e_dt is not None and dts > e_dt:
                return False
            return True

        def _add(codigo, caps, data, foco_snapshot):
            if not _dentro(data):
                return
            cod = str(codigo or "").strip()
            foco = foco_map.get(cod)
            if foco is None:  # imóvel fora da Dim_Imovel -> usa snapshot do registro
                foco = bool(foco_snapshot)
            for cap in caps:
                c = str(cap or "").strip().upper()
                if c in _INVALIDOS:
                    continue
                chave = (cod, c)
                if chave in seen:
                    continue
                seen.add(chave)
                a = acc.setdefault(c, {"n": 0, "n_foco": 0})
                a["n"] += 1
                if foco:
                    a["n_foco"] += 1

        session = SessionLocal()
        try:
            eventos = session.query(EventoImovelLegado).filter(
                EventoImovelLegado.tipo_evento == "captacao"
            ).all()
            for e in eventos:
                _add(e.codigo_imovel, (e.captador1, e.captador2, e.captador3),
                     e.data_evento, None)

            for f in session.query(FatoCaptacao).all():
                snap = bool(f.foco_pp) or bool(f.foco_ac)
                _add(f.codigo_imovel, (f.captador1, f.captador2, f.captador3),
                     f.data_entrada, snap)
        finally:
            session.close()

        return acc

    def relatorio_vgc_foco(self, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        """VGV do CAPTADOR por corretor, seguindo a regra do Power BI:
          - ano <= 2025: valor pré-calculado V3 (captador 1) / V4 (captador 2);
          - ano >= 2026: Valor do negócio ÷ nº de captadores.
        Fonte do VGV: `vendas_legado` (Fato_Venda, flag `foco`).

        **Captações e Captações no Foco NÃO vêm da venda** — vêm da base histórica de
        captação (`eventos_imovel_legado` + `fato_captacao`) cruzada com a Dim_Imovel
        p/ o foco. Assim contam TODO o período (imóvel captado que nunca vendeu também
        entra), não só o que virou venda. Ver `_captacoes_foco_por_captador`."""
        from app.database import SessionLocal
        from app.models.contrato import Contrato
        from app.models.venda_legado import VendaLegado

        s_dt = self._parse_date(start) if start else None
        e_dt = self._parse_date(end) if end else None

        session = SessionLocal()
        try:
            vendas = session.query(VendaLegado).all()
            contratos = session.query(Contrato).filter(Contrato.data_contrato.isnot(None)).all()
        finally:
            session.close()

        id_to_name, name_to_id = self._maps_corretores()
        vgv: Dict[str, Dict[str, float]] = {}
        vgc: Dict[str, Dict[str, float]] = {}

        def _acumular(alvo, chave, valor, tem_foco):
            if not valor:
                return
            a = alvo.setdefault(chave.upper(), {"total": 0.0, "foco": 0.0, "nao_foco": 0.0})
            a["total"] += valor
            a["foco" if tem_foco else "nao_foco"] += valor

        for v in vendas:
            d = v.data_venda
            if not d:
                continue
            dts = pd.Timestamp(d)
            if s_dt is not None and dts < s_dt:
                continue
            if e_dt is not None and dts > e_dt:
                continue
            ano = d.year

            cap1 = str(v.captador_1 or "").strip()
            cap2 = str(v.captador_2 or "").strip()
            tem1 = cap1 not in ("", "0")
            tem2 = cap2 not in ("", "0") and cap2 != cap1
            ncap = (1 if tem1 else 0) + (1 if tem2 else 0)
            vn = self._to_float_br(v.valor_do_negocio)
            foco = bool(v.foco)

            # VGC do captador: Valor_Total_61 é dividido entre os LADOS (venda/captação)
            # e depois entre os membros do lado — mesma regra do `_calc_vgc_geral_algoritmo`.
            v61 = self._to_float_br(v.valor_total_61)
            vendedores = {str(v.vendedor_1 or "").strip(), str(v.vendedor_2 or "").strip()}
            vendedores = {n for n in vendedores if n not in ("", "0")}
            n_lados = (1 if vendedores else 0) + (1 if ncap else 0)
            vgc_por_captador = ((v61 / n_lados) / ncap) if (v61 > 0 and n_lados and ncap) else 0.0

            for is_cap, cap, vcol in ((tem1, cap1, v.v3), (tem2, cap2, v.v4)):
                if not is_cap:
                    continue
                if ano <= 2025:
                    val = self._to_float_br(vcol)
                else:  # 2026 em diante
                    val = (vn / ncap) if ncap else 0.0
                _acumular(vgv, cap, val, foco)
                _acumular(vgc, cap, vgc_por_captador, foco)

        # `vendas_legado` é carga única da planilha e parou em 18/06/2026 — sem isto o
        # VGV do relatório sai ZERADO de julho em diante. Os contratos que a planilha não
        # tem entram por `contratos` (mantida viva pelo cron do sync), com dedup por
        # id do contrato. Valor pelo mesmo critério de 2026: negócio ÷ nº de captadores.
        ja_na_planilha = {str(v.idcontrato or "").strip() for v in vendas if v.idcontrato}
        # Só completa DEPOIS da última venda da planilha. O histórico fechado continua
        # idêntico ao Power BI: contrato antigo ausente da planilha foi decisão de lá,
        # não buraco de carga.
        datas_planilha = [v.data_venda for v in vendas if v.data_venda]
        corte = max(datas_planilha) if datas_planilha else None
        foco_dim = self._foco_por_codigo()
        foco_capt = self._foco_por_codigo_captacao()

        for ct in contratos:
            if str(ct.id_contrato or "").strip() in ja_na_planilha:
                continue
            d = ct.data_contrato
            if corte is not None and d <= corte:
                continue
            dts = pd.Timestamp(d)
            if s_dt is not None and dts < s_dt:
                continue
            if e_dt is not None and dts > e_dt:
                continue

            captadores = {
                self._limpar_nome(ct.corretor_captador_1_nome),
                self._limpar_nome(ct.corretor_captador_2_nome),
            }
            captadores = {n for n in captadores if n}
            if not captadores:
                continue

            valor_negocio = float(ct.valor_negocio or 0)
            if valor_negocio <= 0:
                continue
            por_captador = valor_negocio / len(captadores)

            vendedores = {
                self._limpar_nome(ct.corretor_venda_1_nome),
                self._limpar_nome(ct.corretor_venda_2_nome),
            }
            vendedores = {n for n in vendedores if n}
            n_lados = (1 if vendedores else 0) + 1  # captadores existem (checado acima)
            v61 = float(ct.valor_total_61 or 0)
            vgc_por_captador = (v61 / n_lados) / len(captadores) if v61 > 0 else 0.0

            cod = self._codigo_limpo(ct.codigo_imovel)
            foco = foco_dim.get(cod)
            if foco is None:
                foco = bool(foco_capt.get(cod, False))

            for nome in captadores:
                # `vendas_legado` guarda o ID do captador; o contrato guarda o NOME.
                chave = name_to_id.get(nome.upper(), nome.upper())
                _acumular(vgv, chave, por_captador, foco)
                _acumular(vgc, chave, vgc_por_captador, foco)

        # Captações (todo período) da base histórica de captação, cruzada c/ Dim_Imovel.
        capt = self._captacoes_foco_por_captador(start, end)

        rows = []
        # NÃO aplica a exclusão do ranking ao vivo: este relatório é histórico e bate
        # com o Power BI (que inclui todos os captadores).
        vazio = {"total": 0.0, "foco": 0.0, "nao_foco": 0.0}
        for cap in set(vgv) | set(vgc) | set(capt):
            nome = id_to_name.get(cap.upper(), cap)
            a = vgv.get(cap, vazio)
            g = vgc.get(cap, vazio)
            c = capt.get(cap, {"n": 0, "n_foco": 0})
            rows.append({
                "Corretor": nome,
                "VGV Captador (Total)": round(a["total"], 2),
                "VGV Captador (Foco)": round(a["foco"], 2),
                "VGV Captador (Não Foco)": round(a["nao_foco"], 2),
                "VGC Captador (Total)": round(g["total"], 2),
                "VGC Captador (Foco)": round(g["foco"], 2),
                "VGC Captador (Não Foco)": round(g["nao_foco"], 2),
                "Captações": int(c["n"]),
                "Captações no Foco": int(c["n_foco"]),
            })

        df = pd.DataFrame(rows, columns=[
            "Corretor", "VGV Captador (Total)", "VGV Captador (Foco)", "VGV Captador (Não Foco)",
            "VGC Captador (Total)", "VGC Captador (Foco)", "VGC Captador (Não Foco)",
            "Captações", "Captações no Foco",
        ])
        if not df.empty:
            df = df.sort_values("VGV Captador (Foco)", ascending=False).reset_index(drop=True)
        return df

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
            vgc_bruto_corretor = 0.0
            vgc_fator_corretor = 0.0

            if is_vend and len(vendedores) > 0:
                if v61 > 0:
                    vgc_bruto_corretor += (v61 / n_lados) / len(vendedores)
                    vgc_fator_corretor += (v61 / 0.06 / n_lados) / len(vendedores)

            if is_cap and len(captadores) > 0:
                if v61 > 0:
                    vgc_bruto_corretor += (v61 / n_lados) / len(captadores)
                    vgc_fator_corretor += (v61 / 0.06 / n_lados) / len(captadores)

            # VGV (parte): cada lado divide o Valor_Negocio CHEIO entre seus
            # membros (venda e captacao independentes). Quem esta nos dois lados
            # conta 1x (max). Casa com o ranking. Ex: 3M, 1v+2c => vend 3M,
            # cada captador 1.5M.
            share_vend_vn = (vn / len(vendedores)) if (is_vend and vendedores) else 0.0
            share_cap_vn = (vn / len(captadores)) if (is_cap and captadores) else 0.0
            vgv_part = max(share_vend_vn, share_cap_vn)

            # VGC (parte): SOMA de todas as partes da pessoa (venda + captacao).
            # Ex: vendedor+captador sozinho = (v61/2) + (v61/2) = v61 cheio.
            vgc_part = vgc_bruto_corretor

            # Relatorio UNIFICADO (sem diferenciar VGV/VGC): inclui se a pessoa
            # participou de qualquer lado. valor_corretor mantido p/ compatibilidade.
            valor_corretor = vgc_bruto_corretor if kind == "vgc_geral" else vgv_part
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

    def get_relatorio_vgc_captacao(
        self,
        start: Optional[str],
        end: Optional[str],
        apply_factor: bool = False,
    ) -> Dict[str, Any]:
        """Cruza o VGC dos contratos com a classificação de foco da Dim_Imovel."""
        from app.database import SessionLocal
        from app.models.legado_diversos import ImovelLegado

        vendas = self.load_vendas(start, end)
        detalhes: List[Dict[str, Any]] = []
        por_corretor: Dict[tuple, Dict[str, float]] = {}
        por_foco: Dict[str, Dict[str, float]] = {}
        _, name_to_id = self._maps_corretores()

        session = SessionLocal()
        try:
            foco_por_codigo: Dict[str, Dict[str, bool]] = {}
            for imovel in session.query(ImovelLegado).filter(ImovelLegado.codigo.isnot(None)).all():
                codigo = str(imovel.codigo or "").strip().upper()
                if not codigo:
                    continue
                foco = foco_por_codigo.setdefault(codigo, {"pp": False, "ac": False})
                # O código pode se repetir por reanúncio; preserva qualquer marcação positiva.
                foco["pp"] = foco["pp"] or bool(imovel.foco_pp)
                foco["ac"] = foco["ac"] or bool(imovel.foco_ac)
        finally:
            session.close()

        for _, row in vendas.iterrows():
            vendedores = {
                self._limpar_nome(row.get("Corretor_Venda_1_Nome")),
                self._limpar_nome(row.get("Corretor_Venda_2_Nome")),
            }
            captadores = {
                self._limpar_nome(row.get("Corretor_Captador_1_Nome")),
                self._limpar_nome(row.get("Corretor_Captador_2_Nome")),
            }
            vendedores = {nome for nome in vendedores if nome}
            captadores = {nome for nome in captadores if nome}
            if not captadores:
                continue

            valor_negocio = float(row.get("Valor_Negocio", 0.0) or 0.0)
            vgc_contrato = float(row.get("Valor_Total_61", 0.0) or 0.0)
            if apply_factor and vgc_contrato > 0:
                vgc_contrato /= 0.06

            numero_lados = 1 + (1 if vendedores else 0)
            codigo_imovel = str(row.get("Codigo_Imovel", "")).strip()
            foco = foco_por_codigo.get(codigo_imovel.upper())
            if foco is None:
                classificacao = "NÃO LOCALIZADO"
            elif foco["pp"] and foco["ac"]:
                classificacao = "FOCO PP + AC"
            elif foco["pp"]:
                classificacao = "FOCO PP"
            elif foco["ac"]:
                classificacao = "FOCO AC"
            else:
                classificacao = "NÃO FOCO"

            participantes = vendedores | captadores
            shares: Dict[str, float] = {}
            valor_por_lado = vgc_contrato / numero_lados
            for nome in vendedores:
                shares[nome] = shares.get(nome, 0.0) + valor_por_lado / len(vendedores)
            for nome in captadores:
                shares[nome] = shares.get(nome, 0.0) + valor_por_lado / len(captadores)

            empreendimento = ""
            for coluna in ["Empreendimento", "empreendimento", "Endereco", "Endereco_Imovel", "Descricao"]:
                valor = str(row.get(coluna, "")).strip()
                if valor and valor.lower() not in {"nan", "none"}:
                    empreendimento = valor
                    break

            data_contrato = str(row.get("Data_Contrato", "")).strip().split(" ")[0].split("T")[0]
            for corretor in sorted(participantes):
                if self._is_excluded(
                    nome=corretor,
                    id_corretor=name_to_id.get(corretor, ""),
                ):
                    continue
                detalhes.append({
                    "data_contrato": data_contrato,
                    "id_contrato": str(row.get("Id_Contrato", "")).strip(),
                    "contrato": str(row.get("Contrato", "")).strip(),
                    "empreendimento": empreendimento,
                    "codigo_imovel": codigo_imovel,
                    "classificacao_foco": classificacao,
                    "foco": classificacao.startswith("FOCO"),
                    "corretor": corretor,
                    "papel": "VENDA + CAPTAÇÃO" if corretor in vendedores and corretor in captadores else ("VENDA" if corretor in vendedores else "CAPTAÇÃO"),
                    "captadores": ", ".join(sorted(captadores)),
                    "vendedores": ", ".join(sorted(vendedores)),
                    "valor_negocio": round(valor_negocio, 2),
                    "vgc_61_contrato": round(vgc_contrato, 2),
                    "vgc_do_corretor": round(shares[corretor], 2),
                })
                chave = (classificacao, corretor)
                acc = por_corretor.setdefault(chave, {"qtd": 0, "vgc": 0.0, "vgv": 0.0})
                acc["qtd"] += 1
                acc["vgc"] += shares[corretor]
                acc["vgv"] += valor_negocio

            foco_acc = por_foco.setdefault(classificacao, {"qtd": 0, "vgc": 0.0, "vgv": 0.0})
            foco_acc["qtd"] += 1
            foco_acc["vgc"] += vgc_contrato
            foco_acc["vgv"] += valor_negocio

        ordenado = sorted(por_corretor.items(), key=lambda item: (item[0][0], -item[1]["vgc"], item[0][1]))
        ranking = [
            {
                "classificacao_foco": chave[0],
                "corretor": chave[1],
                "qtd_negocios": int(valores["qtd"]),
                "vgc_corretor": round(valores["vgc"], 2),
                "vgv_imoveis": round(valores["vgv"], 2),
            }
            for chave, valores in ordenado
        ]
        resumo = [
            {
                "classificacao_foco": classificacao,
                "qtd_negocios": int(valores["qtd"]),
                "vgc_total": round(valores["vgc"], 2),
                "vgv_total": round(valores["vgv"], 2),
            }
            for classificacao, valores in sorted(por_foco.items())
        ]
        detalhes.sort(key=lambda item: (item["classificacao_foco"], item["data_contrato"], item["corretor"]))
        return {
            "start": start,
            "end": end,
            "apply_factor": apply_factor,
            "total_vgc": round(sum(item["vgc_total"] for item in resumo), 2),
            "resumo": resumo,
            "ranking": ranking,
            "detalhes": detalhes,
        }

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
