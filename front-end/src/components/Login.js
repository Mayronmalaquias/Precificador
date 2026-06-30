import React, { useState } from 'react';
import PasswordInput from './PasswordInput';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';

function Login() {
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');

  const navigate = useNavigate();
  const { login, isLogado } = useAuth();
  const toast = useToast();

  if (isLogado) return <Navigate to="/" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setErro('');
    setLoading(true);

    try {
      const data = await api.post('/auth/login', { username, password: senha });

      if (data.login === true) {
        login(data.user || {});
        navigate('/');
      } else {
        setErro(data.error || 'Credenciais inválidas.');
      }
    } catch (error) {
      setErro(error.message || 'Erro de conexão com o servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ds-auth-wrapper">
      <div className="ds-auth-card">
        <span className="ds-auth-accent" />
        <h2 className="ds-auth-title">Entrar</h2>
        <p className="ds-auth-subtitle">Acesse sua conta para continuar</p>

        <form className="ds-form" onSubmit={handleSubmit}>
          <div className="ds-form-group">
            <label className="ds-label" htmlFor="username">Usuário</label>
            <input
              id="username"
              className="ds-input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Digite seu usuário"
              disabled={loading}
              required
              autoComplete="username"
            />
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="senha">Senha</label>
            <PasswordInput
              id="senha"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="Digite sua senha"
              disabled={loading}
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="button"
            className="ds-link"
            style={{ alignSelf: 'flex-start' }}
            onClick={() => navigate('/RecuperarSenha')}
          >
            Esqueceu a senha?
          </button>

          {erro && <div className="ds-alert ds-alert-error">{erro}</div>}

          <button
            type="submit"
            className="ds-btn ds-btn-primary ds-btn-full"
            disabled={loading}
          >
            {loading ? <><span className="ds-spinner" /> Entrando...</> : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
