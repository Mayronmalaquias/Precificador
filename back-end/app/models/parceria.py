from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class Parceria(Base):
    """Parcerias da 61 com outras imobiliárias/corretores.

    - percentual: texto livre da divisão ("50/50", "35/65", "30% Captador 50/50"...)
    - faz_parceria: False quando a imobiliária não faz parceria
    - tem_contrato: se há contrato de parceria assinado (o "check" da planilha)
    - observacao: notas (ex: histórico negativo, reciprocidade)
    """

    __tablename__ = "parcerias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False, unique=True, index=True)
    percentual = Column(String(120), nullable=True)
    faz_parceria = Column(Boolean, nullable=False, server_default="1")
    tem_contrato = Column(Boolean, nullable=False, server_default="0")
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=True)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "percentual": self.percentual,
            "faz_parceria": bool(self.faz_parceria),
            "tem_contrato": bool(self.tem_contrato),
            "observacao": self.observacao,
        }
