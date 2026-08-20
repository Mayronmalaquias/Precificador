"""Marca como revisadas as flags de acompanhamento do gerente em TODAS as equipes.

Zera as colunas "Nao viu notas", "Nao viu anexos" e "Nao adicionou motivo" da auditoria
da Visao do Diretor, ligando `viu_notas`/`viu_anexo`/`add_motivo` em
`gerente_visita_visualizada` para toda visita de equipe cadastrada.

A flag e por EQUIPE, nao por pessoa: o painel casa
`gerente_visita_visualizada.id_gerente` com `usuarios.team` do corretor da visita
(ver `_visit_reviews`). Visita sem linha nenhuma conta como nao vista, entao o script
tambem INSERE a linha que falta.

NAO mexe em "Propostas sem acao": aquilo nao e flag de leitura, e uma metrica de tempo
(proposta aberta e sem acao ha >= 1 dia). Zerar exigiria forjar atividade e voltaria a
contar no dia seguinte.

RODA EM DRY-RUN POR PADRAO (faz tudo e da rollback). So grava com --commit.

    venv/bin/python marcar_visitas_revisadas.py            # dry-run
    venv/bin/python marcar_visitas_revisadas.py --commit   # aplica
"""
import sys

from sqlalchemy import text

from app.database import SessionLocal

TB_BACKUP = "gerente_visita_visualizada_backup_2026_08_20"

# Visitas de corretor com equipe cadastrada — o mesmo recorte da auditoria do painel,
# que ignora visita sem equipe ativa (nao ha gerente a cobrar).
BASE_VISITAS = """
    FROM visitas v
    JOIN usuarios u ON u.id_usuarios = v.id_corretor
    JOIN equipes e  ON e.id_equipe   = u.team
"""


def main(commit: bool):
    s = SessionLocal()
    try:
        print(f"{'APLICANDO (--commit)' if commit else 'DRY-RUN (rollback no final)'}\n")

        faltando = s.execute(text(f"""
            SELECT count(*) {BASE_VISITAS}
            LEFT JOIN gerente_visita_visualizada g
                   ON g.id_visita = v.id_visita AND g.id_gerente = u.team
            WHERE g.id IS NULL
        """)).scalar()
        pendentes = s.execute(text(f"""
            SELECT count(*) {BASE_VISITAS}
            JOIN gerente_visita_visualizada g
              ON g.id_visita = v.id_visita AND g.id_gerente = u.team
            WHERE NOT g.viu_anexo OR NOT g.viu_notas OR NOT g.add_motivo
        """)).scalar()
        print(f"[1] antes: {faltando} visitas sem linha de flag, "
              f"{pendentes} linhas com flag pendente\n")

        if not faltando and not pendentes:
            print("Nada a fazer — ja esta tudo marcado como visto.")
            return 0

        # Backup so das linhas que serao alteradas (as inseridas nao existem ainda).
        s.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TB_BACKUP} AS
            SELECT *, now() AS backup_em FROM gerente_visita_visualizada WHERE false
        """))
        s.execute(text(f"""
            INSERT INTO {TB_BACKUP}
            SELECT g.*, now() FROM gerente_visita_visualizada g
            WHERE g.id IN (
                SELECT g2.id {BASE_VISITAS}
                JOIN gerente_visita_visualizada g2
                  ON g2.id_visita = v.id_visita AND g2.id_gerente = u.team
                WHERE NOT g2.viu_anexo OR NOT g2.viu_notas OR NOT g2.add_motivo
            )
        """))
        print(f"[2] backup das linhas alteradas -> {TB_BACKUP} ({pendentes} linhas)\n")

        atualizadas = s.execute(text(f"""
            UPDATE gerente_visita_visualizada g
               SET viu_anexo = true, viu_notas = true, add_motivo = true
             WHERE g.id IN (
                SELECT g2.id {BASE_VISITAS}
                JOIN gerente_visita_visualizada g2
                  ON g2.id_visita = v.id_visita AND g2.id_gerente = u.team
                WHERE NOT g2.viu_anexo OR NOT g2.viu_notas OR NOT g2.add_motivo
             )
        """)).rowcount
        print(f"[3] linhas atualizadas: {atualizadas}")

        # DISTINCT porque a mesma visita pode aparecer mais de uma vez no join se o
        # cadastro tiver corretor duplicado — sem ele, entraria linha repetida.
        inseridas = s.execute(text(f"""
            INSERT INTO gerente_visita_visualizada
                        (id_gerente, id_visita, viu_anexo, viu_notas, add_motivo)
            SELECT DISTINCT u.team, v.id_visita, true, true, true
            {BASE_VISITAS}
            LEFT JOIN gerente_visita_visualizada g
                   ON g.id_visita = v.id_visita AND g.id_gerente = u.team
            WHERE g.id IS NULL
        """)).rowcount
        print(f"[4] linhas inseridas: {inseridas}\n")

        sobrou_sem = s.execute(text(f"""
            SELECT count(*) {BASE_VISITAS}
            LEFT JOIN gerente_visita_visualizada g
                   ON g.id_visita = v.id_visita AND g.id_gerente = u.team
            WHERE g.id IS NULL
        """)).scalar()
        sobrou_pend = s.execute(text(f"""
            SELECT count(*) {BASE_VISITAS}
            JOIN gerente_visita_visualizada g
              ON g.id_visita = v.id_visita AND g.id_gerente = u.team
            WHERE NOT g.viu_anexo OR NOT g.viu_notas OR NOT g.add_motivo
        """)).scalar()
        print(f"[5] depois: {sobrou_sem} sem linha, {sobrou_pend} pendentes")
        if sobrou_sem or sobrou_pend:
            print("  ROLLBACK: ainda sobrou pendencia")
            s.rollback()
            return 1

        if commit:
            s.commit()
            print(f"\nCOMMIT feito. Reverter com {TB_BACKUP} (so as atualizadas; as "
                  f"inseridas sao as que tinham as 3 flags falsas por ausencia).")
        else:
            s.rollback()
            print("\nDRY-RUN: rollback dado, nada gravado. Use --commit para aplicar.")
        return 0

    except Exception as e:
        s.rollback()
        print(f"\nERRO, rollback: {e}")
        raise
    finally:
        s.close()


if __name__ == "__main__":
    sys.exit(main("--commit" in sys.argv))
