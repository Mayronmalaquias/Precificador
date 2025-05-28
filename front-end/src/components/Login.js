import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../assets/css/login.css';

function Login() {
  // 1. Renomear o estado de 'email' para 'username'
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          // 2. Usar a variável de estado 'username' aqui
          username: username, // ou simplesmente 'username,' se a chave e a variável tiverem o mesmo nome
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
    // No React, é uma boa prática usar 'className' em vez de 'class' para atributos CSS
    <div className="divLogin"> {/* Alterado class para className */}
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Username:
          <input
            // 3. Alterar o type do input
            type="text"
            // 4. Usar o estado e setter corretos
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            placeholder="Digite seu nome de usuário" // Opcional: adicionar placeholder
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
            placeholder="Digite sua senha" // Opcional: adicionar placeholder
          />
        </label>
        <br />
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}

export default Login;