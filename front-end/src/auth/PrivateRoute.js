// src/auth/PrivateRoute.js
import React from 'react';
import { Navigate } from 'react-router-dom';

const PrivateRoute = ({ children }) => {
  const autenticado = localStorage.getItem('auth') === 'true';
  return autenticado ? children : <Navigate to="/login" />;
};

export default PrivateRoute;
