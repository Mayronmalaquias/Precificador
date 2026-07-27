-- vw_usuarios_duplicados — relatorio read-only p/ destravar UNIQUE em usuarios.id_usuarios.
-- Mostra cada id_usuarios repetido com as linhas (usuarios.id), nome, team, permissao,
-- ativo, desligado. Use p/ decidir merges (NAO apaga nada).
CREATE OR REPLACE VIEW vw_usuarios_duplicados AS
SELECT u.id_usuarios, u.id, u.nome, u.team, u.permissao, u.ativo, u.desligado
FROM usuarios u
JOIN (
  SELECT id_usuarios
  FROM usuarios
  WHERE coalesce(trim(id_usuarios),'') <> ''
  GROUP BY id_usuarios
  HAVING count(*) > 1
) d ON d.id_usuarios = u.id_usuarios
ORDER BY u.id_usuarios, u.id;
