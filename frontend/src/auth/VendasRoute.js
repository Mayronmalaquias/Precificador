import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function VendasRoute({ children }) {
  const { isLogado, isAdministrador, isDiretor } = useAuth();
  if (!isLogado) return <Navigate to="/login" replace />;
  if (!isAdministrador && !isDiretor) return <Navigate to="/" replace />;
  return children;
}

export default VendasRoute;
