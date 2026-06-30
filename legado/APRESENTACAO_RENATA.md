# Apresentação — Renata: Assistente Virtual da 61 Imóveis

> Documento preparado para apresentação aos gerentes  
> Data: Maio de 2026

---

## 1. O que é a Renata?

A **Renata** é uma assistente virtual inteligente desenvolvida especificamente para a 61 Imóveis. Ela funciona como uma atendente disponível 24h por dia, 7 dias por semana, diretamente no site público da imobiliária.

Ela é alimentada pelo modelo de linguagem **Claude Sonnet** (desenvolvido pela Anthropic), um dos modelos de IA mais avançados do mercado — o mesmo tipo de tecnologia por trás de ferramentas como o ChatGPT, porém da empresa concorrente Anthropic.

A Renata não é uma IA genérica: ela foi treinada com um **contexto específico da 61 Imóveis** e só responde sobre temas relacionados ao mercado imobiliário de Brasília/DF.

---

## 2. Como ela funciona?

O fluxo de uma conversa é o seguinte:

```
Cliente digita uma mensagem
        ↓
Mensagem enviada para o servidor da 61 Imóveis
        ↓
Servidor consulta o modelo de IA com o contexto e histórico
        ↓
IA decide qual ferramenta usar (busca, precificação ou dicas)
        ↓
Ferramenta consulta o banco de dados real de imóveis
        ↓
IA monta a resposta com os dados reais
        ↓
Resposta exibida para o cliente no chat
```

**Ela mantém o histórico da conversa** durante a sessão do usuário, ou seja, se o cliente disse "quero 2 quartos" no início, ela lembra disso nas perguntas seguintes. Esse histórico é apagado ao fechar o navegador.

---

## 3. O que a Renata tem acesso?

A Renata acessa **diretamente o banco de dados da plataforma** em tempo real. Os dados disponíveis para ela são:

| Dado | Descrição |
|------|-----------|
| Imóveis à venda | Apartamentos, casas, comerciais, etc. dos últimos 12 meses |
| Imóveis para aluguel | Incluindo temporada |
| Preços de mercado | Valor/m² por bairro e tipo de imóvel |
| Links dos anúncios | Link direto para o portal (ex: DFImóveis) |
| Dados dos imóveis | Quartos, vagas, área útil, bairro, quadra, anunciante |
| Análises de mercado | Agrupamentos estatísticos para precificação |

**Bairros cobertos:** Asa Sul, Asa Norte, Noroeste, Sudoeste, Lago Norte, Lago Sul, Águas Claras — e demais regiões cadastradas no banco.

**Os dados têm no máximo 365 dias** — ela nunca mostra imóveis desatualizados.

---

## 4. O que a Renata pode responder?

A Renata tem **3 capacidades principais**:

---

### 4.1 Buscar Imóveis Disponíveis

**Quando usar:** O cliente quer ver opções de imóveis para comprar ou alugar.

**Exemplo de perguntas que ela responde:**
- "Tem apartamento de 2 quartos no Sudoeste para alugar?"
- "Quero comprar uma casa no Lago Norte até R$ 800.000"
- "Mostre imóveis para temporada na Asa Sul"

**O que ela retorna:**
- Lista de até 5 imóveis compatíveis
- Tipo, bairro, quartos, vagas, área e preço
- **Link direto para o anúncio no portal**

---

### 4.2 Precificar um Imóvel

**Quando usar:** O cliente (ou proprietário) quer saber quanto vale um imóvel.

**Exemplo de perguntas que ela responde:**
- "Quanto vale um apartamento de 3 quartos no Noroeste?"
- "Qual o valor de mercado de uma casa de 200m² no Lago Sul?"
- "Quero alugar meu apto na Asa Norte — qual o preço justo?"

**O que ela retorna:**
- Valor médio por m² na região
- Estimativa total do imóvel
- Tamanho da amostra usada na análise (transparência dos dados)
- Indicadores de confiança conforme disponibilidade de dados

---

### 4.3 Dicas para Anunciar um Imóvel

**Quando usar:** O proprietário quer saber como anunciar melhor o imóvel dele.

**Exemplo de perguntas que ela responde:**
- "Como devo anunciar meu apartamento para vender mais rápido?"
- "Que informações são mais importantes no anúncio?"
- "Qual o perfil dos imóveis mais procurados no Sudoeste?"

**O que ela retorna:**
- Dados reais de mercado (preço médio, metragem mais comum)
- Número de quartos mais procurado na região
- % de imóveis com vaga de garagem no bairro
- Recomendações específicas baseadas em dados reais

---

## 5. O que a Renata NÃO faz

É importante alinhar com a equipe as limitações da ferramenta:

| Limitação | Explicação |
|-----------|------------|
| Não agenda visitas | Apenas informa — não tem acesso à agenda dos corretores |
| Não processa pagamentos | Não há integração com sistemas financeiros |
| Não cria nem edita anúncios | Acesso somente leitura ao banco de dados |
| Não responde sobre outros temas | Fora do contexto imobiliário, ela redireciona educadamente |
| Não guarda histórico entre sessões | Ao fechar o navegador, o histórico é perdido |
| Não dá consultoria jurídica ou fiscal | Está fora do escopo definido |
| Não acessa dados de clientes cadastrados | Não tem vínculo com o CRM ou autenticação |

---

## 6. Segurança e Privacidade

- A Renata **não coleta dados pessoais** dos clientes durante o chat
- As mensagens são processadas em tempo real e não são armazenadas de forma permanente
- O histórico de conversa existe apenas **na memória temporária da sessão**
- O banco de dados consultado contém apenas **dados de imóveis públicos** (já anunciados nos portais)
- A chave de acesso ao modelo de IA (Anthropic) é gerenciada com segurança no servidor

---

## 7. Mudanças Visuais do Site

Junto com a Renata, foram realizadas atualizações visuais modernas no widget de chat:

### Botão Flutuante
- Posicionado no **canto inferior direito** da tela
- **64x64px** com gradiente roxo (identidade visual da 61)
- Efeito de **pulso animado** para chamar atenção do usuário
- Exibe o avatar da Renata (silhueta feminina) quando fechado
- Transforma no ícone de "X" quando aberto

### Janela do Chat
- Dimensões: **380x560px** (desktop) / **tela cheia** (mobile)
- Bordas arredondadas com **sombra suave**
- Animação de abertura com **efeito de mola** (bouncy)
- Header com **gradiente roxo** e avatar da Renata com moldura circular

### Balões de Mensagem
- **Mensagens da Renata:** fundo branco, borda esquerda roxa, sombra leve
- **Mensagens do cliente:** gradiente roxo, texto branco
- Formato de "bolha" com cantos arredondados assimétricos
- Largura máxima de 82% do chat

### Indicador de Digitação
- 3 pontos roxos **animados** enquanto a Renata "pensa"
- Animação em cascata (cada ponto sobe em sequência)

### Campo de Texto
- Fundo levemente roxo (`#f8f6ff`)
- Borda que muda de cor ao focar (feedback visual)
- Botão de envio circular com gradiente roxo
- Se expande automaticamente com textos longos

### Responsividade Mobile
- Abaixo de 490px de largura: chat ocupa **tela inteira**
- Botão de fechar aparece no header no mobile
- Fontes e espaçamentos otimizados para toque

### Paleta de Cores Utilizada
| Elemento | Cor |
|----------|-----|
| Principal | `#724ae8` (roxo médio) |
| Escuro | `#5a35c8` (roxo escuro) |
| Claro | `#9b6ef5` (roxo claro) |
| Fundo chat | `#f5f3ff` (roxo muito claro) |
| Texto | `#2d2d2d` (cinza escuro) |
| Online | `#4ade80` (verde) |

---

## 8. Resumo Executivo

| Item | Detalhe |
|------|---------|
| **Tecnologia** | Claude Sonnet (Anthropic) — LLM de ponta |
| **Disponibilidade** | 24/7 no site público |
| **Dados em tempo real** | Sim — consulta o banco da plataforma |
| **Idioma** | Português brasileiro |
| **Capacidades** | Busca de imóveis, precificação e dicas de anúncio |
| **Limitações** | Somente imobiliário, somente leitura, sem agenda |
| **Privacidade** | Sem coleta de dados pessoais |
| **Visual** | Widget moderno, animado, responsivo e na identidade da 61 |

---

*Documento interno — 61 Imóveis | Tecnologia & Inovação*
