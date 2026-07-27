"""Equipes DB-driven: coluna ativo, seed das equipes, migra PRIME(G61003) -> SENNA(G61015).

Revision ID: 20260721_equipes_db
Revises: 20260717_parcerias
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_equipes_db"
down_revision = "20260717_parcerias"
branch_labels = None
depends_on = None


PRIME_ID = "G61003"
SENNA_ID = "G61015"

# Fonte da verdade das equipes (id_equipe, nome). Espelha o antigo EQUIPES_MAP hardcoded.
_SEED = [
    ("G61001", "AGEF"),
    ("G61002", "AGUIA"),
    ("G61003", "PRIME"),
    ("G61010", "LOTUS"),
    ("G61014", "NOVA UNIÃO"),
    ("G61015", "SENNA"),
    ("G61016", "LIDER"),
    ("administrativo", "ADMINISTRATIVO"),
]


def _equipes_table():
    return sa.table(
        "equipes",
        sa.column("id_equipe", sa.String),
        sa.column("nome", sa.String),
        sa.column("email", sa.String),
        sa.column("ativo", sa.Boolean),
    )


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1) Garante a tabela equipes e a coluna ativo (a tabela pode não existir ainda).
    if "equipes" not in tables:
        op.create_table(
            "equipes",
            sa.Column("id_equipe", sa.String(length=50), primary_key=True),
            sa.Column("nome", sa.String(length=100), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        )
    else:
        cols = [c["name"] for c in insp.get_columns("equipes")]
        if "ativo" not in cols:
            op.add_column(
                "equipes",
                sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
            )

    equipes = _equipes_table()

    # 2) Upsert do seed (mantém e-mails existentes; só garante nome/ativo).
    for id_equipe, nome in _SEED:
        existe = bind.execute(
            sa.select(equipes.c.id_equipe).where(equipes.c.id_equipe == id_equipe)
        ).first()
        if existe:
            bind.execute(
                equipes.update().where(equipes.c.id_equipe == id_equipe).values(nome=nome)
            )
        else:
            bind.execute(
                equipes.insert().values(id_equipe=id_equipe, nome=nome, ativo=True)
            )

    # 3) Migra usuários da PRIME para a SENNA.
    bind.execute(
        sa.text("UPDATE usuarios SET team = :senna WHERE team = :prime"),
        {"senna": SENNA_ID, "prime": PRIME_ID},
    )

    # 4) PRIME deixa de existir (soft-delete: some das listas, preserva histórico).
    bind.execute(
        equipes.update().where(equipes.c.id_equipe == PRIME_ID).values(ativo=False)
    )


def downgrade():
    # Reativa a PRIME; NÃO reverte a mudança de equipe dos usuários (dado perdido na migração).
    bind = op.get_bind()
    equipes = _equipes_table()
    bind.execute(equipes.update().where(equipes.c.id_equipe == PRIME_ID).values(ativo=True))
    with op.batch_alter_table("equipes") as batch:
        batch.drop_column("ativo")
