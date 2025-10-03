import os, json, time
import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
from app.models.imovel import Imovel, ImovelAluguel, ImovelVenda
from sqlalchemy.orm import sessionmaker
from app.models.imovel import Imovel
from app import engine, cache
from sqlalchemy import text
from datetime import datetime, timedelta, date

# =========================
# NOVO: suporte a valores pré-calculados (em memória)
# =========================
PRECOMPUTED_PATH = "./dados/precomputed_analise.json"
_PRECOMPUTED = {}
_PRECOMPUTED_MTIME = 0.0

def _load_precomputed_if_needed():
    """Carrega o JSON de valores pré-definidos em memória (com hot-reload leve por mtime)."""
    global _PRECOMPUTED, _PRECOMPUTED_MTIME
    print("passou aq")
    try:
        st = os.stat(PRECOMPUTED_PATH)
        if st.st_mtime != _PRECOMPUTED_MTIME:
            print("chegou aqui")
            with open(PRECOMPUTED_PATH, "r", encoding="utf-8") as f:
                _PRECOMPUTED = json.load(f) or {}
                print(_PRECOMPUTED)
            _PRECOMPUTED_MTIME = st.st_mtime
    except FileNotFoundError:
        print("erro")
        _PRECOMPUTED = {}
        _PRECOMPUTED_MTIME = 0.0

def _key(tipo_imovel, bairro, quartos, nr_cluster, oferta):
    """Chave canônica para consulta no cache pré-calculado."""
    # normalize mínimos conforme o front fornecido
    return "|".join([
        str(tipo_imovel or "").strip().upper(),
        str(bairro or "").strip().upper(),
        str(int(quartos) if quartos is not None else 0),
        str(int(nr_cluster) if nr_cluster is not None else 0),
        str(oferta or "").strip().upper()
    ])

def get_precomputed_result(tipo_imovel, bairro, quartos, nr_cluster, oferta):
    """
    Retorna (dict) do cluster já pré-calculado, se existir.
    Caso contrário, executa o cálculo, adiciona o novo valor no arquivo e retorna.
    """
    _load_precomputed_if_needed()
    k = _key(tipo_imovel, bairro, quartos, nr_cluster, oferta)
    
    val = _PRECOMPUTED.get(k)
    if val is None:
        print(f"Chave não encontrada no precomputado. Calculando e salvando: {k}")
        
        # Cálculo normal caso o valor não tenha sido pré-computado
        resultado = analisar_imovel_detalhado(
            tipo_imovel=tipo_imovel,
            bairro=bairro,
            vaga_garagem=None,  # Ajuste conforme necessário
            quartos=quartos,
            metragem=None  # Ajuste conforme necessário
        )
        
        # Exemplo de estrutura de retorno
        if oferta == "Venda":
            val = resultado['venda'][nr_cluster]
        else:
            val = resultado['aluguel'][nr_cluster]

        # Salva o novo valor no arquivo JSON
        _PRECOMPUTED[k] = val
        with open(PRECOMPUTED_PATH, "w", encoding="utf-8") as f:
            json.dump(_PRECOMPUTED, f, ensure_ascii=False, indent=4)

    return val

# ========= LÓGICA JÁ EXISTENTE (preservada) =========



def get_data_cache_token():
    @cache.memoize(timeout=30)
    def _token_inner():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(data_coleta) FROM imoveis")).scalar()
            return (result or datetime(1970,1,1)).isoformat()
    return _token_inner()

input_file = "./dados/dados_map.csv"

def remover_outliers_iqr(df, coluna):
    Q1 = df[coluna].quantile(0.25)
    Q3 = df[coluna].quantile(0.75)
    IQR = Q3 - Q1
    filtro = (df[coluna] >= (Q1 - 1.5 * IQR)) & (df[coluna] <= (Q3 + 1.5 * IQR))
    return df[filtro]

def calcular_rentabilidade(valor_locacao, valor_venda):
    return (valor_locacao) / valor_venda if valor_venda != 0 else np.nan

def calcular_metricas_cluster(df, valor_coluna, oferta_tipo, metragem = None):
    metricas = {}

    if oferta_tipo == 'Venda':
        metricas['valorM2Venda'] = df[valor_coluna].mean()
        metricas['valorVendaNominal'] = df[valor_coluna].mean() * metragem if metragem else df['preco'].mean()
        metricas['metragemMediaVenda'] = df['area_util'].mean()
        metricas['coeficienteVariacaoVenda'] = df[valor_coluna].std() / df[valor_coluna].mean() if df[valor_coluna].mean() != 0 else np.nan
        metricas['tamanhoAmostraVenda'] = len(df)
        if isinstance(metricas, pd.DataFrame):
            if 'tamanhoAmostraVenda' not in metricas.columns:
                metricas['tamanhoAmostraVenda'] = len(df)
            else:
                metricas['tamanhoAmostraVenda'] = metricas['tamanhoAmostraVenda'].fillna(0)
    else:
        metricas['valorM2Aluguel'] = df[valor_coluna].mean()
        metricas['valorAluguelNominal'] =  metricas['valorM2Aluguel'] * metragem if metragem else df['preco'].mean()
        metricas['metragemMediaAluguel'] = df['area_util'].mean()
        metricas['coeficienteVariacaoAluguel'] = df[valor_coluna].std() / df[valor_coluna].mean() if df[valor_coluna].mean() != 0 else np.nan
        metricas['tamanhoAmostraAluguel'] = len(df)

    return metricas

def formatar_resultados(df):
    df_formatted = df.copy()
    df_formatted['valorM2Venda'] = df_formatted['valorM2Venda'].fillna(0).apply(lambda x: f"R$ {x:,.2f} /m²")
    df_formatted['valorVendaNominal'] = df_formatted['valorVendaNominal'].fillna(0).apply(lambda x: f"R$ {x:,.2f}")
    df_formatted['metragemMediaVenda'] = df_formatted['metragemMediaVenda'].fillna(0).apply(lambda x: f"{x:.2f} m²")
    df_formatted['valorM2Aluguel'] = df_formatted['valorM2Aluguel'].fillna(0).apply(lambda x: f"R$ {x:,.2f} /m²")
    df_formatted['valorAluguelNominal'] = df_formatted['valorAluguelNominal'].fillna(0).apply(lambda x: f"R$ {x:,.2f}")
    df_formatted['metragemMediaAluguel'] = df_formatted['metragemMediaAluguel'].fillna(0).apply(lambda x: f"{x:.2f} m²")
    df_formatted['coeficienteVariacaoVenda'] = df_formatted['coeficienteVariacaoVenda'].fillna(0).apply(lambda x: f"{x:.2%}")
    df_formatted['coeficienteVariacaoAluguel'] = df_formatted['coeficienteVariacaoAluguel'].fillna(0).apply(lambda x: f"{x:.2%}")
    df_formatted['rentabilidadeMedia'] = df_formatted['rentabilidadeMedia'].fillna(0).apply(lambda x: f"{x:.2%}")
    return df_formatted

def clusterizar_dados(df, valor_coluna, oferta_tipo, n_clusters=9, metragem=None):
    df_oferta = df[df['oferta'] == oferta_tipo].copy()
    tamanho_n = 0
    if(len(df_oferta) > 0):
        tamanho_n = 10
    if not df_oferta.empty and valor_coluna in df_oferta.columns and tamanho_n >= n_clusters :
        if(len(df_oferta) > 8):
            X = df_oferta[[valor_coluna]].values
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            df_oferta.loc[:, "cluster"] = kmeans.fit_predict(X)
            df_oferta.loc[:, 'cluster'] = df_oferta['cluster'].astype('category')
        else:
            df_oferta.loc[:, "cluster"] = 5
            df_oferta.loc[:, "cluster"] = df_oferta["cluster"].astype("category")
        if(oferta_tipo == 'Aluguel'):
            df_oferta.to_csv("./dados/aluguelC.csv")
            salvar_oferta_no_banco(df_oferta, oferta_tipo)
        elif(oferta_tipo == 'Venda'):
            df_oferta.to_csv("./dados/vendaC.csv")
            salvar_oferta_no_banco(df_oferta, oferta_tipo)

        metricas_clusters = []
        for cluster in sorted(df_oferta['cluster'].unique()):
            cluster_data = df_oferta[df_oferta['cluster'] == cluster]
            metricas = calcular_metricas_cluster(cluster_data, valor_coluna, oferta_tipo, metragem)
            metricas['Cluster'] = cluster
            metricas_clusters.append(metricas)

        metricas_df = pd.DataFrame(metricas_clusters)
        if oferta_tipo == 'Venda':
            metricas_df = metricas_df.reindex(columns=['valorM2Venda', 'valorVendaNominal',
                                                       'metragemMediaVenda', 'coeficienteVariacaoVenda',
                                                       'tamanhoAmostraVenda'], fill_value=0)
        else:
            metricas_df = metricas_df.reindex(columns=['valorM2Aluguel', 'valorAluguelNominal',
                                                       'metragemMediaAluguel', 'coeficienteVariacaoAluguel',
                                                       'tamanhoAmostraAluguel'], fill_value=0)
        return metricas_df.reset_index(drop=True)
    else:
        if oferta_tipo == 'Venda':
            return pd.DataFrame(columns=['valorM2Venda', 'valorVendaNominal',
                                         'metragemMediaVenda', 'coeficienteVariacaoVenda',
                                         'tamanhoAmostraVenda'])
        else:
            return pd.DataFrame(columns=['valorM2Aluguel', 'valorAluguelNominal',
                                         'metragemMediaAluguel', 'coeficienteVariacaoAluguel',
                                         'tamanhoAmostraAluguel'])

@cache.memoize(timeout=3600)
def _analisar_imovel_detalhado_cached(cache_token, tipo_imovel=None, bairro=None, cidade=None, cep=None, vaga_garagem=None, quadra=None, quartos=None, metragem=None):
    df = carregar_dados_df()

    # (… toda a sua lógica de filtros e de expansão de janela de metragem …)
    # Mantida exatamente como você já tinha:

    filtro = pd.Series(True, index=df.index)
    if tipo_imovel:
        filtro &= (df["tipo"] == tipo_imovel)
    if bairro:
        if bairro == "Águas Claras":
            bairro_aguas = ["NORTE", "SUL"]
            filtro &= (df['bairro'].isin(bairro_aguas))
        else:
            filtro &= (df["bairro"] == bairro)
    if cidade:
        filtro &= (df["cidade"] == cidade)
    if cep:
        filtro &= (df["cep"] == cep)
    if vaga_garagem is not None:
        filtro &= (df["vagas"].notnull() if vaga_garagem else df["vagas"].isnull())
    if quadra:
        filtro &= (df["quadra"] == quadra)
    if quartos:
        filtro &= (df["quartos"] == quartos if (quartos < 4) else df["quartos"] >= quartos)

    if metragem:
        micro_filtro = filtro.copy()
        micro_filtro &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
        df_filtrado_metragem = df[micro_filtro]
        tamanho_amostra_aluguel = len(df_filtrado_metragem[df_filtrado_metragem['oferta'] == 'Aluguel'])

        micro_filtro_venda = filtro.copy()
        micro_filtro_venda &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
        df_filtrado_metragem_venda = df[micro_filtro_venda]
        tamanho_amostra_venda = len(df_filtrado_metragem_venda[df_filtrado_metragem_venda['oferta'] == 'Venda'])

        if tamanho_amostra_aluguel < 9 or tamanho_amostra_venda < 9:
            numero_interacoes = 0
            valor = 0.15
            valor_venda = 0.15
            valor_aluguel = 0.15
            boo_venda = False
            boo_aluguel = False
            max_interacoes = 17

            micro_filtro = filtro.copy()
            micro_filtro &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
            df_filtrado_metragem = df[micro_filtro]
            valores_descendo_loop = len(df_filtrado_metragem[df_filtrado_metragem['oferta'] == 'Aluguel'])

            micro_filtro_venda = filtro.copy()
            micro_filtro_venda &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
            df_filtrado_metragem_venda = df[micro_filtro_venda]
            tamanho_amostra_venda_loop = len(df_filtrado_metragem_venda[df_filtrado_metragem_venda['oferta'] == 'Venda'])

            while(((valores_descendo_loop < 9) or (tamanho_amostra_venda_loop < 9)) and numero_interacoes < max_interacoes):
                novo_micro_filtro = filtro.copy()

                if valores_descendo_loop > 9 and not boo_aluguel:
                    valor_aluguel = valor
                    boo_aluguel = True

                if tamanho_amostra_venda > 9 and not boo_venda:
                    valor_venda = valor
                    boo_venda = True

                novo_micro_filtro &= ((df["area_util"] >= metragem * (1 - valor)) & (df["area_util"] <= metragem * (1 + valor)))
                df_filtrado_metragem = df[novo_micro_filtro]
                valores_descendo_loop = len(df_filtrado_metragem[df_filtrado_metragem['oferta'] == 'Aluguel'])

                micro_filtro_venda = filtro.copy()
                micro_filtro_venda &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
                df_filtrado_metragem_venda = df[micro_filtro_venda]
                tamanho_amostra_venda_loop = len(df_filtrado_metragem_venda[df_filtrado_metragem_venda['oferta'] == 'Venda'])

                numero_interacoes += 1
                valor += 0.05
                if valores_descendo_loop > 9 and not boo_aluguel:
                    valor_aluguel = valor
                    boo_aluguel = True

                if tamanho_amostra_venda > 9 and not boo_venda:
                    valor_venda = valor
                    boo_venda = True

            filtro_aluguel = filtro.copy()
            filtro_venda = filtro.copy()

            filtro_venda &= (
                (df["area_util"] >= metragem * (1 - valor_venda)) &
                (df["area_util"] <= metragem * (1 + valor_venda)) &
                (df["oferta"] == 'Venda'))
            filtro_aluguel &= (
                (df["area_util"] >= metragem * (1 - valor_aluguel)) &
                (df["area_util"] <= metragem * (1 + valor_aluguel)) &
                (df["oferta"] == 'Aluguel'))
            filtro = filtro_venda | filtro_aluguel
        else:
            filtro &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))

    df_filtrado = df[filtro]

    venda_df = df_filtrado[df_filtrado['oferta'] == 'Venda'].copy()
    if "valor_m2" in venda_df.columns:
        venda_df = remover_outliers_iqr(venda_df, "valor_m2")
    metricas_venda = clusterizar_dados(venda_df, "valor_m2", "Venda", n_clusters=9,  metragem=metragem)

    aluguel_df = df_filtrado[df_filtrado['oferta'] == 'Aluguel'].copy()
    if "valor_m2" in aluguel_df.columns:
        aluguel_df = remover_outliers_iqr(aluguel_df, "valor_m2")
    metricas_aluguel = clusterizar_dados(aluguel_df, "valor_m2", "Aluguel", n_clusters=9,  metragem=metragem)

    metricas_venda = metricas_venda.sort_values(by="valorM2Venda").reset_index(drop=True)
    metricas_aluguel = metricas_aluguel.sort_values(by="valorM2Aluguel").reset_index(drop=True)
    max_len = max(len(metricas_venda), len(metricas_aluguel))
    metricas_venda = metricas_venda.reindex(range(max_len)).reset_index(drop=True)
    metricas_aluguel = metricas_aluguel.reindex(range(max_len)).reset_index(drop=True)

    _ = pd.concat([metricas_venda, metricas_aluguel], axis=1)
    _['rentabilidadeMedia'] = _.apply(
        lambda row: calcular_rentabilidade(row.get('valorAluguelNominal', np.nan), row.get('valorVendaNominal', np.nan)),
        axis=1
    )

    return {
        'venda': metricas_venda.to_dict(orient='records'),
        'aluguel': metricas_aluguel.to_dict(orient='records')
    }

def analisar_imovel_detalhado(tipo_imovel=None, bairro=None, cidade=None, cep=None, vaga_garagem=None, quadra=None, quartos=None, metragem=None):
    token = get_data_cache_token()
    return _analisar_imovel_detalhado_cached(
        token,
        tipo_imovel=tipo_imovel,
        bairro=bairro,
        cidade=cidade,
        cep=cep,
        vaga_garagem=vaga_garagem,
        quadra=quadra,
        quartos=quartos,
        metragem=metragem
    )

def clusterizar_dados2(df, valor_coluna, oferta_tipo, cluster, n_clusters=9):
    df_oferta = df[df['oferta'] == oferta_tipo].copy()
    if not df_oferta.empty and valor_coluna in df_oferta.columns and len(df_oferta) >= n_clusters:
        X = df_oferta[[valor_coluna]].values
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_oferta.loc[:, "cluster"] = kmeans.fit_predict(X)
        df_oferta.loc[:, 'cluster'] = df_oferta['cluster'].astype('category')
        return df_oferta[df_oferta['cluster'] == cluster]
    else:
        return df_oferta.iloc[0:0]

def carregar_dados_do_banco():
    Session = sessionmaker(bind=engine)
    session = Session()
    hoje = date.today()
    uma_semana_atras = hoje - timedelta(days=90)
    imoveis = session.query(Imovel).all()
    dados = [{
        "id":i.id,
        "codigo": i.codigo,
        "anunciante": i.anunciante,
        "oferta": i.oferta,
        "tipo": i.tipo,
        "area_util": float(i.area_util)if i.area_util is not None else 0.0,
        "bairro": i.bairro,
        "cidade": i.cidade,
        "preco": float(i.preco)if i.preco is not None else 0.0,
        "valor_m2": float(i.valor_m2)if i.valor_m2 is not None else 0.0,
        "quartos": float(i.quartos)if i.quartos is not None else 0.0,
        "vagas": float(i.vagas)if i.vagas is not None else 0.0,
        "latitude": float(i.latitude) if i.latitude is not None else 0.0,
        "longitude": float(i.longitude)if i.longitude is not None else 0.0,
        "data_coleta":i.data_coleta
    } for i in imoveis]
    session.close()
    return pd.DataFrame(dados)

@cache.cached(timeout=600)
def carregar_dados_df():
    Session = sessionmaker(bind=engine)
    session = Session()
    hoje = date.today()
    uma_semana_atras = hoje - timedelta(days=90)
    imoveis = session.query(Imovel).filter(Imovel.data_coleta >= uma_semana_atras).all()
    dados = [{
        "id": i.id,
        "codigo": i.codigo,
        "anunciante": i.anunciante,
        "oferta": i.oferta,
        "tipo": i.tipo,
        "area_util": float(i.area_util) if i.area_util is not None else 0.0,
        "bairro": i.bairro,
        "cidade": i.cidade,
        "preco": float(i.preco) if i.preco is not None else 0.0,
        "valor_m2": float(i.valor_m2) if i.valor_m2 is not None else 0.0,
        "quartos": float(i.quartos) if i.quartos is not None else 0.0,
        "vagas": float(i.vagas) if i.vagas is not None else 0.0,
        "latitude": float(i.latitude) if i.latitude is not None else 0.0,
        "longitude": float(i.longitude)if i.longitude is not None else 0.0,
        "data_coleta":i.data_coleta
    } for i in imoveis]
    session.close()
    return pd.DataFrame(dados)

def salvar_oferta_no_banco(df_oferta, oferta_tipo):
    from app import SessionLocal
    session = SessionLocal()
    try:
        if oferta_tipo == 'Aluguel':
            session.execute(text("TRUNCATE TABLE imoveis_aluguel RESTART IDENTITY CASCADE"))
        elif oferta_tipo == 'Venda':
            session.execute(text("TRUNCATE TABLE imoveis_venda RESTART IDENTITY CASCADE"))

        ids_df = df_oferta['id'].tolist()
        ids_existentes = {id for (id,) in session.query(Imovel.id).filter(Imovel.id.in_(ids_df)).all()}

        objetos = []
        for _, row in df_oferta.iterrows():
            if row['id'] not in ids_existentes:
                continue
            if oferta_tipo == 'Aluguel':
                objetos.append(ImovelAluguel(id=row['id'], cluster=row.get('cluster')))
            else:
                objetos.append(ImovelVenda(id=row['id'], cluster=row.get('cluster')))

        session.bulk_save_objects(objetos)
        session.commit()
        print(f"[OK] Tabela de {oferta_tipo} preenchida com sucesso.")
    except Exception as e:
        session.rollback()
        print(f"[ERRO] Falha ao salvar dados de {oferta_tipo}: {e}")
    finally:
        session.close()
