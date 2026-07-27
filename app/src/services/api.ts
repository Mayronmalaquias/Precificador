/**
 * Cliente HTTP do app. Espelha a semântica de `front-end/src/services/api.js`:
 * - prefixo `/api/v1`
 * - base configurável (aqui via EXPO_PUBLIC_API_URL, inlinado no build — docs Expo v57)
 * - erro de negócio vem em `data.error` / `data.message`
 *
 * Auth: a API exige `X-API-KEY` (chave estática da aplicação, inlinada no build
 * via EXPO_PUBLIC_API_KEY) em toda chamada. Após o login, um JWT pode ser
 * anexado como `Authorization: Bearer <token>` via `setAuthToken()`.
 */
const API_PREFIX = '/api/v1';

function normalizeBaseUrl(value?: string): string {
  const clean = (value || '').replace(/\/+$/, '');
  if (!clean) return API_PREFIX;
  if (clean.endsWith('/api/v1')) return clean;
  if (clean.endsWith('/api')) return `${clean}/v1`;
  return `${clean}${API_PREFIX}`;
}

// EXPO_PUBLIC_* precisa de acesso estático por dot notation (docs Expo v57).
export const BASE = normalizeBaseUrl(process.env.EXPO_PUBLIC_API_URL);

// Chave estática da aplicação (X-API-KEY), inlinada no bundle no build.
const API_KEY = process.env.EXPO_PUBLIC_API_KEY ?? '';

// JWT do usuário (opcional). O login chama setAuthToken(resp.token).
let authToken: string | null = null;
export function setAuthToken(token: string | null): void {
  authToken = token;
}
export function getAuthToken(): string | null {
  return authToken;
}

// Headers de autorização injetados em TODA chamada.
function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (API_KEY) headers['X-API-KEY'] = API_KEY;
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  return headers;
}

if (!process.env.EXPO_PUBLIC_API_URL && __DEV__) {
  console.warn(
    '[api] EXPO_PUBLIC_API_URL não definida — usando path relativo. ' +
      'Em dispositivo físico, defina no .env o IP da LAN (ex.: http://192.168.0.10:5000).',
  );
}

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(message: string, status: number, data: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & { body?: unknown; timeoutMs?: number };

async function request<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, timeoutMs = 20000, headers, ...rest } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...headers },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      ...rest,
    });
  } catch (err: any) {
    clearTimeout(timer);
    if (err?.name === 'AbortError') {
      throw new ApiError('Tempo de conexão esgotado. Tente novamente.', 0, null);
    }
    throw new ApiError('Sem conexão com o servidor.', 0, null);
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  const data = text ? safeJson(text) : null;

  if (!response.ok) {
    const message =
      (data && (data.error || data.message)) || `Erro na requisição (${response.status})`;
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return { message: text };
  }
}

export const api = {
  get: <T = any>(path: string) => request<T>(path),
  post: <T = any>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T = any>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  del: <T = any>(path: string) => request<T>(path, { method: 'DELETE' }),
};
