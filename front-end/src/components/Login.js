import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../assets/css/login.css';

function Login() {
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (loading) return;

    setLoading(true);

    try {
      //const response = await fetch('/api/auth/login', {
      const response = await fetch('http://localhost:5000/auth/login', {  
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: username,
          password: senha
        })
      });

      const data = await response.json();

      if (response.ok && data.login === true) {
        localStorage.setItem('auth', 'true');

        if (data.user) {
          localStorage.setItem('userData', JSON.stringify(data.user));
        }

        navigate('/');
      } else {
        alert(data.error || 'Credenciais inválidas');
      }
    } catch (error) {
      console.error('Erro ao fazer login:', error);
      alert('Erro de conexão com o servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="divLogin">
      <h2>Login</h2>

      <form onSubmit={handleSubmit}>
        <label>
          Username:
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            placeholder="Digite seu nome de usuário"
            disabled={loading}
          />
        </label>

        <br />

        <label>
          Senha:
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
            placeholder="Digite sua senha"
            disabled={loading}
          />
        </label>

        <br />

        <button type="submit" disabled={loading}>
          {loading ? 'Entrando...' : 'Entrar'}
        </button>

        {loading && <p className="login-loading">Carregando...</p>}
      </form>
    </div>
  );
}

export default Login;