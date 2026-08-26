"""Move o acompanhamento do lead para `leads_c2s`.

O acompanhamento (contato, visita agendada, motivo, proxima acao) morava em
`leads_legado`. So que aquela tabela passa por um filtro de negocio na importacao — so
entra lead criado pela recepcao ou de fonte Faixa/Indicacao — e por isso **26% dos leads
do espelho nao tem linha la**: 5.203 leads em 25/08/2026, dos quais 4.761 nunca
existiram no legado. Na pratica, lead de portal (Grupo Zap, DF imoveis, ImovelWeb) nao
podia receber acompanhamento nenhum.

A chave passa a ser `id_c2s`, que e estavel e existe para todo lead. As colunas ficam
FORA do upsert do sync (ver `lead_sync_service._gravar`), senao a passada horaria
apagaria o que o gerente escreveu.

`leads_legado` nao e alterada: ela continua sendo a base do relatorio historico, e as
colunas antigas ficam onde estao como historico. Quem le acompanhamento passa a ler
daqui.

Revision ID: 20260825_acomp_c2s
Revises: 20260825_leads_c2s
"""
from alembic import op
import sqlalchemy as sa

revision = "20260825_acomp_c2s"
down_revision = "20260825_leads_c2s"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("leads_c2s", sa.Column("contato_status", sa.String(length=20), nullable=True))
    # Nulo = ninguem respondeu ainda. Sem o nulo nao daria p/ separar "nao agendou" de
    # "nao olharam o lead" — mesma regra da coluna original.
    op.add_column("leads_c2s", sa.Column("visita_agendada", sa.Boolean(), nullable=True))
    op.add_column("leads_c2s", sa.Column("motivo_sem_visita", sa.Text(), nullable=True))
    op.add_column("leads_c2s", sa.Column("proxima_acao", sa.Text(), nullable=True))
    op.add_column("leads_c2s", sa.Column("acompanhamento_por", sa.String(length=50), nullable=True))
    op.add_column("leads_c2s", sa.Column("acompanhamento_em", sa.DateTime(), nullable=True))

    op.create_index("ix_leads_c2s_contato_status", "leads_c2s", ["contato_status"])
    op.create_index("ix_leads_c2s_visita_agendada", "leads_c2s", ["visita_agendada"])
    op.create_index("ix_leads_c2s_acompanhamento_em", "leads_c2s", ["acompanhamento_em"])

    # Copia o que ja existe, pelo elo que o sync montou. Sao poucas linhas (13 na base
    # inteira em 21/08), mas perde-las seria perder o unico acompanhamento registrado.
    op.execute("""
        UPDATE leads_c2s c
           SET contato_status     = l.contato_status,
               visita_agendada    = l.visita_agendada,
               motivo_sem_visita  = l.motivo_sem_visita,
               proxima_acao       = l.proxima_acao,
               acompanhamento_por = l.acompanhamento_por,
               acompanhamento_em  = l.acompanhamento_em
          FROM leads_legado l
         WHERE c.id_legado = l.id
           AND l.acompanhamento_em IS NOT NULL
    """)


def downgrade():
    for nome in ("ix_leads_c2s_acompanhamento_em", "ix_leads_c2s_visita_agendada",
                 "ix_leads_c2s_contato_status"):
        op.drop_index(nome, table_name="leads_c2s")
    for coluna in ("acompanhamento_em", "acompanhamento_por", "proxima_acao",
                   "motivo_sem_visita", "visita_agendada", "contato_status"):
        op.drop_column("leads_c2s", coluna)
