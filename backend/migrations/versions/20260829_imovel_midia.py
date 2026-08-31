"""Fotos e anexos do imovel, vindos de `/Imovel/RetornarImoveis`.

Contagem de fotos e a lista de nomes dos anexos. Guardado no catalogo, e nao lido ao vivo
a cada abertura, porque o filtro da tela ("so imoveis sem foto") precisa varrer o recorte
inteiro — nao daria para perguntar isso a API imovel por imovel.

`anexos` exige a flag **`exibiranexos=true`**. Sem ela o imovel devolve `quantidadeanexos`
correto e `anexos: []` — o mesmo desenho do `exibircaptadores`, que fez o captador ficar
dois meses tido como "a API nao informa". Medido em 29/08/2026 no imovel 5051: 19 anexos
com a flag, zero sem ela.

**Guarda so o NOME, nunca a URL.** As URLs de anexo do Imoview
(`app.imoview.com.br/url/short/...`) abrem sem autenticacao nenhuma: quem tem o link le a
ficha cadastral e as certidoes do proprietario. Nao gravar a URL e o que impede que uma
tela nossa vire um distribuidor desses links por engano.

Revision ID: 20260829_imovel_midia
Revises: 20260829_imovel_portal
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260829_imovel_midia"
down_revision = "20260829_imovel_portal"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("imovel_area", sa.Column("qtd_fotos", sa.Integer(), nullable=True))
    op.add_column("imovel_area", sa.Column("qtd_anexos", sa.Integer(), nullable=True))
    # [{"nome": "ONUS.pdf", "visibilidade": "Publico"}, ...]. JSONB e nao tabela porque
    # o nome so e exibido: nao ha agregacao por anexo, nem busca dentro deles.
    op.add_column("imovel_area",
                  sa.Column("anexos_nomes", postgresql.JSONB(), nullable=True))
    op.add_column("imovel_area", sa.Column("tem_video", sa.Boolean(), nullable=True))
    op.add_column("imovel_area", sa.Column("midia_em", sa.DateTime(), nullable=True))
    # Os dois filtros da tela sao "tem ou nao tem": indice em cada contagem cobre.
    op.create_index("ix_imovel_area_qtd_fotos", "imovel_area", ["qtd_fotos"])
    op.create_index("ix_imovel_area_qtd_anexos", "imovel_area", ["qtd_anexos"])


def downgrade():
    op.drop_index("ix_imovel_area_qtd_anexos", table_name="imovel_area")
    op.drop_index("ix_imovel_area_qtd_fotos", table_name="imovel_area")
    for c in ("midia_em", "tem_video", "anexos_nomes", "qtd_anexos", "qtd_fotos"):
        op.drop_column("imovel_area", c)
