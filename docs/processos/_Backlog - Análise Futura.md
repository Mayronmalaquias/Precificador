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
- [x] 🔴 ~~**API sem autenticação** — qualquer chamada é aceita (mobile inclusive). Chave "planejada".~~
  **Resolvido:** `auth_middleware.register_auth_middleware` põe um `before_request` global que exige
  **X-API-KEY** ou **Bearer JWT**. Públicos só `/`, `/swagger.json`, `/favicon.ico`, `/docs*`,
  `/swaggerui*`. Kill-switch `AUTH_ENABLED` (default **true**). ([[2.9 - Gestão de Segredos]])
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
- [x] ~~**1.3 / 1.2:** preencher `id_imoview` no cadastro → sincroniza corretor com o CRM e mata o de-para manual.~~
  **Feito (2026-08-06):** campo "Código Imoview" no cadastro e na edição (Register · ControleCorretor ·
  RHUsuarios), único (409 se repetido). ([[1.3 - Cadastro de Usuários]])
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

## 6c. Achados da sessão de 2026-08-06 (cadastro · lançamento · captação)
Levantados enquanto se mexia em [[1.3 - Cadastro de Usuários]], [[1.9 - Lançamento de Imóvel pelos Assistentes]]
e [[2.2 - Rankings]]. **São dados sujos e riscos operacionais, não código a escrever.**

### Limpeza de dado — `usuarios`
- [ ] 🔴 **`id_imoview` duplicado em 6 códigos.** O seletor do Lançar Imóvel usa o código como
  `value` da option: com dois usuários no mesmo código, clicar em um seleciona o outro (o
  `<select>` casa a **primeira** option com aquele valor, e a lista é ordenada por nome).
  Só `5` e `236` afetam a tela hoje. A trava de unicidade impede **novos** duplicados; esses 6
  vieram da migração do legado. Ação: limpar o `id_imoview` do C61053 e fundir a Raquel.

| código | registros | situação |
|---|---|---|
| `5` | Paolla Gardenia (G61016, ativo) · José Marques (C61053, ativo) | **pessoas diferentes** — a aba "Corretores" diz que 5 é da Paolla; o José é `diretor` e não devia ter código |
| `236` | Raquel Silva (`238`) · Raquel Silva (C61082) | mesma pessoa, 2 cadastros — aparece 2× na lista. O `id_usuarios` de um é literalmente `"238"`, fora do padrão `C61xxx` |
| `19` | Daniela - Atendimento · Sueli | pessoas diferentes, ambas inativas |
| `30`, `49`, `52` | mesma pessoa duplicada | só um ativo em cada |

- [ ] 🟠 **21 usuários em equipe `ativo=False`** (G61013 com 16, G61004, G61012, G61011 — 4 delas
  sem `nome`). `equipesOpcoes` filtra por ativo, então a edição desses usuários abre o select sem
  opção correspondente e **salvar zera a equipe**.
- [ ] 🟠 **12 usuários com `team` que não existe em `equipes`:** `inteligencia`(4), `Aguia`(2),
  `ADMINISTRADOR`, `agef`, `Inteligencia`, `C61124`, `administrador`, `SENNA` — variações de caixa
  e nome por extenso em vez de `G61xxx`. Candidato a script de normalização
  (`Aguia`→G61002, `SENNA`→G61015, `agef`→G61001).

### Imoview
- [ ] 🔴 **Imóveis de teste 12367 e 12377 a apagar à mão** no CRM — a API **não tem delete**.
  O 12377 foi o que revelou o contrato de escrita ([[1.9 - Lançamento de Imóvel pelos Assistentes]]).
- [ ] 🟠 **`GET /assistente/imoview/listas` sem cache nem retry.** São 5 chamadas em sequência,
  `timeout=30` cada. Em 05/08/2026 15:10 a 5ª (`RetornarListaLocalChaves`) estourou → 502 → o
  assistente abriu o formulário com os dropdowns vazios. São tabelas de lookup que quase nunca
  mudam: cache com TTL de horas + 1 retry resolve, e ainda tira 5 round-trips da abertura da tela.
- [ ] 🟠 **Aba "Corretores" da planilha não recebe write-back.** Corretor cadastrado no sistema mas
  ausente da aba entra no estoque com o nome do banco (a tela avisa). Hoje se adiciona na mão.

### Captação
- [ ] 🟠 **155 captações importadas ficaram com o nome cru** (não resolveram p/ `id_usuarios`):
  "Renata"(70), "Paulo"(24), "Jhone Motta"(22), "Marcelo"(9)… Contam no ranking exibidas por nome,
  mas não agrupam por equipe nem respeitam exclusão por id. Resolver caso a caso ou aceitar.
- [ ] 🟠 **`fato_captacao` tem duas fontes correntes** — `origem='upload'` (Gestão de Bases) e
  `origem='lancamento'` (Lançar Imóvel). Se o mesmo imóvel entrar pelos dois, o upsert por
  `codigo_imovel` faz o último sobrescrever. Confirmar que é o comportamento desejado.

## 7. Nível 4 (a confirmar se existe)
- [ ] Monitoramento/observabilidade · Data lineage · LGPD/retenção · Modelos preditivos ·
  Atribuição de mídia paga · Runbook/DR · Onboarding técnico.

## Links
[[MOC - Processos Inteligência]]

## 6c. Achados de 17/08/2026 (ver [[_Registro - 2026-08-17]])

### Integridade de usuário
- [ ] 🔴 **Sem UNIQUE em `usuarios.username` e em `id_imoview`.** A base foi limpa
  ([[_Operação - Deduplicação de Usuários 2026-08]]) e a validação em `cadastrar_usuario` cobre
  a aplicação — mas só o índice protege de corrida e de escrita direta. Os dois índices agora
  passam; SQL pronto no registro §7.1.
- [ ] 🟠 **Edição de usuário pode não validar username.** A checagem foi posta só no cadastro;
  `/corretor/editar-usuario` não foi verificado.
- [ ] 🟠 **Raquel Silva pode precisar redefinir senha** — tinha duas contas ativas e ficou a de
  `C61082`.

### `estudo_metricas`
- [ ] 🟠 **Tabela heterogênea:** só o LAGO NORTE foi regravado. Convivem dois esquemas de
  `metragem_fx` (`>1000` × as 4 faixas novas) e, nos meses antigos do LN, a nomenclatura
  anterior (`SUPER LUXO`, `01 - Original`). Some quando rodar o lote completo — que também
  aplica o corte por série a todos (**+46%** de volume na Asa Sul).
- [ ] 🟠 **Instabilidade de cluster isolada, não resolvida.** k=3 + `valor_m2` ficou só no LN;
  a **Asa Sul segue com 6,4%** de imóveis trocando de rótulo a cada rodada.
- [ ] 🟠 **`SHIS QL 12` fora de todas as faixas** do Lago Sul (`QL Meio` = `{8,10,14,16}` pula o
  12) → ~149 anúncios saem do `QUADRA_VAGA`. Decisão do especialista do bairro.
- [ ] 🟡 Congelar os clusters como **faixas fixas de R$/m²**? Com uma feature só, os rótulos já
  são faixas contíguas e auditáveis — validando com o especialista, dá para aposentar o KMeans.

### Integração Imoview
- [ ] 🟠 **Não há sincronização de corretores.** `/Usuario/RetornarTipo3` traz **clientes**
  (60.972), não usuários, e o `codigo` dele **não é** o `id_imoview` — sincronizar por ali
  atribuiria imóvel ao corretor errado. O caminho é `/Usuario/App_RetornarUsuarios`, que exige
  `codigoacesso` de `App_ValidarAcesso` (e-mail + senha MD5). `.env` já tem
  `IMOVIEW_CODIGOACESSO` comentado. Swagger: `https://api.imoview.com.br/Scripts/swagger.json`.
- [ ] 🟡 `id_imoview` vem hoje da aba "Corretores" de uma planilha, casado **por nome**
  (`seed_id_imoview.py`) — é a origem provável dos 5 códigos duplicados.
