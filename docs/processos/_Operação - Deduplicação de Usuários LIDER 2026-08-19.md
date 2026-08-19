---
tags: [operacao, processo/inteligencia, dominio/usuarios, dominio/qualidade]
tipo: Registro de operação (migração de dados)
data: 2026-08-19
status: aplicado em produção · reversível pelos backups
---

# Operação — Deduplicação de Usuários LIDER (19/08/2026)

Segunda rodada de limpeza de identidade, agora nas contas do time **LIDER (G61016)**.
Três pessoas tinham duas contas cada. **1.985 referências remapeadas, 3 contas apagadas.**

Complementa a [[_Operação - Deduplicação de Usuários 2026-08]] (17/08), que tratou de
usernames e `id_imoview` duplicados. Aqui o caso é outro: **mesma pessoa, dois cadastros,
usernames e ids diferentes** — nenhum duplicado formal, então nenhuma validação pegava.

| | antes | depois |
|---|---:|---:|
| contas do LIDER ativas | 21 | **18** |
| referências remapeadas | — | **1.985** |
| `id_imoview` duplicados | 0 | **0** (mantido) |

---

## 1. O padrão que gerou os duplicados

Idêntico nos três casos, e igual ao Grupo A de 17/08: a pessoa foi **recadastrada**. O
cadastro novo ficou com o `id_imoview` e o contato; o antigo ficou com **todo o histórico**
de jornada e visitas. Como o `id_imoview` é o que o **Lançar Imóvel** usa para resolver o
corretor, a conta com o histórico era invisível para o lançamento — e a conta usada no
lançamento aparecia sem nenhuma captação.

Nenhuma validação pegava isso: username diferente, `id_usuarios` diferente, `id_imoview`
sem colisão. Só a leitura visual da tela de RH expôs.

## 2. O que foi mesclado

| pessoa | fica | apagado | refs movidas | observação |
|---|---|---|---:|---|
| Jéssica | **C61251** `jessica_gomes` (imv 245) | C61201 | **660** | 10 visitas + 19 captações + 627 snapshots |
| Karla | **C61254** `karla_madrilis` (imv 237) | C61199 | **1.325** | 25 captações + 1.295 snapshots |
| Samya | **C61219** `samya_amorim` | C61259 | **0** | ver §3 — direção invertida |

Campos vazios da conta que fica foram preenchidos com o valor da descartada (nunca
sobrescreve): `C61251` e `C61254` ganharam o e-mail; `C61219` ganhou e-mail, telefone e
**`id_imoview=259`**.

## 3. Samya — as duas contas estavam ativas

Diferente das outras duas, aqui **nenhuma das contas estava inativa**, então a regra
"mantém a ativa" não decidia. As opções eram opostas:

- `C61259` (Sâmia Amorim Ribeiro) — cadastro novo, com `id_imoview=259`, e-mail e telefone,
  **zero histórico**;
- `C61219` (Samya Amorim) — **38 captações e 322 snapshots** (02–14/08), sem `id_imoview`,
  sem contato.

**Decisão: ficou a `C61219`**, a do histórico, herdando o `id_imoview=259` da descartada.
Sem essa herança ela continuaria fora do seletor do Lançar Imóvel.

> Por isso essa linha aparece com **0 referências movidas**: a conta que ficou já era a dona
> do histórico. O que se moveu foi o `id_imoview`, no sentido inverso das outras duas.

## 4. Falso duplicado — não mexer

A tela mostrava lado a lado **"Patrícia Vicentino Tayarol Marques" (C61202)** e
**"patricia moreira" (C61240)**, ambas do LIDER. **Não são a mesma pessoa.**

`C61240` (username `patricia_moreira_Lider`, sem atividade) é homônima da **Patricia Moreira
do time G61017** (`C61237` ativa com 237 refs, `C61221` inativa). `C61202` tem 385
referências próprias e segue intacta.

⚠️ Mesma armadilha do `victor_hugo` em 17/08: **proximidade na tela não é identidade**.
Duas pessoas de mesmo primeiro nome no mesmo time aparecem coladas na listagem.

## 5. Como foi executado

Script versionado em **`backend/merge_usuarios_dup.py`** — os três scripts da operação de
17/08 não tinham sido commitados, essa lacuna está fechada.

Desenho (transação única, `--commit` explícito, **dry-run por padrão**):

1. **Checagem de segurança** — aborta se algum id a descartar for usado como `team`;
2. **Backup** — linha completa de `usuarios` + `to_jsonb` de cada linha de referência;
3. **Remapeamento** — varre 141 colunas de texto candidatas, descobertas por
   `information_schema`;
4. **Completa campos vazios** da conta que fica (inclui `id_imoview`);
5. **DELETE**;
6. **Verificação** — qualquer referência órfã restante causa `rollback`.

### Dois erros pegos no dry-run

Valem para qualquer varredura dinâmica de `information_schema`:

1. **A tabela de backup entrava na varredura** e tinha o próprio `id_usuarios` remapeado —
   ou seja, o backup passaria a apontar para o id novo, destruindo justamente o dado que
   permite reverter. Corrigido excluindo `%_backup%` / `%backup_%`. Isso alcançava também os
   backups de 17/08.
2. **Uma view entrava junto** (`vw_usuarios_duplicados`). `UPDATE` em view pode escrever
   através e atingir a tabela de origem uma segunda vez. Corrigido com
   `table_type = 'BASE TABLE'`.

## 6. Verificação pós-operação

```
C61251 Jessica Gomes    ativo imv=245  visitas=10 captacoes=19 snapshots=627
C61254 Karla Madrilis   ativo imv=237  visitas=0  captacoes=25 snapshots=1295
C61219 Samya Amorim     ativo imv=259  visitas=0  captacoes=38 snapshots=322
```

- contas apagadas: **0 linhas** restantes para `C61201`, `C61199`, `C61259`;
- referências órfãs: **0**;
- `id_imoview` duplicado em toda a tabela: **nenhum**;
- LIDER ficou com **18 ativos** (era 21).

## 7. Backups — como reverter

| tabela | conteúdo |
|---|---|
| `usuarios_merge_backup_2026_08_19` | 6 linhas de `usuarios` (as 3 apagadas + as 3 que ficaram, estado anterior) |
| `usuarios_merge_refs_backup_2026_08_19` | 1.985 referências em `jsonb`, com `tabela`, `coluna`, `id_antigo`, `id_novo` |

```sql
-- o que foi movido, por tabela
select tabela, coluna, id_antigo, id_novo, count(*)
from usuarios_merge_refs_backup_2026_08_19 group by 1,2,3,4 order by 5 desc;
```

## 8. Em aberto

1. **Continua sem UNIQUE no banco** — a causa raiz de 17/08 §7.1 segue valendo, e esta
   operação mostra que ela **não era suficiente**: aqui nada colidia formalmente. Um índice
   único não teria evitado nenhum destes três.
2. **Mais duplicados prováveis, não tratados** (decisão: ficam para revisão própria):
   - LIDER, mesmo padrão de uma ativa + uma inativa: Flavia Ferreira (`C61191`/`C61207`),
     Sérgio Camargo (`C61245`/`C61209`), Wladimir (`C61241`/`C61244`), Marcela Bagli
     (`C61187`/`C61196`), Nilton Leal (`C61215`/`C61246` — sobra do merge de 17/08);
   - **ambíguos, exigem decisão**: Renata Almeida (`C61086`/`C61250`, **as duas ativas**),
     Heloisa de Vivo (`C61257`/`C61210`, **times diferentes** — G61015 e G61017),
     Patricia Moreira (`C61237`/`C61221`/`C61240`, três contas em dois times).
3. **Nada testado via HTTP** — verificação feita direto contra o banco, como em 17/08.
4. **`nome` não foi normalizado.** As contas que ficaram mantiveram o nome curto
   ("Jessica Gomes", "Samya Amorim") e o nome completo foi para o backup. Se o RH precisar
   do nome civil completo, está em `usuarios_merge_backup_2026_08_19`.

## Links
[[MOC - Processos Inteligência]] · [[_Operação - Deduplicação de Usuários 2026-08]] ·
[[_Registro - 2026-08-17]] · [[1.3 - Cadastro de Usuários]] · [[2.3 - Jornada de Captação]] ·
[[1.9 - Lançamento de Imóvel pelos Assistentes]] · [[3.7 - Permissionamento]]
