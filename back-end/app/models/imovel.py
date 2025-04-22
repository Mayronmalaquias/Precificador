from app.__init__ import db

class Imovel(db.Model):
    __tablename__ = "imoveis"

    codigo = db.Column(db.String(50), primary_key=True)
    anunciante = db.Column(db.String(100))
    oferta = db.Column(db.String(20))
    tipo = db.Column(db.String(50))
    area_util = db.Column(db.Numeric)
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    preco = db.Column(db.Numeric)
    valor_m2 = db.Column(db.Numeric)
    quartos = db.Column(db.String(10))
    vagas = db.Column(db.String(10))
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)

    def __repr__(self):
        return f"<Imovel {self.codigo} - {self.bairro}>"
    

class ImovelVenda(Imovel):
    __tablename__ = "imoveis_venda"
    
    # Adiciona qualquer campo específico para imóveis de venda
    cluster = db.Column(db.Integer)  # Coluna 'cluster' para armazenar o cluster dos imóveis de venda

    def __repr__(self):
        return f"<ImovelVenda {self.codigo} - {self.bairro} - Cluster {self.cluster}>"

class ImovelAluguel(Imovel):
    __tablename__ = "imoveis_aluguel"

    # Adiciona qualquer campo específico para imóveis de aluguel
    cluster = db.Column(db.Integer)  # Coluna 'cluster' para armazenar o cluster dos imóveis de aluguel

    def __repr__(self):
        return f"<ImovelAluguel {self.codigo} - {self.bairro} - Cluster {self.cluster}>"