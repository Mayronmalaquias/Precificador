import { api } from '@/services/api';

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
  return data.user;
}
