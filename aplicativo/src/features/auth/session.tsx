import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { loginRequest, type AppUser } from '@/services/auth';
import { storage } from '@/services/storage';

const USER_KEY = 'app61.user';

type SessionContextValue = {
  user: AppUser | null;
  isAuthenticated: boolean;
  isLoading: boolean; // true enquanto lê o storage no boot
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;

  // Flags de hierarquia (espelha front-end/src/context/AuthContext.js)
  permissao: string;
  nomeUsuario: string;
  idCorretor: string;
  isGerente: boolean;
  isAdministrador: boolean;
  isDiretor: boolean;
  isAdministrativo: boolean;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Reidrata a sessão persistida no boot.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const raw = await storage.getItem(USER_KEY);
        if (alive && raw) setUser(JSON.parse(raw));
      } catch {
        // storage corrompido — segue deslogado
      } finally {
        if (alive) setIsLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const loggedUser = await loginRequest(username, password);
    await storage.setItem(USER_KEY, JSON.stringify(loggedUser));
    setUser(loggedUser);
  }, []);

  const signOut = useCallback(async () => {
    await storage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const derived = useMemo(() => {
    const permissao = String(user?.permissao || '');
    const equipe = String(user?.team || '').toLowerCase();
    const isAdministrativo = permissao === 'administrativo' || equipe === 'administrativo';

    // Hierarquia: corretor < gerente < administrador < diretor
    const isGerente = ['gerente', 'administrador', 'diretor'].includes(permissao);
    const isAdministrador =
      ['administrador', 'diretor'].includes(permissao) || isAdministrativo;
    const isDiretor = permissao === 'diretor';

    const nomeUsuario =
      user?.nome || user?.name || user?.nomeCorretor || user?.usuario || 'Usuário';
    const idCorretor = user?.id_usuarios || user?.id_corretor || 'Não informado';

    return {
      permissao,
      isAdministrativo,
      isGerente,
      isAdministrador,
      isDiretor,
      nomeUsuario: String(nomeUsuario),
      idCorretor: String(idCorretor),
    };
  }, [user]);

  const value = useMemo<SessionContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      signIn,
      signOut,
      ...derived,
    }),
    [user, isLoading, signIn, signOut, derived],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession deve ser usado dentro de <SessionProvider>');
  return ctx;
}
