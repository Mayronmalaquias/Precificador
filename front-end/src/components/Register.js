import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../assets/css/login.css'; // Reutilizando seu CSS

function Cadastro() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    team: '',
    id_user: '',
    permissao: ''
  });
  
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validação local antes do fetch
    if (formData.password.length < 8) {
      alert('A senha deve conter no mínimo 8 caracteres');
      return;
    }

    try {
      const response = await fetch('http://52.67.252.192/auth/cadastro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        alert('Usuário cadastrado com sucesso!');
        navigate('/login'); // Redireciona para o login após sucesso
      } else {
        alert(data.error || 'Erro ao cadastrar usuário');
      }
    } catch (error) {
      console.error('Erro na requisição:', error);
      alert('Erro de conexão com o servidor.');
    }
  };

  return (
    <div className="divLogin">
      <h2>Cadastro de Usuário</h2>
      <form onSubmit={handleSubmit}>
        <input
          name="username"
          type="text"
          placeholder="Username"
          value={formData.username}
          onChange={handleChange}
          required
        />
        <input
          name="id_user"
          type="text"
          placeholder="ID do Usuário"
          value={formData.id_user}
          onChange={handleChange}
          required
        />
        <input
          name="team"
          type="text"
          placeholder="Equipe (Team)"
          value={formData.team}
          onChange={handleChange}
          required
        />
        <select 
          name="permissao" 
          value={formData.permissao} 
          onChange={handleChange} 
          required
        >
          <option value="">Selecione a Permissão</option>
          <option value="user">Usuário</option>
          <option value="admin">Administrador</option>
        </select>
        <input
          name="password"
          type="password"
          placeholder="Senha (mín. 8 caracteres)"
          value={formData.password}
          onChange={handleChange}
          required
        />
        <button type="submit">Cadastrar</button>
        <button type="button" onClick={() => navigate('/login')} style={{backgroundColor: '#666', marginTop: '10px'}}>
          Voltar para Login
        </button>
      </form>
    </div>
  );
}

export default Cadastro;