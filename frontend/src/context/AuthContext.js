import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const AuthContext = createContext(null);

function loadUserData() {
  try {
    return JSON.parse(localStorage.getItem('userData') || '{}');
  } catch {
    return {};
  }
}

export function AuthProvider({ children }) {
  const [isLogado, setIsLogado] = useState(() => localStorage.getItem('auth') === 'true');
  const [userData, setUserData] = useState(loadUserData);

  const login = useCallback((user, token) => {
    localStorage.setItem('auth', 'true');
    localStorage.setItem('userData', JSON.stringify(user));
    if (token) localStorage.setItem('auth_token', token); // JWT p/ o interceptor
    setIsLogado(true);
    setUserData(user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth');
    localStorage.removeItem('userData');
    localStorage.removeItem('auth_token');
    setIsLogado(false);
    setUserData({});
  }, []);

  const permissao = useMemo(() => userData.permissao || '', [userData]);
  const equipe = useMemo(() => String(userData.team || '').toLowerCase(), [userData]);
  const isAdministrativo = useMemo(() => permissao === 'administrativo' || equipe === 'administrativo', [permissao, equipe]);

  // Hierarquia: corretor < gerente < administrador < diretor
  const isGerente      = useMemo(() => ['gerente', 'administrador', 'diretor'].includes(permissao), [permissao]);
  const isAdministrador = useMemo(() => ['administrador', 'diretor'].includes(permissao) || isAdministrativo, [permissao, isAdministrativo]);
  const isDiretor      = useMemo(() => permissao === 'diretor', [permissao]);
  const isAssistente   = useMemo(() => permissao === 'assistente', [permissao]);

  // Mantém isAdmin como alias de isGerente para compatibilidade interna
  const isAdmin = isGerente;

  const nomeUsuario = useMemo(
    () => userData.nome || userData.name || userData.nomeCorretor || userData.usuario || 'Usuário',
    [userData]
  );

  const idCorretor = useMemo(
    () => userData.id_usuarios || userData.id_corretor || 'Não informado',
    [userData]
  );

  const value = useMemo(
    () => ({ isLogado, userData, permissao, isAdmin, isGerente, isAdministrador, isDiretor, isAssistente, isAdministrativo, nomeUsuario, idCorretor, login, logout }),
    [isLogado, userData, permissao, isAdmin, isGerente, isAdministrador, isDiretor, isAssistente, isAdministrativo, nomeUsuario, idCorretor, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider');
  return ctx;
}
