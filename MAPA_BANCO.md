# Mapa do Banco — `coleta_imobiliaria` (RDS Postgres)

Gerado por introspecção do banco real (47 tabelas) + models SQLAlchemy.
Objetivo: enxergar tudo, achar redundância e planejar normalização **sem perder dado**.

## Convenção de identidade (IDs de negócio)
- **Pessoa** → `usuarios.id_usuarios` no formato `C61xxx` (corretor), `ADMxxx`, `EXCLUSIVE USER`...
  ⚠️ É a chave de negócio, mas **não é UNIQUE** (PK real é `usuarios.id`).
- **Equipe/Gerente** → `equipes.id_equipe` no formato `G61xxx` (= `usuarios.team`).
- Quase todas as tabelas guardam esses códigos **por valor, sem FK** (ou guardam só o nome).

---

## Domínios (47 tabelas)

### 1. Pessoas & Equipes — núcleo de identidade
| tabela | linhas | papel |
|---|---|---|
| `usuarios` | 232 | pessoas. `id_usuarios`(C-code), `nome`, `team`(G-code), `permissao`, `id_imoview` |
| `equipes` | 11 | `id_equipe`(G-code) = `usuarios.team`; `nome` (AGEF, AGUIA, PRIME...) |

Relação implícita (sem FK): `usuarios.team → equipes.id_equipe`.

### 2. Vendas / Contratos / Comissão
| tabela | linhas | cols | período | pessoas |
|---|---|---|---|---|
| `contratos` | 661 | 148 | **2024→2026** | só **nome** (`diretor_nome`, `gerente_*_nome`, `corretor_*_nome`) |
| `vendas_legado` | 1557 | 61 | **2015→2026** | só nome (vendedor/captador/gerente); tem `idcontrato` |
| `divisao_comissao` | 0 | 9 | — | `id_corretor` **+** `nome_corretor` |
| `recebidos_legado` | 172 | 5 | — | `Data`, `contrato`, valor |

### 3. Captação — jornada do corretor (operacional do site)
| tabela | linhas | papel |
|---|---|---|
| `captacao` | 568 | `id_corretor` **+** `nome_corretor` **+** `team` (etapas da jornada) |
| `captacao_historico` | 2646 | `captacao_id` (sem FK) |
| `cliente_acao` | 4 | ações de cliente |

### 4. Fatos de imóvel / BI (Base Inteligência)
| tabela | linhas | papel |
|---|---|---|
| `eventos_imovel_legado` | 171.401 | histórico congelado captacao/saida/estoque/destaque*; `captador1/2/3`=C-code, `id_gerente`=G-code (sem FK) |
| `fato_captacao/saida/estoque/destaque` | 0 | **correntes** (novas, gestão pelo site) |
| `imoveis_legado` | 17.100 | Dim_Imovel — **FK** `tipo→tipos_imovel_legado`, `bairro→bairros_legado` |
| `bairros_legado` | 95 | Dim_Bairro |
| `tipos_imovel_legado` | 11 | Dim_Tipo |
| `nichos_legado` | 40 | nicho por corretor (`corretor`, `gerente`, `equipe` por nome) |
| `metas_mensais_legado` | 41 | meta por `id_gerente` (G-code, sem FK) |
| `campanhas_legado` | 2019 | mídia paga |
| `anuncios_imovel_legado` | 109 | Dim_Anuncio |
| `portais_legado` | 5 / `fontes_legado` 14 / `atendimentos_legado` 8 / `diretores_legado` 1 | dims pequenas |

### 5. Visitas (operacional do site)
| tabela | linhas | papel |
|---|---|---|
| `visitas` | 1342 | **FK** → `clientes_visita`, `parceiros_visita` |
| `clientes_visita` 706 / `parceiros_visita` 14 | | pessoas da visita |
| `visita_cliente` 1271 / `visita_parceiro` 18 | | N:N (**FK**) |
| `avaliacoes_visita` | 1342 | **FK** visita/cliente/parceiro |
| `gerente_visita_visualizada` | 816 | controle de leitura |
| `relatorios_imovel_legado` 98 / `sessoes_usuario_legado` 11 / `menus_legado` 9 / `admins_legado` 3 | | legado do app de visitas |

### 6. Leads / CRM
| tabela | linhas | papel |
|---|---|---|
| `leads_legado` | 63.430 | histórico de leads |
| `leads` 0 / `contatos` 0 / `logestagios` 0 | | CRM novo **vazio** (FK `contatos.lead_id→leads`, `logestagios.lead_id→leads`) |
| `clientes_legado` | 1540 | CPF/nome/contrato |

### 7. Coleta de mercado (scraping — DOMÍNIO SEPARADO)
| tabela | linhas | papel |
|---|---|---|
| `imoveis` | **7.011.321** | scraping de portais |
| `imoveis_venda` 4738 / `imoveis_aluguel` 783 | | subtipo (**FK** `id→imoveis.id`) |
| `coleta_geral` 0 / `performe_imoveis` 1013 | | apoio à coleta |

---

## Relações

### FK reais existentes (16)
```
visitas.id_cliente_assinante -> clientes_visita.id_cliente
visitas.id_parceiro          -> parceiros_visita.id_parceiro
visita_cliente.id_visita     -> visitas.id_visita
visita_cliente.id_cliente    -> clientes_visita.id_cliente
visita_parceiro.id_visita    -> visitas.id_visita
visita_parceiro.id_parceiro  -> parceiros_visita.id_parceiro
avaliacoes_visita.(id_visita|id_cliente|id_parceiro) -> visitas|clientes_visita|parceiros_visita
imoveis_legado.tipo   -> tipos_imovel_legado.id_tipo
imoveis_legado.bairro -> bairros_legado.id_bairro
imoveis_venda.id      -> imoveis.id
imoveis_aluguel.id    -> imoveis.id
contatos.lead_id      -> leads.id
logestagios.lead_id   -> leads.id
```

### Relações implícitas (por valor, SEM FK — o que falta amarrar)
```
usuarios.team                         -> equipes.id_equipe
contratos.{*_nome}                    -> usuarios.nome        (só NOME, sem id)
vendas_legado.{vendedor/captador/...} -> usuarios.nome        (só NOME)
captacao.id_corretor / team           -> usuarios.id_usuarios / equipes.id_equipe
divisao_comissao.id_corretor          -> usuarios.id_usuarios
captacao_historico.captacao_id        -> captacao.id
eventos_imovel_legado.captador1/2/3   -> usuarios.id_usuarios
eventos_imovel_legado.id_gerente      -> equipes.id_equipe
fato_*.captador1/2/3 / id_gerente     -> usuarios.id_usuarios / equipes.id_equipe
imoveis_legado.codigo                 -> (codigo Imoview; usado por fato_*/eventos por valor)
metas_mensais_legado.id_gerente       -> equipes.id_equipe
```

---

## Redundâncias encontradas (o que você quer evitar)

1. **Vendas duplicadas** `contratos` × `vendas_legado`
   - `contratos`: 2024(281) 2025(228) 2026(152).
   - `vendas_legado`: 2015–2023 (746) **+** 2024(280) 2025(228) 2026(153).
   - 2024–2026 está **nas duas**; 477 linhas de `vendas_legado` batem em `contratos` via `idcontrato`.
   - O histórico 2015–2023 só existe em `vendas_legado` → por isso "contratos deveria ser de 2015".

2. **Nome de pessoa solto** em vez de `id_usuarios`
   - `contratos.diretor_nome`, `gerente_venda_nome`, `corretor_*_nome` etc. — nome já está em `usuarios`.
   - Match: dos 7 nomes distintos de `gerente_venda` em contratos, 6 casam em `usuarios` (1 é texto sujo/typo). Idem `vendas_legado`.

3. **id + nome + team juntos** (nome/team são deriváveis do id)
   - `captacao.nome_corretor`, `captacao.team`; `divisao_comissao.nome_corretor`.

4. **Falta de FK** em quase tudo que referencia `usuarios`/`equipes` → integridade não garantida, joins frágeis.

5. **Pares novo/legado coexistindo**
   - `leads` (0) × `leads_legado` (63k); `fato_*` (0) × `eventos_imovel_legado` (171k); `contratos` × `vendas_legado`.

6. **`diretores_legado` (1 linha)** — diretor já existe em `usuarios`.

7. **Dims pequenas** (`fontes_legado`, `atendimentos_legado`, `portais_legado`) — ok manter como dimensão, mas sem FK quem as usa.

---

## Plano de normalização (aditivo, sem perder dado)

> Princípio: **nunca dropar coluna/tabela antes de** (1) criar o destino, (2) backfill, (3) validar contagem, (4) manter `*_legado` como arquivo bruto. FKs criadas como `NOT VALID` e validadas depois.

**Etapa A — Identidade canônica**
- `usuarios.id_usuarios` → UNIQUE + index. (Resolver eventuais duplicados antes.)
- Tabela de-para `pessoa_alias(nome_origem → id_usuarios)` para casar nomes sujos/históricos uma vez.

**Etapa B — Vendas unificadas (resolve o "2015→hoje")**
- Criar **`vendas`** única cobrindo 2015→hoje (ou estender `contratos` para trás).
- Importar `vendas_legado` (2015–2023) + manter `contratos` (2024+); deduplicar por `idcontrato`.
- Para cada papel: adicionar `*_id_usuario` (FK) **ao lado** do `*_nome` (mantém o nome p/ linha histórica não-casável).
- `*_legado` permanece intocado como fonte bruta.

**Etapa C — Trocar nome por id (FK por valor)**
- Onde só há nome: adicionar coluna `*_id`, backfill via Etapa A, criar FK.
- Onde há id+nome+team (`captacao`, `divisao_comissao`): parar de gravar `nome`/`team`; expor via **view** que faz join com `usuarios`/`equipes`.

**Etapa D — Pessoas/dims redundantes**
- `diretores_legado` → mapear para `usuarios` e descontinuar.
- Amarrar `metas_mensais_legado.id_gerente`, `nichos_legado`, `eventos_imovel_legado`, `fato_*` a `usuarios`/`equipes` por FK.

**Etapa E — Isolar a coleta de mercado**
- `imoveis` (7M) + `imoveis_venda/aluguel` + `coleta_geral`/`performe_imoveis` são domínio de scraping. Manter separado do operacional (schema próprio/visões), não misturar com vendas/captação.

**Entregar primeiro VIEWS de leitura unificada** (vendas 2015→hoje com nomes resolvidos) antes de mexer na escrita — valida o de-para sem risco.

---

## Entregue — `vw_vendas` (Etapa B, passo 1: view read-only)
Arquivo: `back-end/sql/vw_vendas.sql`. **Não altera dados.** Une `contratos` (2024+) +
`vendas_legado` (<2024) = **1557 vendas contínuas 2015→2026**, sem double-count.

Descoberta importante: **`vendas_legado` guarda pessoa como `id_usuarios` (C61xxx); `contratos`
guarda NOME.** Por isso o resolver aceita os dois (id OU nome → `id_usuarios`).

Taxa de resolução pessoa→`id_usuarios` na view:
| papel | preenchido | resolvido |
|---|---|---|
| vendedor | 1287 | 84% |
| captador | 1306 | 85% |
| gerente venda | 1442 | 91% |
| gerente captação | 1433 | 89% |
| diretor | 452 | 100% |

Não resolvidos = primeiros-nomes soltos ("Lorrane", "Clara", "Eduardo") e placeholders
("Outro Z/M") → resolver com de-para curado (Etapa A) antes de persistir os `*_id`.

---

## Entregue — Etapa A: de-para `pessoa_alias` + relatórios
Migration `20260625_add_pessoa_alias` (aplicada). Tudo aditivo/reversível.

- **`pessoa_alias`** (`alias_key` único → `id_usuarios`, `origem`): de-para canônico.
  Semeado com 426 linhas (217 por id C61xxx + 209 por nome). `vw_vendas` agora resolve
  via essa tabela → adicionar alias `manual` melhora a view sem recriar nada:
  ```sql
  INSERT INTO pessoa_alias (alias_key, id_usuarios, origem)
  VALUES (lower(trim('Lorrane')), 'C61058', 'manual');
  ```
- **`vw_pessoa_nao_resolvida`** (`sql/vw_pessoa_nao_resolvida.sql`): 70 refs ainda sem id,
  com `ocorrencias` + `sugestao_id` + `qtd_candidatos`. Roteiro pra fechar o de-para.
  Casos: candidato único (auto-confiável), ambíguo (>1), e sem candidato
  (ex: "marcelo souza" 290 ocorr. — pessoa fora de `usuarios`).
- **`vw_usuarios_duplicados`** (`sql/vw_usuarios_duplicados.sql`): 9 `id_usuarios`
  repetidos (19 linhas). Maioria = mesma pessoa em 2 linhas (ativo true/false, reimport);
  2 colisões de código reais: `ADM002` (Tauane **e** Anna), `ADM001` (Mayron gerente/diretor).
- Index `ix_usuarios_id_usuarios` criado. **UNIQUE adiado** até resolver os duplicados acima
  (decisão sua — merge não apaga sozinho).

---

## Entregue — Passos 1, 2 e 3

### Passo 1 — dedup `usuarios` + UNIQUE
- `sql/dedup_usuarios.sql`: backup completo em **`usuarios_dup_backup`** (19 linhas) antes de tocar.
  Merge de 8 códigos (mesma pessoa, mantém ativo/mais recente) → 9 linhas apagadas (232→223).
  Colisão real **ADM002** (Tauane **e** Anna) virou SPLIT: Anna → **ADM004** (ninguém perdido).
- Migration `20260626_uq_id_usuarios` → depois `20260626_vendas` troca p/ índice único cheio
  **`uq_usuarios_id_usuarios`** (NULLs permitidos). 0 duplicados restantes.
- Reverter: restaurar de `usuarios_dup_backup`.

### Passo 2 — de-para auto
- +21 aliases `auto_sugestao` (refs com candidato único) em `pessoa_alias`.
- Resolução vendedor/captador subiu p/ **91%**. Restam **49 refs**:
  ambíguas (`eduardo` 4 cand, `paulo`/`luiz`...) e sem candidato em `usuarios`
  (destaque: **"marcelo souza" 290 ocorr.**, placeholders "outro z/m").
  Fechar manual via `INSERT INTO pessoa_alias ... origem='manual'` (ver `vw_pessoa_nao_resolvida`).

### Passo 3 — tabela canônica `vendas`
- Migration `20260626_vendas` + `popula_vendas.py` (re-executável: TRUNCATE+reload de `vw_vendas`).
- **1557 vendas 2015→2026** (896 legado + 661 contrato), `*_id` com **FK → usuarios.id_usuarios**
  (0 órfãos), `*_nome` preservado, `valor_*` parseado (BR-aware). Fontes brutas intactas.

### Próximos (pendências suas)
1. Refs não resolvidas: preencher `pessoa_alias` manual (ou cadastrar "marcelo souza" em `usuarios`).
2. Apontar leitores (`ranking_service`/`meta_service`/AdminBases Venda) para `vendas` e parar de
   escrever em `contratos`/`vendas_legado` (viram só arquivo bruto). `vendas` passa a ser a fonte.
3. Repetir o padrão (id+FK) em `captacao`, `divisao_comissao`, `eventos_imovel_legado`, `fato_*`.
