import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

print("--- INICIANDO SCRIPT DE TESTE DE CONEXÃO ---")

# Pegando as credenciais do ambiente (do arquivo .env)
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Verificando se todas as variáveis foram carregadas
if not all([db_user, db_pass, db_host, db_port, db_name]):
    print("ERRO: Uma ou mais variáveis de ambiente (DB_...) não foram encontradas no arquivo .env!")
else:
    print(f"Variáveis carregadas. Tentando conectar em: {db_host}")
    
    try:
        # Monta a URL de conexão
        db_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        # Cria o motor de conexão
        engine = create_engine(db_url)
        
        # Define a query mais simples possível para testar a coluna
        query = text("SELECT data_coleta FROM imoveis LIMIT 1;")
        
        # Tenta se conectar e executar a query
        with engine.connect() as connection:
            print("Conexão com o banco de dados bem-sucedida.")
            print(f"Executando a query: {query}")
            
            result = connection.execute(query)
            row = result.fetchone()
            
            print("\nSUCESSO! A coluna 'data_coleta' foi lida com êxito.")
            print(f"   Valor encontrado: {row}")

    except ProgrammingError as e:
        print("\n❌ FALHA! O banco de dados retornou um erro de 'UndefinedColumn'.")
        print("   Isso prova que o problema está na conexão ou no próprio banco (schema, nome da coluna, etc.).")
        print(f"   Erro original do psycopg2: {e.orig}")
        
    except Exception as e:
        print(f"\nFALHA! Ocorreu um erro inesperado ao tentar conectar ou executar a query.")
        print(f"   Detalhes do erro: {e}")

print("\n--- FIM DO SCRIPT DE TESTE ---")