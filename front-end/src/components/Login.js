import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../assets/css/login.css';

function Login() {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch('http://localhost:5000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: email,
          password: senha
        })
      });

      const data = await response.json();

      if (response.ok && data.login === true) {
        localStorage.setItem('auth', 'true');
        navigate('/interno');
      } else {
        alert(data.error || 'Credenciais inválidas');
      }
    } catch (error) {
      console.error('Erro ao fazer login:', error);
      alert('Erro de conexão com o servidor.');
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
