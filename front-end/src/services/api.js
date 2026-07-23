const API_PREFIX = '/api/v1';

function normalizeBaseUrl(value) {
  const clean = (value || '').replace(/\/+$/, '');
  if (!clean) return API_PREFIX;
  if (clean.endsWith('/api/v1')) return clean;
  if (clean.endsWith('/api')) return `${clean}/v1`;
  return `${clean}${API_PREFIX}`;
}

export const BASE = normalizeBaseUrl(process.env.REACT_APP_API_URL);

// Auth (X-API-KEY / Bearer) e injetada globalmente pelo interceptor em
// `services/authFetch.js` (instalado no index.js). Aqui so o Content-Type.
async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
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
