from app import create_app

# Cria a aplicação Flask usando a função de fábrica
app = create_app()

if __name__ == '__main__':
    # Rodar a aplicação em modo de desenvolvimento
    app.run(debug=True)
