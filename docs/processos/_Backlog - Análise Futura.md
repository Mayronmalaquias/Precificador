---
tags: [processo/inteligencia, backlog, status/a-analisar]
tipo: backlog / parking lot
proposito: itens levantados na documentação, PARA ANÁLISE FUTURA (nada decidido/comprometido)
---

# _Backlog — Análise Futura

> **Natureza deste doc:** são **observações e candidatos** surgidos durante a documentação dos
> processos. **Nada aqui está decidido nem em execução.** Serve para você, no futuro, avaliar a
> **necessidade** de cada item e promover (ou descartar). Marque `[x]` o que virar decisão.

---

## 1. Processo candidato (não existe no catálogo ainda)
- [ ] **2.10 — Controle de Qualidade documental de imóveis**
  Rotinas legadas `verificarDocumentacoes` · `finalizarImoveis` · `verificarDocumentacoesEEnviarEmail`
  (movem imóvel de `Em Andamento`→`Finalizados`, checam documentação, mandam e-mail de pendências).
  **Hoje em 100% de erro** (crítico). Precisa: os `.gs` completos + entrevista. Fonte:
  [[Acionadores e Processos — Base Inteligente]].

## 2. Reconciliações (notas que podem estar incompletas)
- [ ] **1.1 Coleta de Leads — existem 2 fluxos.** O 1.1 cobre C2S→e-mail e diz "sem dedup".
  A camada Apps Script ([[Acionadores e Processos — Base Inteligente]]) tem outro fluxo:
  `importarLeadsParaPlanilha` (05:00, ignora locação, `Recepção_Temp`) → **dedup**
  `cliente|telefone|código|portal` → `Fato_Lead` → **distribuição D+** (Repick→D+2…D+14).
  Avaliar: são o mesmo lead por caminhos diferentes? Há **e-mail de leads redundante**?

## 3. Achados críticos (risco — priorizar análise)
- [ ] 🔴 **API sem autenticação** — qualquer chamada é aceita (mobile inclusive). Chave "planejada". ([[2.9 - Gestão de Segredos]])
- [ ] 🔴 **Scraper + geração de `estudo_metricas` só na máquina local**, manual, sem versionamento aparente. `estudo_metricas` = full replace mensal (sem histórico/rollback). ([[3.2 - Coleta de Mercado (Scraping)]])
- [ ] 🔴 **Restore nunca testado**; recuperação de erro lógico = backup semanal (~7 dias de perda); Multi-AZ não cobre erro lógico; PITR ativado mas fora do hábito. ([[1.5 - Backup e Recuperação]])
- [ ] 🟠 **Reatribuição de carteira** 100% manual, sem script, sem auditoria. ([[3.9 - Reatribuição de Carteira]])
- [ ] 🟠 **Metas no localStorage** — voláteis, sem histórico, sem fonte única. ([[2.7 - Metas]])
- [ ] 🟠 **Deploy** na branch única `dev_miron`, sem monitoramento/healthcheck, rollback nunca testado, migrations manuais do local. ([[3.8 - Deploy e Produção]])

## 4. Instabilidades da camada legada (Apps Script — taxas de erro reais)
Fonte: [[Acionadores e Processos — Base Inteligente]] (painel 13–14/07/2026).
- [ ] `verificarDocumentacoes*` / `finalizarImoveis` — **100%** (4 acionadores) → ver item 2.10.
- [ ] `verifyAndSyncFatoVendaFromVendas` — **35,71%** (sync Fato_Venda). Liga a [[3.5 - ETL de Vendas]].
- [ ] `transferData` (Controle de Contratos 2024) — **18,52%**. Liga a [[3.5 - ETL de Vendas]] / [[1.6 - Divisão de Comissão]].
- [ ] Acionadores redundantes/obsoletos: `enviarEmailLeads` separado; `ValoresRecebidos_Contratos61_Obsoleto` ativo.

## 5. Melhorias por processo (das notas 🟨 e 🙋 — "Perguntas em aberto")
Cada nota tem seu bloco próprio; resumo dos itens de maior valor:
- [ ] **1.3 / 1.2:** preencher `id_imoview` no cadastro → sincroniza corretor com o CRM e mata o de-para manual.
- [ ] **2.9:** autenticar a API · backup redundante de segredos · rotação de chaves · avaliar Secrets Manager.
- [ ] **3.2 / 1.5:** versionar/automatizar o scraper · snapshot antes de op destrutiva · testar restore.
- [ ] **3.9:** criar ferramenta de reatribuição (transacional + backup + auditoria + checklist de domínios).
- [ ] **2.7:** persistir metas no banco (`metas_mensais_legado`) · reativar PDF.
- [ ] **2.5:** incluir leads diretos · alerta de inatividade · dedup de cliente.
- [ ] **3.8:** monitoramento/healthcheck (o back tem `/health`) · branch de release/CI · testar rollback+downgrade.
- [ ] **1.6:** confirmar destino (planilha `Divisao_Comissao` vs tabela `divisao_comissao`) · validar soma 100%.
- [ ] **2.8:** persistir histórico do chat? · rate limit na página pública · renomear ids CSS `sofiaGrad`→`renataGrad`.

## 6. Validação pendente das notas 🟨 (auto, inferidas do código)
Revisar com o time e promover 🟨→✅:
- [ ] 1.4 · 1.6 · 2.1 · 2.2 · 2.3 · 2.4 · 2.6 · 2.8 · 3.1 · 3.3 · 3.4 · 3.5 · 3.6 · 3.7

## 7. Nível 4 (a confirmar se existe)
- [ ] Monitoramento/observabilidade · Data lineage · LGPD/retenção · Modelos preditivos ·
  Atribuição de mídia paga · Runbook/DR · Onboarding técnico.

## Links
[[MOC - Processos Inteligência]]
