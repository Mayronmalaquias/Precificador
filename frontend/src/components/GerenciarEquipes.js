import React, { useCallback, useEffect, useState } from "react";
import { useToast } from "../context/ToastContext";
import { useEquipes } from "../context/EquipesContext";
import { api } from "../services/api";
import {
  fetchEquipes,
  criarEquipe,
  atualizarEquipe,
} from "../services/equipes";
import "../assets/css/design-system.css";

function GerenciarEquipes() {
  const toast = useToast();
  const { reload: reloadContexto } = useEquipes();

  const [equipes, setEquipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);

  // Usuários (para escolher o gerente da equipe)
  const [usuarios, setUsuarios] = useState([]);

  // Form de criação
  const [novo, setNovo] = useState({ id_equipe: "", nome: "", email: "", id_gerente: "" });

  // Edição inline de nome
  const [editandoId, setEditandoId] = useState(null);
  const [editNome, setEditNome] = useState("");

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      // incluir inativas para poder reativar/gerenciar
      setEquipes(await fetchEquipes(true));
    } catch (e) {
      toast(e.message || "Erro ao carregar equipes.", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // Lista de usuários ativos p/ escolher quem é o gerente da equipe.
  useEffect(() => {
    api
      .get("/corretor/retornar-lista?ativo=true&per_page=1000")
      .then((data) => {
        const lista = (data?.lista || [])
          .filter((u) => String(u.id_usuarios || "").trim())
          .sort((a, b) => String(a.nome || a.id_usuarios).localeCompare(String(b.nome || b.id_usuarios)));
        setUsuarios(lista);
      })
      .catch(() => {});
  }, []);

  async function aposMutacao(msg) {
    toast(msg, "success");
    await carregar();
    reloadContexto(); // atualiza os selects das outras telas
  }

  async function handleCriar(e) {
    e.preventDefault();
    if (salvando) return;
    const id_equipe = novo.id_equipe.trim();
    const nome = novo.nome.trim();
    if (!id_equipe || !nome) {
      toast("Informe id da equipe e nome.", "error");
      return;
    }
    setSalvando(true);
    try {
      await criarEquipe({
        id_equipe,
        nome,
        email: novo.email.trim() || undefined,
        id_gerente: novo.id_gerente.trim() || undefined,
      });
      setNovo({ id_equipe: "", nome: "", email: "", id_gerente: "" });
      await aposMutacao(novo.id_gerente ? "Equipe criada e gerente definido." : "Equipe criada.");
    } catch (err) {
      toast(err.message || "Erro ao criar equipe.", "error");
    } finally {
      setSalvando(false);
    }
  }

  async function salvarNome(id_equipe) {
    const nome = editNome.trim();
    if (!nome) {
      toast("Nome não pode ficar vazio.", "error");
      return;
    }
    setSalvando(true);
    try {
      await atualizarEquipe(id_equipe, { nome });
      setEditandoId(null);
      setEditNome("");
      await aposMutacao("Nome atualizado.");
    } catch (err) {
      toast(err.message || "Erro ao renomear.", "error");
    } finally {
      setSalvando(false);
    }
  }

  async function alternarAtivo(equipe) {
    setSalvando(true);
    try {
      await atualizarEquipe(equipe.id_equipe, { ativo: !equipe.ativo });
      await aposMutacao(equipe.ativo ? "Equipe desativada." : "Equipe reativada.");
    } catch (err) {
      toast(err.message || "Erro ao alterar status.", "error");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="ds-page" style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h2 className="ds-title" style={{ marginBottom: 4 }}>Gerenciar equipes</h2>
      <p className="ds-subtitle" style={{ marginBottom: 24 }}>
        As equipes vêm do banco. Ao registrar um gerente a equipe dele é criada automaticamente;
        aqui você pode criar, renomear e ativar/desativar.
      </p>

      {/* Criar equipe */}
      <form className="ds-card" onSubmit={handleCriar} style={{ padding: 16, marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>Nova equipe</h3>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <div className="ds-form-group" style={{ flex: "1 1 160px" }}>
            <label className="ds-label">ID da equipe</label>
            <input
              className="ds-input"
              placeholder="Ex: G61020"
              value={novo.id_equipe}
              onChange={(e) => setNovo((p) => ({ ...p, id_equipe: e.target.value }))}
              disabled={salvando}
            />
          </div>
          <div className="ds-form-group" style={{ flex: "2 1 220px" }}>
            <label className="ds-label">Nome</label>
            <input
              className="ds-input"
              placeholder="Ex: NOVA EQUIPE"
              value={novo.nome}
              onChange={(e) => setNovo((p) => ({ ...p, nome: e.target.value }))}
              disabled={salvando}
            />
          </div>
          <div className="ds-form-group" style={{ flex: "2 1 220px" }}>
            <label className="ds-label">E-mail (opcional)</label>
            <input
              className="ds-input"
              placeholder="email@61imoveis.com"
              value={novo.email}
              onChange={(e) => setNovo((p) => ({ ...p, email: e.target.value }))}
              disabled={salvando}
            />
          </div>
          <div className="ds-form-group" style={{ flex: "2 1 220px" }}>
            <label className="ds-label">Gerente (opcional)</label>
            <select
              className="ds-input"
              value={novo.id_gerente}
              onChange={(e) => setNovo((p) => ({ ...p, id_gerente: e.target.value }))}
              disabled={salvando}
            >
              <option value="">Sem gerente por enquanto</option>
              {usuarios.map((u) => (
                <option key={u.id_usuarios} value={u.id_usuarios}>
                  {(u.nome || u.id_usuarios)}{u.permissao ? ` — ${u.permissao}` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="ds-help" style={{ fontSize: 12, color: "#71717a", marginTop: 4 }}>
          Ao escolher um gerente, ele passa a ter <strong>permissão gerente</strong> e o
          <strong> team</strong> da equipe — vira o gerente dela. Os corretores dessa equipe
          devem ter o mesmo team (via "Alterar gerente").
        </p>
        <button type="submit" className="ds-btn ds-btn-primary" disabled={salvando} style={{ marginTop: 12 }}>
          {salvando ? "Salvando..." : "Criar equipe"}
        </button>
      </form>

      {/* Lista */}
      {loading ? (
        <p>Carregando equipes...</p>
      ) : equipes.length === 0 ? (
        <p>Nenhuma equipe cadastrada.</p>
      ) : (
        <table className="ds-table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--ds-border, #e5e7eb)" }}>
              <th style={{ padding: "8px 6px" }}>Equipe</th>
              <th style={{ padding: "8px 6px" }}>ID</th>
              <th style={{ padding: "8px 6px" }}>Status</th>
              <th style={{ padding: "8px 6px", textAlign: "right" }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {equipes.map((eq) => (
              <tr key={eq.id_equipe} style={{ borderBottom: "1px solid var(--ds-border, #f0f0f3)", opacity: eq.ativo ? 1 : 0.55 }}>
                <td style={{ padding: "8px 6px" }}>
                  {editandoId === eq.id_equipe ? (
                    <input
                      className="ds-input"
                      value={editNome}
                      onChange={(e) => setEditNome(e.target.value)}
                      autoFocus
                    />
                  ) : (
                    <strong>{eq.nome || eq.id_equipe}</strong>
                  )}
                </td>
                <td style={{ padding: "8px 6px", color: "#71717a" }}>{eq.id_equipe}</td>
                <td style={{ padding: "8px 6px" }}>
                  <span
                    style={{
                      fontSize: 12,
                      padding: "2px 8px",
                      borderRadius: 999,
                      background: eq.ativo ? "#dcfce7" : "#f4f4f5",
                      color: eq.ativo ? "#16a34a" : "#71717a",
                    }}
                  >
                    {eq.ativo ? "Ativa" : "Inativa"}
                  </span>
                </td>
                <td style={{ padding: "8px 6px", textAlign: "right", whiteSpace: "nowrap" }}>
                  {editandoId === eq.id_equipe ? (
                    <>
                      <button className="ds-btn ds-btn-primary" disabled={salvando} onClick={() => salvarNome(eq.id_equipe)}>
                        Salvar
                      </button>{" "}
                      <button className="ds-btn" disabled={salvando} onClick={() => { setEditandoId(null); setEditNome(""); }}>
                        Cancelar
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="ds-btn"
                        disabled={salvando}
                        onClick={() => { setEditandoId(eq.id_equipe); setEditNome(eq.nome || ""); }}
                      >
                        Renomear
                      </button>{" "}
                      <button
                        className={`ds-btn ${eq.ativo ? "" : "ds-btn-primary"}`}
                        disabled={salvando}
                        onClick={() => alternarAtivo(eq)}
                      >
                        {eq.ativo ? "Desativar" : "Reativar"}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default GerenciarEquipes;
