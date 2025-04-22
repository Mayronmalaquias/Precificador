# Utiliza uma imagem do Python como base
FROM python:3.9-slim

# Defina o diretório de trabalho no container
WORKDIR /app

# Copia o arquivo de requerimentos e instala as dependências
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos do projeto para o diretório de trabalho
COPY . .

# Define a variável de ambiente para indicar ao Flask que está em modo produção
ENV FLASK_ENV=production

# Expõe a porta que o Flask irá rodar
EXPOSE 5000

# Define o comando padrão para rodar a aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "240", "run:app"]
