import React, { useState } from "react";
import { BASE } from '../services/api';

const API_BASE = `${BASE}/auth`;

export default function RecuperarSenha() {
  const [idCorretor, setIdCorretor] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRecuperarSenha(e) {
    e.preventDefault();
    setMensagem("");
    setErro("");

    if (!idCorretor || !novaSenha) {
      setErro("Preencha o ID do corretor e a nova senha.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/recuperar-senha`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_corretor: idCorretor, newpass: novaSenha }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErro(data.error || "Erro ao recuperar senha.");
        return;
      }

      setMensagem(data.ok || data.message || "Senha alterada com sucesso.");
      setIdCorretor("");
      setNovaSenha("");
    } catch {
      setErro("Não foi possível conectar ao servidor.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ds-auth-wrapper">
      <div className="ds-auth-card">
        <span className="ds-auth-accent" />
        <h2 className="ds-auth-title">Recuperar Senha</h2>
        <p className="ds-auth-subtitle">Informe o ID do corretor e a nova senha para redefinir o acesso.</p>

        <form className="ds-form" onSubmit={handleRecuperarSenha}>
          <div className="ds-form-group">
            <label className="ds-label" htmlFor="id-corretor">ID do Corretor</label>
            <input id="id-corretor" className="ds-input" type="text"
              value={idCorretor} onChange={(e) => setIdCorretor(e.target.value)}
              placeholder="Digite o ID do corretor" disabled={loading} />
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="nova-senha-rec">Nova Senha</label>
            <input id="nova-senha-rec" className="ds-input" type="password"
              value={novaSenha} onChange={(e) => setNovaSenha(e.target.value)}
              placeholder="Digite a nova senha" disabled={loading} />
          </div>

          {erro     && <div className="ds-alert ds-alert-error">{erro}</div>}
          {mensagem && <div className="ds-alert ds-alert-success">{mensagem}</div>}

          <button type="submit" className="ds-btn ds-btn-primary ds-btn-full" disabled={loading}>
            {loading ? <><span className="ds-spinner" /> Redefinindo...</> : 'Redefinir senha'}
          </button>
        </form>
      </div>
    </div>
  );
}
