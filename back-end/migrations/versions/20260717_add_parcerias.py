"""Add parcerias (parcerias da 61 com imobiliarias) + seed do PDF.

Revision ID: 20260717_parcerias
Revises: 20260702_captacao_snapshot
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_parcerias"
down_revision = "20260702_captacao_snapshot"
branch_labels = None
depends_on = None


# (nome, percentual|None, tem_contrato)  -> faz_parceria = percentual is not None
_SEED = [
    ("Agropar", "50/50", False, None),
    ("Alpha Brasilia", "35/65", False, None),
    ("Alvaro Júnior", "50/50", False, None),
    ("Ana Junqueira Imoveis (16001)", "50/50", False, None),
    ("Anderson Moraes", "50/50", False, None),
    ("Aucinelio (61 9513-2929) (Histórico Negativo)", None, False, None),
    ("Beira-Mar", "50/50", False, None),
    ("Bekari Imóveis", "30% Captador 50/50", False, None),
    ("Bilhion Elegui Imoveis", None, False, None),
    ("Bordalo Imob", "40/60", False, "Reciprocidade, última negociação com eles fechou em 40/60"),
    ("Bordalo Prime", "50/50", False, None),
    ("Brasilis", "50/50", True, None),
    ("Bravo Imob", None, False, None),
    ("Bruno Linhares", None, False, None),
    ("Carlos Alberto (61 8462-5435)", None, False, None),
    ("Clodoaldo Orefice (25021 CJ)", None, False, None),
    ("COEMI", "50/50", False, None),
    ("Comigo Imóveis", "30/70", False, None),
    ("Corretor Francisco Chagas", None, False, None),
    ("Daleprane", "50/50", False, None),
    ("Daniela Conde", "50/50", False, None),
    ("Denali Imobiliária", "50/50", True, None),
    ("Digito Imoveis (61 98197-4627) (26648 CJ)", None, False, None),
    ("Elenio dos Santos Pires (Histórico Negativo)", None, False, None),
    ("Exito", None, False, None),
    ("Farias Imóveis", "50/50", True, None),
    ("Felipe Goes", None, False, None),
    ("Fence", "50/50", True, None),
    ("Ferola", "50/50", False, None),
    ("Forti Imobi", None, False, None),
    ("Gilberto Danzmann (61 8181-6688)", "30/70", False, None),
    ("GM", "50/50", False, None),
    ("Imob Estrela", None, False, None),
    ("Imobiliaria Mude", "35/65", False, None),
    ("J Ribeiro Imoveis", None, False, None),
    ("JBR", "66,67/33", False, None),
    ("Jribeiro Imoveis", None, False, None),
    ("Juliana Oliveíra/ Fábio de Almeida (61 9214-0881)", None, False, "HISTÓRICO NEGATIVO"),
    ("Kontá Imóveis", "35/65", False, None),
    ("KR Real State", None, False, "HISTÓRICO NEGATIVO"),
    ("Kubi Imóveis", None, False, "HISTÓRICO NEGATIVO"),
    ("KZABSB", "50/50", True, None),
    ("Legacy Real State", "35/65", False, None),
    ("Luciano Corretor (61 9981-6080) (Histórico Negativo)", None, False, None),
    ("Luxury House", None, False, "HISTÓRICO NEGATIVO"),
    ("Manu", "50/50", False, None),
    ("Marco Antônio (61 9 85224444)", None, False, None),
    ("Margareth Correa", "50/50", False, None),
    ("Mário Lúcio", "50/50", False, None),
    ("Markus Ferreira", "30% Captador 50/50", False, None),
    ("Moni", "50/50", False, None),
    ("Myhouse", None, False, None),
    ("Navarro Imobiliária", "50/50", True, None),
    ("ORJ imóveis", None, False, None),
    ("Oswaldo Corretor (8156-3351) (Histórico Negativo)", None, False, None),
    ("Pauliane Soares (61 9926-3194) (Histórico Negativo)", None, False, None),
    ("Penisula Imóveis", "50/50", False, None),
    ("Perazzo Imóveis", None, False, "HISTÓRICO NEGATIVO"),
    ("Petrus Imob", "25/75", False, None),
    ("Pilotis", "35/65", False, None),
    ("Pires Netimoveis", "50/50", False, None),
    ("Precisa", "35/65", False, None),
    ("PRISCILLA BATISTA ALVARO", None, False, "HISTÓRICO NEGATIVO"),
    ("Private Broker (61983331111)", "40/60", False, None),
    ("Quadra Imob", "35/65", False, None),
    ("R Sul", "50/50", False, None),
    ("RBM Imobiliária", "50/50", False, None),
    ("RD&S Imóveis Creci 24663", None, False, None),
    ("Rede Brasília", "50/50", False, None),
    ("REMAX - Todas", "50/50", False, None),
    ("Renova Imob", "50/50", False, None),
    ("RJR", "50/50", False, None),
    ("Rogerbras", "50/50", False, None),
    ("Sacra", "50/50", False, None),
    ("Salermo", "62,5/37,5", False, None),
    ("Salerno Imob", "50/50", True, None),
    ("Sanchez DF4 Imóveis", "50/50", False, None),
    ("Sartori Imob", "50/50", False, None),
    ("Smile", "50/50", False, None),
    ("SOMA Imóveis", "50/50", False, None),
    ("Sonia", "50/50", False, None),
    ("Tau Imóveis", "50/50", True, None),
    ("Thais Imobiliária", "50/50", False, None),
    ("TRK", "50/50", False, None),
    ("Unique Imob", "50/50", False, None),
    ("Urbana", "50/50", False, None),
    ("Yani", "50/50", False, None),
]


def upgrade():
    parcerias = op.create_table(
        "parcerias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("percentual", sa.String(length=120), nullable=True),
        sa.Column("faz_parceria", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("tem_contrato", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome", name="uq_parcerias_nome"),
    )
    op.create_index("ix_parcerias_nome", "parcerias", ["nome"])

    op.bulk_insert(
        parcerias,
        [
            {
                "nome": nome,
                "percentual": percentual,
                "faz_parceria": percentual is not None,
                "tem_contrato": tem_contrato,
                "observacao": obs,
            }
            for (nome, percentual, tem_contrato, obs) in _SEED
        ],
    )


def downgrade():
    op.drop_index("ix_parcerias_nome", table_name="parcerias")
    op.drop_table("parcerias")
