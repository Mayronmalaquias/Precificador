"""Regulariza o acompanhamento dos leads existentes.

Todos os leads que ja estavam no espelho no momento desta migracao deixam de compor o
backlog historico de "sem acompanhamento". Leads inseridos pelo sync depois do corte
continuam nascendo com `acompanhamento_em` nulo e entram normalmente na fila.

Revision ID: 20260826_regulariza_acomp
Revises: 20260825_acomp_c2s
"""
from alembic import op


revision = "20260826_regulariza_acomp"
down_revision = "20260825_acomp_c2s"
branch_labels = None
depends_on = None


MARCADOR = "sistema_corte_20260826"


def upgrade():
    op.execute(f"""
        UPDATE leads_c2s
           SET acompanhamento_em = CURRENT_TIMESTAMP,
               acompanhamento_por = COALESCE(acompanhamento_por, '{MARCADOR}')
         WHERE acompanhamento_em IS NULL
    """)


def downgrade():
    # So desfaz linhas ainda intactas desde a regularizacao. Se alguem registrou um
    # acompanhamento real depois, `acompanhamento_por` mudou e a informacao e preservada.
    op.execute(f"""
        UPDATE leads_c2s
           SET acompanhamento_em = NULL,
               acompanhamento_por = NULL
         WHERE acompanhamento_por = '{MARCADOR}'
           AND contato_status IS NULL
           AND visita_agendada IS NULL
           AND motivo_sem_visita IS NULL
           AND proxima_acao IS NULL
    """)
