import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';

function Cadastro() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    team: '',
    permissao: '',
    id_usuarios: '',
    nome: '',
    email: '',
    telefone: '',
    instagram: '',
    descricao: '',
  });
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const toast = useToast();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.password.length < 8) {
      toast('A senha deve ter no mínimo 8 caracteres.', 'error');
      return;
    }

    if (formData.email && !/^\S+@\S+\.\S+$/.test(formData.email)) {
      toast('E-mail inválido.', 'error');
      return;
    }

    const payload = {
      ...formData,
      telefone: formData.telefone ? formData.telefone.replace(/\D/g, '') : '',
    };

    setLoading(true);
    try {
      await api.post('/auth/cadastro', payload);
      toast('Usuário cadastrado com sucesso!', 'success');
      navigate('/login');
    } catch (error) {
      toast(error.message || 'Erro de conexão com o servidor.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ds-auth-wrapper">
      <div className="ds-auth-card ds-auth-card--wide">
        <span className="ds-auth-accent" />
        <h2 className="ds-auth-title">Cadastro de Usuário</h2>
        <p className="ds-auth-subtitle">Preencha os dados para criar uma nova conta</p>

        <form className="ds-form" onSubmit={handleSubmit}>
          <div className="ds-form-row">
            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-username">Username *</label>
              <input id="reg-username" className="ds-input" name="username"
                type="text" placeholder="Username" value={formData.username}
                onChange={handleChange} required disabled={loading} />
            </div>

            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-nome">Nome</label>
              <input id="reg-nome" className="ds-input" name="nome"
                type="text" placeholder="Nome completo" value={formData.nome}
                onChange={handleChange} disabled={loading} />
            </div>
          </div>

          <div className="ds-form-row">
            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-email">E-mail</label>
              <input id="reg-email" className="ds-input" name="email"
                type="email" placeholder="email@exemplo.com" value={formData.email}
                onChange={handleChange} disabled={loading} />
            </div>

            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-tel">Telefone</label>
              <input id="reg-tel" className="ds-input" name="telefone"
                type="text" placeholder="(61) 9 9999-9999" value={formData.telefone}
                onChange={handleChange} disabled={loading} />
            </div>
          </div>

          <div className="ds-form-row">
            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-id">ID do Usuário *</label>
              <input id="reg-id" className="ds-input" name="id_usuarios"
                type="text" placeholder="ID" value={formData.id_usuarios}
                onChange={handleChange} required disabled={loading} />
            </div>

            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-team">Equipe *</label>
              <input id="reg-team" className="ds-input" name="team"
                type="text" placeholder="Nome da equipe" value={formData.team}
                onChange={handleChange} required disabled={loading} />
            </div>
          </div>

          <div className="ds-form-row">
            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-insta">Instagram</label>
              <input id="reg-insta" className="ds-input" name="instagram"
                type="text" placeholder="@usuario" value={formData.instagram}
                onChange={handleChange} disabled={loading} />
            </div>

            <div className="ds-form-group">
              <label className="ds-label" htmlFor="reg-perm">Permissão *</label>
              <select id="reg-perm" className="ds-input ds-select" name="permissao"
                value={formData.permissao} onChange={handleChange} required disabled={loading}>
                <option value="">Selecione...</option>
                <option value="user">Usuário</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="reg-desc">Descrição</label>
            <textarea id="reg-desc" className="ds-input ds-textarea" name="descricao"
              placeholder="Descrição (opcional)" value={formData.descricao}
              onChange={handleChange} rows={3} disabled={loading} />
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="reg-pass">Senha *</label>
            <input id="reg-pass" className="ds-input" name="password"
              type="password" placeholder="Mínimo 8 caracteres" value={formData.password}
              onChange={handleChange} required disabled={loading} autoComplete="new-password" />
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
            <button type="submit" className="ds-btn ds-btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? <><span className="ds-spinner" /> Cadastrando...</> : 'Cadastrar'}
            </button>
            <button type="button" className="ds-btn ds-btn-secondary" onClick={() => navigate('/login')} disabled={loading}>
              Voltar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Cadastro;
