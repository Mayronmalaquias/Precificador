from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Date
from app.models.base import Base


class Imovel(Base):
    __tablename__ = "imoveis"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50))
    link = Column(String(500))
    data_coleta = Column(Date)
    anunciante = Column(String(100))
    creci = Column(String(50))
    oferta = Column(String(30))
    tipo = Column(String(50))
    area_util = Column(Integer)
    bairro = Column(String(100))
    cidade = Column(String(100))
    preco = Column(Integer)
    valor_m2 = Column(Integer)
    quartos = Column(Integer)
    vagas = Column(Integer)
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    quadra = Column(String(100))
    portal = Column(String(50))

    __mapper_args__ = {
        "polymorphic_identity": "imovel"
        # "polymorphic_on": tipo_imovel
    }


class ImovelVenda(Base):
    __tablename__ = "imoveis_venda"
    
    id = Column(Integer, ForeignKey("imoveis.id"), primary_key=True)
    cluster = Column(Integer)

    __mapper_args__ = {
        "polymorphic_identity": "venda",
    }


class ImovelAluguel(Base):
    __tablename__ = "imoveis_aluguel"
    
    id = Column(Integer, ForeignKey("imoveis.id"), primary_key=True)
    cluster = Column(Integer)

