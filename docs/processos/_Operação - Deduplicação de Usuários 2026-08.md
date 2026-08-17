---
tags: [operacao, processo/inteligencia, dominio/usuarios, dominio/qualidade]
tipo: Registro de operação (migração de dados)
data: 2026-08-17
status: aplicado em produção · reversível pelos backups
---

# Operação — Deduplicação de Usuários (08/2026)

Registro da limpeza de identidade da tabela `usuarios`: **7 usernames duplicados** e
**5 `id_imoview` duplicados**, todos resolvidos. Documenta o que foi decidido, o que foi
executado e **como reverter**.

| | antes | depois |
|---|---:|---:|
| usernames duplicados | 7 | **0** |
| `id_imoview` duplicados | 5 | **0** |
| total de usuários | 274 | **267** |
| referências remapeadas | — | **18.574** |

---

## 1. Por que existia

`usuarios.username` **não tem UNIQUE** — nem no model (`String(100)` simples) nem no banco.
Nada impedia dois cadastros com o mesmo login. O `login()` casa pelo primeiro registro que
encontrar, então a pessoa podia entrar com a permissão errada dependendo da ordem do banco.

Mesma coisa com `id_imoview`: o **Lançar Imóvel resolve o corretor por esse campo**, então
dois usuários com o mesmo código significavam imóvel atribuído a quem aparecesse primeiro.

> Já houve uma limpeza anterior, de natureza **diferente**: `usuarios_dup_backup` (19 linhas)
> trata de **`id_usuarios` duplicado** — mesma pessoa, mesmo id, dois usernames. Aqui é o
> inverso: mesmo username, **ids diferentes**.

## 2. Os 7 usernames — não eram todos o mesmo caso

A análise mostrou **três naturezas distintas**. Tratar tudo como "duplicata" teria destruído dados.

### Grupo A — duplicata real (3): mesclados
Padrão idêntico: recadastro recente ficou com o `id_imoview` novo, enquanto o registro antigo
tinha todo o histórico.

| username | mantido | apagado | id_imoview transferido |
|---|---|---|---:|
| `andre_brusk` | C61248 (96 refs) | C61249 | 256 |
| `nilton_leal` | C61215 (290 refs) | C61246 | 261 |
| `yasmin_nasser` | C61222 (85 refs) | C61247 | 265 |

4 referências remapeadas (todas em `fato_captacao.captador1`). Os descartados **não foram
apagados** neste lote: ficaram `ativo=false`, `desligado=true` e username sufixado `_dup_<id>`.

### Grupo B — conta pessoal × conta de equipe (2)
`G61001` e `G61003` **não são só usuário — são identificador de equipe**. `G61001` é a equipe
**AGEF (ativa)**, com 29 usuários apontando para ela em `usuarios.team` e 47.393 registros em
`eventos_imovel_legado.id_gerente`.

Primeiro passo (conservador): renomear a conta G6 e manter os dois ids.
Depois, por decisão explícita, **a conta C6 foi apagada** e tudo consolidado no G6 — ver §3.

### Grupo C — não eram a mesma pessoa (2)

| username | o que era | decisão |
|---|---|---|
| `admin` | `NULL` = Miron Malaquias (desligado) e `123456` = sem nome, gerente, **ativo** | **as duas apagadas** |
| `victor_hugo` | C61161 "Victor Hugo Pereira Santos" (corretor, G61015, 596 refs) e C61226 "Victor Hugo" (**assistente**, sem team) | pessoas diferentes → assistente renomeado para `victor_hugo_assistente` |

## 3. Consolidação C6 → G6 (José e Luana)

Decisão posterior: apagar as contas `C6…` e consolidar tudo no `G6…`.

| pessoa | fica | apagado | refs remapeadas |
|---|---|---|---:|
| José Marques | G61001 (diretor) | C61053 | 871 |
| Luana Salvinski | G61003 (gerente) | C61059 | 5.822 |

**Ordem obrigatória:** as FKs de `vendas` (`vendedor_id`, `captador_id`, `gerente_venda_id`,
`gerente_captacao_id`, `diretor_id`) **não têm `ON DELETE`** — o DELETE só passa depois de
remapear tudo.

⚠️ **`C61053` era a conta ATIVA do José.** Sem cuidado, apagá-la o deixaria sem login. Foram
migrados para `G61001`: **senha**, `id_imoview=5`, `ativo=true`, `desligado=false`. Ele segue
logando como `jose_marques` com a mesma senha.

A Luana não teve esse risco: as duas contas dela já estavam desligadas.

Ao final, os usernames limpos voltaram para as contas sobreviventes
(`jose_marques`, `luana_salvinski`).

## 4. Os 5 `id_imoview`

| código | situação | decisão |
|---:|---|---|
| **5** | `jose_marques` (G61001, ativo) × `paolla_gardenia` (G61016, ativa) — **dois ativos** | código é do **José**; Paolla foi para **192** |
| **19** | `daniela_-_atendimento` (C61141) × `sueli` (C61143), ambos desligados | código é da **Sueli**; Daniela ficou `NULL` |
| **30** | `thais` (C61114, desligada) × `thais_tannus` (G61010, gerente ativa) | mesma pessoa → consolidado em **G61010** |
| **52** | `marcelo_..._souza` (C61064, desligado) × `marcelo_ribeiro` (G61002, gerente ativo) | mesma pessoa → consolidado em **G61002** |
| **236** | `raquel_silva` (id `238`, ativo) × `raquel-silva` (C61082, ativo) | mesma pessoa → consolidado em **C61082** |

> O conflito do código **5** foi **criado nesta própria sessão**: veio junto do `C61053` na
> consolidação do José. Lição: ao migrar `id_imoview` num merge, checar se o código já está
> em uso por outra pessoa.

**Pegadinha do 192:** o código já estava em `C61170` (`paolla_gardenia_gomes`, conta antiga e
inativa da mesma Paolla). Escrever 192 direto em `G61016` só trocaria o duplicado de lugar —
foi preciso limpar da conta antiga primeiro.

### Consolidações do §4 (30, 52, 236)

| pessoa | fica | apagado | refs |
|---|---|---|---:|
| Thais Tannús | G61010 | C61114 | 3.587 |
| Marcelo Ribeiro | G61002 | C61064 | 8.282 |
| Raquel Silva | C61082 (→ `raquel_silva`) | `238` | 7 |

**Diferença importante em relação ao §3:** aqui a conta que fica **já era a ativa**, então
**não** se transferiu senha nem estado. Transferir trocaria a credencial que a pessoa usa hoje.

## 5. Como foi executado

Três scripts, todos com o mesmo desenho:

1. **Checagem de segurança** — aborta se algum id a descartar for usado como `team` por outro
   usuário (nenhum era).
2. **Backup** — linha completa de `usuarios` + `to_jsonb(t.*)` de **cada linha de referência**
   antes de alterar, com `id_antigo` e `id_novo`.
3. **Remapeamento** — 43 colunas varridas (`visitas`, `captacao`, `captacao_snapshot`,
   `fato_captacao/saida/estoque/destaque`, `eventos_imovel_legado`, `vendas`, `proposta_efetiva`,
   `pessoa_alias`, `usuarios.team`…), pulando as que não existem.
4. **`id_imoview`** transferido só quando a conta que fica está sem.
5. **DELETE** da conta duplicada.
6. **Verificação antes do commit** — se sobrar qualquer referência órfã, faz `rollback`.

Todos rodaram primeiro em **dry-run** (rollback ao final) e só depois com `--commit`.

## 6. Backups — como reverter

| tabela | conteúdo |
|---|---|
| `usuarios_merge_backup_2026_08` | 23 linhas completas de `usuarios` (inclui as apagadas) |
| `usuarios_merge_refs_backup_2026_08` | 18.574 referências em `jsonb`, com `tabela`, `coluna`, `id_antigo`, `id_novo` |

```sql
-- o que foi movido, por tabela
select tabela, coluna, id_antigo, id_novo, count(*)
from usuarios_merge_refs_backup_2026_08 group by 1,2,3,4 order by 5 desc;

-- desfazer um remapeamento específico
update <tabela> set <coluna> = '<id_antigo>'
where <coluna> = '<id_novo>'
  and <pk> in (select (linha->>'<pk>') from usuarios_merge_refs_backup_2026_08
               where tabela='<tabela>' and coluna='<coluna>' and id_antigo='<id_antigo>');
```

## 7. Verificação de acesso pós-operação

Feita **rodando as funções reais de escopo**, não por inspeção visual.

**Gestão de Clientes / Relatórios** (`_resolver_ids_corretor_gestao`):
```
Jose Marques     diretor  modo=61      263 corretores (todos)
Marcelo Ribeiro  gerente  modo=equipe   62
Thais Tannús     gerente  modo=equipe   42
Paolla Gardenia  gerente  modo=equipe   36
```

**Jornada de Captação** (`escopo_jornada`):
```
Jose Marques     ve_tudo=True   gestor=True
Marcelo Ribeiro  ve_tudo=False  gestor=True   159 captações
Thais Tannús     ve_tudo=False  gestor=True   308
Paolla Gardenia  ve_tudo=False  gestor=True   285
Raquel Silva     corretor       gestor=False  360
```

**Equipes intactas** — nenhuma linha de `usuarios.team` foi remapeada em nenhum merge:
```
G61001 AGEF 28 · G61002 AGUIA 62 · G61010 LOTUS 42 · G61015 SENNA 28 · G61016 LIDER 36
```

**Por que nada quebrou:** o escopo de gerente é resolvido pelo campo **`team`**, não pelo
`id_usuarios`. Os ids apagados eram sempre a conta *pessoal antiga*, nunca um id usado como
equipe. As permissões ficaram nas contas sobreviventes.

## 8. Riscos remanescentes

- 🔴 **Sem UNIQUE no banco.** A validação em `cadastrar_usuario` cobre a aplicação, mas não
  protege de corrida entre requisições nem de escrita direta. Índices em
  [[_Registro - 2026-08-17]] §7.1.
- 🟠 **Raquel Silva pode precisar redefinir senha** — tinha duas contas ativas e ficou a de
  `C61082`.
- 🟠 **Nada testado via HTTP** — verificação feita chamando os serviços direto contra o banco.
- 🟠 **`victor_hugo` e `admin` eram armadilhas de homonímia.** Vale lembrar disso em qualquer
  limpeza futura: `RetornarTipo3` do Imoview tem um **cliente** chamado "VITOR HUGO PEREIRA",
  homônimo do corretor. Casar por nome entre bases produz exatamente esse tipo de erro.

## Links
[[MOC - Processos Inteligência]] · [[_Registro - 2026-08-17]] · [[1.3 - Cadastro de Usuários]] ·
[[1.8 - Cadastro em Massa de Usuários]] · [[3.7 - Permissionamento]] ·
[[3.9 - Reatribuição de Carteira]] · [[2.9 - Gestão de Segredos]]
