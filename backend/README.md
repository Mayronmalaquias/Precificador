# Back-end — Inteligência Imobiliária 61

API REST em **Flask** que sustenta a plataforma interna da Imobiliária 61: precificação
de imóveis por mercado, jornada de captação, relatórios de visita, vendas/comissão,
rankings, RH de corretores, gestão de bases (BI) e um assistente de IA.

- **Framework:** Flask 2.1 + Flask-RESTx (Swagger automático em `/docs`)
- **ORM:** SQLAlchemy 1.4 (sessão em `app/database.py`)
- **Banco:** PostgreSQL (AWS RDS — `coleta_imobiliaria`)
- **Análise:** Pandas + NumPy + scikit-learn (KMeans, clusterização de imóveis)
- **PDF/Mapas/Gráficos:** fpdf2, folium, matplotlib
- **Integrações externas:** Imoview (CRM), Google Sheets/Drive, Anthropic (Claude)
- **Auth:** API fechada — `X-API-KEY` (chave da app) **ou** `Bearer` JWT (ver §Autenticação)
- **Prod:** Gunicorn (workers `gthread`) em `127.0.0.1:5000`, atrás do nginx, serviço systemd
  `precificador.service` — roda na **VM de backend**, separada da VM do front

> **Banco de dados:** o mapa completo (47 tabelas, 7 domínios, FKs e relações por valor)
> está em [`../MAPA_BANCO.md`](../MAPA_BANCO.md) e o diagrama ER em
> [`../DIAGRAMA_BANCO.md`](../DIAGRAMA_BANCO.md). Leia-os antes de mexer em dados.

---

## Arquitetura

Aplicação em camadas, montada por *app factory* (`app/__init__.py` → `create_app`):

```
HTTP → routes/ (Flask-RESTx Namespaces)   ← valida request, formata resposta
         └→ services/ (regra de negócio)   ← lógica, integrações, queries
              └→ models/ (SQLAlchemy ORM)   ← mapeamento das tabelas
                   └→ database.py (Session)  ← engine + sessão scoped
```

- **`app/config.py`** — lê `.env` (via `python-dotenv`). Monta a URI do banco a partir de
  `DATABASE_URL` **ou** de `DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME` (fallback:
  SQLite `precificador_dev.db`). Também define `API_PREFIX` (padrão `/api/v1`), `SECRET_KEY`,
  `CORS_ORIGINS` e opções de cache.
- **`app/database.py`** — `engine` + `SessionLocal` (scoped session). A sessão é removida a
  cada request (`teardown_appcontext`). Serviços fazem `from app.database import SessionLocal`.
- **`app/extensions.py`** — `cache` (Flask-Caching), usado em análises pesadas.
- **`run.py`** — entrypoint: `app = create_app()`. Em prod é servido pelo Gunicorn (`run:app`).

Todos os *namespaces* são registrados sob o prefixo `API_PREFIX` (`/api/v1`). O
**gerente-dashboard** ganha um sub-prefixo próprio (`/api/v1/gerente-dashboard`). A
documentação interativa (Swagger UI) fica em **`/docs`** e é a fonte canônica dos endpoints.

---

## Domínios / funcionalidades

| Domínio | O que faz | Rotas (namespace) | Serviços principais |
|---|---|---|---|
| **Precificação** | Sugere faixa de preço (venda/aluguel) por bairro/tipo/quartos/cluster usando KMeans sobre a base de scraping (`imoveis`). Resultado cacheado 1h + `precomputed_analise.json`. | `analise` | `analise_service` |
| **Mapa** | Gera mapa (folium) e dados geográficos dos imóveis coletados. | `mapa` | `mapa_service` |
| **Gráficos** | Séries/linhas de métricas de imóveis. | `graph` | `graph_service` |
| **Relatório de imóvel** | Relatório público de um imóvel (widget "verificar imóvel"). | `report` | `imovel_rel_service` |
| **Catálogo do corretor** | Lista imóveis do corretor + PDF do catálogo. | `imovel_catalogo` | `imovel_rel_service`, `imoview_service` |
| **Autenticação** | Cadastro, login, troca e recuperação de senha. | `auth` | `auth_service` |
| **Usuários / Corretores (RH)** | CRUD de usuários, campos de RH, ativar/desligar, trocar gerente. | `corretor` | `usuarios_service` |
| **Captação (Jornada)** | Jornada de captação do corretor por etapas (escolha→prospecção→interação→apresentação→captação), histórico, fechamento, exclusividade e snapshots diários de evolução. | `captacao` | `captacao_service`, `captacao_snapshot_service` |
| **Visitas** | Lançamento de visitas, clientes/parceiros, upload e geração de PDF do relatório de visita (salvo no Google Drive). | `visitas`, `relatorio_visita` | `visita_service`, `relatorio_visita_service`, `visita_vistas_service`, `google_service` |
| **Dashboard do gerente** | Consolidado da equipe: imóveis, corretores, visitas, clientes, ranking, séries, evolução, PDFs por corretor/gerente/equipe e gestão de clientes. | `gerente-dashboard` | `gerente_visitas_service`, `rela_gerentes_service`, `corretor_pdf_service`, `cliente_acao_service` |
| **Vendas / Contratos** | Resumo e detalhe de vendas (base canônica `contratos`/`vendas` 2015→hoje). | `vendas` | `vendas_dash_service`, `sync_contratos_service` |
| **Divisão de comissão** | Divisão manual de comissão de contratos. | `divisao` | `divisao_comissao` (routes/service) |
| **Rankings** | VGV, VGC, captação e visitas — por corretor e equipe, com PDF e ocultação de participantes. | `ranking` + blueprint `meta_gerente_bp` | `ranking_service`, `ranking_ocultos_service`, `meta_service` |
| **Gestão de Bases (BI)** | Importação/edição das bases de captação, saída, estoque, destaque, venda e leads (planilhas Imoview/Contact2Sale) → tabelas `fato_*`. | `admin-bases` | `admin_bases_service`, `leads_service` |
| **Assistente IA (Renata)** | Chat com Claude (Anthropic) no site público. | `chat` | `chat_service` |

---

## Autenticação (API fechada — 2026-07-23)

Guard global em `app/utils/auth_middleware.py` (`before_request`). **Toda** requisição precisa
de **um** dos dois (regra "OU"):

1. `X-API-KEY: <API_SECRET_KEY>` — chave estática da aplicação, compartilhada por web + mobile.
2. `Authorization: Bearer <jwt>` — JWT por usuário, emitido no login (`gerar_jwt`, HS256 com
   `JWT_SECRET`).

Sem credencial válida → **HTTP 401** `{"error":"Nao autorizado", ...}`.

- **Rotas públicas** (sem auth): preflight `OPTIONS`, `/`, `/health` (e `{prefix}/health`),
  `/swagger.json`, `/docs`, `/swaggerui`.
- **Kill-switch:** `AUTH_ENABLED=false` reabre a API inteira sem redeploy.
- O front injeta os headers via interceptor (`frontend/src/services/authFetch.js`); o app
  mobile manda `X-API-KEY` em `app/src/services/api.ts`. **Downloads não podem ser navegação
  do browser** (`window.open`/`<a download>`) — não levam o header → 401; usar `fetch`→blob.

---

## Referência da API

Prefixo global: **`/api/v1`**. Todas as rotas abaixo são relativas a ele
(ex.: `POST /api/v1/auth/login`). Fonte canônica e testável: **Swagger em `/docs`**.
Login (`POST /auth/login`) devolve, além do usuário, um `token` (JWT) usado como `Bearer`.

### `auth` — autenticação
| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/cadastro` | Cadastra usuário |
| POST | `/auth/login` | Login (retorna dados do usuário/permissão) |
| POST | `/auth/switch-password` | Troca de senha do usuário logado |
| POST | `/auth/recuperar-senha` | Reset por `id_corretor` + `newpass` |

### `corretor` — usuários / RH
| Método | Rota | Descrição |
|---|---|---|
| GET | `/corretor/retornar-lista` | Lista corretores |
| GET | `/corretor/retornar-informacao` | Dados de um corretor |
| GET | `/corretor/retornar-nome` | Nome por id |
| GET | `/corretor/campos-rh` | Metadados dos campos de RH |
| POST | `/corretor/alterar-ativo` | Ativa/inativa usuário |
| POST | `/corretor/excluir-usuario` | Exclui usuário |
| POST | `/corretor/alterar-gerente` | Troca o gerente responsável |
| POST | `/corretor/editar-usuario` | Edita cadastro |
| POST | `/corretor/editar-rh-gerente` | Edição de RH pelo gerente |

### `analise` — precificação
| Método | Rota | Parâmetros |
|---|---|---|
| GET | `/imovel/venda` | `tipoImovel, bairro, nrCluster, quartos, vagas, metragem` |
| GET | `/imovel/aluguel` | idem |

### `mapa` / `graph` / `report`
| Método | Rota | Descrição |
|---|---|---|
| GET | `/mapa/carregar` | Dados/HTML do mapa |
| GET | `/graph/graficoLinha` | Série de linha |
| GET | `/reporteImovel` | Relatório público de imóvel |
| GET | `/health` | Healthcheck |

### `captacao` — jornada do corretor
| Método | Rota | Descrição |
|---|---|---|
| GET/POST | `/captacoes` | Lista / cria captação |
| GET/PUT | `/captacoes/<id>` | Detalha / atualiza |
| GET | `/captacoes/<id>/historico` | Histórico de etapas |
| POST | `/captacoes/<id>/fechar` | Fecha a captação |
| DELETE | `/captacoes/<id>/excluir` | Exclui |
| POST | `/captacoes/<id>/exclusividade` | Marca exclusividade |
| POST | `/captacoes/snapshot` | Gera snapshot diário |
| GET | `/captacoes/evolucao` · `/evolucao/opcoes` | Série de evolução + filtros |

### `visitas` / `relatorio_visita`
| Método | Rota | Descrição |
|---|---|---|
| POST · PUT · DELETE | `/visitas` · `/visitas/<id_visita>` | CRUD de visita |
| GET/POST | `/visitas/vistas` | Controle de leitura pelo gerente |
| GET | `/visitas/pdf` · `/visitas/pdf/download` | Relatório de visita em PDF |
| POST | `/upload_pdf` | Upload de PDF (Google Drive) |
| GET | `/imoveis_busca` · `/visitas_busca` · `/clientes_busca` · `/leads_busca` | Buscas (autocomplete) |
| GET/POST | `/clientes` | Clientes de visita |
| GET | `/clientes/pdf` · `/clientes/pdf/download` | PDF de clientes |
| GET | `/gerentes` | Lista de gerentes |
| GET | `/corretores/<id_corretor>/imoveis` | Imóveis do corretor (Imoview) |

### `gerente-dashboard` (prefixo `/api/v1/gerente-dashboard`)
`/imoveis`, `/corretores`, `/dashboard`, `/visitas`, `/clientes`, `/ranking`, `/serie`,
`/visitas/evolucao` (+`/opcoes`), `/visita/detalhe`, `/gestao-clientes` (+`/acoes`,
`/acoes/<id>`), e PDFs: `/corretor/pdf`(+`/download`), `/gerente/pdf`(+`/download`),
`/equipes/dashboard`, `/equipes/pdf/download`.

### `vendas` / `divisao`
| Método | Rota | Descrição |
|---|---|---|
| GET | `/vendas/resumo` · `/vendas` · `/vendas/<id_contrato>` | Dashboard e detalhe de vendas |
| GET | `/contratos-2026` · `/corretores` | Apoio à divisão |
| POST | `/divisao-comissao` | Salva divisão manual |

### `ranking`
`/rankings` (todos), `/rankings/<kind>` (kind = vgv/vgc/captacao/visitas), `/rankings/<kind>/equipe`,
`/rankings/todos/pdf`, `/rankings/corretor/detalhe`, `/rankings/corretor/pdf`,
`/rankings/ocultos` (GET/POST) e `/rankings/ocultos/<id_corretor>` (DELETE).
Blueprint extra: `POST /relatorio/metas-gerentes` e `/relatorio/metas-gerentes/preview`.

### `admin-bases` — gestão de bases (BI)
Importação (POST `/admin/bases/importar/{captacao,saida,estoque,destaque,leads-contact2sale}`),
CRUD por base (`/admin/bases/{captacao,saida,estoque,destaque,venda,leads}` GET/POST),
dimensões (`/admin/bases/tipos`, `/admin/bases/bairros` com PUT/DELETE por id) e
`POST /admin/bases/sync-contratos` (sincroniza contratos com a planilha).

### `chat`
| Método | Rota | Descrição |
|---|---|---|
| POST | `/chat` | Mensagem para a assistente IA (Claude) |

---

## Banco de dados & migrations

- **Schema atual:** ver [`../MAPA_BANCO.md`](../MAPA_BANCO.md) (inventário + redundâncias +
  plano de normalização) e [`../DIAGRAMA_BANCO.md`](../DIAGRAMA_BANCO.md) (ER Mermaid).
- **Migrations:** Alembic via Flask-Migrate, em `migrations/versions/`. A URL vem de
  `Config.SQLALCHEMY_DATABASE_URI` (`migrations/env.py`).
  ```bash
  flask db upgrade          # aplica
  flask db migrate -m "..." # gera nova (revise antes de aplicar)
  ```
- **Views SQL** (`sql/`): `vw_vendas` (vendas contínuas 2015→hoje), `vw_usuarios_duplicados`,
  `vw_pessoa_nao_resolvida`, `dedup_usuarios.sql`. Base canônica de vendas = `contratos`
  (coluna `fonte`), lida por `vendas`.
- **Identidade de negócio:** pessoa = `usuarios.id_usuarios` (`C61xxx`); equipe =
  `equipes.id_equipe` (`G61xxx`) = `usuarios.team`. `pessoa_alias` resolve nome/código →
  `id_usuarios`.

Scripts de dados (raiz do backend): `popula_vendas.py` (recarrega `vendas`),
`importar_contratos_legado.py` (importa histórico pré-2024), `sync_contratos.py`.

---

## Integrações externas

- **Imoview** (`imoview_service.py`) — CRM/portal; chave em `IMOVIEW_CHAVE`. Busca imóveis,
  corretores e leads.
- **Google Sheets/Drive** (`google_service.py`) — planilhas de vendas/visitas e upload de PDFs
  de relatório. Credenciais em `app/utils/asserts/service_account.json` (`GOOGLE_SA_JSON`).
- **Anthropic / Claude** (`chat_service.py`) — assistente Renata. `ANTHROPIC_API_KEY`.

---

## Variáveis de ambiente (`.env`)

```
# Banco (uma das opções)
DATABASE_URL=postgresql://user:senha@host:5432/coleta_imobiliaria
# ou:
DB_USER=... DB_PASSWORD=... DB_HOST=... DB_PORT=5432 DB_NAME=coleta_imobiliaria

API_PREFIX=/api/v1
SECRET_KEY=troque-em-producao
CORS_ORIGINS=http://localhost:3000,https://inteligencia61imoveis.com.br
CACHE_TYPE=simple
SQLALCHEMY_ECHO=false

# Auth (API fechada) — ver §Autenticação
AUTH_ENABLED=true
API_SECRET_KEY=...          # mesma chave usada como REACT_APP_API_KEY no front + app mobile
JWT_SECRET=...              # assina os JWT do login
JWT_ALGORITHM=HS256
JWT_EXPIRES_SECONDS=...

IMOVIEW_CHAVE=...
ANTHROPIC_API_KEY=...
GOOGLE_SA_JSON=/caminho/service_account.json
GSHEET_VENDAS_ID=...  GSHEET_VISITAS_ID=...  GSHEET_BASE_INTELIGENCIA_ID=...
```

> ⚠️ O `.env` versionado contém segredos reais (banco, Anthropic, Imoview). Não expor.

---

## Rodando localmente

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# .env configurado na raiz do backend
python run.py                      # dev, porta 5000 (host 0.0.0.0)
```

Swagger: http://localhost:5000/docs

### Produção (VM backend / systemd)

Roda na **VM de backend** (separada da do front). Serviço `precificador.service` com
`WorkingDirectory=~/Precificador/backend` e Gunicorn do `backend/venv`. Deploy:

```bash
cd ~/Precificador && git pull origin dev_miron
sudo systemctl restart precificador.service
sudo journalctl -u precificador.service -n 100 --no-pager   # logs

# renovar token OAuth do Google (Drive de visitas), quando necessário:
python -c "from app.services.visita_service import ensure_oauth_token; ensure_oauth_token()"
```

Gunicorn (linha real do `ExecStart`):

```bash
backend/venv/bin/gunicorn --workers 5 --worker-class gthread --threads 4 \
  --timeout 240 --max-requests 200 --max-requests-jitter 20 \
  --bind 127.0.0.1:5000 run:app
```

**Cron:** `sync_contratos.py` roda a cada 30 min (`crontab -e`), com caminho absoluto pra
`~/Precificador/backend/venv/bin/python`.

> ⚠️ **venv não é relocável.** Ao mover/renomear a pasta do backend, os shebangs em
> `venv/bin/*` continuam apontando pro caminho antigo → `systemctl` dá `status=203/EXEC`.
> Conserte com `sed -i 's#/caminho/antigo#/caminho/novo#g'` nos `venv/bin/*` + `pyvenv.cfg`,
> ou recrie o venv (`python3 -m venv venv && venv/bin/pip install -r requirements.txt`).
> `pd.read_excel(.xlsx)` (import de bases) exige `openpyxl` instalado no venv.

Docker (opcional): `Dockerfile` na raiz do backend; orquestração em `../docker-compose.yml`.
**Não** é o que roda em produção.

---

## Estrutura de pastas

```
backend/
├── app/
│   ├── __init__.py          # app factory + registro de namespaces + auth middleware
│   ├── config.py            # env, URI do banco, CORS, cache, auth (API_SECRET_KEY/JWT)
│   ├── database.py          # engine + SessionLocal
│   ├── extensions.py        # cache
│   ├── models/              # ORM (ver MAPA_BANCO.md)
│   ├── routes/              # namespaces Flask-RESTx (a API)
│   ├── services/            # regra de negócio + integrações
│   └── utils/               # auth_middleware (X-API-KEY/JWT), cache, asserts (credenciais)
├── migrations/versions/     # Alembic
├── sql/                     # views e scripts de manutenção
├── dados/                   # CSVs, precomputed_analise.json + planilhas Imoview (xlsx)
├── sync_contratos.py        # sync de contratos (roda no cron, 30 min)
├── requirements.txt
├── run.py
└── Dockerfile
```
