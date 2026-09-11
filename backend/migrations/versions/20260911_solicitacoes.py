"""Solicitacoes operacionais, historico e anexos privados."""
from alembic import op
import sqlalchemy as sa
revision = "20260911_solicitacoes"
down_revision = "20260908_proposta_previsao"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("solicitacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("chave_cliente", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("trello_id", sa.String(64), unique=True),
        sa.Column("trello_url", sa.Text()), sa.Column("lista_nome", sa.String(255)),
        *[sa.Column(n, sa.DateTime(), nullable=n != "criado_em") for n in
          ("criado_em", "integrado_em", "concluido_em", "enviado_em", "sincronizado_em")],
        sa.Column("erro", sa.Text()), sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("resultado", sa.JSON()), sa.UniqueConstraint("usuario_id", "chave_cliente"))
    op.create_index("ix_solicitacoes_usuario_id", "solicitacoes", ["usuario_id"])
    op.create_index("ix_solicitacoes_status", "solicitacoes", ["status"])
    op.create_table("solicitacao_anexos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solicitacao_id", sa.Integer(), sa.ForeignKey("solicitacoes.id"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False), sa.Column("trello_id", sa.String(64)))
    op.create_index("ix_solicitacao_anexos_solicitacao_id", "solicitacao_anexos", ["solicitacao_id"])
    op.create_table("solicitacao_eventos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solicitacao_id", sa.Integer(), sa.ForeignKey("solicitacoes.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False), sa.Column("descricao", sa.Text(), nullable=False))
    op.create_index("ix_solicitacao_eventos_solicitacao_id", "solicitacao_eventos", ["solicitacao_id"])

def downgrade():
    op.drop_table("solicitacao_eventos")
    op.drop_table("solicitacao_anexos")
    op.drop_table("solicitacoes")
