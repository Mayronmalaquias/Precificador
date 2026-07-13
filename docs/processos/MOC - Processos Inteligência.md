---
tags: [moc, processo/inteligencia]
tipo: MOC (Map of Content)
---

# MOC — Processos do Setor de Inteligência (61 Imóveis)

Índice-mestre do "Segundo Cérebro". Cada processo é uma nota própria no template
**Objetivo · Regras de Negócio · Fluxo · Troubleshooting**.

**Legenda status:** ✅ documentado e validado · 🟨 rascunho auto (inferido do código, **a validar**) · ⬜ pendente
**Origem:** 🤖 deduzível do código · 🙋 precisa de entrevista

## Nível 1 — Baixa complexidade
| # | Processo | Status | Nota |
|---|---|---|---|
| 1.1 | Coleta de Leads / Captura no Site | ✅ | [[1.1 - Coleta de Leads]] |
| 1.2 | Importação de Planilhas de Base (BI) | ✅ | [[1.2 - Importação de planilhas de base]] |
| 1.3 | Cadastro / Manutenção de Usuários (RH) | ✅ | [[1.3 - Cadastro de Usuários]] |
| 1.4 | Relatório de Visita (PDF) | 🟨 🤖 | [[1.4 - Relatório de Visita]] |
| 1.5 | Backup antes de operação em massa | ⬜ 🙋 | — |
| 1.6 | Divisão de Comissão (manual) | 🟨 🤖 | [[1.6 - Divisão de Comissão]] |

## Nível 2 — Média complexidade
| # | Processo | Status | Nota |
|---|---|---|---|
| 2.1 | Relatórios de BI / Dashboards do Gerente | 🟨 🤖 | [[2.1 - Dashboards do Gerente]] |
| 2.2 | Rankings (VGV/VGC/Captação/Visitas) | 🟨 🤖 | [[2.2 - Rankings]] |
| 2.3 | Jornada de Captação | 🟨 🤖 | [[2.3 - Jornada de Captação]] |
| 2.4 | Snapshot Diário / Evolução | 🟨 🤖 | [[2.4 - Snapshot e Evolução de Captação]] |
| 2.5 | Gestão de Clientes / CRM operacional | ⬜ 🙋 | — |
| 2.6 | Sincronização com planilhas Google | 🟨 🤖 | [[2.6 - Sincronização com Planilhas]] |
| 2.7 | Metas (gerente/equipe) | ⬜ 🙋 | — |
| 2.8 | Assistente IA (Renata) | 🟨 🤖 | [[2.8 - Assistente IA]] |
| 2.9 | Gestão de segredos / credenciais | ⬜ 🙋 | — |

## Nível 3 — Alta complexidade
| # | Processo | Status | Nota |
|---|---|---|---|
| 3.1 | Precificação por mercado (KMeans) | 🟨 🤖 | [[3.1 - Precificação por Mercado]] |
| 3.2 | Coleta de mercado (scraping) | ⬜ 🙋 | — |
| 3.3 | Auditoria / qualidade de dados | 🟨 🤖 | [[3.3 - Auditoria e Qualidade de Dados]] |
| 3.4 | Modelagem / normalização de banco | 🟨 🤖 | [[3.4 - Modelagem e Normalização]] |
| 3.5 | ETL / unificação de vendas | 🟨 🤖 | [[3.5 - ETL de Vendas]] |
| 3.6 | Integração de site / web | 🟨 🤖 | [[3.6 - Integração de Site e Web]] |
| 3.7 | Governança de acesso / permissionamento | 🟨 🤖 | [[3.7 - Permissionamento]] |
| 3.8 | Deploy / operação em produção | ⬜ 🙋 | — |
| 3.9 | Migração / reatribuição de dados em massa | ⬜ 🙋 | — |

## Nível 4 — Estratégico / a confirmar
Monitoramento · Data lineage · LGPD/retenção · Modelos preditivos · Atribuição de mídia paga ·
Runbook/DR · Onboarding técnico. (todos 🙋, a validar existência)

---

## Fila de trabalho
- **🤖 Auto: CONCLUÍDO** ✅ (1.4, 1.6, 2.1, 2.2, 2.3, 2.4, 2.6, 2.8, 3.1, 3.3–3.7). Todos 🟨 = **a validar** com o time.
- **🙋 Entrevista (preciso de você):** 1.5 backup · 2.5 gestão clientes · 2.7 metas · 2.9 segredos · 3.2 scraping · 3.8 deploy · 3.9 reatribuição · Nível 4. Ver "Perguntas em aberto" no fim de cada nota 🟨.

## Convenções
- Um processo = uma nota. Frontmatter com `tags`, `complexidade`, `dono`, `frequencia`, `sistemas`, `status_evolucao`.
- **as-is** (como funciona hoje) vs **to-be** (evolução planejada) sinalizados no corpo.
- Banco: [[MAPA_BANCO]] · [[DIAGRAMA_BANCO]]. Código: `back-end/` e `front-end/` (ver READMEs).
