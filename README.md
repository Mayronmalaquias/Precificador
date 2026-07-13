# Inteligência Imobiliária 61 — Precificador

Plataforma full-stack da Imobiliária 61. Junta um **site público** (precificação de imóveis
por mercado + captura de leads + assistente de IA) e uma **plataforma interna** para
corretores, gerentes e administração: jornada de captação, relatórios de visita,
vendas/comissão, rankings, RH e gestão de bases (BI).

```
┌──────────────┐      HTTP /api/v1      ┌──────────────┐      SQLAlchemy      ┌──────────────┐
│  front-end   │ ─────────────────────▶ │   back-end   │ ───────────────────▶ │  PostgreSQL  │
│  React 19    │ ◀───────────────────── │  Flask API   │ ◀─────────────────── │  (AWS RDS)   │
└──────────────┘                        └──────────────┘                      └──────────────┘
        │                                       │
        │                              Imoview · Google (Sheets/Drive) · Anthropic (Claude)
```

## Componentes

| Parte | Stack | Doc |
|---|---|---|
| **Back-end** | Flask + Flask-RESTx, SQLAlchemy, Pandas/scikit-learn (KMeans), fpdf2/folium | [`back-end/README.md`](back-end/README.md) |
| **Front-end** | React 19 + react-router-dom 7, Context API | [`front-end/README.md`](front-end/README.md) |
| **Banco** | PostgreSQL `coleta_imobiliaria` (47 tabelas, 7 domínios) | [`MAPA_BANCO.md`](MAPA_BANCO.md) · [`DIAGRAMA_BANCO.md`](DIAGRAMA_BANCO.md) |

## O que o sistema faz

- **Precificação** — sugere faixa de venda/aluguel por bairro, tipo, quartos e cluster (KMeans
  sobre a base de scraping de portais).
- **Captação** — jornada do corretor por etapas, com histórico, exclusividade e evolução.
- **Visitas** — lançamento, clientes/parceiros e geração de PDF (salvo no Google Drive).
- **Vendas & comissão** — dashboard de contratos (2015→hoje) e divisão manual de comissão.
- **Rankings** — VGV, VGC, captação e visitas, por corretor e equipe.
- **RH & gestão** — CRUD de usuários, RH de equipe, gestão de bases (importação de planilhas).
- **IA** — assistente "Sofia" (Claude) no site público.

Identidade de negócio: pessoa = `usuarios.id_usuarios` (`C61xxx`); equipe = `equipes.id_equipe`
(`G61xxx`). Detalhes em [`MAPA_BANCO.md`](MAPA_BANCO.md).

## Rodando

### Docker (raiz)

```bash
docker-compose up --build
# front → http://localhost:3000   ·   API → http://localhost:5000  (Swagger em /docs)
```

### Local (sem Docker)

Back-end e front-end têm instruções próprias — ver os READMEs de cada pasta.

```bash
# back-end
cd back-end && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python run.py

# front-end (outro terminal)
cd front-end && npm install && npm start
```

## Produção

Back-end em VM via serviço systemd `precificador`; front servido como estático (mesma origem
da API). Deploy:

```bash
git pull origin dev_miron
sudo systemctl restart precificador
sudo journalctl -u precificador -n 100 --no-pager
```

## Estrutura

```
/
├── back-end/          # API Flask (routes, services, models, migrations, sql)
├── front-end/         # SPA React
├── legado/            # material/documentação legada
├── MAPA_BANCO.md      # inventário do banco + plano de normalização
├── DIAGRAMA_BANCO.md  # diagrama ER (Mermaid)
└── docker-compose.yml
```
