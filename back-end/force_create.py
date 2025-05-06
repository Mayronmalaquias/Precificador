# arquivo: force_create.py
from app import create_app, db
from app.models.imovel import Imovel, ImovelVenda, ImovelAluguel

app = create_app()

with app.app_context():
    print("Criando as tabelas...")
    db.drop_all()
    db.create_all()
    print("Tabelas criadas com sucesso!")

print(f"Banco conectado: {app.config['SQLALCHEMY_DATABASE_URI']}")