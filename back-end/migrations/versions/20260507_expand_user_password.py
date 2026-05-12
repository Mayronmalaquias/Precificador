"""Expand user password hash column.

Revision ID: 20260507_expand_user_password
Revises:
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_expand_user_password"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "usuarios",
        "password",
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "usuarios",
        "password",
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
