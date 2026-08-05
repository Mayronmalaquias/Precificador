import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Página operacional: assistentes, administradores e administrativo. Diretor não acessa.
function AssistenteRoute({ children }) {
  const { isLogado, isAssistente, isAdministrador } = useAuth();

  if (!isLogado) return <Navigate to="/login" replace />;
  if (!isAssistente && !isAdministrador) return <Navigate to="/" replace />;

  return children;
}

export default AssistenteRoute;
