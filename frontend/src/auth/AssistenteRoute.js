import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Página de lançamento de imóvel: só assistentes (+ administrador/diretor, que supervisionam).
function AssistenteRoute({ children }) {
  const { isLogado, isAssistente, isAdministrador } = useAuth();

  if (!isLogado) return <Navigate to="/login" replace />;
  if (!isAssistente && !isAdministrador) return <Navigate to="/" replace />;

  return children;
}

export default AssistenteRoute;
