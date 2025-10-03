# 🚀 Projeto Front-End com Docker e React

Este projeto utiliza **React** no front-end e Docker para empacotar e servir a aplicação de forma otimizada com o pacote `serve`.

---

## 🧱 Estrutura do Dockerfile

O `Dockerfile` possui dois estágios:

1. **Build Stage**: Constrói a aplicação com Node.js (React).
2. **Serve Stage**: Usa uma imagem leve (`node:18-slim`) para servir os arquivos estáticos com o `serve`.

---

## ✅ Pré-requisitos

Antes de executar o projeto, certifique-se de ter:

- [Node.js](https://nodejs.org/) instalado (apenas para rodar localmente sem Docker)
- [Docker](https://www.docker.com/) instalado (para rodar via contêiner)
- Git (opcional)

---

## 🧪 Como Rodar o Projeto Localmente (sem Docker)

Se quiser rodar o projeto diretamente com o Node.js:

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/seu-repo.git
cd seu-repo

# Instale as dependências
npm install

# Rode o projeto em ambiente de desenvolvimento
npm start
