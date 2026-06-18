from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class ClienteAcao(Base):
    __tablename__ = "cliente_acao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(String(100), nullable=False, index=True)
    id_corretor = Column(String(50), nullable=True, index=True)
    criado_por = Column(String(50), nullable=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    data_acao = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="a_fazer", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
