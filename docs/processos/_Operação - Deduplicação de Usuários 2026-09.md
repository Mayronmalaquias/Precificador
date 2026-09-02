---
tags: [operacao, processo/inteligencia, dominio/cadastro]
tipo: Registro de operação
data: 2026-09-02
status: 2 merges aplicados · 6 casos limpos aguardando ok · 3 casos precisam de decisão
---

# Operação — Deduplicação de Usuários 09/2026

Continuação de [[_Operação - Deduplicação de Usuários 2026-08]]. Mesma ferramenta:
`backend/merge_usuarios_dup.py`, que roda em **dry-run por padrão** e só grava com
`--commit`.

## Por que apareceu de novo

Duplicado = **recadastro**. A pessoa é cadastrada outra vez e o histórico fica numa conta
enquanto o `id_imoview` (ou o login em uso) fica na outra.

O sintoma que trouxe o assunto: na **Jornada de Captação**, o dropdown de corretor
mostrava o mesmo nome duas vezes. Ele funde os usuários ativos com os corretores achados
nas captações, deduplicando **por id, não por nome** — então duas contas da mesma pessoa
viram duas linhas.

---

## Aplicados

### André Brusk — `C61248` → `C61249`

| | `C61248` | `C61249` |
|---|---|---|
| username | `andre_brusk_old` | `andre_brusk` |
| ativo | não | **sim** |
| id_imoview | — | 256 |
| equipe | G61010 (LOTUS) | G61010 |

**Todo o trabalho estava na conta inativa**: 12 captações, 276 snapshots, 1 linha em
`fato_captacao` e 1 em `fato_estoque`. A ativa tinha zero. **290 referências remapeadas**,
0 órfãs.

### Renata Almeida — `C61250` → `C61086`

Caso diferente: **as duas ativas**, mesma equipe.

| | `C61086` | `C61250` |
|---|---|---|
| username | `renata-almeida` | `renata_almeida` |
| nome | `'Renata Almeida'` | `'Renata Almeida '` ← espaço no fim |
| id_imoview | — | 32 |
| **referências** | **6.043** | 126 |

Ficou a **antiga**, contra a intuição de manter a mais nova. O critério foi onde a pessoa
trabalha:

```
C61086  95 visitas (ultima 27/08), 36 snapshots ate hoje, 115 fato_estoque
C61250  so 79 fato_estoque e 1 fato_captacao
```

As linhas da C61250 vieram do sync casando por **nome**, não de trabalho dela. Apagar a
C61086 quebraria o login que ela usa todo dia. `CAMPOS_COMPLETAR` levou o `id_imoview=32` e
o telefone para a conta que ficou — o que também conserta o casamento por nome do sync de
estoque daqui pra frente.

---

## Armadilha nova: o nome desnormalizado

> ⚠️ O script remapeia colunas de **id**. A Jornada agrupa o ranking por
> `captacao.nome_corretor`, que é **texto**.
>
> Só o merge deixaria 288 linhas escritas "Andre Brusk da silva fonseca" apontando para uma
> conta chamada "Andre Brusk". Foi preciso um `UPDATE` extra em `captacao` e
> `captacao_snapshot`.
>
> Vale para qualquer merge futuro de quem tem captação.

Conferido também que não regride: os 276 snapshots não são trabalho novo, são a foto diária
das mesmas 12 captações (12 × 23 dias). Como o job copia `captacao.id_corretor`, e essa
coluna agora aponta para a conta certa, os snapshots futuros já nascem corretos.

---

## Casos limpos, aguardando ok

Ativa + inativa na **mesma equipe**, com a inativa quase sem registros:

| pessoa | descarta | refs | fica |
|---|---|---:|---|
| Nilton Leal | `C61246` | **0** | `C61215` |
| Wladimir Costa | `C61244` | **0** | `C61241` |
| Yasmin Nasser | `C61247` | 1 | `C61222` |
| Sérgio Camargo | `C61245` | 1 | `C61209` |
| Patrícia Moreira | `C61221` + `C61240` | 1 + 1 | `C61237` |
| Flávia Ferreira | `C61207` | 19 | `C61191` |

---

## Casos que precisam de decisão

**Lucas — não mesclar sem confirmação.**

| | `C61206` | `C61178` |
|---|---|---|
| nome | Lucas **Rodrigues da** Silva | Lucas **Souza** Silva |
| username | `lucas_silva` | `lucas_souza_silva` |
| id_imoview | — | 214 |
| captações | **26** | **66** |

Nomes do meio diferentes e **nenhum campo de identidade coincide** — sem CPF, CRECI,
e-mail ou telefone em nenhuma das duas. O agrupamento por "primeiro + último nome" junta
por "Silva", o sobrenome mais comum do país. Podem ser duas pessoas.

**Victor Hugo** — a conta ativa (`C61226`) está **sem equipe**; a inativa (`C61116`) está na
SENNA com 23 referências. Mesclar tiraria os registros da equipe.

**Heloísa de Vivo** — duas contas **ativas em equipes diferentes** (`C61257`/SENNA e
`C61210`/Alpha). Precisa saber onde ela está hoje.

---

## Como detectar

O sinal mais confiável é o **username terminando em `_old`**. A varredura por nome
normalizado não pega tudo: "Andre Brusk da silva fonseca" e "Andre Brusk" têm nomes
diferentes.

```sql
SELECT id_usuarios, nome, username, team, ativo
FROM usuarios WHERE username ILIKE '%\_old';
```

Depois, agrupar por **primeiro + último token** do nome normalizado pega o resto — mas gera
falso positivo em sobrenome comum, como o caso do Lucas.

## Backups

`usuarios_merge_backup_2026_09_01` / `_refs_backup_2026_09_01` (André)
`usuarios_merge_backup_2026_09_01b` / `_refs_backup_2026_09_01b` (Renata)

Guardam a linha original de `usuarios` e cada referência alterada.

---
[[MOC - Processos Inteligência]] · [[_Operação - Deduplicação de Usuários 2026-08]] · [[1.3 - Cadastro de Usuários]] · [[2.3 - Jornada de Captação]] · [[_Registro - 2026-09-02]]
