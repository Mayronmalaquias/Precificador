-- vw_vendas — leitura de vendas 2015 -> hoje a partir da base UNICA `contratos`.
-- Apos importar o pre-2024 (fonte='legado_pre2024') para contratos, esta view le
-- SO de contratos (nao usa mais vendas_legado -> evita duplicar). vendas_legado fica
-- como arquivo bruto. Resolve pessoa (nome) -> usuarios.id_usuarios via pessoa_alias.

CREATE OR REPLACE VIEW vw_vendas AS
SELECT
  c.fonte                             AS fonte,
  c.id_contrato,
  c.data_contrato                     AS data_venda,
  NULL::date                          AS data_captacao,
  c.bairro,
  c.tipo,
  c.codigo_imovel,
  c.valor_negocio::text               AS valor_negocio,
  c.valor_comissao::text              AS valor_comissao,
  c.corretor_venda_1_nome             AS vendedor_ref,
  rv.id_usuarios                      AS vendedor_id,
  c.corretor_captador_1_nome          AS captador_ref,
  rc.id_usuarios                      AS captador_id,
  c.gerente_venda_nome                AS gerente_venda_ref,
  rgv.id_usuarios                     AS gerente_venda_id,
  c.gerente_captacao_nome             AS gerente_captacao_ref,
  rgc.id_usuarios                     AS gerente_captacao_id,
  c.diretor_nome                      AS diretor_ref,
  rd.id_usuarios                      AS diretor_id
FROM contratos c
LEFT JOIN pessoa_alias rv  ON rv.alias_key  = lower(trim(c.corretor_venda_1_nome))
LEFT JOIN pessoa_alias rc  ON rc.alias_key  = lower(trim(c.corretor_captador_1_nome))
LEFT JOIN pessoa_alias rgv ON rgv.alias_key = lower(trim(c.gerente_venda_nome))
LEFT JOIN pessoa_alias rgc ON rgc.alias_key = lower(trim(c.gerente_captacao_nome))
LEFT JOIN pessoa_alias rd  ON rd.alias_key  = lower(trim(c.diretor_nome));
