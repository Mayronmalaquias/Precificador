import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../assets/css/login.css';

function Login() {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();

    // Simula autenticação
    if (email === 'admin@teste.com' && senha === '1234') {
      localStorage.setItem('auth', 'true');
      navigate('/interno');
    } else {
      alert('Credenciais inválidas');
    }
  };

  return (
    <div class="divLogin">
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <label>
          E-mail:
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required />
        </label>
        <br />
        <label>
          Senha:
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required />
        </label>
        <br />
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}

export default Login;
