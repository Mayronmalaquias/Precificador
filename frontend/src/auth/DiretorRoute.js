import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Diretor/administrativo veem todas as equipes; gerente entra na mesma tela, mas o
// back-end tranca o escopo na equipe dele (ver diretor_dashboard_routes._escopo).
function DiretorRoute({ children }) {
  const { isLogado, isDiretor, permissao } = useAuth();

  if (!isLogado) return <Navigate to="/login" replace />;
  if (!isDiretor && permissao !== 'gerente') return <Navigate to="/" replace />;

  return children;
}

export default DiretorRoute;
