const chatInput = document.querySelector(".chat-input textarea");
const sendChatBtn = document.querySelector("#send-btn");
const chatbox = document.querySelector(".chatbox");
const chatbotToggler = document.querySelector(".chatbot-toggler");
const chatbotCloseBtn = document.querySelector(".close-btn");
const chatbotContainer = document.querySelector(".snow-chatbot"); // Adicionado para manipular a classe corretamente

let userMessage;
const API_KEY = ""; // Insira sua chave da API
const inputInitHeight = chatInput.scrollHeight;

// Alternar visibilidade do chatbot
chatbotToggler.addEventListener("click", () => {
    chatbotContainer.classList.toggle("snow-chatbot");
});

// Fechar chatbot ao clicar no botão de fechar
chatbotCloseBtn.addEventListener("click", () => {
    chatbotContainer.classList.remove("snow-chatbot");
});

// Fechar chatbot ao clicar fora dele
document.addEventListener("click", (event) => {
    if (!chatbotContainer.contains(event.target) && !chatbotToggler.contains(event.target)) {
        chatbotContainer.classList.remove("snow-chatbot");
    }
});

// Criar um novo item na lista de chat
const createChatLi = (message, className) => {
    const chatLi = document.createElement("li");
    chatLi.classList.add("chat", className);
    
    let chatContent = className === "outgoing" 
        ? `<p>${message}</p>` 
        : `<span class="material-symbols-outlined">smart_toy</span><p>${message}</p>`;

    chatLi.innerHTML = chatContent;
    chatbox.appendChild(chatLi);
    chatbox.scrollTop = chatbox.scrollHeight; // Rolagem automática para a última mensagem
    return chatLi;
};

// Gerar resposta da API OpenAI
const generateResponse = (incomingChatLi) => {
    const API_URL = "https://api.openai.com/v1/chat/completions";
    const messageElement = incomingChatLi.querySelector("p");

    const requestOptions = {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${API_KEY}`
        },
        body: JSON.stringify({
            model: "gpt-3.5-turbo",
            messages: [{ role: "user", content: userMessage }]
        })
    };

    fetch(API_URL, requestOptions)
        .then(res => res.json())
        .then(data => {
            if (data.choices && data.choices.length > 0) {
                messageElement.textContent = data.choices[0].message.content;
            } else {
                messageElement.textContent = "Erro ao obter resposta.";
            }
        })
        .catch(() => {
            messageElement.classList.add("error");
            messageElement.textContent = "Ops! Algo deu errado.";
        })
        .finally(() => chatbox.scrollTo(0, chatbox.scrollHeight));
};

// Função para enviar mensagem
const handleChat = () => {
    userMessage = chatInput.value.trim(); // Obtém o valor digitado
    if (!userMessage) return; // Verifica se está vazio
    chatInput.value = "";
    chatInput.style.height = `${inputInitHeight}px`;

    createChatLi(userMessage, "outgoing"); // Cria e exibe a mensagem do usuário

    setTimeout(() => {
        const incomingChatLi = createChatLi("Pensando...", "incoming");
        generateResponse(incomingChatLi);
    }, 600);
};

// Ajusta a altura do campo de entrada conforme o usuário digita
chatInput.addEventListener("input", () => {
    chatInput.style.height = `${inputInitHeight}px`;
    chatInput.style.height = `${chatInput.scrollHeight}px`;
});

// Permite envio ao pressionar Enter
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && window.innerWidth > 800) {
        e.preventDefault();
        handleChat();
    }
});

// Evento de clique no botão de envio
sendChatBtn.addEventListener("click", handleChat);
