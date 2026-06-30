"""Refaz a tabela canonica `vendas` a partir de `contratos` (base unica 2015->hoje).

INSERT...SELECT unico (rapido) - resolve pessoa nome->id_usuarios via pessoa_alias e
pega o nome canonico de usuarios. valores ja sao numericos em contratos. Re-executavel.
"""

from sqlalchemy import text

from app.database import engine

SQL = """
TRUNCATE TABLE vendas RESTART IDENTITY;

INSERT INTO vendas (
  fonte, id_contrato, data_venda, data_captacao, bairro, tipo, codigo_imovel,
  valor_negocio, valor_comissao,
  vendedor_nome, vendedor_id, captador_nome, captador_id,
  gerente_venda_nome, gerente_venda_id, gerente_captacao_nome, gerente_captacao_id,
  diretor_nome, diretor_id
)
SELECT
  c.fonte, c.id_contrato, c.data_contrato, NULL::date, c.bairro, c.tipo, c.codigo_imovel,
  c.valor_negocio, c.valor_comissao,
  COALESCE(uv.nome,  c.corretor_venda_1_nome),     rv.id_usuarios,
  COALESCE(uc.nome,  c.corretor_captador_1_nome),  rc.id_usuarios,
  COALESCE(ugv.nome, c.gerente_venda_nome),        rgv.id_usuarios,
  COALESCE(ugc.nome, c.gerente_captacao_nome),     rgc.id_usuarios,
  COALESCE(ud.nome,  c.diretor_nome),              rd.id_usuarios
FROM contratos c
LEFT JOIN pessoa_alias rv  ON rv.alias_key  = lower(trim(c.corretor_venda_1_nome))
LEFT JOIN usuarios     uv  ON uv.id_usuarios = rv.id_usuarios
LEFT JOIN pessoa_alias rc  ON rc.alias_key  = lower(trim(c.corretor_captador_1_nome))
LEFT JOIN usuarios     uc  ON uc.id_usuarios = rc.id_usuarios
LEFT JOIN pessoa_alias rgv ON rgv.alias_key = lower(trim(c.gerente_venda_nome))
LEFT JOIN usuarios     ugv ON ugv.id_usuarios = rgv.id_usuarios
LEFT JOIN pessoa_alias rgc ON rgc.alias_key = lower(trim(c.gerente_captacao_nome))
LEFT JOIN usuarios     ugc ON ugc.id_usuarios = rgc.id_usuarios
LEFT JOIN pessoa_alias rd  ON rd.alias_key  = lower(trim(c.diretor_nome))
LEFT JOIN usuarios     ud  ON ud.id_usuarios = rd.id_usuarios;
"""


def main():
    with engine.begin() as c:
        c.exec_driver_sql(SQL)
    with engine.connect() as c:
        n = c.execute(text("SELECT count(*) FROM vendas")).scalar()
    print(f"vendas repopulada: {n} linhas")


if __name__ == "__main__":
    main()
