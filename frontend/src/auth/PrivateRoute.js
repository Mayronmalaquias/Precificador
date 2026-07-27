import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const PrivateRoute = ({ children }) => {
  const { isLogado } = useAuth();
  return isLogado ? children : <Navigate to="/login" />;
};

export default PrivateRoute;
