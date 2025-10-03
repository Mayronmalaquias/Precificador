# Projeto Full Stack com Docker Compose

Este projeto utiliza Docker Compose para orquestrar dois contêineres principais:

* Um **back-end** em Flask (com suporte a clusterização via KMeans)
* Um **front-end** (React)

## 🔧 Tecnologias Utilizadas

* Docker & Docker Compose
* Flask + Gunicorn (back-end)
* Front-end em React (ou outra tecnologia web)
* Flask-RESTx, SQLAlchemy, Pandas, Scikit-Learn, entre outras libs Python

## 📁 Estrutura do Projeto

```
/
├── docker-compose.yml
├── back-end/
│   ├── Dockerfile
│   └── (código Python Flask)
├── front-end/
│   ├── Dockerfile
│   └── (código do front-end)
```

## ▶️ Como Rodar o Projeto com Docker Compose

### 1. Clone o repositório e entre no diretório raiz:

```bash
git clone https://github.com/seu-usuario/seu-projeto.git
cd seu-projeto
```

### 2. (Opcional) Crie um arquivo `.env` com variáveis para o back-end:

```
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
OPENAI_API_KEY=sua-chave
```

### 3. Construa e suba os containers:

```bash
docker-compose up --build
```

O front-end estará acessível em: [http://localhost:3000](http://localhost:3000)
O back-end (API Flask) em: [http://localhost:5000](http://localhost:5000)

## 🔄 Reiniciar sem reconstruir:

```bash
docker-compose up
```

Para subir em segundo plano:

```bash
docker-compose up -d
```

## ❌ Parar os containers:

```bash
docker-compose down
```

## 📌 Observações

* O `depends_on` garante que o front-end só inicie após o back-end estar disponível.
* Certifique-se de que os ports `3000` (frontend) e `5000` (backend) estejam livres.
* Adapte os caminhos dos `Dockerfile` e `context` conforme a estrutura real do seu projeto.

## 📄 Licença

Este projeto está licenciado sob os termos da **MIT License**.
