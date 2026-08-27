"""Captadores do imóvel no catálogo, vindos da API do Imoview.

Descoberta de 27/08/2026: `POST /Imovel/RetornarImoveis` aceita **`exibircaptadores`**.
Sem a flag o campo `captadores` volta `[]` — e era por isso que se acreditava que a API
não informava o captador, e que `fato_estoque` só podia ser alimentado por upload de
planilha exportada à mão.

Com a flag, a cobertura é **100%**: numa amostra de 160 imóveis, nenhum sem captador.
Pelo caminho antigo (`fato_captacao`) só 53% dos imóveis do catálogo tinham captador
conhecido.

Vem também o **`percentual`**, que é o rateio oficial entre co-captadores. E ele nem
sempre é meio a meio: no imóvel 10911 o captador marcado como "principal" tem 0% e o
outro tem 100%. Guardar o percentual evita a suposição de `1/n`, que estaria errada
justamente nos casos que motivaram a conferência do fechamento.

Três colunas de cada porque a API devolveu no máximo 3 captadores por imóvel na amostra,
e é a mesma forma que `fato_estoque` já usa — os consumidores existentes leem
`captador1/2/3`.

Revision ID: 20260827_area_capt
Revises: 20260826_regulariza_acomp
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_area_capt"
down_revision = "20260826_regulariza_acomp"
branch_labels = None
depends_on = None

COLUNAS = (
    # Nome como o Imoview devolve. A tradução para o id interno (`C61xxx`) é feita na
    # leitura, com o mesmo mapa que a importação de planilha usa — guardar o nome cru
    # mantém rastreável de onde veio quando o mapa falhar.
    ("captador1", sa.Text()),
    ("captador2", sa.Text()),
    ("captador3", sa.Text()),
    ("percentual1", sa.Numeric(5, 2)),
    ("percentual2", sa.Numeric(5, 2)),
    ("percentual3", sa.Numeric(5, 2)),
    # Quem o CRM marca como principal. Não é quem tem o maior percentual — ver o caso do
    # 10911 no cabeçalho.
    ("captador_principal", sa.Text()),
)


def upgrade():
    for nome, tipo in COLUNAS:
        op.add_column("imovel_area", sa.Column(nome, tipo, nullable=True))
    op.create_index("ix_imovel_area_captador1", "imovel_area", ["captador1"])


def downgrade():
    op.drop_index("ix_imovel_area_captador1", table_name="imovel_area")
    for nome, _ in reversed(COLUNAS):
        op.drop_column("imovel_area", nome)
