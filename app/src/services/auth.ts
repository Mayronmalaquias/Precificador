import { api, setAuthToken } from '@/services/api';
import { storage } from '@/services/storage';

const TOKEN_KEY = 'app61.token';

/** Objeto de usuário retornado por `_usuario_to_dict` no back-end (campos variáveis). */
export type AppUser = {
  id_usuarios?: string;
  id_corretor?: string;
  nome?: string;
  name?: string;
  nomeCorretor?: string;
  usuario?: string;
  username?: string;
  permissao?: string;
  team?: string;
  [key: string]: unknown;
};

type LoginResponse = {
  login: boolean;
  message?: string;
  user?: AppUser;
  token?: string;
};

/**
 * POST /auth/login — contrato real:
 *  200 { login: true, user }  |  401 { error }  |  403 { error } (aguardando RH).
 * Erros HTTP viram ApiError (tratado na tela).
 */
export async function loginRequest(username: string, password: string): Promise<AppUser> {
  const data = await api.post<LoginResponse>('/auth/login', { username, password });
  if (!data?.login || !data.user) {
    throw new Error(data?.message || 'Usuário ou senha incorretos.');
  }
  await guardarToken(data.token ?? null); // anexa o Bearer JWT nas chamadas seguintes
  return data.user;
}

/** Injeta o JWT nas chamadas e grava no storage seguro. */
async function guardarToken(token: string | null): Promise<void> {
  setAuthToken(token);
  if (token) await storage.setItem(TOKEN_KEY, token);
  else await storage.removeItem(TOKEN_KEY);
}

/**
 * Reinjeta o JWT salvo no boot.
 *
 * A sessão (`app61.user`) já era reidratada, mas o token não: ao reabrir o app
 * o usuário voltava "logado" e todas as chamadas saíam só com a X-API-KEY.
 * Isso passa no middleware (a regra é "X-API-KEY OU Bearer"), mas o back-end
 * fica sem saber QUEM chamou — as rotas novas leem `g.jwt_payload.sub` para
 * resolver o escopo.
 */
export async function restaurarToken(): Promise<void> {
  try {
    setAuthToken(await storage.getItem(TOKEN_KEY));
  } catch {
    setAuthToken(null); // storage indisponível — segue só com a X-API-KEY
  }
}

/** Descarta o JWT (logout). */
export async function limparToken(): Promise<void> {
  await guardarToken(null);
}
