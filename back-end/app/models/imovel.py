from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app.models.base import Base

# Conexão com o banco
engine = create_engine('postgresql://postgres:1234@localhost:5432/database', echo=True)


class Imovel(Base):
    __tablename__ = "imoveis"
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50))
    anunciante = Column(String(100))
    oferta = Column(String(20))
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
    tipo_imovel = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity': 'imovel',
        'polymorphic_on': tipo_imovel
    }

class ImovelVenda(Imovel):
    __tablename__ = "imoveis_venda"
    
    id = Column(Integer, ForeignKey("imoveis.id"), primary_key=True)
    cluster = Column(Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'venda'
    }

class ImovelAluguel(Imovel):
    __tablename__ = "imoveis_aluguel"
    
    id = Column(Integer, ForeignKey("imoveis.id"), primary_key=True)
    cluster = Column(Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'aluguel'
    }

# Cria as tabelas
print("Criando tabelas...")
Base.metadata.create_all(engine)
print("Tabelas criadas com sucesso.")
