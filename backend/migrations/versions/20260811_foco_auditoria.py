"""fato_captacao: auditoria do foco (declarado x sugerido pela regra).

Permite responder, depois de alguns meses de uso: quando o estagiário diverge da regra,
quem está errado — a regra ou a pessoa? Ver [1.9 - Lançamento de Imóvel pelos Assistentes].

Revision ID: 20260811_foco_auditoria
Revises: 20260811_link_documentos
Create Date: 2026-08-11
"""
import sqlalchemy as sa
from alembic import op

revision = "20260811_foco_auditoria"
down_revision = "20260811_link_documentos"
branch_labels = None
depends_on = None

COLUNAS = [
    # 'manual' = escolhido no formulário; 'regra' = classificado automaticamente.
    ("foco_origem", sa.String(length=10)),
    ("foco_pp_sugerido", sa.Boolean()),
    ("foco_ac_sugerido", sa.Boolean()),
]


def upgrade():
    for nome, tipo in COLUNAS:
        op.add_column("fato_captacao", sa.Column(nome, tipo, nullable=True))


def downgrade():
    for nome, _ in reversed(COLUNAS):
        op.drop_column("fato_captacao", nome)
