# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import tempfile
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

# Tenta importar gspread, mas permite execução local sem ele
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    gspread = None
    ServiceAccountCredentials = None


# ==========================================================
# CONFIG / DTOs
# ==========================================================
@dataclass
class MetaGerenteConfig:
    ano_relatorio: int
    mes_relatorio: int
    sheet_id_contratos: str = "1cw4mB_fx-8YmnmLByx4au5ytpbQMV-OY1btOIoYAufg"
    sheet_id_base_inteligencia: str = "1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw"
    sheet_id_visitas: str = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"
    aba_contratos: str = "Vendas"
    aba_dim_corretor: str = "Dim_Corretor"
    aba_dim_gerente: str = "Dim_Gerente"
    aba_fato_captacao: str = "Fato_Captacao"
    aba_fato_visitas: str = "Fato_Visitas"
    caminho_credencial: str = "../cred.json"
    gerentes_por_pagina_painel: int = 3

    @property
    def nome_mes(self) -> str:
        nomes = {
            1: "janeiro",
            2: "fevereiro",
            3: "marco",
            4: "abril",
            5: "maio",
            6: "junho",
            7: "julho",
            8: "agosto",
            9: "setembro",
            10: "outubro",
            11: "novembro",
            12: "dezembro",
        }
        return nomes.get(self.mes_relatorio, "mes")

    @property
    def nome_arquivo_pdf(self) -> str:
        return f"relatorio_metas_gerentes_{self.ano_relatorio}_{self.mes_relatorio:02d}.pdf"


class MetaGerenteService:
    def __init__(self, config: MetaGerenteConfig):
        self.config = config

    # ==========================================================
    # FUNÇÕES DE APOIO
    # ==========================================================
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
    def limpar_nome(n):
        if pd.isna(n) or str(n).strip() in ["", "-", "nan", "NAN", "None"]:
            return ""
        return str(n).strip().upper()

    @staticmethod
    def formatar_moeda_br(valor):
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def formatar_numero_br_sem_moeda(valor):
        try:
            valor = float(valor)
        except Exception:
            valor = 0.0
        return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def valor_positivo(self, x):
        if pd.isna(x):
            return False
        try:
            return float(self._to_float_br(x)) > 0
        except Exception:
            return False

    def autenticar_google_sheets(self):
        if not gspread:
            raise ImportError(
                "Biblioteca gspread não instalada. Instale com:\n"
                "pip install gspread oauth2client"
            )

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            self.config.caminho_credencial,
            scope
        )
        client = gspread.authorize(creds)
        return client

    def carregar_aba_por_id(self, sheet_id: str, nome_aba: str) -> pd.DataFrame:
        client = self.autenticar_google_sheets()
        planilha = client.open_by_key(sheet_id)
        aba = planilha.worksheet(nome_aba)
        dados = aba.get_all_values()

        if not dados:
            return pd.DataFrame()

        header = dados[0]
        rows = dados[1:]

        df = pd.DataFrame(rows, columns=header)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all")
        return df

    @staticmethod
    def dividir_em_blocos(lista, tamanho):
        for i in range(0, len(lista), tamanho):
            yield lista[i:i + tamanho]

    # ==========================================================
    # CARREGAMENTO DAS BASES
    # ==========================================================
    def carregar_contratos(self):
        return self.carregar_aba_por_id(
            self.config.sheet_id_contratos,
            self.config.aba_contratos
        )

    def carregar_base_inteligencia(self):
        df_corretor = self.carregar_aba_por_id(
            self.config.sheet_id_base_inteligencia,
            self.config.aba_dim_corretor
        )
        df_gerente = self.carregar_aba_por_id(
            self.config.sheet_id_base_inteligencia,
            self.config.aba_dim_gerente
        )
        df_captacao = self.carregar_aba_por_id(
            self.config.sheet_id_base_inteligencia,
            self.config.aba_fato_captacao
        )
        return df_corretor, df_gerente, df_captacao

    # ==========================================================
    # MAPAS
    # ==========================================================
    def montar_mapas_dim_corretor(
        self,
        df_dim_corretor: pd.DataFrame,
        df_dim_gerente: pd.DataFrame
    ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str], Dict[str, str]]:
        """
        Retorna:
        - mapa_nome_corretor_para_gerente_nome
        - mapa_nome_corretor_para_id_gerente
        - mapa_id_corretor_para_gerente_nome
        - mapa_id_corretor_para_nome_corretor
        """
        dfc = df_dim_corretor.copy()
        dfg = df_dim_gerente.copy()

        dfc.columns = [str(c).strip() for c in dfc.columns]
        dfg.columns = [str(c).strip() for c in dfg.columns]

        dfc["Nome_norm"] = dfc["Nome"].apply(self.limpar_nome)
        dfc["IdGerente_norm"] = dfc["IdGerente"].astype(str).str.strip().str.upper()
        dfc["IdCorretor_norm"] = dfc["IdCorretor"].astype(str).str.strip().str.upper()

        dfg["IdGerente_norm"] = dfg["IdGerente"].astype(str).str.strip().str.upper()
        dfg["NomeGerente_norm"] = dfg["Nome"].apply(self.limpar_nome)

        mapa_idgerente_para_nome = dict(zip(dfg["IdGerente_norm"], dfg["NomeGerente_norm"]))

        mapa_corretor_para_idgerente = {}
        mapa_corretor_para_nomegerente = {}
        mapa_id_corretor_para_gerente_nome = {}
        mapa_id_corretor_para_nome_corretor = {}

        for _, row in dfc.iterrows():
            nome_corretor = row.get("Nome_norm", "")
            id_gerente = row.get("IdGerente_norm", "")
            id_corretor = row.get("IdCorretor_norm", "")

            nome_gerente = mapa_idgerente_para_nome.get(id_gerente, "")

            if nome_corretor:
                mapa_corretor_para_idgerente[nome_corretor] = id_gerente
                mapa_corretor_para_nomegerente[nome_corretor] = nome_gerente

            if id_corretor:
                mapa_id_corretor_para_gerente_nome[id_corretor] = nome_gerente
                mapa_id_corretor_para_nome_corretor[id_corretor] = nome_corretor

        return (
            mapa_corretor_para_nomegerente,
            mapa_corretor_para_idgerente,
            mapa_id_corretor_para_gerente_nome,
            mapa_id_corretor_para_nome_corretor,
        )

    # ==========================================================
    # VGV DOS GERENTES VIA VENDAS
    # ==========================================================
    def processar_gerentes_via_dim_corretor(
        self,
        df_subset: pd.DataFrame,
        mapa_corretor_gerente: Dict[str, str]
    ) -> Dict[str, Any]:
        vgv_cap, vgv_vend, vgv_geral = {}, {}, {}
        vgc_cap, vgc_vend, vgc_geral = {}, {}, {}

        vend_qtd = {}
        geral_qtd = {}

        detalhes_vgv_cap = {}
        detalhes_vgv_vend = {}
        detalhes_vgv_geral = {}

        for _, row in df_subset.iterrows():
            v_imovel = self._to_float_br(row.get("Valor_Negocio", 0))
            v_comissao_total = self._to_float_br(row.get("Valor_Total_61", 0))

            corretores_venda = []
            if self.valor_positivo(row.get("$_Corretor_Venda_1")):
                nome = self.limpar_nome(row.get("Corretor_Venda_1_Nome"))
                if nome:
                    corretores_venda.append(nome)

            if self.valor_positivo(row.get("$_Corretor_Venda_2")):
                nome = self.limpar_nome(row.get("Corretor_Venda_2_Nome"))
                if nome and nome not in corretores_venda:
                    corretores_venda.append(nome)

            corretores_capt = []
            if self.valor_positivo(row.get("$_Corretor_Captador_1")):
                nome = self.limpar_nome(row.get("Corretor_Captador_1_Nome"))
                if nome:
                    corretores_capt.append(nome)

            if self.valor_positivo(row.get("$_Corretor_Captador_2")):
                nome = self.limpar_nome(row.get("Corretor_Captador_2_Nome"))
                if nome and nome not in corretores_capt:
                    corretores_capt.append(nome)

            gerentes_venda_dict = {}
            for corretor in corretores_venda:
                gerente = mapa_corretor_gerente.get(corretor, "")
                if gerente:
                    gerentes_venda_dict.setdefault(gerente, []).append(corretor)

            gerentes_capt_dict = {}
            for corretor in corretores_capt:
                gerente = mapa_corretor_gerente.get(corretor, "")
                if gerente:
                    gerentes_capt_dict.setdefault(gerente, []).append(corretor)

            for gerente, lista_corretores in gerentes_venda_dict.items():
                vgv_vend[gerente] = vgv_vend.get(gerente, 0) + v_imovel
                vend_qtd[gerente] = vend_qtd.get(gerente, 0) + 1

                detalhes_vgv_vend.setdefault(gerente, {})
                quota = v_imovel / len(lista_corretores)

                for corretor in lista_corretores:
                    detalhes_vgv_vend[gerente][corretor] = (
                        detalhes_vgv_vend[gerente].get(corretor, 0) + quota
                    )

            for gerente, lista_corretores in gerentes_capt_dict.items():
                vgv_cap[gerente] = vgv_cap.get(gerente, 0) + v_imovel

                detalhes_vgv_cap.setdefault(gerente, {})
                quota = v_imovel / len(lista_corretores)

                for corretor in lista_corretores:
                    detalhes_vgv_cap[gerente][corretor] = (
                        detalhes_vgv_cap[gerente].get(corretor, 0) + quota
                    )

            gerentes_geral_dict = {}

            for gerente, lista_corretores in gerentes_venda_dict.items():
                gerentes_geral_dict.setdefault(gerente, set()).update(lista_corretores)

            for gerente, lista_corretores in gerentes_capt_dict.items():
                gerentes_geral_dict.setdefault(gerente, set()).update(lista_corretores)

            for gerente, conjunto_corretores in gerentes_geral_dict.items():
                vgv_geral[gerente] = vgv_geral.get(gerente, 0) + v_imovel
                geral_qtd[gerente] = geral_qtd.get(gerente, 0) + 1

                detalhes_vgv_geral.setdefault(gerente, {})
                lista = list(conjunto_corretores)
                quota = v_imovel / len(lista)

                for corretor in lista:
                    detalhes_vgv_geral[gerente][corretor] = (
                        detalhes_vgv_geral[gerente].get(corretor, 0) + quota
                    )

            if gerentes_venda_dict and gerentes_capt_dict:
                parcela_venda = v_comissao_total * 0.5
                parcela_capt = v_comissao_total * 0.5
            elif gerentes_venda_dict:
                parcela_venda = v_comissao_total
                parcela_capt = 0
            elif gerentes_capt_dict:
                parcela_venda = 0
                parcela_capt = v_comissao_total
            else:
                parcela_venda = parcela_capt = 0

            if gerentes_venda_dict and parcela_venda:
                quota_gerente_venda = parcela_venda / len(gerentes_venda_dict)
                for gerente in gerentes_venda_dict:
                    vgc_vend[gerente] = vgc_vend.get(gerente, 0) + quota_gerente_venda
                    vgc_geral[gerente] = vgc_geral.get(gerente, 0) + quota_gerente_venda

            if gerentes_capt_dict and parcela_capt:
                quota_gerente_capt = parcela_capt / len(gerentes_capt_dict)
                for gerente in gerentes_capt_dict:
                    vgc_cap[gerente] = vgc_cap.get(gerente, 0) + quota_gerente_capt
                    vgc_geral[gerente] = vgc_geral.get(gerente, 0) + quota_gerente_capt

        return {
            "VGV_CAP": vgv_cap,
            "VGV_VEND": vgv_vend,
            "VGV_GERAL": vgv_geral,
            "VGC_CAP": vgc_cap,
            "VGC_VEND": vgc_vend,
            "VGC_GERAL": vgc_geral,
            "VEND_QTD": vend_qtd,
            "GERAL_QTD": geral_qtd,
            "DETALHES_VGV_CAP": detalhes_vgv_cap,
            "DETALHES_VGV_VEND": detalhes_vgv_vend,
            "DETALHES_VGV_GERAL": detalhes_vgv_geral,
        }

    # ==========================================================
    # CAPTAÇÕES DOS GERENTES VIA FATO_CAPTACAO
    # ==========================================================
    def processar_captacoes_por_gerente(
        self,
        df_captacao: pd.DataFrame,
        mapa_id_corretor_para_gerente_nome: Dict[str, str]
    ) -> Dict[str, int]:
        cap_qtd = {}

        if df_captacao.empty:
            return cap_qtd

        dfc = df_captacao.copy()
        dfc.columns = [str(c).strip() for c in dfc.columns]

        if "Captador1" not in dfc.columns:
            raise ValueError("A aba Fato_Captacao precisa ter a coluna 'Captador1'.")

        coluna_data = None
        for c in ["Data_Captacao", "DataCaptacao", "Data", "DataEntrada", "DtCaptacao"]:
            if c in dfc.columns:
                coluna_data = c
                break

        if coluna_data is None:
            raise ValueError(
                "Não encontrei coluna de data em Fato_Captacao. "
                "Use uma destas: Data_Captacao, DataCaptacao, Data, DataEntrada, DtCaptacao."
            )

        dfc[coluna_data] = pd.to_datetime(dfc[coluna_data], errors="coerce")
        dfc = dfc[
            (dfc[coluna_data].dt.year == self.config.ano_relatorio) &
            (dfc[coluna_data].dt.month == self.config.mes_relatorio)
        ].copy()

        dfc["IdCorretor_norm"] = dfc["Captador1"].astype(str).str.strip().str.upper()

        for _, row in dfc.iterrows():
            id_corretor = row.get("IdCorretor_norm", "")
            gerente = mapa_id_corretor_para_gerente_nome.get(id_corretor, "")

            if gerente:
                cap_qtd[gerente] = cap_qtd.get(gerente, 0) + 1

        return cap_qtd

    def processar_visitas_por_gerente(
        self,
        df_visitas: pd.DataFrame,
        mapa_id_corretor_para_gerente_nome: Dict[str, str]
    ) -> Dict[str, int]:
        vis_qtd: Dict[str, int] = {}
        if df_visitas.empty:
            return vis_qtd

        dfv = df_visitas.copy()
        dfv.columns = [str(c).strip() for c in dfv.columns]

        id_col = None
        for c in ["Id_Corretor", "IdCorretor", "id_corretor", "ID_CORRETOR"]:
            if c in dfv.columns:
                id_col = c
                break
        if not id_col:
            return vis_qtd

        date_col = None
        for c in ["Data_Visita", "DataVisita", "Data", "data", "CreatedAt"]:
            if c in dfv.columns:
                date_col = c
                break
        if not date_col:
            return vis_qtd

        dfv[date_col] = pd.to_datetime(dfv[date_col], dayfirst=True, errors="coerce")
        dfv = dfv[
            (dfv[date_col].dt.year == self.config.ano_relatorio) &
            (dfv[date_col].dt.month == self.config.mes_relatorio)
        ].copy()

        dfv["IdCorretor_norm"] = dfv[id_col].astype(str).str.strip().str.upper()

        for _, row in dfv.iterrows():
            id_corretor = row.get("IdCorretor_norm", "")
            gerente = mapa_id_corretor_para_gerente_nome.get(id_corretor, "")
            if gerente:
                vis_qtd[gerente] = vis_qtd.get(gerente, 0) + 1

        return vis_qtd

    # ==========================================================
    # NORMALIZAÇÃO DAS METAS
    # ==========================================================
    def normalizar_metas_mensais(
        self,
        lista_gerentes: List[str],
        metas_mensais: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Espera receber algo como:
        {
            "NOME GERENTE": {
                "Meta_VGV_Mes": 8500000,
                "Meta_Cap_Mes": 12
            }
        }
        """
        metas_normalizadas = {}
        metas_mensais = metas_mensais or {}

        for gerente in lista_gerentes:
            meta_raw = metas_mensais.get(gerente, {})
            meta_vgv = self._to_float_br(meta_raw.get("Meta_VGV_Mes", 0))
            meta_cap = int(self._to_float_br(meta_raw.get("Meta_Cap_Mes", 0)))
            meta_vgc = self._to_float_br(meta_raw.get("Meta_VGC_Mes", 0))
            meta_vis = int(self._to_float_br(meta_raw.get("Meta_Vis_Mes", 0)))

            metas_normalizadas[gerente] = {
                "Meta_VGV_Mes": meta_vgv,
                "Meta_Cap_Mes": meta_cap,
                "Meta_VGC_Mes": meta_vgc,
                "Meta_Vis_Mes": meta_vis,
            }

        return metas_normalizadas

    # ==========================================================
    # RELATÓRIO
    # ==========================================================
    def montar_relatorio_final(
        self,
        df_dim_gerente: pd.DataFrame,
        res_gerentes: Dict[str, Any],
        cap_qtd_por_gerente: Dict[str, int],
        metas_mensais: Dict[str, Dict[str, Any]],
        vis_qtd_por_gerente: Optional[Dict[str, int]] = None
    ) -> pd.DataFrame:
        dfg = df_dim_gerente.copy()
        dfg.columns = [str(c).strip() for c in dfg.columns]
        dfg["NomeGerente_norm"] = dfg["Nome"].apply(self.limpar_nome)

        gerentes_base = set(dfg["NomeGerente_norm"].dropna().tolist())
        gerentes_resultado = set(res_gerentes["VGV_GERAL"].keys())
        gerentes_cap = set(cap_qtd_por_gerente.keys())
        gerentes_meta = set(metas_mensais.keys())

        todos_gerentes = sorted(gerentes_base | gerentes_resultado | gerentes_cap | gerentes_meta)

        vis_por_gerente = vis_qtd_por_gerente or {}
        linhas = []

        for gerente in todos_gerentes:
            meta_vgv = metas_mensais.get(gerente, {}).get("Meta_VGV_Mes", 0.0)
            meta_cap = metas_mensais.get(gerente, {}).get("Meta_Cap_Mes", 0)
            meta_vgc = metas_mensais.get(gerente, {}).get("Meta_VGC_Mes", 0.0)
            meta_vis = metas_mensais.get(gerente, {}).get("Meta_Vis_Mes", 0)

            vgv_realizado = res_gerentes["VGV_GERAL"].get(gerente, 0.0)
            cap_realizada = cap_qtd_por_gerente.get(gerente, 0)
            vgc_realizado = res_gerentes["VGC_GERAL"].get(gerente, 0.0)
            vis_realizada = vis_por_gerente.get(gerente, 0)

            perc_vgv = (vgv_realizado / meta_vgv * 100) if meta_vgv > 0 else 0.0
            perc_cap = (cap_realizada / meta_cap * 100) if meta_cap > 0 else 0.0
            perc_vgc = (vgc_realizado / meta_vgc * 100) if meta_vgc > 0 else 0.0
            perc_vis = (vis_realizada / meta_vis * 100) if meta_vis > 0 else 0.0

            linhas.append({
                "Gerente": gerente,
                "Meta_VGV_Mes": meta_vgv,
                f"VGV_Realizado_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": vgv_realizado,
                "%_Atingido_VGV": perc_vgv,
                "Status_VGV": "BATEU" if meta_vgv > 0 and vgv_realizado >= meta_vgv else "NAO BATEU",
                "Meta_Cap_Mes": meta_cap,
                f"Cap_Realizada_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": cap_realizada,
                "%_Atingido_Cap": perc_cap,
                "Status_Cap": "BATEU" if meta_cap > 0 and cap_realizada >= meta_cap else "NAO BATEU",
                "Meta_VGC_Mes": meta_vgc,
                f"VGC_Realizado_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": vgc_realizado,
                "%_Atingido_VGC": perc_vgc,
                "Status_VGC": "BATEU" if meta_vgc > 0 and vgc_realizado >= meta_vgc else "NAO BATEU",
                "Meta_Vis_Mes": meta_vis,
                f"Vis_Realizada_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": vis_realizada,
                "%_Atingido_Vis": perc_vis,
                "Status_Vis": "BATEU" if meta_vis > 0 and vis_realizada >= meta_vis else "NAO BATEU",
                f"VGV_Cap_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["VGV_CAP"].get(gerente, 0.0),
                f"VGV_Venda_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["VGV_VEND"].get(gerente, 0.0),
                f"Qtd_Vendas_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["VEND_QTD"].get(gerente, 0),
                f"Qtd_Geral_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["GERAL_QTD"].get(gerente, 0),
            })

        df_relatorio = pd.DataFrame(linhas)
        col_vgv_real = f"VGV_Realizado_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}"
        df_relatorio = df_relatorio.sort_values(by=col_vgv_real, ascending=False).reset_index(drop=True)
        return df_relatorio

    def montar_detalhes_vgv_geral(self, res_gerentes: Dict[str, Any]) -> pd.DataFrame:
        linhas = []
        detalhes = res_gerentes.get("DETALHES_VGV_GERAL", {})

        for gerente, mapa_corretores in detalhes.items():
            for corretor, valor in sorted(mapa_corretores.items(), key=lambda x: x[1], reverse=True):
                linhas.append({
                    "Gerente": gerente,
                    "Corretor": corretor,
                    "VGV_Usado_na_Soma": valor
                })

        df_det = pd.DataFrame(linhas)

        if not df_det.empty:
            df_det = df_det.sort_values(
                by=["Gerente", "VGV_Usado_na_Soma"],
                ascending=[True, False]
            ).reset_index(drop=True)

        return df_det

    # ==========================================================
    # GRÁFICOS
    # ==========================================================
    def _desenhar_barra_progresso(self, ax, realizado, meta, titulo, usar_moeda=False):
        realizado = float(realizado or 0)
        meta = float(meta or 0)
        pct = (realizado / meta * 100) if meta > 0 else 0.0

        eixo_max = max(meta * 1.4, realizado * 1.1, 1.0) if meta > 0 else max(realizado * 1.3, 1.0)
        real_norm = min(realizado / eixo_max, 1.0)
        meta_norm = (meta / eixo_max) if (meta > 0 and meta <= eixo_max) else None

        if meta <= 0:
            cor = "#94a3b8"
        elif realizado >= meta:
            cor = "#16a34a"
        elif pct >= 60:
            cor = "#2563eb"
        else:
            cor = "#ef4444"

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.patch.set_facecolor("#ffffff")

        ax.text(0.02, 0.93, titulo, ha="left", va="top", fontsize=8.0,
                color="#64748b", transform=ax.transAxes, clip_on=False)
        pct_str = f"{pct:.0f}%" if meta > 0 else "—"
        ax.text(0.98, 0.93, pct_str, ha="right", va="top", fontsize=9.5,
                color=cor, fontweight="bold", transform=ax.transAxes, clip_on=False)

        BAR_Y, BAR_H = 0.46, 0.30
        ax.barh(BAR_Y, 1.0, left=0, height=BAR_H, color="#e2e8f0", edgecolor="none", zorder=1)

        if real_norm > 0:
            ax.barh(BAR_Y, real_norm, left=0, height=BAR_H, color=cor, edgecolor="none", zorder=2)

        if meta_norm and 0 < meta_norm < 1.0:
            ax.axvline(meta_norm, ymin=0.26, ymax=0.82, color="#f97316", lw=2.5, zorder=3)

        def _fmt(v):
            return self.formatar_moeda_br(v) if usar_moeda else self.formatar_numero_br_sem_moeda(v)

        if realizado > 0:
            lbl = _fmt(realizado)
            if real_norm > 0.32:
                ax.text(real_norm / 2, BAR_Y, lbl, ha="center", va="center",
                        fontsize=6.5, color="white", fontweight="bold", zorder=4)
            else:
                ax.text(real_norm + 0.02, BAR_Y, lbl, ha="left", va="center",
                        fontsize=6.5, color=cor, fontweight="bold", zorder=4)

        if meta_norm and meta > 0:
            ax.text(meta_norm, 0.11, _fmt(meta),
                    ha="center", va="bottom", fontsize=5.5, color="#f97316", fontweight="bold")

        ax.axhline(0.02, color="#f1f5f9", lw=1.0)

    def gerar_paineis_metas_estilo_imagem(
        self,
        df_relatorio: pd.DataFrame,
        pasta_temp: str,
        gerentes_por_pagina: Optional[int] = None
    ) -> List[str]:
        if df_relatorio.empty:
            raise ValueError("df_relatorio está vazio. Não há dados para gerar o painel.")

        gerentes_por_pagina = gerentes_por_pagina or self.config.gerentes_por_pagina_painel
        ano, mes = self.config.ano_relatorio, self.config.mes_relatorio

        col_vgv_real = f"VGV_Realizado_{ano}_{mes:02d}"
        col_cap_real = f"Cap_Realizada_{ano}_{mes:02d}"
        col_vgc_real = f"VGC_Realizado_{ano}_{mes:02d}"
        col_vis_real = f"Vis_Realizada_{ano}_{mes:02d}"

        METRICAS = [
            (col_vgv_real, "Meta_VGV_Mes",  "VGV",       True),
            (col_cap_real, "Meta_Cap_Mes",   "Captações", False),
            (col_vgc_real, "Meta_VGC_Mes",   "VGC",       True),
            (col_vis_real, "Meta_Vis_Mes",   "Visitas",   False),
        ]

        df_plot = df_relatorio.copy().sort_values(col_vgv_real, ascending=False).reset_index(drop=True)
        registros = df_plot.to_dict("records")
        caminhos = []

        for pagina_idx, bloco in enumerate(self.dividir_em_blocos(registros, gerentes_por_pagina), start=1):
            n = len(bloco)

            fig = plt.figure(figsize=(13.0, max(9.0, n * 5.8)), facecolor="#f1f5f9")
            gs_main = GridSpec(n, 1, figure=fig, hspace=0.045,
                               top=0.975, bottom=0.015, left=0.015, right=0.985)

            for i, row in enumerate(bloco):
                gerente = row["Gerente"]
                gs_card = GridSpecFromSubplotSpec(
                    5, 1, subplot_spec=gs_main[i],
                    hspace=0.0,
                    height_ratios=[0.30, 1.0, 1.0, 1.0, 1.0]
                )

                ax_h = fig.add_subplot(gs_card[0])
                ax_h.axis("off")
                ax_h.patch.set_facecolor("#1e293b")
                ax_h.text(0.02, 0.5, gerente.title(), ha="left", va="center",
                          fontsize=12, color="#f8fafc", fontweight="bold",
                          transform=ax_h.transAxes)
                ax_h.text(0.98, 0.5, f"{mes:02d}/{ano}",
                          ha="right", va="center", fontsize=9, color="#94a3b8",
                          transform=ax_h.transAxes)

                for j, (col_r, col_m, titulo, usar_moeda) in enumerate(METRICAS):
                    ax = fig.add_subplot(gs_card[j + 1])
                    ax.patch.set_facecolor("#ffffff")
                    self._desenhar_barra_progresso(
                        ax,
                        realizado=row.get(col_r, 0),
                        meta=row.get(col_m, 0),
                        titulo=titulo,
                        usar_moeda=usar_moeda
                    )

            caminho = os.path.join(pasta_temp, f"painel_metas_{ano}_{mes:02d}_p{pagina_idx}.png")
            plt.savefig(caminho, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            caminhos.append(caminho)

        return caminhos

    # ==========================================================
    # PDF
    # ==========================================================
    def gerar_pdf_relatorio_buffer(self, df_relatorio: pd.DataFrame, caminhos_paineis: List[str]) -> BytesIO:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader

        ano, mes = self.config.ano_relatorio, self.config.mes_relatorio
        col_vgv_real = f"VGV_Realizado_{ano}_{mes:02d}"
        col_cap_real = f"Cap_Realizada_{ano}_{mes:02d}"
        col_vgc_real = f"VGC_Realizado_{ano}_{mes:02d}"
        col_vis_real = f"Vis_Realizada_{ano}_{mes:02d}"

        COR_HEADER   = colors.HexColor("#1e293b")
        COR_VERDE    = colors.HexColor("#dcfce7")
        COR_VERDE_TXT= colors.HexColor("#15803d")
        COR_VERMELHO = colors.HexColor("#fee2e2")
        COR_VERM_TXT = colors.HexColor("#dc2626")
        COR_ZEBRA    = colors.HexColor("#f8fafc")

        NOMES_MESES = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
                       7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

        pdf_buffer = BytesIO()
        larg_pag, alt_pag = landscape(A4)
        MG = 20 * mm

        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            rightMargin=MG, leftMargin=MG,
            topMargin=MG, bottomMargin=MG
        )

        styles = getSampleStyleSheet()
        s_titulo = ParagraphStyle("titulo", parent=styles["Normal"],
                                  fontSize=18, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#0f172a"), spaceAfter=2)
        s_sub    = ParagraphStyle("sub", parent=styles["Normal"],
                                  fontSize=9, textColor=colors.HexColor("#64748b"), spaceAfter=8)
        s_h2     = ParagraphStyle("h2", parent=styles["Normal"],
                                  fontSize=12, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#1e293b"), spaceBefore=12, spaceAfter=6)

        story = []

        # ── Cabeçalho do relatório ─────────────────────────────────
        story.append(Paragraph(
            f"Relatório de Metas · {NOMES_MESES.get(mes, str(mes))} {ano}", s_titulo
        ))
        story.append(Paragraph(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}  •  {len(df_relatorio)} gerentes",
            s_sub
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

        # ── Tabela resumo ──────────────────────────────────────────
        # Colunas: Gerente | VGV Real | %VGV | Cap | %Cap | VGC Real | %VGC | Vis | %Vis
        header = [
            "Gerente",
            "VGV Meta → Real", "% VGV",
            "Cap Meta → Real", "% Cap",
            "VGC Meta → Real", "% VGC",
            "Vis Meta → Real", "% Vis",
        ]
        tabela = [header]
        style_cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0),  COR_HEADER),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
            ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",         (0, 0), (0,  -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.5, colors.HexColor("#334155")),
        ]

        pct_cols = [2, 4, 6, 8]

        def _pct_style_cmd(col_idx, r_idx, bateu):
            if bateu:
                return [
                    ("BACKGROUND", (col_idx, r_idx), (col_idx, r_idx), COR_VERDE),
                    ("TEXTCOLOR",  (col_idx, r_idx), (col_idx, r_idx), COR_VERDE_TXT),
                    ("FONTNAME",   (col_idx, r_idx), (col_idx, r_idx), "Helvetica-Bold"),
                ]
            return [
                ("BACKGROUND", (col_idx, r_idx), (col_idx, r_idx), COR_VERMELHO),
                ("TEXTCOLOR",  (col_idx, r_idx), (col_idx, r_idx), COR_VERM_TXT),
                ("FONTNAME",   (col_idx, r_idx), (col_idx, r_idx), "Helvetica-Bold"),
            ]

        def _seta(meta_v, real_v, moeda=True):
            m = self.formatar_moeda_br(meta_v) if moeda else self.formatar_numero_br_sem_moeda(meta_v)
            r = self.formatar_moeda_br(real_v) if moeda else self.formatar_numero_br_sem_moeda(real_v)
            return f"{m} → {r}"

        for r_idx, row in enumerate(df_relatorio.to_dict("records"), start=1):
            if r_idx % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, r_idx), (-1, r_idx), COR_ZEBRA))

            for cmd in _pct_style_cmd(2, r_idx, row.get("Status_VGV", "") == "BATEU"):
                style_cmds.append(cmd)
            for cmd in _pct_style_cmd(4, r_idx, row.get("Status_Cap", "") == "BATEU"):
                style_cmds.append(cmd)
            for cmd in _pct_style_cmd(6, r_idx, row.get("Status_VGC", "") == "BATEU"):
                style_cmds.append(cmd)
            for cmd in _pct_style_cmd(8, r_idx, row.get("Status_Vis", "") == "BATEU"):
                style_cmds.append(cmd)

            tabela.append([
                str(row.get("Gerente", "")).title(),
                _seta(row.get("Meta_VGV_Mes", 0), row.get(col_vgv_real, 0), True),
                f"{row.get('%_Atingido_VGV', 0):.0f}%",
                _seta(row.get("Meta_Cap_Mes", 0), row.get(col_cap_real, 0), False),
                f"{row.get('%_Atingido_Cap', 0):.0f}%",
                _seta(row.get("Meta_VGC_Mes", 0), row.get(col_vgc_real, 0), True),
                f"{row.get('%_Atingido_VGC', 0):.0f}%",
                _seta(row.get("Meta_Vis_Mes", 0), row.get(col_vis_real, 0), False),
                f"{row.get('%_Atingido_Vis', 0):.0f}%",
            ])

        larg_disp = larg_pag - 2 * MG
        col_widths = [larg_disp * w for w in [0.17, 0.14, 0.07, 0.10, 0.07, 0.14, 0.07, 0.10, 0.07]]

        tb = Table(tabela, colWidths=col_widths, repeatRows=1)
        tb.setStyle(TableStyle(style_cmds))
        story.append(tb)

        # ── Painéis gráficos ────────────────────────────────────────
        if caminhos_paineis:
            story.append(PageBreak())

        alt_disp = alt_pag - 2 * MG - 30
        for i, caminho_img in enumerate(caminhos_paineis, start=1):
            story.append(Paragraph(f"Painel de Metas — Parte {i} de {len(caminhos_paineis)}", s_h2))
            img_reader = ImageReader(caminho_img)
            img_w, img_h = img_reader.getSize()
            escala = min(larg_disp / img_w, alt_disp / img_h)
            story.append(Image(caminho_img, width=img_w * escala, height=img_h * escala))
            if i < len(caminhos_paineis):
                story.append(PageBreak())

        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer

    # ==========================================================
    # ORQUESTRAÇÃO
    # ==========================================================
    def calcular_dados_relatorio(self, metas_mensais: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        df_vendas = self.carregar_contratos()
        df_vendas["Data_Contrato"] = pd.to_datetime(df_vendas["Data_Contrato"], errors="coerce")
        df_dim_corretor, df_dim_gerente, df_captacao = self.carregar_base_inteligencia()

        if df_vendas.empty:
            raise ValueError("A aba Vendas está vazia.")
        if df_dim_corretor.empty:
            raise ValueError("A aba Dim_Corretor está vazia.")
        if df_dim_gerente.empty:
            raise ValueError("A aba Dim_Gerente está vazia.")
        if df_captacao.empty:
            raise ValueError("A aba Fato_Captacao está vazia.")

        (mapa_corretor_gerente, _, mapa_id_corretor_para_gerente_nome, _) = \
            self.montar_mapas_dim_corretor(df_dim_corretor, df_dim_gerente)

        for col in ["Valor_Negocio", "Valor_Total_61"]:
            if col in df_vendas.columns:
                df_vendas[col] = df_vendas[col].apply(self._to_float_br)
            else:
                raise ValueError(f"Coluna obrigatória não encontrada na aba Vendas: {col}")

        if "Data_Contrato" not in df_vendas.columns:
            raise ValueError("Coluna obrigatória não encontrada na aba Vendas: Data_Contrato")

        df_vendas_mes = df_vendas[
            (df_vendas["Data_Contrato"].dt.year == self.config.ano_relatorio) &
            (df_vendas["Data_Contrato"].dt.month == self.config.mes_relatorio)
        ].copy()

        if df_vendas_mes.empty:
            raise ValueError(
                f"Não foram encontradas vendas para "
                f"{self.config.mes_relatorio:02d}/{self.config.ano_relatorio}."
            )

        res_gerentes = self.processar_gerentes_via_dim_corretor(df_vendas_mes, mapa_corretor_gerente)
        cap_qtd_por_gerente = self.processar_captacoes_por_gerente(df_captacao, mapa_id_corretor_para_gerente_nome)

        try:
            df_visitas = self.carregar_aba_por_id(self.config.sheet_id_visitas, self.config.aba_fato_visitas)
        except Exception:
            df_visitas = pd.DataFrame()
        vis_qtd_por_gerente = self.processar_visitas_por_gerente(df_visitas, mapa_id_corretor_para_gerente_nome)

        lista_gerentes = sorted(set(
            list(res_gerentes["VGV_GERAL"].keys()) +
            list(cap_qtd_por_gerente.keys()) +
            [self.limpar_nome(x) for x in df_dim_gerente["Nome"].tolist() if self.limpar_nome(x)]
        ))
        metas_normalizadas = self.normalizar_metas_mensais(lista_gerentes, metas_mensais)

        return self.montar_relatorio_final(
            df_dim_gerente, res_gerentes, cap_qtd_por_gerente, metas_normalizadas, vis_qtd_por_gerente
        )

    def gerar_relatorio_pdf(self, metas_mensais: Dict[str, Dict[str, Any]]) -> BytesIO:
        df_relatorio = self.calcular_dados_relatorio(metas_mensais)

        with tempfile.TemporaryDirectory() as pasta_temp:
            caminhos_paineis = self.gerar_paineis_metas_estilo_imagem(
                df_relatorio=df_relatorio,
                pasta_temp=pasta_temp,
                gerentes_por_pagina=self.config.gerentes_por_pagina_painel
            )
            pdf_buffer = self.gerar_pdf_relatorio_buffer(df_relatorio, caminhos_paineis)

        return pdf_buffer