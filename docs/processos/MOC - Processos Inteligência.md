---
tags: [moc, processo/inteligencia]
tipo: MOC (Map of Content)
---

# MOC — Processos do Setor de Inteligência (61 Imóveis)

Índice-mestre do "Segundo Cérebro". Cada processo é uma nota própria no template
**Objetivo · Regras de Negócio · Fluxo · Troubleshooting**.

**Legenda status:** ✅ documentado e validado · 🟨 rascunho auto (inferido do código, **a validar**) · ⬜ pendente
**Origem:** 🤖 deduzível do código · 🙋 precisa de entrevista
**Repositório:** 📦 = processo implementado no repo **`Estudos`** (scripts da máquina local da Inteligência)

## Nível 1 — Baixa complexidade
| # | Processo | Status | Nota |
|---|---|---|---|
| 1.1 | Coleta de Leads / Captura no Site | ✅ | [[1.1 - Coleta de Leads]] |
| 1.2 | Importação de Planilhas de Base (BI) | ✅ | [[1.2 - Importação de planilhas de base]] |
| 1.3 | Cadastro / Manutenção de Usuários (RH) | ✅ | [[1.3 - Cadastro de Usuários]] |
| 1.4 | Relatório de Visita (PDF) | 🟨 🤖 | [[1.4 - Relatório de Visita]] |
| 1.5 | Backup e Recuperação | ✅ 🙋 | [[1.5 - Backup e Recuperação]] |
| 1.6 | Divisão de Comissão (manual) | 🟨 🤖 | [[1.6 - Divisão de Comissão]] |
| 1.7 | Preparação de Estoque (Imoview → `Fato_Estoque`) | 🟨 🤖 📦 | [[1.7 - Preparação de Estoque (Imoview)]] |
| 1.8 | Cadastro em massa de usuários (corretores) | 🟨 🤖 📦 | [[1.8 - Cadastro em Massa de Usuários]] |

## Nível 2 — Média complexidade
| # | Processo | Status | Nota |
|---|---|---|---|
| 2.1 | Relatórios de BI / Dashboards do Gerente | 🟨 🤖 | [[2.1 - Dashboards do Gerente]] |
| 2.2 | Rankings (VGV/VGC/Captação/Visitas) | 🟨 🤖 | [[2.2 - Rankings]] |
| 2.3 | Jornada de Captação | 🟨 🤖 | [[2.3 - Jornada de Captação]] |
| 2.4 | Snapshot Diário / Evolução | 🟨 🤖 | [[2.4 - Snapshot e Evolução de Captação]] |
| 2.5 | Gestão de Clientes / CRM operacional | ✅ 🙋 | [[2.5 - Gestão de Clientes]] |
| 2.6 | Sincronização com planilhas Google | 🟨 🤖 | [[2.6 - Sincronização com Planilhas]] |
| 2.7 | Metas (gerente/equipe) | ✅ 🙋 | [[2.7 - Metas]] |
| 2.8 | Assistente IA (Renata) | 🟨 🤖 | [[2.8 - Assistente IA]] |
| 2.9 | Gestão de segredos / credenciais | ✅ 🙋 | [[2.9 - Gestão de Segredos]] |
| 2.10 | _(reservado — Controle de Qualidade documental, ver backlog)_ | ⬜ | [[_Backlog - Análise Futura]] |
| 2.11 | Registro de Captação e Saída de imóveis | 🟨 🤖 📦 | [[2.11 - Registro de Captação e Saída]] |
| 2.12 | Rankings e Premiação (VGV/VGC) | 🟨 🤖 📦 | [[2.12 - Rankings e Premiação]] |
| 2.13 | Relatório de Metas dos Gerentes | 🟨 🤖 📦 | [[2.13 - Relatório de Metas dos Gerentes]] |

## Nível 3 — Alta complexidade
| # | Processo | Status | Nota |
|---|---|---|---|
| 3.1 | Precificação por mercado (KMeans) | 🟨 🤖 | [[3.1 - Precificação por Mercado]] |
| 3.2 | Coleta de mercado (scraping) | ✅ 🙋 | [[3.2 - Coleta de Mercado (Scraping)]] |
| 3.3 | Auditoria / qualidade de dados | 🟨 🤖 | [[3.3 - Auditoria e Qualidade de Dados]] |
| 3.4 | Modelagem / normalização de banco | 🟨 🤖 | [[3.4 - Modelagem e Normalização]] |
| 3.5 | ETL / unificação de vendas | 🟨 🤖 | [[3.5 - ETL de Vendas]] |
| 3.6 | Integração de site / web | 🟨 🤖 | [[3.6 - Integração de Site e Web]] |
| 3.7 | Governança de acesso / permissionamento | 🟨 🤖 | [[3.7 - Permissionamento]] |
| 3.8 | Deploy / operação em produção | ✅ 🙋 | [[3.8 - Deploy e Produção]] |
| 3.9 | Migração / reatribuição de dados em massa | ✅ 🙋 | [[3.9 - Reatribuição de Carteira]] |
| 3.10 | Scraper DFImóveis (execução) | 🟨 🤖 📦 | [[3.10 - Scraper DFImóveis (execução)]] |
| 3.11 | Carga da base `imoveis` (CSV → Postgres) | 🟨 🤖 📦 | [[3.11 - Carga da Base imoveis]] |
| 3.12 | Geração de `analytics.estudo_metricas` | 🟨 🤖 📦 | [[3.12 - Geração de estudo_metricas]] |
| 3.13 | Estudos individuais por bairro (→ Sheets) | 🟨 🤖 📦 | [[3.13 - Estudos Individuais por Bairro]] |
| 3.14 | Análises exploratórias e auditoria de coleta | 🟨 🤖 📦 | [[3.14 - Análises Exploratórias e Auditoria de Coleta]] |

## Nível 4 — Estratégico / a confirmar
Monitoramento · Data lineage · LGPD/retenção · Modelos preditivos · Atribuição de mídia paga ·
Runbook/DR · Onboarding técnico. (todos 🙋, a validar existência)

---

## Referências (legado — Google Apps Script)
Documentação dos **acionadores/triggers das planilhas legadas** (camada de automação que **ainda
roda** em paralelo ao sistema novo). Não são processos do catálogo, mas o **as-is real** de várias
rotinas. Data de referência: 13–14/07/2026.

| Doc | Cobre | Relaciona-se com |
|---|---|---|
| [[Acionadores e Processos — Base Inteligente]] | Inventário completo dos acionadores (leads 05:00, sync Fato_Venda, controle de qualidade, ETL Acelera, D+ distribution) + taxas de erro + prioridades | 1.1, 1.2, 2.6, 3.5, novo (qualidade) |
| [[Documentacao_Base_Inteligencia_61]] | Base Inteligência 61 — `showMainMenu`, `verifyAndSyncFatoVendaFromVendas` | [[2.6 - Sincronização com Planilhas]] · [[3.5 - ETL de Vendas]] |
| [[Documentacao_Controle_de_Contratos_61_Imoveis]] | Ecossistema contratual (`transferData`, `showForm` recebidos, sync) | [[3.5 - ETL de Vendas]] · [[1.6 - Divisão de Comissão]] |
| [[Documentacao_Modelo_Visitas]] | Base de visitas (Sheets + Drive) | [[1.4 - Relatório de Visita]] |

### Descobertas dos docs de referência ⚠️
- 🆕 **Processo ausente no catálogo:** **Controle de Qualidade documental** de imóveis
  (`verificarDocumentacoes`/`finalizarImoveis`/`verificarDocumentacoesEEnviarEmail`) — hoje em
  **100% de erro** (crítico). Candidato a virar processo próprio (ex.: `2.10`).
- **Leads têm camada Apps Script adicional** ao [[1.1 - Coleta de Leads]]: `importarLeadsParaPlanilha`
  (05:00, ignora equipe de locação, `Recepção_Temp`), **dedup** por `cliente|telefone|código|portal`
  em `transferirDadosDaRecepcaoParaFatoLead`, e **distribuição D+** (Repick→D+2…D+14) para nutrição.
  → Reconciliar com o 1.1 (que cobre o fluxo C2S→e-mail). Possível **e-mail de leads redundante**.
- **Sync de vendas instável:** `verifyAndSyncFatoVendaFromVendas` **35,71%** e `transferData`
  **18,52%** de erro → risco no [[3.5 - ETL de Vendas]]/[[2.6 - Sincronização com Planilhas]].

---

## Repositório `Estudos` — scripts da máquina local 📦
Repo separado (`61E/Estudos`, Python), com as rotinas que a Inteligência roda **manualmente na
máquina local**. É a **origem real** de várias coisas que outras notas descreviam como "fora do repo".

| Processo | Código | Preenche a lacuna de |
|---|---|---|
| [[3.10 - Scraper DFImóveis (execução)]] | `dfimoveis_scraper/` | [[3.2 - Coleta de Mercado (Scraping)]] ("scraper fora do repo") |
| [[3.11 - Carga da Base imoveis]] | `BD/enviar_BD.py` | elo CSV → banco, antes ausente |
| [[3.12 - Geração de estudo_metricas]] | `analise/acionador/` | pergunta nº 1 de [[3.1 - Precificação por Mercado]] |
| [[3.13 - Estudos Individuais por Bairro]] | `Estudos_Individuais/` | estudos publicados em planilha |
| [[3.14 - Análises Exploratórias e Auditoria de Coleta]] | `analise/`, `DF-Anunciantes/` | ferramental de [[3.3 - Auditoria e Qualidade de Dados]] |
| [[2.11 - Registro de Captação e Saída]] | `Estoque/registrar*.py` | alimentação de [[2.3 - Jornada de Captação]] |
| [[2.12 - Rankings e Premiação]] | `Premiacao/` | cálculo real de [[2.2 - Rankings]] / [[1.6 - Divisão de Comissão]] |
| [[2.13 - Relatório de Metas dos Gerentes]] | `Premiacao/relatorio_metas_*.py` | relatório impresso de [[2.7 - Metas]] |
| [[1.7 - Preparação de Estoque (Imoview)]] | `Estoque/tratamento_estoque.py` | insumo do Apps Script de estoque |
| [[1.8 - Cadastro em Massa de Usuários]] | `Script/cadastrar_usuarios_corretores.py` | carga em lote de [[1.3 - Cadastro de Usuários]] |

### Descobertas do repo `Estudos` ⚠️
- ✅ **O scraper ESTÁ versionado** (`dfimoveis_scraper/`) — corrige a premissa de
  [[3.2 - Coleta de Mercado (Scraping)]]. O que segue sem automação é a **execução**.
- 🔴 **Credenciais hardcoded** como fallback de `os.getenv`: senha do RDS em `BD/enviar_BD.py` e
  `analise/acionador/acionador.py`; chave da API Imoview em `Estoque/testeDIsponiveis.py`;
  senha padrão `12345678` no cadastro em massa. → [[2.9 - Gestão de Segredos]].
- 🔴 **Lógica duplicada em produção:** `estudo_metricas` é gerada por **3 arquivos diferentes**
  com cortes de amostra e colunas divergentes; a premiação tem **4 versões** apontando para
  **planilhas diferentes**; os estudos por bairro são **~25 cópias** do mesmo código.
- 🟠 **`QUADRA_VAGA`** é gravado em `estudo_metricas` mas **não aparece na cascata do serving**
  descrita em [[3.1 - Precificação por Mercado]].
- 🟠 **Duas fontes de verdade** para "média do bairro": `estudo_metricas` (banco/site) e a planilha
  dos estudos individuais — com **faixas e regras de cluster diferentes**.
- 🟠 **Carga da `imoveis` sem idempotência** (append puro, sem chave natural) → recarga duplica.

---

## Fila de trabalho
- **🤖 Auto: CONCLUÍDO** ✅ (1.4, 1.6, 2.1, 2.2, 2.3, 2.4, 2.6, 2.8, 3.1, 3.3–3.7). Todos 🟨 = **a validar** com o time.
- **🤖 Auto (repo `Estudos`): CONCLUÍDO** ✅ (1.7, 1.8, 2.11–2.13, 3.10–3.14). Todos 🟨 = **a validar**.
- **🙋 Entrevista: CONCLUÍDA** ✅ (1.1, 1.2, 1.3, 1.5, 2.5, 2.7, 2.9, 3.2, 3.8, 3.9).
- **Pendente:** **Nível 4** (confirmar existência) + validar as notas 🟨 (auto) com o time +
  **reconciliar 3.1/3.2 com 3.10–3.12** (agora que o código foi localizado).

## Backlog / análise futura
Itens levantados na documentação (achados, candidatos, riscos, reconciliações) — **nada decidido**,
para avaliar necessidade depois: [[_Backlog - Análise Futura]].

## Convenções
- Um processo = uma nota. Frontmatter com `tags`, `complexidade`, `dono`, `frequencia`, `sistemas`, `status_evolucao`.
- **as-is** (como funciona hoje) vs **to-be** (evolução planejada) sinalizados no corpo.
- Banco: [[MAPA_BANCO]] · [[DIAGRAMA_BANCO]]. Código: `back-end/` e `front-end/` (ver READMEs).
