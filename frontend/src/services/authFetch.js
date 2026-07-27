/**
 * Interceptor global de fetch.
 *
 * Injeta os headers de autenticacao em TODA chamada para a API (`/api/v1`),
 * cobrindo tanto o cliente central (`services/api.js`) quanto os ~68 `fetch()`
 * crus espalhados nos componentes. Instalado UMA vez no `index.js`, antes de
 * renderizar o App.
 *
 * Regra do back (auth_middleware): basta X-API-KEY valida OU Bearer JWT.
 * - X-API-KEY: sempre (autoriza a aplicacao web).
 * - Authorization: Bearer <jwt> se houver token salvo no login.
 *
 * Nao mexe em Content-Type nem no body -> uploads multipart (FormData) seguem
 * intactos.
 */
const API_KEY = process.env.REACT_APP_API_KEY || '';
const API_MARK = '/api/v1';

const originalFetch = window.fetch.bind(window);

function urlOf(input) {
  if (typeof input === 'string') return input;
  if (typeof Request !== 'undefined' && input instanceof Request) return input.url;
  if (typeof URL !== 'undefined' && input instanceof URL) return input.href;
  return String(input || '');
}

function getToken() {
  try {
    return localStorage.getItem('auth_token');
  } catch {
    return null;
  }
}

window.fetch = (input, init = {}) => {
  const url = urlOf(input);
  if (!url.includes(API_MARK)) return originalFetch(input, init);

  // Preserva headers do init e de um eventual Request passado como input.
  const fromRequest =
    typeof Request !== 'undefined' && input instanceof Request ? input.headers : undefined;
  const headers = new Headers((init && init.headers) || fromRequest);

  if (API_KEY) headers.set('X-API-KEY', API_KEY);
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  return originalFetch(input, { ...init, headers });
};
