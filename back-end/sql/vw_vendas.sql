-- vw_vendas — leitura unificada de vendas 2015 -> hoje (Etapa B do MAPA_BANCO.md)
-- NAO altera dados. Une contratos (2024+) + vendas_legado (<2024) = serie continua.
-- Resolucao pessoa -> usuarios.id_usuarios via tabela de-para pessoa_alias
-- (cobre id C61xxx E nome livre; aliases 'manual' fecham nomes soltos sem mexer na view).

CREATE OR REPLACE VIEW vw_vendas AS
SELECT
  'contrato'::text                    AS fonte,
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
LEFT JOIN pessoa_alias rd  ON rd.alias_key  = lower(trim(c.diretor_nome))

UNION ALL

SELECT
  'legado'::text                      AS fonte,
  v.idcontrato                        AS id_contrato,
  v.data_venda,
  v.data_captacao,
  v.bairro,
  v.tipo,
  NULL::text                          AS codigo_imovel,
  v.valor_do_negocio                  AS valor_negocio,
  v.valor_comissao,
  v.vendedor_1                        AS vendedor_ref,
  rv.id_usuarios                      AS vendedor_id,
  v.captador_1                        AS captador_ref,
  rc.id_usuarios                      AS captador_id,
  v.gerente_de_venda1                 AS gerente_venda_ref,
  rgv.id_usuarios                     AS gerente_venda_id,
  v.gerente_de_captacao_1             AS gerente_captacao_ref,
  rgc.id_usuarios                     AS gerente_captacao_id,
  NULL::text                          AS diretor_ref,
  NULL::text                          AS diretor_id
FROM vendas_legado v
LEFT JOIN pessoa_alias rv  ON rv.alias_key  = lower(trim(v.vendedor_1))
LEFT JOIN pessoa_alias rc  ON rc.alias_key  = lower(trim(v.captador_1))
LEFT JOIN pessoa_alias rgv ON rgv.alias_key = lower(trim(v.gerente_de_venda1))
LEFT JOIN pessoa_alias rgc ON rgc.alias_key = lower(trim(v.gerente_de_captacao_1))
WHERE v.data_venda < DATE '2024-01-01';
