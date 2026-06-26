-- vw_pessoa_nao_resolvida — refs de pessoa em vw_vendas que NAO casaram em pessoa_alias.
-- Ferramenta p/ fechar o de-para: mostra a chave, ocorrencias, e um id sugerido
-- (usuario cujo nome contem a ref). Preencher com:
--   INSERT INTO pessoa_alias (alias_key, id_usuarios, origem)
--   VALUES (lower(trim('Lorrane')), 'C61xxx', 'manual');
CREATE OR REPLACE VIEW vw_pessoa_nao_resolvida AS
WITH refs AS (
  SELECT vendedor_ref          AS ref FROM vw_vendas WHERE vendedor_id          IS NULL AND coalesce(trim(vendedor_ref),'')          <> ''
  UNION ALL SELECT captador_ref            FROM vw_vendas WHERE captador_id           IS NULL AND coalesce(trim(captador_ref),'')           <> ''
  UNION ALL SELECT gerente_venda_ref       FROM vw_vendas WHERE gerente_venda_id      IS NULL AND coalesce(trim(gerente_venda_ref),'')      <> ''
  UNION ALL SELECT gerente_captacao_ref    FROM vw_vendas WHERE gerente_captacao_id   IS NULL AND coalesce(trim(gerente_captacao_ref),'')   <> ''
  UNION ALL SELECT diretor_ref             FROM vw_vendas WHERE diretor_id            IS NULL AND coalesce(trim(diretor_ref),'')            <> ''
),
agg AS (
  SELECT lower(trim(ref)) AS alias_key, max(ref) AS exemplo, count(*) AS ocorrencias
  FROM refs GROUP BY 1
)
SELECT
  a.alias_key,
  a.exemplo,
  a.ocorrencias,
  (SELECT min(u.id_usuarios) FROM usuarios u
     WHERE coalesce(trim(u.id_usuarios),'') <> '' AND lower(u.nome) LIKE '%' || a.alias_key || '%') AS sugestao_id,
  (SELECT count(DISTINCT u.id_usuarios) FROM usuarios u
     WHERE coalesce(trim(u.id_usuarios),'') <> '' AND lower(u.nome) LIKE '%' || a.alias_key || '%') AS qtd_candidatos
FROM agg a
ORDER BY a.ocorrencias DESC;
