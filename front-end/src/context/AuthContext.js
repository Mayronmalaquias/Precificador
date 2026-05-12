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

  const login = useCallback((user) => {
    localStorage.setItem('auth', 'true');
    localStorage.setItem('userData', JSON.stringify(user));
    setIsLogado(true);
    setUserData(user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth');
    localStorage.removeItem('userData');
    setIsLogado(false);
    setUserData({});
  }, []);

  const isAdmin = useMemo(
    () => userData.grant === 'admin' || userData.permissao === 'admin',
    [userData]
  );

  const nomeUsuario = useMemo(
    () => userData.nome || userData.name || userData.nomeCorretor || userData.usuario || 'Usuário',
    [userData]
  );

  const idCorretor = useMemo(
    () => userData.id_usuarios || userData.id_corretor || 'Não informado',
    [userData]
  );

  const value = useMemo(
    () => ({ isLogado, userData, isAdmin, nomeUsuario, idCorretor, login, logout }),
    [isLogado, userData, isAdmin, nomeUsuario, idCorretor, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider');
  return ctx;
}
