"""Add HR profile fields to usuarios.

Revision ID: 20260625_usuario_rh
Revises: 20260624_drop_eventos_antigas
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_usuario_rh"
down_revision = "20260624_drop_eventos_antigas"
branch_labels = None
depends_on = None


_COLUMNS = [
    sa.Column("status", sa.String(length=30), nullable=True),
    sa.Column("unidade", sa.String(length=100), nullable=True),
    sa.Column("gerente_responsavel", sa.String(length=100), nullable=True),
    sa.Column("data_entrada_61", sa.Date(), nullable=True),
    sa.Column("creci", sa.String(length=50), nullable=True),
    sa.Column("validade_creci", sa.Date(), nullable=True),
    sa.Column("telefone_pessoal", sa.String(length=30), nullable=True),
    sa.Column("telefone_corporativo", sa.String(length=30), nullable=True),
    sa.Column("email_pessoal", sa.String(length=255), nullable=True),
    sa.Column("email_corporativo", sa.String(length=255), nullable=True),
    sa.Column("data_nascimento", sa.Date(), nullable=True),
    sa.Column("estado_civil", sa.String(length=50), nullable=True),
    sa.Column("possui_filhos", sa.Boolean(), nullable=True),
    sa.Column("endereco", sa.Text(), nullable=True),
    sa.Column("contato_emergencia", sa.Text(), nullable=True),
    sa.Column("cpf", sa.String(length=20), nullable=True),
    sa.Column("rg", sa.String(length=30), nullable=True),
    sa.Column("cnpj", sa.String(length=30), nullable=True),
    sa.Column("razao_social", sa.String(length=255), nullable=True),
    sa.Column("banco", sa.String(length=100), nullable=True),
    sa.Column("agencia", sa.String(length=30), nullable=True),
    sa.Column("conta", sa.String(length=50), nullable=True),
    sa.Column("tipo_conta", sa.String(length=30), nullable=True),
    sa.Column("chave_pix", sa.String(length=255), nullable=True),
    sa.Column("contrato_assinado", sa.Boolean(), nullable=True),
    sa.Column("codigo_conduta_assinado", sa.Boolean(), nullable=True),
    sa.Column("lgpd_assinada", sa.Boolean(), nullable=True),
    sa.Column("onboarding_realizado", sa.Boolean(), nullable=True),
    sa.Column("data_desligamento", sa.Date(), nullable=True),
    sa.Column("observacoes", sa.Text(), nullable=True),
]


def upgrade():
    for column in _COLUMNS:
        op.add_column("usuarios", column)
    op.create_index("ix_usuarios_status", "usuarios", ["status"], unique=False)
    op.create_index("ix_usuarios_unidade", "usuarios", ["unidade"], unique=False)
    op.create_index("ix_usuarios_gerente_responsavel", "usuarios", ["gerente_responsavel"], unique=False)
    op.create_index("ix_usuarios_cpf", "usuarios", ["cpf"], unique=False)


def downgrade():
    op.drop_index("ix_usuarios_cpf", table_name="usuarios")
    op.drop_index("ix_usuarios_gerente_responsavel", table_name="usuarios")
    op.drop_index("ix_usuarios_unidade", table_name="usuarios")
    op.drop_index("ix_usuarios_status", table_name="usuarios")
    for column in reversed(_COLUMNS):
        op.drop_column("usuarios", column.name)
