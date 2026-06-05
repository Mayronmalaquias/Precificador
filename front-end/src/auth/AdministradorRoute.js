import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function AdministradorRoute({ children }) {
  const { isLogado, isAdministrador } = useAuth();

  if (!isLogado) return <Navigate to="/login" replace />;
  if (!isAdministrador) return <Navigate to="/" replace />;

  return children;
}

export default AdministradorRoute;
