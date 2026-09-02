"""Mescla contas duplicadas de usuario: remapeia as referencias e apaga a conta descartada.

Mesmo desenho da operacao de 17/08/2026 (ver docs/processos/_Operacao - Deduplicacao de
Usuarios 2026-08.md), agora versionado: checagem de seguranca -> backup -> remapeamento ->
verificacao -> DELETE, tudo numa transacao so.

RODA EM DRY-RUN POR PADRAO (faz tudo e da rollback). So grava com --commit.

    venv/bin/python merge_usuarios_dup.py            # dry-run
    venv/bin/python merge_usuarios_dup.py --commit   # aplica

`MERGES` lista os pares (fica, descartado). O que fica recebe as referencias do descartado;
campos vazios do que fica sao preenchidos com o valor do descartado (nunca sobrescreve).
"""
import sys

from sqlalchemy import text

from app.database import SessionLocal

# (id que FICA, id DESCARTADO, motivo)
MERGES = [
    # Conta antiga da Paolla, inativa, mas com `team=G61010` (LOTUS) — e ela e gerente da
    # LIDER. Como o escopo do gerente e "todo usuario com este team", a conta velha fazia
    # os 270 leads dela aparecerem no relatorio da equipe da Thais.
    # ("G61016", "C61170", ...) — Paolla, aplicado em 20/08/2026. Fora da lista porque a
    # conta descartada ja nao existe e o script aborta quando um dos lados falta.

    # Recadastro: `andre_brusk_old` (inativa, sem id_imoview) x `andre_brusk` (ativa,
    # id_imoview 256), as duas na LOTUS. A conta velha segurava 290 referencias — 276
    # delas em `captacao_snapshot` — e por isso o Andre aparecia DUAS vezes na Jornada
    # de Captacao, uma com o historico e outra com o cadastro atual.
    # ("C61249", "C61248", ...) — Andre Brusk, aplicado em 01/09/2026.

    # Renata Almeida, as DUAS ativas na LOTUS (recadastro: `renata-almeida` com hifen x
    # `renata_almeida` com underscore). Fica a ANTIGA: e nela que a pessoa trabalha —
    # 95 visitas ate 27/08, 36 snapshots ate hoje — enquanto a nova so tem linhas de
    # sincronizacao do Imoview. Apagar a que ela usa quebraria o login dela.
    # `CAMPOS_COMPLETAR` leva o `id_imoview=32` da descartada para a que fica, o que
    # tambem conserta o casamento por nome do sync de estoque.
    ("C61086", "C61250", "Renata Almeida: conta de trabalho recebe o id_imoview da nova"),
]

SUFIXO = "2026_09_01b"
TB_BACKUP = f"usuarios_merge_backup_{SUFIXO}"
TB_REFS = f"usuarios_merge_refs_backup_{SUFIXO}"

# Campos preenchidos a partir da conta descartada quando o que fica esta vazio.
CAMPOS_COMPLETAR = (
    "email", "telefone", "instagram", "descricao", "id_imoview", "creci", "cpf", "rg",
    "unidade", "gerente_responsavel", "data_entrada_61", "telefone_pessoal",
    "telefone_corporativo", "email_pessoal", "email_corporativo", "data_nascimento",
    "estado_civil", "endereco", "contato_emergencia", "cnpj", "razao_social",
    "banco", "agencia", "conta", "tipo_conta", "chave_pix", "link_documentos",
)


def colunas_de_referencia(s):
    """Colunas de texto que podem guardar um id_usuarios (mesma varredura da operacao anterior)."""
    linhas = s.execute(text("""
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = 'public'
          -- So tabela base: UPDATE em view pode escrever atraves e atingir a origem duas vezes.
          AND t.table_type = 'BASE TABLE'
          -- Tabela de backup guarda o estado ANTERIOR: remapear ali destruiria justamente
          -- o dado que permite reverter. Vale para os backups das operacoes passadas tambem.
          AND c.table_name NOT LIKE '%_backup%'
          AND c.table_name NOT LIKE '%backup_%'
          AND c.data_type IN ('character varying', 'text', 'character')
          AND (
            c.column_name ILIKE '%corretor%' OR c.column_name ILIKE '%captador%'
            OR c.column_name ILIKE '%gerente%' OR c.column_name ILIKE '%usuario%'
            OR c.column_name ILIKE '%vendedor%' OR c.column_name ILIKE '%diretor%'
            OR c.column_name ILIKE '%autor%' OR c.column_name ILIKE '%criado_por%'
            OR c.column_name ILIKE '%solicitante%' OR c.column_name ILIKE '%responsavel%'
            OR c.column_name ILIKE '%atendimento%' OR c.column_name ILIKE '%equipe%'
            OR c.column_name = 'team'
          )
        ORDER BY table_name, column_name
    """)).all()
    # `usuarios.id_usuarios` e a propria identidade e `usuarios.team` e equipe, nao referencia
    # de pessoa — as duas sao tratadas fora do remapeamento.
    return [(t, c) for t, c in linhas
            if not (t == "usuarios" and c in ("id_usuarios", "team"))]


def chave_primaria(s, tabela):
    return s.execute(text("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = to_regclass(:t) AND i.indisprimary
    """), {"t": f"public.{tabela}"}).scalars().first()


def main(commit: bool):
    s = SessionLocal()
    fica_ids = [f for f, _, _ in MERGES]
    descartar = [d for _, d, _ in MERGES]

    try:
        print(f"{'APLICANDO (--commit)' if commit else 'DRY-RUN (rollback no final)'}\n")

        # 1) Checagem de seguranca: id descartado nao pode ser equipe de ninguem.
        usados = s.execute(text("""
            SELECT team, count(*) FROM usuarios WHERE team = ANY(:ids) GROUP BY team
        """), {"ids": descartar}).all()
        if usados:
            print(f"ABORTADO: id descartado usado como team: {usados}")
            return 1
        print("[1] checagem de team: OK, nenhum descartado e equipe de alguem\n")

        # Todos os envolvidos precisam existir.
        for fica, desc, motivo in MERGES:
            for i in (fica, desc):
                if not s.execute(text("SELECT 1 FROM usuarios WHERE id_usuarios=:i"),
                                 {"i": i}).first():
                    print(f"ABORTADO: {i} nao existe")
                    return 1

        # 2) Backup das linhas de usuarios (as que ficam tambem, pro antes/depois).
        s.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TB_BACKUP} AS
            SELECT *, now() AS backup_em FROM usuarios WHERE false
        """))
        s.execute(text(f"""
            INSERT INTO {TB_BACKUP}
            SELECT *, now() FROM usuarios WHERE id_usuarios = ANY(:ids)
        """), {"ids": fica_ids + descartar})
        print(f"[2] backup de usuarios -> {TB_BACKUP} ({len(fica_ids + descartar)} linhas)\n")

        s.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TB_REFS} (
                id serial PRIMARY KEY,
                tabela text, coluna text, id_antigo text, id_novo text,
                linha jsonb, backup_em timestamp DEFAULT now()
            )
        """))

        # 3) Remapeamento.
        cols = colunas_de_referencia(s)
        print(f"[3] varrendo {len(cols)} colunas de referencia")
        total = 0
        for fica, desc, motivo in MERGES:
            print(f"\n  {desc} -> {fica}   ({motivo})")
            movidas = 0
            for tabela, coluna in cols:
                try:
                    n = s.execute(text(f"""
                        SELECT count(*) FROM "{tabela}" WHERE "{coluna}" = :d
                    """), {"d": desc}).scalar()
                except Exception:
                    s.rollback()
                    print(f"      ABORTADO ao ler {tabela}.{coluna}")
                    return 1
                if not n:
                    continue

                pk = chave_primaria(s, tabela)
                if pk:
                    s.execute(text(f"""
                        INSERT INTO {TB_REFS} (tabela, coluna, id_antigo, id_novo, linha)
                        SELECT :t, :c, :d, :f, to_jsonb(x.*)
                        FROM "{tabela}" x WHERE x."{coluna}" = :d
                    """), {"t": tabela, "c": coluna, "d": desc, "f": fica})

                s.execute(text(f"""
                    UPDATE "{tabela}" SET "{coluna}" = :f WHERE "{coluna}" = :d
                """), {"f": fica, "d": desc})
                print(f"      {tabela}.{coluna}: {n}")
                movidas += n
            print(f"      -> {movidas} referencias remapeadas")
            total += movidas

        # 4) Completa campos vazios da conta que fica com o dado da descartada.
        print(f"\n[4] completando campos vazios da conta que fica")
        for fica, desc, _ in MERGES:
            atual = s.execute(text("SELECT * FROM usuarios WHERE id_usuarios=:i"),
                              {"i": fica}).mappings().first()
            antigo = s.execute(text("SELECT * FROM usuarios WHERE id_usuarios=:i"),
                               {"i": desc}).mappings().first()
            preenchidos = []
            for campo in CAMPOS_COMPLETAR:
                if campo not in atual:
                    continue
                vazio = atual[campo] is None or str(atual[campo]).strip() == ""
                tem = antigo.get(campo) is not None and str(antigo.get(campo)).strip() != ""
                if vazio and tem:
                    s.execute(text(f'UPDATE usuarios SET "{campo}" = :v WHERE id_usuarios = :i'),
                              {"v": antigo[campo], "i": fica})
                    preenchidos.append(f"{campo}={antigo[campo]!r}")
            print(f"  {fica}: {', '.join(preenchidos) if preenchidos else '(nada a completar)'}")

        # 5) DELETE das contas descartadas.
        print(f"\n[5] apagando contas descartadas")
        for fica, desc, _ in MERGES:
            s.execute(text("DELETE FROM usuarios WHERE id_usuarios = :d"), {"d": desc})
            print(f"  {desc} apagado")

        # 6) Verificacao: nenhuma referencia orfa pode sobrar.
        print(f"\n[6] verificacao final")
        orfas = []
        for tabela, coluna in cols:
            try:
                n = s.execute(text(f"""
                    SELECT count(*) FROM "{tabela}" WHERE "{coluna}" = ANY(:ids)
                """), {"ids": descartar}).scalar()
            except Exception:
                s.rollback()
                return 1
            if n:
                orfas.append(f"{tabela}.{coluna}={n}")
        if orfas:
            print(f"  ROLLBACK: sobraram referencias orfas: {orfas}")
            s.rollback()
            return 1
        sobrou = s.execute(text("""
            SELECT count(*) FROM usuarios WHERE id_usuarios = ANY(:ids)
        """), {"ids": descartar}).scalar()
        if sobrou:
            print(f"  ROLLBACK: {sobrou} conta(s) descartada(s) ainda em usuarios")
            s.rollback()
            return 1
        print(f"  OK: 0 referencias orfas, {total} referencias remapeadas")

        if commit:
            s.commit()
            print(f"\nCOMMIT feito. Backups: {TB_BACKUP}, {TB_REFS}")
        else:
            s.rollback()
            print(f"\nDRY-RUN: rollback dado, nada foi gravado. Use --commit para aplicar.")
        return 0

    except Exception as e:
        s.rollback()
        print(f"\nERRO, rollback: {e}")
        raise
    finally:
        s.close()


if __name__ == "__main__":
    sys.exit(main("--commit" in sys.argv))
