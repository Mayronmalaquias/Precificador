# Inteligência Imobiliária 61 — Precificador

Plataforma full-stack da Imobiliária 61. Junta um **site público** (precificação de imóveis
por mercado + captura de leads + assistente de IA) e uma **plataforma interna** para
corretores, gerentes e administração: jornada de captação, relatórios de visita,
vendas/comissão, rankings, RH e gestão de bases (BI).

```
┌──────────────┐   HTTP /api/v1 (+X-API-KEY)  ┌──────────────┐   SQLAlchemy   ┌──────────────┐
│   frontend   │ ───────────────────────────▶ │   backend    │ ─────────────▶ │  PostgreSQL  │
│  React 19    │ ◀─────────────────────────── │  Flask API   │ ◀───────────── │  (AWS RDS)   │
└──────────────┘                              └──────────────┘                └──────────────┘
        │                                             │
        │                              Imoview · Google (Sheets/Drive) · Anthropic (Claude)
     app/ (Expo/React Native — mobile do corretor, mesma API)
```

> **Pastas renomeadas (2026-07-27):** `back-end→backend`, `front-end→frontend`,
> `aplicativo→app`. Configs de deploy (systemd, nginx, cron, `docker-compose.yml`) já
> apontam pros nomes novos. Ver seção **Produção**.

## Componentes

| Parte | Stack | Doc |
|---|---|---|
| **Backend** | Flask + Flask-RESTx, SQLAlchemy, Pandas/scikit-learn (KMeans), fpdf2/folium | [`backend/README.md`](backend/README.md) |
| **Frontend** | React 19 + react-router-dom 7, Context API | [`frontend/README.md`](frontend/README.md) |
| **Mobile** | Expo / React Native (app do corretor) | [`app/README.md`](app/README.md) |
| **Banco** | PostgreSQL `coleta_imobiliaria` (47 tabelas, 7 domínios) | [`MAPA_BANCO.md`](MAPA_BANCO.md) · [`DIAGRAMA_BANCO.md`](DIAGRAMA_BANCO.md) |

## O que o sistema faz

- **Precificação** — sugere faixa de venda/aluguel por bairro, tipo, quartos e cluster (KMeans
  sobre a base de scraping de portais).
- **Captação** — jornada do corretor por etapas, com histórico, exclusividade e evolução.
- **Visitas** — lançamento, clientes/parceiros e geração de PDF (salvo no Google Drive).
- **Vendas & comissão** — dashboard de contratos (2015→hoje) e divisão manual de comissão.
- **Rankings** — VGV, VGC, captação e visitas, por corretor e equipe.
- **RH & gestão** — CRUD de usuários, RH de equipe, gestão de bases (importação de planilhas).
- **IA** — assistente **Renata** (Claude) no site público.

Identidade de negócio: pessoa = `usuarios.id_usuarios` (`C61xxx`); equipe = `equipes.id_equipe`
(`G61xxx`). Detalhes em [`MAPA_BANCO.md`](MAPA_BANCO.md).

## Rodando

### Docker (raiz)

```bash
docker-compose up --build
# front → http://localhost:3000   ·   API → http://localhost:5000  (Swagger em /docs)
```

### Local (sem Docker)

Backend e frontend têm instruções próprias — ver os READMEs de cada pasta.

```bash
# backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python run.py

# frontend (outro terminal)
cd frontend && npm install && npm start
```

> No dev, `frontend/.env.local` aponta pra `http://localhost:5000`. Em prod cada VM tem o
> seu `.env`/`.env.local` (nunca versionado) com a URL/keys de produção.

## Produção

Rodam **duas VMs AWS separadas**, a API atrás de `https://api.inteligencia61imoveis.com.br`
e o site em `https://inteligencia61imoveis.com.br`. A API é **fechada** (2026-07-23): toda
requisição exige `X-API-KEY` (chave estática da app, web + mobile) **ou** `Authorization:
Bearer <jwt>` — ver [`backend/README.md`](backend/README.md) §Autenticação e o interceptor
`frontend/src/services/authFetch.js`.

**VM backend** — API via **systemd + Gunicorn** (`precificador.service`, `WorkingDirectory` e
`ExecStart` em `~/Precificador/backend`, venv em `backend/venv`). Cron roda `sync_contratos.py`
a cada 30 min.
```bash
cd ~/Precificador && git pull origin dev_miron
sudo systemctl restart precificador.service
sudo journalctl -u precificador.service -n 100 --no-pager
```

**VM frontend** — nginx serve o **build estático** de `/var/www/html` (o processo
`react-scripts start` na :3000 é **legado, não serve nada**). Deploy = build + copiar:
```bash
cd ~/Precificador && git pull origin dev_miron
cd frontend && npm run build
sudo rm -rf /var/www/html/static && sudo cp -r build/* /var/www/html/
```
> ⚠️ **Rebuildar não basta**: nada é servido até copiar `build/` pra `/var/www/html`. Os
> nomes de bundle têm hash (`main.<hash>.js`) → o cache do browser quebra sozinho a cada
> deploy. `frontend/.env.local` (com `REACT_APP_API_URL` + `REACT_APP_API_KEY`) **precisa
> existir na VM antes do build** — CRA inlina essas vars no bundle; sem elas → 401.

> ⚠️ **Downloads de PDF** vão por `fetch`→blob (não `window.open`/`<a download>`), senão a
> navegação do browser não leva o `X-API-KEY` e a API responde 401.

Docker (`docker-compose.yml`) existe e sobe os dois serviços localmente, mas **não** é o que
roda em produção.

## Estrutura

```
/
├── backend/           # API Flask (routes, services, models, migrations, sql, dados)
├── frontend/          # SPA React (build/ servido por nginx em prod)
├── app/               # app mobile Expo / React Native (corretor)
├── docs/processos/    # "segundo cérebro": processos da Inteligência (.md)
├── legado/            # material/documentação legada
├── MAPA_BANCO.md      # inventário do banco + plano de normalização
├── DIAGRAMA_BANCO.md  # diagrama ER (Mermaid)
└── docker-compose.yml
```
