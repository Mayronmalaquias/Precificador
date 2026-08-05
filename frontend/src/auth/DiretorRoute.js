import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function DiretorRoute({ children }) {
  const { isLogado, isDiretor } = useAuth();

  if (!isLogado) return <Navigate to="/login" replace />;
  if (!isDiretor) return <Navigate to="/" replace />;

  return children;
}

export default DiretorRoute;
