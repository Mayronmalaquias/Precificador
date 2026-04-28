import React, { useState } from "react";
import "../assets/css/RecuperarSenha.css";

const API_BASE = "/api/auth";
//const API_BASE ="http://localhost:5000/auth"

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
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          id_corretor: idCorretor,
          newpass: novaSenha
        })
      });

      const data = await response.json();

      if (!response.ok) {
        setErro(data.error || "Erro ao recuperar senha.");
        return;
      }

      setMensagem(data.ok || data.message || "Senha alterada com sucesso.");
      setIdCorretor("");
      setNovaSenha("");
    } catch (err) {
      setErro("Não foi possível conectar ao servidor.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="recuperar-senha-page">
      <div className="recuperar-senha-card">
        <h2>Recuperar Senha</h2>
        <p className="subtitulo">
          Informe o ID do corretor e a nova senha para redefinir o acesso.
        </p>

        <form onSubmit={handleRecuperarSenha} className="bloco-form">
          <div className="form-group">
            <label>ID do corretor</label>
            <input
              type="text"
              value={idCorretor}
              onChange={(e) => setIdCorretor(e.target.value)}
              placeholder="Digite o ID do corretor"
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

          {erro && <div className="alert erro">{erro}</div>}
          {mensagem && <div className="alert sucesso">{mensagem}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Alterando..." : "Redefinir senha"}
          </button>
        </form>
      </div>
    </div>
  );
}