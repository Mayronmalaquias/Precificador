import React, { useState } from "react";
import PasswordInput from "./PasswordInput";
import { BASE } from '../services/api';

export default function TrocarSenha() {
  const userData = (() => {
    try { return JSON.parse(localStorage.getItem("userData") || "{}"); } catch { return {}; }
  })();
  const username = userData.username || "";

  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setMensagem("");
    setErro("");

    if (!username) { setErro("Usuário não identificado. Faça login novamente."); return; }
    if (!senhaAtual || !novaSenha || !confirmarSenha) { setErro("Preencha todos os campos."); return; }
    if (novaSenha !== confirmarSenha) { setErro("A nova senha e a confirmação não coincidem."); return; }

    setLoading(true);
    try {
      const response = await fetch(`${BASE}/auth/switch-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, old_pass: senhaAtual, new_pass: novaSenha }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErro(data.error || data.message || "Erro ao alterar senha.");
        return;
      }

      setMensagem(data.message || "Senha alterada com sucesso.");
      setSenhaAtual("");
      setNovaSenha("");
      setConfirmarSenha("");
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
        <h2 className="ds-auth-title">Trocar Senha</h2>
        <p className="ds-auth-subtitle">Altere sua senha de acesso com segurança.</p>

        <form className="ds-form" onSubmit={handleSubmit}>
          <div className="ds-form-group">
            <label className="ds-label">Usuário</label>
            <input className="ds-input" type="text" value={username} disabled />
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="senha-atual">Senha atual</label>
            <PasswordInput id="senha-atual"
              value={senhaAtual} onChange={(e) => setSenhaAtual(e.target.value)}
              placeholder="Digite sua senha atual" disabled={loading} />
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="nova-senha">Nova senha</label>
            <PasswordInput id="nova-senha"
              value={novaSenha} onChange={(e) => setNovaSenha(e.target.value)}
              placeholder="Digite a nova senha" disabled={loading} />
          </div>

          <div className="ds-form-group">
            <label className="ds-label" htmlFor="confirmar-senha">Confirmar nova senha</label>
            <PasswordInput id="confirmar-senha"
              value={confirmarSenha} onChange={(e) => setConfirmarSenha(e.target.value)}
              placeholder="Confirme a nova senha" disabled={loading} />
          </div>

          {erro     && <div className="ds-alert ds-alert-error">{erro}</div>}
          {mensagem && <div className="ds-alert ds-alert-success">{mensagem}</div>}

          <button type="submit" className="ds-btn ds-btn-primary ds-btn-full" disabled={loading}>
            {loading ? <><span className="ds-spinner" /> Alterando...</> : 'Alterar senha'}
          </button>
        </form>
      </div>
    </div>
  );
}
