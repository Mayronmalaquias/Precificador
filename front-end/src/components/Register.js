import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';
import { RH_FIELDS, emptyRhForm } from './rhFields';
import { useEquipes } from '../context/EquipesContext';
import PasswordInput from './PasswordInput';

function Cadastro() {
  const { equipesOpcoes } = useEquipes();
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    team: '',
    permissao: '',
    nome: '',
    email: '',
    telefone: '',
    instagram: '',
    descricao: '',
    ...emptyRhForm(),
  });
  const [aceiteLgpd, setAceiteLgpd] = useState(false);
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
      lgpd_assinada: aceiteLgpd,
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
              <label className="ds-label" htmlFor="reg-nome">Nome completo *</label>
              <input id="reg-nome" className="ds-input" name="nome"
                type="text" placeholder="Nome completo" value={formData.nome}
                onChange={handleChange} required disabled={loading} />
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
              <label className="ds-label" htmlFor="reg-team">Equipe *</label>
              <select id="reg-team" className="ds-input ds-select" name="team"
                value={formData.team} onChange={handleChange} required disabled={loading}>
                <option value="">Selecione...</option>
                {equipesOpcoes.map((equipe) => (
                  <option key={equipe.value} value={equipe.value}>{equipe.label}</option>
                ))}
              </select>
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
                <option value="corretor">Corretor</option>
                <option value="gerente">Gerente</option>
                <option value="administrativo">Administrativo</option>
                <option value="administrador">Administrador</option>
                <option value="diretor">Diretor</option>
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
            <PasswordInput id="reg-pass" name="password"
              placeholder="Mínimo 8 caracteres" value={formData.password}
              onChange={handleChange} required disabled={loading} autoComplete="new-password" />
          </div>

          <div className="ds-divider" />

          <div>
            <h3 className="ds-page-title" style={{ fontSize: '1.05rem', marginBottom: 4 }}>Dados de RH</h3>
            <p className="ds-page-subtitle" style={{ marginBottom: 14 }}>Dados de RH são opcionais no cadastro — podem ser preenchidos depois.</p>
          </div>

          <div className="ds-form-row">
            {RH_FIELDS.filter((field) => field.name !== 'nome' && field.name !== 'lgpd_assinada').map((field) => {
              const required = false; // RH opcional no registro (por enquanto)
              const id = `reg-rh-${field.name}`;
              const label = field.label;

              if (field.type === 'textarea') {
                return (
                  <div key={field.name} className="ds-form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="ds-label" htmlFor={id}>{label}</label>
                    <textarea id={id} className="ds-input ds-textarea" name={field.name}
                      value={formData[field.name] || ''} onChange={handleChange}
                      required={required} rows={2} disabled={loading} />
                  </div>
                );
              }

              if (field.type === 'boolean') {
                return (
                  <div key={field.name} className="ds-form-group">
                    <label className="ds-label" htmlFor={id}>{label}</label>
                    <select id={id} className="ds-input ds-select" name={field.name}
                      value={formData[field.name] ?? ''} onChange={handleChange}
                      required={required} disabled={loading}>
                      <option value="">Selecione...</option>
                      <option value="true">Sim</option>
                      <option value="false">Não</option>
                    </select>
                  </div>
                );
              }

              if (field.type === 'select') {
                return (
                  <div key={field.name} className="ds-form-group">
                    <label className="ds-label" htmlFor={id}>{label}</label>
                    <select id={id} className="ds-input ds-select" name={field.name}
                      value={formData[field.name] || ''} onChange={handleChange}
                      required={required} disabled={loading}>
                      <option value="">Selecione...</option>
                      {(field.options || []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </div>
                );
              }

              return (
                <div key={field.name} className="ds-form-group">
                  <label className="ds-label" htmlFor={id}>{label}</label>
                  <input id={id} className="ds-input" name={field.name}
                    type={field.type || 'text'} value={formData[field.name] || ''}
                    onChange={handleChange} required={required} disabled={loading} />
                </div>
              );
            })}
          </div>

          <div className="ds-alert ds-alert-info">
            <div>
              <strong>Termo de LGPD</strong>
              <p style={{ margin: '6px 0 0' }}>
                Autorizo a 61 Imóveis a coletar, armazenar e tratar meus dados pessoais para fins de cadastro,
                validação pelo RH, gestão contratual, comunicações internas e cumprimento de obrigações legais,
                conforme a Lei Geral de Proteção de Dados. Declaro estar ciente de que posso solicitar correção,
                atualização ou informações sobre o tratamento dos meus dados pelos canais oficiais da empresa.
              </p>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontWeight: 700 }}>
                <input
                  type="checkbox"
                  checked={aceiteLgpd}
                  onChange={(e) => setAceiteLgpd(e.target.checked)}
                  required
                  disabled={loading}
                />
                Li e aceito os termos de LGPD *
              </label>
            </div>
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
