import pandas as pd
from flask_caching import Cache
import os
from dotenv import load_dotenv

def carregar_variaveis_ambiente():
    load_dotenv()

def init_cache(app):
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    return cache

def carregar_dados():
    df = pd.read_csv('./static/dados/2024-09-06.csv')
    df_map = pd.read_csv('./static/dados/dados_map.csv')
    return df, df_map
