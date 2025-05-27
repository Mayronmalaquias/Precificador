# Projeto Back-End com Flask e KMeans

Este projeto é um back-end desenvolvido em **Flask** que realiza **clusterização de dados utilizando o algoritmo KMeans**, expondo os resultados por meio de uma API RESTful. A aplicação é conteinerizada com **Docker** e utiliza **Gunicorn** para execução em ambiente de produção.

## 🔧 Tecnologias Utilizadas

* Python 3.9
* Flask
* Flask-RESTx
* SQLAlchemy
* Scikit-Learn (KMeans)
* Pandas / NumPy
* Docker + Gunicorn
* PostgreSQL (via `psycopg2-binary`)
* Folium (para geração de mapas, se aplicável)

## 📁 Estrutura do Projeto

```
/
├── app/
│   ├── models/            # Modelos ORM (SQLAlchemy)
│   ├── routes/            # Rotas da API (Flask-RESTx)
│   ├── utils/             # Funções auxiliares e de clusterização
│   └── run.py             # Entrypoint Flask
├── requirements.txt       # Dependências
├── Dockerfile             # Build do container
└── README.md              # Este arquivo
```

## ▶️ Como Rodar com Docker

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/seu-projeto.git
cd seu-projeto
```

### 2. Configure variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto (caso utilize variáveis como `DATABASE_URL`, `OPENAI_API_KEY`, etc.):

```
DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_do_banco
OPENAI_API_KEY=sua-chave
```

### 3. Construa a imagem Docker

```bash
docker build -t flask-kmeans-api .
```

### 4. Execute o container

```bash
docker run -p 5000:5000 --env-file .env flask-kmeans-api
```

A aplicação estará acessível em: [http://localhost:5000](http://localhost:5000)

---

## 🧠 Exemplo de Funcionalidades

* `GET /api/clusters` – Retorna os dados clusterizados
* `POST /api/analisar` – Envia novos dados para clusterização
* `GET /api/mapa` – Retorna mapa com os clusters (via Folium)

> Se estiver usando `flask-restx`, a documentação Swagger pode estar acessível em `/docs`.

---

## 🐍 Executar Localmente (sem Docker)

1. Crie e ative um ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Exporte variáveis de ambiente (ou use um `.env` com `python-dotenv`):

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
```

4. Execute o Flask localmente:

```bash
flask run
```

---

## 📌 Observações

* A aplicação roda na porta `5000`.
* Gunicorn é utilizado no container como servidor WSGI:

  ```bash
  gunicorn --bind 0.0.0.0:5000 --timeout 240 run:app
  ```
* Certifique-se de que o banco de dados esteja acessível, especialmente se estiver usando PostgreSQL via `psycopg2-binary`.

---

## 📄 Licença

Este projeto está licenciado sob os termos da **MIT License**.
