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
import { ehAbort } from '@/utils/erro';

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

async function request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
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
  } catch (err) {
    clearTimeout(timer);
    if (ehAbort(err)) {
      throw new ApiError('Tempo de conexão esgotado. Tente novamente.', 0, null);
    }
    throw new ApiError('Sem conexão com o servidor.', 0, null);
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  const data = text ? safeJson(text) : null;

  if (!response.ok) {
    const message = mensagemDaResposta(data) ?? `Erro na requisição (${response.status})`;
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

/**
 * POST multipart (upload de arquivo).
 *
 * Não passa por `request` porque o corpo é `FormData`: o Content-Type precisa
 * ser definido pelo runtime (que anexa o `boundary`), então ele NÃO é enviado
 * aqui. Os headers de auth continuam obrigatórios — a API é fechada e devolve
 * 401 em qualquer chamada sem `X-API-KEY` ou `Bearer`.
 */
export async function postForm<T = unknown>(
  path: string,
  form: FormData,
  timeoutMs = 60000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method: 'POST',
      signal: controller.signal,
      headers: authHeaders(),
      body: form,
    });
  } catch (err) {
    if (ehAbort(err)) {
      throw new ApiError('Tempo de conexão esgotado. Tente novamente.', 0, null);
    }
    throw new ApiError('Sem conexão com o servidor.', 0, null);
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  const data = text ? safeJson(text) : null;

  if (!response.ok) {
    const message = mensagemDaResposta(data) ?? `Erro no upload (${response.status})`;
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

/** `error` ou `message` do corpo, quando o corpo for um objeto com um deles em texto. */
function mensagemDaResposta(data: unknown): string | null {
  if (typeof data !== 'object' || data === null) return null;
  const corpo = data as { error?: unknown; message?: unknown };
  const texto = corpo.error ?? corpo.message;
  return typeof texto === 'string' && texto ? texto : null;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    // Resposta que nao e JSON (HTML de erro do nginx, texto puro) vira mensagem.
    return { message: text };
  }
}

export const api = {
  get: <T = unknown>(path: string) => request<T>(path),
  post: <T = unknown>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T = unknown>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  del: <T = unknown>(path: string) => request<T>(path, { method: 'DELETE' }),
};
