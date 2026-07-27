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
- [x] 🔴 ~~**Scraper + geração de `estudo_metricas` só na máquina local**, manual, sem versionamento aparente.~~
  **Atualizado:** o código **está versionado** no repo `Estudos` ([[3.10 - Scraper DFImóveis (execução)]] ·
  [[3.12 - Geração de estudo_metricas]]). **Permanece** o ponto único de **execução** (manual, sem
  agendador) e a substituição destrutiva de `estudo_metricas` (delete+insert por escopo, sem
  histórico/rollback). ([[3.2 - Coleta de Mercado (Scraping)]])
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
- [ ] **Repo `Estudos`:** 1.7 · 1.8 · 2.11 · 2.12 · 2.13 · 3.10 · 3.11 · 3.12 · 3.13 · 3.14

## 6b. Achados do repo `Estudos` 📦 (novos — priorizar análise)

### Segredos
- [ ] 🔴 **Senha do RDS hardcoded** como fallback de `os.getenv` em `BD/enviar_BD.py` e
  `analise/acionador/acionador.py` (arquivos versionados). Mover para `.env`/Secrets Manager e
  **remover o fallback**. ([[3.11 - Carga da Base imoveis]] · [[3.12 - Geração de estudo_metricas]] · [[2.9 - Gestão de Segredos]])
- [ ] 🔴 **Chave da API Imoview hardcoded** em `Estoque/testeDIsponiveis.py`. ([[1.7 - Preparação de Estoque (Imoview)]])
- [ ] 🔴 **Senha padrão `12345678`** para todos os usuários criados em lote, sem troca obrigatória
  no 1º acesso — combinado com a **API sem autenticação** (item 3). ([[1.8 - Cadastro em Massa de Usuários]])

### Duplicação / fonte da verdade
- [ ] 🔴 **`estudo_metricas` gerada por 3 arquivos** (`acionador.py`, `enviar_banco.py`,
  `analise_estudo_bd.py`) com **corte de amostra diferente** (5 vs 3) e `variacao_m2_pct` só em um.
  Definir o oficial e arquivar o resto. ([[3.12 - Geração de estudo_metricas]])
- [ ] 🔴 **Premiação em 4 versões** (`Premiacao.py`, `PremIndividual.py`, `PremGerent.py`,
  `PremPDF.py`) apontando para **planilhas de contratos diferentes** e com regra de time
  divergente. ([[2.12 - Rankings e Premiação]])
- [ ] 🔴 **~25 cópias** do estudo por bairro em `Estudos_Individuais/`, várias com variante `_novo`.
  Consolidar em um script parametrizado. ([[3.13 - Estudos Individuais por Bairro]])
- [ ] 🟠 **Duas médias de bairro** convivendo (banco vs planilha de estudos) com **faixas de
  metragem e regra de cluster diferentes**. Decidir a fonte da verdade.

### Pipeline de dados
- [ ] 🟠 **Carga da `imoveis` sem idempotência** — append puro, sem chave natural
  (`codigo, data_coleta, portal`). Recarga duplica. ([[3.11 - Carga da Base imoveis]])
- [ ] 🟠 **Descasamento de nomes de coluna** entre o CSV do scraper (`tipo`/`tipo_imovel`/`data`) e o
  que a carga espera (`oferta`/`tipo`/`horario`). Confirmar se falta um passo intermediário.
- [ ] 🟠 **`QUADRA_VAGA`** é gerado mas não é consumido pela cascata do serving descrita em
  [[3.1 - Precificação por Mercado]]. Usar ou parar de gerar.
- [ ] 🟠 **`precomputed_analise.json`** (citado em 3.1) **não está** no repo `Estudos` — origem ainda desconhecida.
- [ ] 🟠 `analise/analise_estudo_bd.py` **grava em produção** apesar de estar na pasta de análise —
  fácil de executar por engano.

### Operação
- [ ] 🟠 **Tudo manual, sem agendador e sem alerta:** scraping, carga, geração mensal, captação/saída,
  premiação. Semana sem coleta ou mês sem regeneração passa despercebido.
- [ ] 🟠 **Relatório de metas exige digitar as metas no terminal** a cada execução (não dá para
  agendar, sem histórico). Liga a [[2.7 - Metas]]. ([[2.13 - Relatório de Metas dos Gerentes]])
- [ ] 🟠 **Reescrita total de aba** em `Dim_Imovel`/`Fato_Captacao` — edição manual entre execuções
  é perdida. ([[2.11 - Registro de Captação e Saída]])

## 7. Nível 4 (a confirmar se existe)
- [ ] Monitoramento/observabilidade · Data lineage · LGPD/retenção · Modelos preditivos ·
  Atribuição de mídia paga · Runbook/DR · Onboarding técnico.

## Links
[[MOC - Processos Inteligência]]
