import React from 'react';
import { Navigate } from 'react-router-dom';

function AdminRoute({ children }) {
  const isLogado = localStorage.getItem('auth') === 'true';
  const userData = JSON.parse(localStorage.getItem('userData') || '{}');
  const isAdmin = userData.grant === 'admin' || userData.permissao === 'admin';

  if (!isLogado) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default AdminRoute;