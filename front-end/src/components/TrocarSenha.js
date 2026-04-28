import React, { useMemo, useState } from "react";
import "../assets/css/TrocarSenha.css";

const API_BASE = "/api";
//const API_BASE = "http://localhost:5000/"

export default function TrocarSenha() {
  const userLogado = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || null;
    } catch {
      return null;
    }
  }, []);
  const userDataString = localStorage.getItem("userData");
  const userData = JSON.parse(userDataString);
  const username = userData.username
  //const username = userLogado?.username || "";

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

    if (!username) {
      setErro("Usuário não identificado. Faça login novamente.");
      return;
    }

    if (!senhaAtual || !novaSenha || !confirmarSenha) {
      setErro("Preencha todos os campos.");
      return;
    }

    if (novaSenha !== confirmarSenha) {
      setErro("A nova senha e a confirmação não coincidem.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/auth/switch-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username,
          old_pass: senhaAtual,
          new_pass: novaSenha,
        }),
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
    } catch (err) {
      setErro("Não foi possível conectar ao servidor.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="trocar-senha-page">
      <div className="trocar-senha-card">
        <h2>Troca de Senha</h2>
        <p className="subtitulo">
          Altere sua senha de acesso com segurança.
        </p>

        <form onSubmit={handleSubmit} className="trocar-senha-form">
          <div className="form-group">
            <label>Usuário</label>
            <input
              type="text"
              value={username}
              disabled
              placeholder="Usuário logado"
            />
          </div>

          <div className="form-group">
            <label>Senha atual</label>
            <input
              type="password"
              value={senhaAtual}
              onChange={(e) => setSenhaAtual(e.target.value)}
              placeholder="Digite sua senha atual"
            />
          </div>

          <div className="form-group">
            <label>Nova senha</label>
            <input
              type="password"
              value={novaSenha}
              onChange={(e) => setNovaSenha(e.target.value)}
              placeholder="Digite a nova senha"
            />
          </div>

          <div className="form-group">
            <label>Confirmar nova senha</label>
            <input
              type="password"
              value={confirmarSenha}
              onChange={(e) => setConfirmarSenha(e.target.value)}
              placeholder="Confirme a nova senha"
            />
          </div>

          {erro && <div className="alert erro">{erro}</div>}
          {mensagem && <div className="alert sucesso">{mensagem}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Alterando..." : "Alterar senha"}
          </button>
        </form>
      </div>
    </div>
  );
}