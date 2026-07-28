# Front-end — Inteligência Imobiliária 61

SPA em **React 19** (Create React App) que consome a API Flask (`/api/v1`). Reúne o site
público (precificador + captura de leads) e a plataforma interna de corretores/gerentes:
visitas, jornada de captação, rankings, RH, vendas, gestão de bases e o chat de IA.

- **React 19** + **react-router-dom 7** (roteamento client-side)
- **Context API** para autenticação (`AuthContext`) e toasts (`ToastContext`)
- **fetch** encapsulado em `src/services/api.js`; interceptor global de auth em
  `src/services/authFetch.js` (injeta `X-API-KEY` + `Bearer` em toda chamada `/api/v1`)
- Estilo próprio (design system em CSS, sem framework de UI)
- Servido em produção pelo **nginx como build estático** em `/var/www/html` (ver §Produção)

---

## Como a página funciona

O `App.js` monta a árvore: `AuthProvider → ToastProvider → Router`, com `<Header />` fixo
no topo, `<Footer />` embaixo e as rotas no `<main>`. O **Header** exibe o menu **Serviços**
(itens filtrados por permissão) e o menu de perfil (trocar senha / sair).

- **Rota pública `/`** → `FormularioPublico`: landing com o **precificador** e captura de lead.
- **Rota interna `/interno`** → `Tabs`: alterna entre **Formulário**, **Mapa** e **Relatório**
  (o núcleo de precificação — consulta `/imovel/venda` e `/imovel/aluguel`, mapa e relatório).

### Autenticação e permissões

`AuthContext` guarda o login em `localStorage` (`auth` + `userData`) e a permissão vem do
`userData.permissao` retornado no login.

**API fechada (2026-07-23).** Toda chamada precisa de `X-API-KEY` **ou** `Authorization:
Bearer <jwt>`. Quem injeta é o interceptor global `src/services/authFetch.js` (instalado uma
vez no `index.js`): ele faz *monkeypatch* do `window.fetch` e adiciona os headers em qualquer
URL que contenha `/api/v1` — cobrindo o `api.js` e os `fetch()` crus dos componentes.

- `X-API-KEY` = chave estática da app (`REACT_APP_API_KEY`, **inlined no build** pelo CRA;
  mesma `API_SECRET_KEY` do backend). Como fica no bundle, é legível por quem usa o site —
  fecha a API só pra chamador não-browser.
- `Bearer` = JWT do usuário salvo no login (`localStorage.auth_token`), quando houver.

> ⚠️ **Downloads (PDF/relatórios)** têm que ir por `fetch`→blob, **nunca** `window.open` ou
> `<a href download>` direto na URL da API: navegação do browser não carrega o `X-API-KEY` →
> 401. Ver `baixarArquivoApi` em `components/RelatorioGerente.js` e o padrão fetch→blob→anchor
> no `Ranking.js`.

Hierarquia (crescente): **corretor → gerente → administrador → diretor**. Há ainda o perfil
**administrativo** (por `permissao` ou `team === 'administrativo'`). Flags derivadas:

| Flag | Verdadeiro para |
|---|---|
| `isLogado` | qualquer usuário autenticado |
| `isGerente` / `isAdmin` | gerente, administrador, diretor |
| `isAdministrador` | administrador, diretor **ou** administrativo |
| `isDiretor` | diretor |

### Guardas de rota (`src/auth/`)

| Guarda | Regra | Redireciona para |
|---|---|---|
| `PrivateRoute` | exige `isLogado` | `/login` |
| `AdminRoute` | logado **e** `isAdmin` (gerente+) | `/login` ou `/` |
| `AdministradorRoute` | logado **e** `isAdministrador` | `/login` ou `/` |

---

## Mapa de rotas

| Rota | Componente | Acesso | Função |
|---|---|---|---|
| `/` | `FormularioPublico` | público | Landing + precificador + lead |
| `/login` | `Login` | público | Autenticação |
| `/register` | `Register` | público / administrador | Criar conta / registrar usuário |
| `/RecuperarSenha` | `RecuperarSenha` | público | Recuperar senha |
| `/Experts` | `Experts` | público | Página de corretores/experts |
| `/61Financiamento` | `CalculoFinanciamento` | público | Simulador de financiamento |
| `/verificarImovel` | `ReporteImovelWidget` | público | Widget de verificação de imóvel |
| `/enviarVisita` | `FormVisita` | público | Envio de formulário de visita |
| `/FormComissao` | `FormComissao` | público | Formulário de comissão |
| `/interno` | `Tabs` (Formulário/Mapa/Relatório) | privado | Núcleo de precificação |
| `/TrocarSenha` | `TrocarSenha` | privado | Trocar senha |
| `/Ranking` | `Ranking` | privado | Rankings (VGV/VGC/captação/visitas) |
| `/NovaVisita` | `NovaVisita` | privado | Criar visita |
| `/AppVisita` | `FormVisitaApp` | privado | Relatório de visita (app) |
| `/JornadaCaptacao` | `JornadaCaptacao` | privado | Jornada de captação (`?novo=1` cria) |
| `/GestaoClientes` | `GestaoClientesVisitas` | privado | Gestão de clientes de visita |
| `/RelatorioGerente` | `RelatorioGerente` | gerente+ | Dashboard consolidado do gerente |
| `/GerenteRH` | `GerenteRHCorretores` | gerente+ | RH da equipe |
| `/RHUsuarios` | `RHUsuarios` | administrador+ | RH de usuários |
| `/ControleCorretor` | `ControleCorretor` | administrador+ | Controle de usuários |
| `/AdminBases` | `AdminBases` | administrador+ | Gestão de bases (BI) |
| `/Vendas` | `Vendas` | administrador+ | Dashboard de vendas |

> O menu **Serviços** (`Header.js`) espelha essas permissões: itens de gerente aparecem só
> para `isAdmin`; itens de gestão (`AdminBases`, `Vendas`) para administrador/diretor.

---

## Catálogo de componentes (`src/components/`)

**Público / precificação**
- `FormularioPublico` — landing pública com precificador e captura de lead.
- `Tabs` → `Formulario`, `Mapa`, `Relatorio` — as três abas do estudo de precificação.
- `ReporteImovelWidget`, `Experts`, `CalculoFinanciamento`, `FormComissao`, `ChatWidget`
  (assistente **Renata**).

**Autenticação**
- `Login`, `Register`, `RecuperarSenha`, `TrocarSenha`, `PasswordInput`.

**Visitas**
- `FormVisita`, `FormVisitaApp`, `NovaVisita`, `GestaoClientesVisitas`, `VisitasEvolucao`.

**Captação**
- `JornadaCaptacao`, `CaptacaoEvolucao`.

**Gestão / gerência**
- `RelatorioGerente`, `GerenteRHCorretores`, `RHUsuarios`, `ControleCorretor`,
  `AdminBases`, `Vendas`, `Ranking`, `rhFields`.

**Layout**
- `Header` (nav + perfil + menu Serviços), `Footer`.

Contextos: `AuthContext` (login/permissões) e `ToastContext` (notificações). Dados estáticos
em `src/assets/data/experts.json`.

---

## Comunicação com a API (`src/services/api.js`)

Cliente `fetch` fino com helpers `api.get/post/put/delete`. A base é resolvida de
`process.env.REACT_APP_API_URL` e **sempre normalizada para terminar em `/api/v1`**:

- Sem `REACT_APP_API_URL` → usa o caminho relativo `/api/v1` (mesma origem, atrás de proxy).
- Com host → `https://host` vira `https://host/api/v1`.

Respostas não-OK lançam `Error` com `data.error`/`data.message` (tratado nos componentes,
geralmente via toast).

```js
import { api } from '../services/api';
const dados = await api.get('/corretor/retornar-lista');
await api.post('/auth/login', { username, password }); // → { login, message, user }
```

---

## Estilo / design system

- `src/assets/css/design-system.css` — tokens e base compartilhada.
- Um CSS por componente/feature (`Header.css`, `ranking.css`, `JornadaCaptacao.css`,
  `Vendas.css`, `chat.css`, `Toast.css`, versões `*PaginaUnica.css` para páginas de impressão…).
- Imagens/logos em `src/assets/img/`; PDF institucional em `src/assets/pdf/`.

---

## Rodando

```bash
npm install
npm start      # dev, http://localhost:3000 (proxy da API via REACT_APP_API_URL)
npm run build  # build de produção (pasta build/)
npm test       # testes (react-scripts)
```

Configuração de ambiente (`.env.local`, **não versionado**):

```
REACT_APP_API_URL=https://api.inteligencia61imoveis.com.br
REACT_APP_API_KEY=<mesma API_SECRET_KEY do backend>   # inlined no build pelo CRA
```

> As `REACT_APP_*` são **inlined no build** (`npm run build`), não lidas em runtime. Trocar a
> URL/key exige rebuild. Sem `.env.local` com a key → interceptor manda header vazio → 401.

### Produção — nginx serve o build estático

O nginx da VM do front (`inteligencia61imoveis.com.br`) serve **`/var/www/html`** (build
estático), atrás de um `proxy_pass` de `/api/v1` pra API. O processo `react-scripts start` na
`:3000` é **legado e não serve nada** — não confie nele.

Deploy (na VM do front):
```bash
cd ~/Precificador && git pull origin dev_miron
cd frontend && npm run build
sudo rm -rf /var/www/html/static && sudo cp -r build/* /var/www/html/
```

> ⚠️ **`npm run build` sozinho não muda o site** — nada é servido até copiar `build/` pra
> `/var/www/html`. O bundle tem hash no nome (`main.<hash>.js`), então o cache do browser
> quebra sozinho ao trocar o `index.html`. Se algo "não atualiza", confira **onde o nginx
> aponta** (`sudo nginx -T | grep -E 'root|proxy_pass'`), não o build.

`Dockerfile` (multi-stage: build React → `serve`) e `../docker-compose.yml` existem para uso
local, mas **não** são o que roda em produção.

---

## Estrutura de pastas

```
frontend/src/
├── App.js                 # rotas + providers + layout
├── index.js               # instala o interceptor authFetch antes do render
├── auth/                  # PrivateRoute, AdminRoute, AdministradorRoute
├── context/               # AuthContext, ToastContext
├── components/            # telas e widgets (ver catálogo acima)
├── services/
│   ├── api.js             # cliente HTTP (base /api/v1)
│   └── authFetch.js       # interceptor global: injeta X-API-KEY + Bearer
└── assets/                # css (design system), img, pdf, data
```
