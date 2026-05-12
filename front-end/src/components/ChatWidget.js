import React, { useState, useRef, useEffect } from 'react';
import '../assets/css/chat.css';
import { BASE } from '../services/api';

const SESSION_KEY = '61imoveis_chat_session';

function getSessionId() {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/* Silhueta feminina usada no header e no avatar das mensagens */
function WomanSilhouette() {
  return (
    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="50" fill="url(#sofiaGrad)" />
      {/* Cabelo fundo (longo, atrás dos ombros) */}
      <path
        d="M26 50 Q18 30 28 16 Q40 5 60 8 Q74 14 76 30 Q80 52 72 74 Q64 82 56 82"
        fill="rgba(255,255,255,0.35)"
      />
      {/* Cabeça */}
      <ellipse cx="50" cy="34" rx="14" ry="16" fill="white" />
      {/* Cabelo topo / franja */}
      <path
        d="M36 32 Q34 13 50 13 Q66 13 64 32 Q68 20 62 14 Q50 7 38 14 Q31 20 36 32Z"
        fill="white"
      />
      {/* Pescoço */}
      <rect x="45" y="48" width="10" height="9" rx="3" fill="white" />
      {/* Ombros e busto */}
      <path
        d="M12 100 Q14 76 27 67 Q36 62 50 62 Q64 62 73 67 Q86 76 88 100Z"
        fill="white"
      />
      <defs>
        <linearGradient id="sofiaGrad" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4a28b0" />
          <stop offset="100%" stopColor="#9b6ef5" />
        </linearGradient>
      </defs>
    </svg>
  );
}

/* Avatar mini nas mensagens do bot */
function BotAvatarSmall() {
  return (
    <div className="chat-avatar-sm">
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="50" fill="url(#sofiaGradSm)" />
        <path d="M26 50 Q18 30 28 16 Q40 5 60 8 Q74 14 76 30 Q80 52 72 74 Q64 82 56 82"
          fill="rgba(255,255,255,0.35)" />
        <ellipse cx="50" cy="34" rx="14" ry="16" fill="white" />
        <path d="M36 32 Q34 13 50 13 Q66 13 64 32 Q68 20 62 14 Q50 7 38 14 Q31 20 36 32Z"
          fill="white" />
        <rect x="45" y="48" width="10" height="9" rx="3" fill="white" />
        <path d="M12 100 Q14 76 27 67 Q36 62 50 62 Q64 62 73 67 Q86 76 88 100Z"
          fill="white" />
        <defs>
          <linearGradient id="sofiaGradSm" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#4a28b0" />
            <stop offset="100%" stopColor="#9b6ef5" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: 'Olá! Sou a Renata, assistente virtual da 61 Imóveis 😊\n\nPosso te ajudar a:\n• Encontrar imóveis disponíveis\n• Avaliar o valor de um imóvel\n• Dicas de como anunciar\n\nComo posso te ajudar?'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatboxRef = useRef(null);

  useEffect(() => {
    if (chatboxRef.current) {
      chatboxRef.current.scrollTop = chatboxRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages(prev => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: getSessionId() })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || 'Erro ao contatar a IA');

      setMessages(prev => [...prev, { role: 'bot', text: data.resposta }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'bot',
        text: 'Desculpe, tive um problema para responder. Tente novamente em instantes.',
        error: true
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function formatText(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = text.split(urlRegex);
    return parts.map((part, i) =>
      urlRegex.test(part)
        ? <a key={i} href={part} target="_blank" rel="noopener noreferrer">{part}</a>
        : <span key={i}>{part}</span>
    );
  }

  return (
    <div className={open ? 'snow-chatbot' : ''}>
      {/* Botão flutuante */}
      <button
        className="chatbot-toggler"
        onClick={() => setOpen(o => !o)}
        aria-label={open ? 'Fechar chat' : 'Falar com a Renata'}
        title="Falar com a Renata"
      >
        <span className="material-symbols-rounded toggler-close">close</span>
        <span className="toggler-avatar-wrap">
          <WomanSilhouette />
        </span>
      </button>

      {/* Janela do chat */}
      <div className="chatbot">
        {/* Header */}
        <div className="chatbot-header">
          <span
            className="material-symbols-rounded chatbot-header-close"
            onClick={() => setOpen(false)}
          >
            close
          </span>

          <div className="chatbot-avatar-ring">
            <WomanSilhouette />
          </div>

          <div className="chatbot-header-info">
            <strong>Renata</strong>
            <div className="chatbot-header-status">
              <span className="chatbot-status-dot" />
              Online · 61 Imóveis
            </div>
          </div>
        </div>

        {/* Mensagens */}
        <ul className="chatbox" ref={chatboxRef}>
          {messages.map((msg, idx) => (
            <li key={idx} className={`chat ${msg.role === 'user' ? 'outgoing' : 'incoming'}`}>
              {msg.role === 'bot' && <BotAvatarSmall />}
              <p className={msg.error ? 'error' : ''}>
                {formatText(msg.text)}
              </p>
            </li>
          ))}

          {loading && (
            <li className="chat incoming">
              <BotAvatarSmall />
              <div className="typing-indicator">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </li>
          )}
        </ul>

        {/* Input */}
        <div className="chat-input">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Digite sua mensagem..."
            rows={1}
          />
          <button
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            aria-label="Enviar"
          >
            <span className="material-symbols-rounded">send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
