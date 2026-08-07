import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Propostas efetivas: gerente e administrativo lançam/editam; diretor e assistente
// (perfil usado pelo estagiário) acompanham em leitura. O back-end é quem decide de
// fato quem edita — ver proposta_service.escopo_do_solicitante.
function PropostasRoute({ children }) {
  const { isLogado, isDiretor, isAdministrativo, isAssistente, permissao } = useAuth();

  if (!isLogado) return <Navigate to="/login" replace />;
  const permitido = isDiretor || isAdministrativo || isAssistente || permissao === 'gerente';
  if (!permitido) return <Navigate to="/" replace />;

  return children;
}

export default PropostasRoute;
