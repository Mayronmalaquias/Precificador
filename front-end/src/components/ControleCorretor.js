import React, { useEffect, useMemo, useState, useCallback } from "react";
import "../assets/css/ControleCorretores.css";

//const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";
const API_BASE = "/api"
const EQUIPES_MAP = {
  G61001: "AGEF",
  G61002: "AGUIA",
  G61003: "PRIME",
  G61010: "LOTUS",
  G61014: "NOVA UNIÃO",
  G61015: "SENNA",
  G61016: "LIDER",
};

const IDS_EQUIPES_VALIDOS = Object.keys(EQUIPES_MAP);

function getNomeEquipe(teamId) {
  return EQUIPES_MAP[String(teamId)] || String(teamId || "-");
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

function ControleCorretores() {
  const [usuario, setUsuario] = useState(null);
  const [corretores, setCorretores] = useState([]);
  const [equipes, setEquipes] = useState([]);
  const [busca, setBusca] = useState("");
  const [filtroEquipe, setFiltroEquipe] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [erroAcesso, setErroAcesso] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingAcao, setLoadingAcao] = useState(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("userData");

      if (!raw) {
        setErroAcesso("Nenhum login encontrado. Faça login para acessar esta página.");
        return;
      }

      const user = JSON.parse(raw);

      setUsuario({
        id: user.id || "",
        id_usuarios: user.id_usuarios || user.id || "",
        nome: user.nome || user.username || "Usuário",
        permissao: user.permissao || "",
        team: user.team || null,
      });
    } catch {
      setErroAcesso("Erro ao ler dados do usuário logado.");
    }
  }, []);

  const isAdmin = usuario?.team === "administrativo";
  const isAdministrativo = String(usuario?.team || "").toLowerCase() === "administrativo";
  const podeGerenciarTodasEquipes = isAdmin || isAdministrativo;
  const isGerente = usuario?.permissao === "gerente";

  const carregarCorretores = useCallback(async (usuarioAtual) => {
    if (!usuarioAtual) return;

    setLoading(true);

    try {
      const usuarioEhAdmin = usuarioAtual.permissao === "admin";
      const usuarioEhAdministrativo =
        String(usuarioAtual.team || "").toLowerCase() === "administrativo";
      const podeVerTodas = usuarioEhAdmin || usuarioEhAdministrativo;

      const params = new URLSearchParams();

      if (!podeVerTodas && usuarioAtual.team) {
        params.set("gerente", usuarioAtual.team);
      }

      const { ok, data } = await apiFetch(`/corretor/retornar-lista?${params.toString()}`);

      if (!ok) {
        setErroAcesso(data?.error || "Erro ao carregar corretores.");
        return;
      }

      const listaOriginal = data.lista || [];

      const listaFiltrada = listaOriginal.filter((c) =>
        IDS_EQUIPES_VALIDOS.includes(String(c.team))
      );

      setCorretores(listaFiltrada);

      const equipesUnicas = [
        ...new Set(listaFiltrada.map((c) => String(c.team)).filter(Boolean)),
      ].sort();

      setEquipes(equipesUnicas);
    } catch {
      setErroAcesso("Não foi possível conectar à API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (usuario) {
      carregarCorretores(usuario);
    }
  }, [usuario, carregarCorretores]);

  const alterarEquipe = async (idCorretor, novoGerente) => {
    if (!idCorretor || !novoGerente) return;

    setLoadingAcao(idCorretor);

    try {
      const { ok, data } = await apiFetch("/corretor/alterar-gerente", {
        method: "POST",
        body: JSON.stringify({
          manager: novoGerente,
          corretor: idCorretor,
        }),
      });

      if (ok) {
        setCorretores((prev) =>
          prev.map((c) =>
            c.id_usuarios === idCorretor ? { ...c, team: novoGerente } : c
          )
        );
      } else {
        alert(data?.error || "Erro ao alterar gerente.");
      }
    } catch {
      alert("Erro de comunicação com a API.");
    } finally {
      setLoadingAcao(null);
    }
  };

  const alterarAtivo = async (idCorretor, novoAtivo) => {
    setLoadingAcao(idCorretor);

    try {
      const { ok, data } = await apiFetch("/corretor/alterar-ativo", {
        method: "POST",
        body: JSON.stringify({
          id_corretor: idCorretor,
          new_ativo: novoAtivo,
        }),
      });

      if (ok) {
        setCorretores((prev) =>
          prev.map((c) =>
            c.id_usuarios === idCorretor ? { ...c, ativo: novoAtivo } : c
          )
        );
      } else {
        alert(data?.error || "Erro ao alterar status.");
      }
    } catch {
      alert("Erro de comunicação com a API.");
    } finally {
      setLoadingAcao(null);
    }
  };

  const corretoresFiltrados = useMemo(() => {
    if (!usuario) return [];

    let lista = [...corretores];

    if (podeGerenciarTodasEquipes && filtroEquipe) {
      lista = lista.filter((c) => String(c.team) === String(filtroEquipe));
    }

    if (filtroStatus !== "") {
      const ativoFiltro = filtroStatus === "ativo";
      lista = lista.filter((c) => c.ativo === ativoFiltro);
    }

    if (busca.trim()) {
      const termo = busca.toLowerCase();

      lista = lista.filter(
        (c) =>
          String(c.nome || "").toLowerCase().includes(termo) ||
          String(c.username || "").toLowerCase().includes(termo) ||
          String(c.id_usuarios || "").toLowerCase().includes(termo) ||
          String(getNomeEquipe(c.team)).toLowerCase().includes(termo)
      );
    }

    return lista;
  }, [usuario, corretores, filtroEquipe, filtroStatus, busca, podeGerenciarTodasEquipes]);

  const totalAtivos = corretoresFiltrados.filter((c) => c.ativo === true).length;
  const totalInativos = corretoresFiltrados.filter((c) => c.ativo === false).length;
  const totalEquipesVisiveis = new Set(corretoresFiltrados.map((c) => c.team)).size;

  return (
    <div className="controle-corretores">
      <div className="controle-corretores__container">
        {erroAcesso && (
          <div className="controle-corretores__empty" style={{ padding: "20px" }}>
            {erroAcesso}
          </div>
        )}

        {!usuario ? null : (
          <>
            <section className="controle-corretores__header">
              <div className="controle-corretores__header-top">
                <div className="controle-corretores__header-left">
                  <span className="controle-corretores__tag">
                    {podeGerenciarTodasEquipes ? "Painel administrativo" : "Painel gerencial"}
                  </span>

                  <h1 className="controle-corretores__header-title">
                    {podeGerenciarTodasEquipes
                      ? "Controle Geral de Corretores"
                      : "Minha Equipe de Corretores"}
                  </h1>

                  <p className="controle-corretores__header-text">
                    {podeGerenciarTodasEquipes
                      ? "Visualize todas as equipes, filtre registros e gerencie os corretores."
                      : `Acompanhe os corretores da equipe ${getNomeEquipe(usuario.team)}.`}
                  </p>
                </div>

                <div className="controle-corretores__header-actions">
                  {!podeGerenciarTodasEquipes && isGerente && (
                    <button
                      type="button"
                      className="controle-corretores__button controle-corretores__button--ghost"
                    >
                      Exportar minha equipe
                    </button>
                  )}
                </div>
              </div>
            </section>

            <section className="controle-corretores__hero">
              <div className="controle-corretores__hero-card">
                <h2 className="controle-corretores__hero-card-title">
                  {podeGerenciarTodasEquipes
                    ? "Visão ampla para gestão de equipes"
                    : "Visão focada da equipe"}
                </h2>

                <p className="controle-corretores__hero-card-text">
                  {podeGerenciarTodasEquipes
                    ? "Você acompanha todas as equipes e pode redistribuir corretores."
                    : "Você visualiza apenas os corretores da sua própria equipe."}
                </p>
              </div>

              <div className="controle-corretores__user-card">
                <div className="controle-corretores__user-header">
                  <h3 className="controle-corretores__user-title">Usuário logado</h3>
                  <span className="controle-corretores__role">
                    {usuario.permissao || "sem permissão"}
                  </span>
                </div>

                <div className="controle-corretores__user-grid">
                  <div className="controle-corretores__user-item">
                    <span className="controle-corretores__user-label">Nome</span>
                    <span className="controle-corretores__user-value">{usuario.nome}</span>
                  </div>

                  <div className="controle-corretores__user-item">
                    <span className="controle-corretores__user-label">Equipe</span>
                    <span className="controle-corretores__user-value">
                      {isAdministrativo ? "ADMINISTRATIVO" : getNomeEquipe(usuario.team)}
                    </span>
                  </div>

                  <div className="controle-corretores__user-item">
                    <span className="controle-corretores__user-label">Escopo de acesso</span>
                    <span className="controle-corretores__user-value">
                      {podeGerenciarTodasEquipes
                        ? "Todas as equipes"
                        : `Somente equipe ${getNomeEquipe(usuario.team)}`}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            <section className="controle-corretores__summary">
              <div className="controle-corretores__summary-card">
                <span className="controle-corretores__summary-label">
                  {podeGerenciarTodasEquipes ? "Total exibido" : "Minha equipe"}
                </span>
                <div className="controle-corretores__summary-value">
                  {loading ? "..." : corretoresFiltrados.length}
                </div>
                <div className="controle-corretores__summary-helper">
                  {podeGerenciarTodasEquipes
                    ? "Corretores no resultado atual"
                    : "Corretores visíveis"}
                </div>
              </div>

              <div className="controle-corretores__summary-card">
                <span className="controle-corretores__summary-label">Ativos</span>
                <div className="controle-corretores__summary-value">
                  {loading ? "..." : totalAtivos}
                </div>
                <div className="controle-corretores__summary-helper">
                  Corretores em atividade
                </div>
              </div>

              <div className="controle-corretores__summary-card">
                <span className="controle-corretores__summary-label">Inativos</span>
                <div className="controle-corretores__summary-value">
                  {loading ? "..." : totalInativos}
                </div>
                <div className="controle-corretores__summary-helper">
                  Corretores fora de atividade
                </div>
              </div>

              <div className="controle-corretores__summary-card">
                <span className="controle-corretores__summary-label">
                  {podeGerenciarTodasEquipes ? "Equipes visíveis" : "Equipe atual"}
                </span>
                <div className="controle-corretores__summary-value">
                  {podeGerenciarTodasEquipes
                    ? totalEquipesVisiveis
                    : getNomeEquipe(usuario.team)}
                </div>
                <div className="controle-corretores__summary-helper">
                  {podeGerenciarTodasEquipes
                    ? "Equipes presentes após filtros"
                    : "Sob sua responsabilidade"}
                </div>
              </div>
            </section>

            <section className="controle-corretores__panel">
              <div className="controle-corretores__panel-top">
                <div>
                  <h3 className="controle-corretores__panel-title">
                    {podeGerenciarTodasEquipes
                      ? "Lista geral de corretores"
                      : "Corretores da minha equipe"}
                  </h3>

                  <p className="controle-corretores__panel-subtitle">
                    {podeGerenciarTodasEquipes
                      ? "Filtre por equipe, status e busca textual."
                      : "Acompanhe os corretores com filtros por status e busca."}
                  </p>
                </div>

                <div className="controle-corretores__count-badge">
                  {corretoresFiltrados.length} registro(s)
                </div>
              </div>

              <div className="controle-corretores__toolbar">
                <div className="controle-corretores__toolbar-left">
                  {podeGerenciarTodasEquipes && (
                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label" htmlFor="filtroEquipe">
                        Equipe
                      </label>

                      <select
                        id="filtroEquipe"
                        className="controle-corretores__select"
                        value={filtroEquipe}
                        onChange={(e) => setFiltroEquipe(e.target.value)}
                      >
                        <option value="">Todas as equipes</option>
                        {equipes.map((eq) => (
                          <option key={eq} value={eq}>
                            {getNomeEquipe(eq)}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="controle-corretores__field">
                    <label className="controle-corretores__label" htmlFor="filtroStatus">
                      Status
                    </label>

                    <select
                      id="filtroStatus"
                      className="controle-corretores__select"
                      value={filtroStatus}
                      onChange={(e) => setFiltroStatus(e.target.value)}
                    >
                      <option value="">Todos</option>
                      <option value="ativo">Ativo</option>
                      <option value="inativo">Inativo</option>
                    </select>
                  </div>
                </div>

                <div className="controle-corretores__toolbar-right">
                  <div className="controle-corretores__field">
                    <label className="controle-corretores__label" htmlFor="buscaCorretor">
                      Buscar
                    </label>

                    <input
                      id="buscaCorretor"
                      type="text"
                      className="controle-corretores__search"
                      placeholder="Nome, ID ou equipe"
                      value={busca}
                      onChange={(e) => setBusca(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="controle-corretores__table-wrapper">
                <div className="controle-corretores__table-scroll">
                  {loading ? (
                    <div className="controle-corretores__empty">Carregando corretores...</div>
                  ) : (
                    <table className="controle-corretores__table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Corretor</th>
                          <th>Equipe Atual</th>
                          <th>Status</th>
                          {podeGerenciarTodasEquipes && <th>Alterar Equipe</th>}
                          {(podeGerenciarTodasEquipes || isGerente) && <th>Ativo</th>}
                        </tr>
                      </thead>

                      <tbody>
                        {corretoresFiltrados.length === 0 ? (
                          <tr>
                            <td
                              colSpan={podeGerenciarTodasEquipes ? 6 : 5}
                              className="controle-corretores__empty"
                            >
                              Nenhum corretor encontrado com os filtros informados.
                            </td>
                          </tr>
                        ) : (
                          corretoresFiltrados.map((c) => (
                            <tr key={c.id_usuarios}>
                              <td className="controle-corretores__id">{c.id_usuarios}</td>

                              <td>
                                <div className="controle-corretores__nome-wrap">
                                  <span className="controle-corretores__nome">{c.nome}</span>
                                  <span className="controle-corretores__nome-sub">
                                    {c.username}
                                  </span>
                                </div>
                              </td>

                              <td>
                                <span className="controle-corretores__team">
                                  {getNomeEquipe(c.team)}
                                </span>
                              </td>

                              <td>
                                <span
                                  className={`controle-corretores__badge ${
                                    c.ativo
                                      ? "controle-corretores__badge--ativo"
                                      : "controle-corretores__badge--inativo"
                                  }`}
                                >
                                  {c.ativo ? "ativo" : "inativo"}
                                </span>
                              </td>

                              {podeGerenciarTodasEquipes && (
                                <td>
                                  <select
                                    className="controle-corretores__select"
                                    value={c.team ?? ""}
                                    disabled={loadingAcao === c.id_usuarios}
                                    onChange={(e) => alterarEquipe(c.id_usuarios, e.target.value)}
                                  >
                                    {equipes.map((eq) => (
                                      <option key={eq} value={eq}>
                                        {getNomeEquipe(eq)}
                                      </option>
                                    ))}
                                  </select>
                                </td>
                              )}

                              {(podeGerenciarTodasEquipes || isGerente) && (
                                <td>
                                  <button
                                    type="button"
                                    className={`controle-corretores__button ${
                                      c.ativo
                                        ? "controle-corretores__button--ghost"
                                        : "controle-corretores__button--primary"
                                    }`}
                                    disabled={loadingAcao === c.id_usuarios}
                                    onClick={() => alterarAtivo(c.id_usuarios, !c.ativo)}
                                  >
                                    {loadingAcao === c.id_usuarios
                                      ? "..."
                                      : c.ativo
                                      ? "Desativar"
                                      : "Ativar"}
                                  </button>
                                </td>
                              )}
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              <div className="controle-corretores__mobile-list">
                {loading ? (
                  <div className="controle-corretores__mobile-card">
                    <div className="controle-corretores__empty">Carregando...</div>
                  </div>
                ) : corretoresFiltrados.length === 0 ? (
                  <div className="controle-corretores__mobile-card">
                    <div className="controle-corretores__empty">
                      Nenhum corretor encontrado com os filtros informados.
                    </div>
                  </div>
                ) : (
                  corretoresFiltrados.map((c) => (
                    <div key={c.id_usuarios} className="controle-corretores__mobile-card">
                      <div className="controle-corretores__mobile-top">
                        <div>
                          <h3 className="controle-corretores__mobile-name">{c.nome}</h3>
                          <div className="controle-corretores__mobile-id">ID {c.id_usuarios}</div>
                        </div>

                        <span
                          className={`controle-corretores__badge ${
                            c.ativo
                              ? "controle-corretores__badge--ativo"
                              : "controle-corretores__badge--inativo"
                          }`}
                        >
                          {c.ativo ? "ativo" : "inativo"}
                        </span>
                      </div>

                      <div className="controle-corretores__mobile-grid">
                        <div className="controle-corretores__mobile-field">
                          <span className="controle-corretores__mobile-field-label">
                            Equipe atual
                          </span>
                          <span className="controle-corretores__mobile-field-value">
                            {getNomeEquipe(c.team)}
                          </span>
                        </div>

                        <div className="controle-corretores__mobile-field">
                          <span className="controle-corretores__mobile-field-label">
                            Username
                          </span>
                          <span className="controle-corretores__mobile-field-value">
                            {c.username}
                          </span>
                        </div>
                      </div>

                      <div className="controle-corretores__mobile-action">
                        {podeGerenciarTodasEquipes && (
                          <>
                            <label className="controle-corretores__label">Alterar equipe</label>
                            <select
                              className="controle-corretores__select"
                              value={c.team ?? ""}
                              disabled={loadingAcao === c.id_usuarios}
                              onChange={(e) => alterarEquipe(c.id_usuarios, e.target.value)}
                            >
                              {equipes.map((eq) => (
                                <option key={eq} value={eq}>
                                  {getNomeEquipe(eq)}
                                </option>
                              ))}
                            </select>
                          </>
                        )}

                        {(podeGerenciarTodasEquipes || isGerente) && (
                          <button
                            type="button"
                            className={`controle-corretores__button ${
                              c.ativo
                                ? "controle-corretores__button--ghost"
                                : "controle-corretores__button--primary"
                            }`}
                            style={{ marginTop: "8px" }}
                            disabled={loadingAcao === c.id_usuarios}
                            onClick={() => alterarAtivo(c.id_usuarios, !c.ativo)}
                          >
                            {loadingAcao === c.id_usuarios
                              ? "..."
                              : c.ativo
                              ? "Desativar"
                              : "Ativar"}
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default ControleCorretores;