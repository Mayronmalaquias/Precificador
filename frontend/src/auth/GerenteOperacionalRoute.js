import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function GerenteOperacionalRoute({ children }) {
  const { isLogado, permissao, isAdministrador } = useAuth();
  const permitido = permissao === 'gerente' || isAdministrador;
  if (!isLogado) return <Navigate to="/login" replace />;
  if (!permitido) return <Navigate to="/" replace />;
  return children;
}

export default GerenteOperacionalRoute;
