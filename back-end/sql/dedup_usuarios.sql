-- dedup_usuarios — resolve id_usuarios duplicados antes do UNIQUE (Etapa A).
-- SEGURO: backup completo antes; merge SO de duplicata mesma-pessoa; colisao real
-- (ADM002 = Tauane E Anna) vira SPLIT (Anna ganha codigo novo, ninguem some).
-- Reversivel via usuarios_dup_backup.

-- 1) backup de todas as linhas com id_usuarios duplicado
CREATE TABLE IF NOT EXISTS usuarios_dup_backup AS
SELECT u.*, now() AS backup_em
FROM usuarios u
WHERE u.id_usuarios IN (
  SELECT id_usuarios FROM usuarios
  WHERE coalesce(trim(id_usuarios),'') <> ''
  GROUP BY id_usuarios HAVING count(*) > 1
);

-- 2) SPLIT da colisao real: Anna (id=447) sai de ADM002 -> ADM004 (Tauane fica ADM002)
UPDATE usuarios SET id_usuarios = 'ADM004'
WHERE id = 447 AND id_usuarios = 'ADM002' AND nome = 'Anna';

-- 3) merge das duplicatas mesma-pessoa: mantem canonico (ativo desc, id desc), apaga resto
DELETE FROM usuarios
WHERE id IN (
  SELECT id FROM (
    SELECT id, row_number() OVER (
      PARTITION BY id_usuarios ORDER BY ativo DESC NULLS LAST, id DESC
    ) AS rn
    FROM usuarios
    WHERE id_usuarios IN (
      SELECT id_usuarios FROM usuarios
      WHERE coalesce(trim(id_usuarios),'') <> ''
      GROUP BY id_usuarios HAVING count(*) > 1
    )
  ) z WHERE rn > 1
);
