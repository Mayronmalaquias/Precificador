"""De-para canonico pessoa -> usuarios.id_usuarios (Etapa A do MAPA_BANCO.md).

Resolve qualquer 'ref' (um id_usuarios C61xxx OU um nome livre como 'Lorrane')
para o id_usuarios canonico. Usado pelas views unificadas (vw_vendas) e, no futuro,
pela escrita normalizada. Linhas 'auto_*' sao semeadas de usuarios; 'manual' sao
preenchidas a mao para fechar nomes soltos/placeholders que o seed nao casa.

Obs: id_usuarios NAO tem FK aqui porque usuarios.id_usuarios ainda nao e UNIQUE
(ha duplicatas a resolver antes - ver vw_usuarios_duplicados).
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class PessoaAlias(Base):
    __tablename__ = "pessoa_alias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_key = Column(String(255), nullable=False, unique=True, index=True)  # lower(trim(ref))
    id_usuarios = Column(String(50), nullable=False, index=True)
    origem = Column(String(20), nullable=True)  # auto_id | auto_nome | manual
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=True)
