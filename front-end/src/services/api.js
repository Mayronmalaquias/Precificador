const API_PREFIX = '/api/v1';

function normalizeBaseUrl(value) {
  const clean = (value || '').replace(/\/+$/, '');
  if (!clean) return API_PREFIX;
  if (clean.endsWith('/api/v1')) return clean;
  if (clean.endsWith('/api')) return `${clean}/v1`;
  return `${clean}${API_PREFIX}`;
}

export const BASE = normalizeBaseUrl(process.env.REACT_APP_API_URL);

// Chave estatica da aplicacao (X-API-KEY), inlinada no build pelo CRA.
const API_KEY = process.env.REACT_APP_API_KEY || '';

// Monta os headers de autorizacao injetados em TODA chamada:
// - X-API-KEY: sempre (autoriza a aplicacao web na API).
// - Authorization: Bearer <jwt> se houver token salvo no login.
function authHeaders() {
  const headers = {};
  if (API_KEY) headers['X-API-KEY'] = API_KEY;
  try {
    const token = localStorage.getItem('auth_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
  } catch (_) {
    // localStorage indisponivel (SSR/modo restrito) -> segue so com X-API-KEY.
  }
  return headers;
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...options.headers,
    },
    ...options,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || data.message || 'Erro na requisicao');
  }

  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
};
