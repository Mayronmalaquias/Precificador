import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../assets/css/login.css';

function Cadastro() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    team: '',
    permissao: '',
    id_usuarios: '',

    // novos
    nome: '',
    email: '',
    telefone: '',
    instagram: '',
    descricao: ''
  });

  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // validações básicas front
    if (formData.password.length < 8) {
      alert('A senha deve conter no mínimo 8 caracteres');
      return;
    }

    // (opcional) validação simples de email
    if (formData.email && !/^\S+@\S+\.\S+$/.test(formData.email)) {
      alert('E-mail inválido');
      return;
    }

    // (opcional) limpar telefone pra só números
    const payload = {
      ...formData,
      telefone: formData.telefone ? formData.telefone.replace(/\D/g, '') : ''
    };

    try {
      const response = await fetch('http://56.124.51.158/auth/cadastro', {
      // const response = await fetch('http://localhost:5000/auth/cadastro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok) {
        alert('Usuário cadastrado com sucesso!');
        navigate('/login');
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
          name="nome"
          type="text"
          placeholder="Nome"
          value={formData.nome}
          onChange={handleChange}
        />

        <input
          name="email"
          type="email"
          placeholder="E-mail"
          value={formData.email}
          onChange={handleChange}
        />

        <input
          name="telefone"
          type="text"
          placeholder="Telefone (DDD + número)"
          value={formData.telefone}
          onChange={handleChange}
        />

        <input
          name="instagram"
          type="text"
          placeholder="Instagram (ex: @usuario)"
          value={formData.instagram}
          onChange={handleChange}
        />

        <input
          name="id_usuarios"
          type="text"
          placeholder="ID do Usuário"
          value={formData.id_usuarios}
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

        <textarea
          name="descricao"
          placeholder="Descrição (opcional)"
          value={formData.descricao}
          onChange={handleChange}
          rows={3}
          style={{ resize: 'vertical' }}
        />

        <input
          name="password"
          type="password"
          placeholder="Senha (mín. 8 caracteres)"
          value={formData.password}
          onChange={handleChange}
          required
        />

        <button type="submit">Cadastrar</button>

        <button
          type="button"
          onClick={() => navigate('/login')}
          style={{ backgroundColor: '#666', marginTop: '10px' }}
        >
          Voltar para Login
        </button>
      </form>
    </div>
  );
}

export default Cadastro;
