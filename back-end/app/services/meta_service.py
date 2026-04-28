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
    aba_contratos: str = "Vendas"
    aba_dim_corretor: str = "Dim_Corretor"
    aba_dim_gerente: str = "Dim_Gerente"
    aba_fato_captacao: str = "Fato_Captacao"
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
        print(self.config.sheet_id_contratos)
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

            metas_normalizadas[gerente] = {
                "Meta_VGV_Mes": meta_vgv,
                "Meta_Cap_Mes": meta_cap,
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
        metas_mensais: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        dfg = df_dim_gerente.copy()
        dfg.columns = [str(c).strip() for c in dfg.columns]
        dfg["NomeGerente_norm"] = dfg["Nome"].apply(self.limpar_nome)

        gerentes_base = set(dfg["NomeGerente_norm"].dropna().tolist())
        gerentes_resultado = set(res_gerentes["VGV_GERAL"].keys())
        gerentes_cap = set(cap_qtd_por_gerente.keys())
        gerentes_meta = set(metas_mensais.keys())

        todos_gerentes = sorted(gerentes_base | gerentes_resultado | gerentes_cap | gerentes_meta)

        linhas = []

        for gerente in todos_gerentes:
            meta_vgv = metas_mensais.get(gerente, {}).get("Meta_VGV_Mes", 0.0)
            meta_cap = metas_mensais.get(gerente, {}).get("Meta_Cap_Mes", 0)

            vgv_realizado = res_gerentes["VGV_GERAL"].get(gerente, 0.0)
            cap_realizada = cap_qtd_por_gerente.get(gerente, 0)

            perc_vgv = (vgv_realizado / meta_vgv * 100) if meta_vgv > 0 else 0.0
            perc_cap = (cap_realizada / meta_cap * 100) if meta_cap > 0 else 0.0

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
                f"VGV_Cap_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["VGV_CAP"].get(gerente, 0.0),
                f"VGV_Venda_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["VGV_VEND"].get(gerente, 0.0),
                f"VGC_Geral_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}": res_gerentes["VGC_GERAL"].get(gerente, 0.0),
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
    def _desenhar_barra_progresso(
        self,
        ax,
        realizado,
        meta,
        titulo,
        usar_moeda=False,
        cor_bateu="#3cb44b",
        cor_nao_bateu="#e91e63",
        cor_fundo="#d9d9d9",
        cor_meta="#ff4f8b",
        cor_super_meta="#666666"
    ):
        realizado = float(realizado or 0)
        meta = float(meta or 0)

        percentual = (realizado / meta * 100) if meta > 0 else 0.0

        if meta > 0:
            super_meta = meta * 1.5
            eixo_max = super_meta
            largura_fundo = super_meta
            largura_preenchida = min(realizado, super_meta)
            cor_barra = cor_bateu if realizado >= meta else cor_nao_bateu
        else:
            super_meta = 0
            eixo_max = max(realizado, 1)
            largura_fundo = eixo_max
            largura_preenchida = realizado
            cor_barra = cor_nao_bateu

        ax.set_xlim(0, eixo_max * 1.05 if eixo_max > 0 else 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        ax.text(
            0, 0.92, titulo,
            ha="left", va="top",
            fontsize=8, color="black"
        )

        ax.barh(
            y=0.42,
            width=largura_fundo if largura_fundo > 0 else 1,
            left=0,
            height=0.34,
            color=cor_fundo,
            edgecolor="none",
            zorder=1
        )

        if largura_fundo > 0:
            for frac in [0.166, 0.333, 0.5, 0.666, 0.833]:
                ax.axvline(
                    largura_fundo * frac,
                    ymin=0.23,
                    ymax=0.60,
                    color="white",
                    lw=0.8,
                    alpha=0.28,
                    zorder=2
                )

        if largura_preenchida > 0:
            ax.barh(
                y=0.42,
                width=largura_preenchida,
                left=0,
                height=0.34,
                color=cor_barra,
                edgecolor="none",
                zorder=3
            )

        if meta > 0:
            ax.axvline(
                meta,
                ymin=0.18,
                ymax=0.72,
                color=cor_meta,
                linestyle="--",
                lw=1.2,
                zorder=4
            )

            texto_meta = self.formatar_moeda_br(meta) if usar_moeda else self.formatar_numero_br_sem_moeda(meta)
            ax.text(
                meta,
                0.83,
                texto_meta,
                rotation=45,
                ha="center",
                va="bottom",
                fontsize=7,
                color=cor_meta
            )

        if super_meta > 0:
            texto_super_meta = self.formatar_moeda_br(super_meta) if usar_moeda else self.formatar_numero_br_sem_moeda(super_meta)
            ax.text(
                super_meta,
                0.10,
                texto_super_meta,
                ha="center",
                va="top",
                fontsize=7,
                color=cor_super_meta
            )

        if realizado > 0:
            x_real = min(realizado, super_meta) if super_meta > 0 else realizado
            texto_real = self.formatar_moeda_br(realizado) if usar_moeda else self.formatar_numero_br_sem_moeda(realizado)

            ax.text(
                x_real,
                0.70,
                texto_real,
                rotation=45,
                ha="center",
                va="bottom",
                fontsize=7,
                color="black"
            )

        if largura_preenchida > 0:
            x_pct = largura_preenchida / 2
            cor_texto = "white" if largura_preenchida >= (largura_fundo * 0.18 if largura_fundo > 0 else 0) else "black"

            ax.text(
                x_pct,
                0.42,
                f"{percentual:.1f}%",
                ha="center",
                va="center",
                fontsize=8,
                color=cor_texto,
                fontweight="bold",
                zorder=5
            )

    def gerar_paineis_metas_estilo_imagem(
        self,
        df_relatorio: pd.DataFrame,
        pasta_temp: str,
        gerentes_por_pagina: Optional[int] = None
    ) -> List[str]:
        if df_relatorio.empty:
            raise ValueError("df_relatorio está vazio. Não há dados para gerar o painel.")

        gerentes_por_pagina = gerentes_por_pagina or self.config.gerentes_por_pagina_painel

        col_vgv_real = f"VGV_Realizado_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}"
        col_cap_real = f"Cap_Realizada_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}"

        df_plot = df_relatorio.copy().sort_values(by=col_vgv_real, ascending=False).reset_index(drop=True)

        caminhos = []
        registros = df_plot.to_dict("records")

        for pagina_idx, bloco in enumerate(self.dividir_em_blocos(registros, gerentes_por_pagina), start=1):
            n = len(bloco)

            fig, axes = plt.subplots(
                nrows=n * 3,
                ncols=1,
                figsize=(12, max(4.5, n * 2.3)),
                gridspec_kw={"height_ratios": [0.20, 1.0, 1.0] * n}
            )

            try:
                axes = axes.flatten().tolist()
            except Exception:
                axes = [axes]

            fig.patch.set_facecolor("#f2f2f2")

            idx = 0
            for row in bloco:
                gerente = row["Gerente"]

                ax_header = axes[idx]
                idx += 1
                ax_header.set_facecolor("#9e9e9e")
                ax_header.set_xticks([])
                ax_header.set_yticks([])
                for spine in ax_header.spines.values():
                    spine.set_visible(False)

                ax_header.text(
                    0.5, 0.5,
                    f"Metas Equipe {gerente} - {self.config.mes_relatorio:02d}/{self.config.ano_relatorio}",
                    ha="center",
                    va="center",
                    fontsize=12,
                    color="#222222"
                )

                ax_vgv = axes[idx]
                idx += 1
                ax_vgv.set_facecolor("#f2f2f2")
                self._desenhar_barra_progresso(
                    ax=ax_vgv,
                    realizado=row[col_vgv_real],
                    meta=row["Meta_VGV_Mes"],
                    titulo="Meta Mensal VGV",
                    usar_moeda=True
                )

                ax_cap = axes[idx]
                idx += 1
                ax_cap.set_facecolor("#f2f2f2")
                self._desenhar_barra_progresso(
                    ax=ax_cap,
                    realizado=row[col_cap_real],
                    meta=row["Meta_Cap_Mes"],
                    titulo="Meta Mensal Captações",
                    usar_moeda=False
                )

            plt.tight_layout(h_pad=1.0)

            caminho = os.path.join(
                pasta_temp,
                f"painel_metas_gerentes_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}_parte_{pagina_idx}.png"
            )

            plt.savefig(caminho, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)

            caminhos.append(caminho)

        return caminhos

    # ==========================================================
    # PDF
    # ==========================================================
    def gerar_pdf_relatorio_buffer(self, df_relatorio: pd.DataFrame, caminhos_paineis: List[str]) -> BytesIO:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
        )
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.utils import ImageReader

        col_vgv_real = f"VGV_Realizado_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}"
        col_cap_real = f"Cap_Realizada_{self.config.ano_relatorio}_{self.config.mes_relatorio:02d}"

        pdf_buffer = BytesIO()

        largura_pagina, altura_pagina = landscape(A4)

        margem_esq = 25
        margem_dir = 25
        margem_top = 25
        margem_bottom = 25

        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            rightMargin=margem_dir,
            leftMargin=margem_esq,
            topMargin=margem_top,
            bottomMargin=margem_bottom
        )

        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(
            f"Relatório de Metas de Gerentes - {self.config.mes_relatorio:02d}/{self.config.ano_relatorio}",
            styles["Title"]
        ))
        story.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"]
        ))
        story.append(Spacer(1, 12))

        tabela = [[
            "Gerente",
            "Meta VGV Mês",
            "VGV Realizado",
            "% VGV",
            "Meta Cap Mês",
            "Cap Realizada",
            "% Cap"
        ]]

        for _, row in df_relatorio.iterrows():
            tabela.append([
                row["Gerente"],
                self.formatar_moeda_br(row["Meta_VGV_Mes"]),
                self.formatar_moeda_br(row[col_vgv_real]),
                f'{row["%_Atingido_VGV"]:.1f}%',
                int(row["Meta_Cap_Mes"]),
                int(row[col_cap_real]),
                f'{row["%_Atingido_Cap"]:.1f}%'
            ])

        tb = Table(tabela, repeatRows=1)
        tb.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))

        story.append(tb)

        if caminhos_paineis:
            story.append(PageBreak())

        largura_disp = largura_pagina - margem_esq - margem_dir
        altura_disp = altura_pagina - margem_top - margem_bottom - 40

        for i, caminho_img in enumerate(caminhos_paineis, start=1):
            story.append(Paragraph(f"Painel de Metas - Parte {i}", styles["Heading2"]))
            story.append(Spacer(1, 8))

            img_reader = ImageReader(caminho_img)
            img_w, img_h = img_reader.getSize()

            escala = min(largura_disp / img_w, altura_disp / img_h)
            img = Image(caminho_img, width=img_w * escala, height=img_h * escala)

            story.append(img)

            if i < len(caminhos_paineis):
                story.append(PageBreak())

        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer

    # ==========================================================
    # ORQUESTRAÇÃO
    # ==========================================================
    def gerar_relatorio_pdf(self, metas_mensais: Dict[str, Dict[str, Any]]) -> BytesIO:
        """
        Exemplo de metas_mensais:
        {
            "GERENTE A": {"Meta_VGV_Mes": 8500000, "Meta_Cap_Mes": 10},
            "GERENTE B": {"Meta_VGV_Mes": 4300000, "Meta_Cap_Mes": 7}
        }

        Retorna:
            BytesIO com o PDF final
        """
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

        (
            mapa_corretor_gerente,
            _,
            mapa_id_corretor_para_gerente_nome,
            _
        ) = self.montar_mapas_dim_corretor(df_dim_corretor, df_dim_gerente)

        for col in ["Valor_Negocio", "Valor_Total_61"]:
            if col in df_vendas.columns:
                df_vendas[col] = df_vendas[col].apply(self._to_float_br)
            else:
                raise ValueError(f"Coluna obrigatória não encontrada na aba Vendas: {col}")

        if "Data_Contrato" not in df_vendas.columns:
            raise ValueError("Coluna obrigatória não encontrada na aba Vendas: Data_Contrato")

        df_vendas["Data_Contrato"] = pd.to_datetime(df_vendas["Data_Contrato"], errors="coerce")
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

        cap_qtd_por_gerente = self.processar_captacoes_por_gerente(
            df_captacao,
            mapa_id_corretor_para_gerente_nome
        )

        lista_gerentes = sorted(set(
            list(res_gerentes["VGV_GERAL"].keys()) +
            list(cap_qtd_por_gerente.keys()) +
            [self.limpar_nome(x) for x in df_dim_gerente["Nome"].tolist() if self.limpar_nome(x)]
        ))

        metas_mensais_normalizadas = self.normalizar_metas_mensais(lista_gerentes, metas_mensais)

        df_relatorio = self.montar_relatorio_final(
            df_dim_gerente,
            res_gerentes,
            cap_qtd_por_gerente,
            metas_mensais_normalizadas
        )

        with tempfile.TemporaryDirectory() as pasta_temp:
            caminhos_paineis = self.gerar_paineis_metas_estilo_imagem(
                df_relatorio=df_relatorio,
                pasta_temp=pasta_temp,
                gerentes_por_pagina=self.config.gerentes_por_pagina_painel
            )

            pdf_buffer = self.gerar_pdf_relatorio_buffer(df_relatorio, caminhos_paineis)

        return pdf_buffer