import React, { useEffect, useMemo, useState, useCallback } from "react";
import "../assets/css/ControleCorretores.css";

import { BASE as API_BASE } from '../services/api';
import { useToast } from '../context/ToastContext';
import { useEquipes } from '../context/EquipesContext';

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

function ControleCorretores() {
  const toast = useToast();
  const { equipesOpcoes, getNomeEquipe } = useEquipes();
  const [usuario, setUsuario] = useState(null);
  const [corretores, setCorretores] = useState([]);
  const [equipes, setEquipes] = useState([]);
  const [busca, setBusca] = useState("");
  const [filtroEquipe, setFiltroEquipe] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [erroAcesso, setErroAcesso] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingAcao, setLoadingAcao] = useState(null);
  const [editando, setEditando] = useState(null);
  const [salvandoEdicao, setSalvandoEdicao] = useState(false);

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

  const isAdministrativo = usuario?.permissao === "administrativo" || String(usuario?.team || "").toLowerCase() === "administrativo";
  const podeGerenciarTodasEquipes = ['administrador', 'diretor'].includes(usuario?.permissao) || isAdministrativo;
  const isGerente = usuario?.permissao === "gerente";
  const isDiretor = usuario?.permissao === "diretor" || usuario?.permissao === "administrativo" || isAdministrativo;

  const carregarCorretores = useCallback(async (usuarioAtual) => {
    if (!usuarioAtual) return;

    setLoading(true);

    try {
      const usuarioEhAdministrativo = usuarioAtual.permissao === "administrativo" ||
        String(usuarioAtual.team || "").toLowerCase() === "administrativo";
      const podeVerTodas = ['administrador', 'diretor'].includes(usuarioAtual.permissao) || usuarioEhAdministrativo;

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

      const listaFiltrada = listaOriginal.filter((c) => String(c.team || "").trim());

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
        toast(data?.error || "Erro ao alterar gerente.", "error");
      }
    } catch {
      toast("Erro de comunicação com a API.", "error");
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
        toast(data?.error || "Erro ao alterar status.", "error");
      }
    } catch {
      toast("Erro de comunicação com a API.", "error");
    } finally {
      setLoadingAcao(null);
    }
  };

  const excluirUsuario = async (c) => {
    if (!window.confirm(
      `Excluir o usuário "${c.nome}" (${c.id_usuarios})?\n\nRemove o cadastro permanentemente. O histórico de vendas mantém o nome.`
    )) return;
    setLoadingAcao(c.id_usuarios);
    try {
      const { ok, data } = await apiFetch("/corretor/excluir-usuario", {
        method: "POST",
        body: JSON.stringify({ id_corretor: c.id_usuarios }),
      });
      if (ok) {
        setCorretores((prev) => prev.filter((x) => x.id_usuarios !== c.id_usuarios));
        toast(data?.ok || "Usuário excluído.", "success");
      } else {
        toast(data?.error || "Erro ao excluir usuário.", "error");
      }
    } catch {
      toast("Erro de comunicação com a API.", "error");
    } finally {
      setLoadingAcao(null);
    }
  };

  const abrirEdicao = (corretor) => {
    setEditando({
      id_usuarios: corretor.id_usuarios,
      nome: corretor.nome || "",
      username: corretor.username || "",
      email: corretor.email || "",
      telefone: corretor.telefone || "",
      instagram: corretor.instagram || "",
      descricao: corretor.descricao || "",
      permissao: corretor.permissao || "corretor",
      team: corretor.team || "",
      id_imoview: corretor.id_imoview || "",
      novaSenha: "",
    });
  };

  const fecharEdicao = () => setEditando(null);

  const salvarEdicaoUsuario = async () => {
    if (!editando || !usuario) return;

    setSalvandoEdicao(true);

    try {
      const payload = {
        solicitante_id: usuario.id_usuarios,
        id_corretor: editando.id_usuarios,
        nome: editando.nome,
        username: editando.username,
        email: editando.email,
        telefone: editando.telefone,
        instagram: editando.instagram,
        descricao: editando.descricao,
        permissao: editando.permissao,
        team: editando.team,
        id_imoview: editando.id_imoview,
      };

      if (editando.novaSenha) {
        payload.nova_senha = editando.novaSenha;
      }

      const { ok, data } = await apiFetch("/corretor/editar-usuario", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!ok || data?.error) {
        toast(data?.error || "Erro ao editar usuário.", "error");
        return;
      }

      setCorretores((prev) =>
        prev.map((c) =>
          c.id_usuarios === editando.id_usuarios ? { ...c, ...data.usuario } : c
        )
      );
      toast("Usuário atualizado com sucesso.", "success");
      setEditando(null);
    } catch {
      toast("Erro de comunicação com a API.", "error");
    } finally {
      setSalvandoEdicao(false);
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
  }, [usuario, corretores, filtroEquipe, filtroStatus, busca, podeGerenciarTodasEquipes, getNomeEquipe]);

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
                          {isDiretor && <th>Editar</th>}
                        </tr>
                      </thead>

                      <tbody>
                        {corretoresFiltrados.length === 0 ? (
                          <tr>
                            <td
                              colSpan={
                                4 +
                                (podeGerenciarTodasEquipes ? 1 : 0) +
                                (podeGerenciarTodasEquipes || isGerente ? 1 : 0) +
                                (isDiretor ? 1 : 0)
                              }
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
                                    {equipesOpcoes.map((op) => (
                                      <option key={op.value} value={op.value}>
                                        {op.label}
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
                                        ? "controle-corretores__button--ghost-light"
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

                              {isDiretor && (
                                <td>
                                  <div className="controle-corretores__acoes">
                                    <button
                                      type="button"
                                      className="controle-corretores__button controle-corretores__button--ghost-light"
                                      onClick={() => abrirEdicao(c)}
                                    >
                                      Editar
                                    </button>
                                    <button
                                      type="button"
                                      className="controle-corretores__button controle-corretores__button--danger"
                                      disabled={loadingAcao === c.id_usuarios}
                                      onClick={() => excluirUsuario(c)}
                                    >
                                      Excluir
                                    </button>
                                  </div>
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
                              {equipesOpcoes.map((op) => (
                                <option key={op.value} value={op.value}>
                                  {op.label}
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
                                ? "controle-corretores__button--ghost-light"
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

                        {isDiretor && (
                          <button
                            type="button"
                            className="controle-corretores__button controle-corretores__button--ghost-light"
                            style={{ marginTop: "8px" }}
                            onClick={() => abrirEdicao(c)}
                          >
                            Editar
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            {editando && (
              <div className="controle-corretores__modal-overlay" onClick={fecharEdicao}>
                <div
                  className="controle-corretores__modal"
                  onClick={(e) => e.stopPropagation()}
                >
                  <h3 className="controle-corretores__panel-title">
                    Editar usuário {editando.id_usuarios}
                  </h3>

                  <div className="controle-corretores__modal-grid">
                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Nome</label>
                      <input
                        className="controle-corretores__search"
                        value={editando.nome}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, nome: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Username</label>
                      <input
                        className="controle-corretores__search"
                        value={editando.username}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, username: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">E-mail</label>
                      <input
                        className="controle-corretores__search"
                        value={editando.email}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, email: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Telefone</label>
                      <input
                        className="controle-corretores__search"
                        value={editando.telefone}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, telefone: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Instagram</label>
                      <input
                        className="controle-corretores__search"
                        value={editando.instagram}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, instagram: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Código Imoview</label>
                      <input
                        className="controle-corretores__search"
                        inputMode="numeric"
                        placeholder="Ex: 112"
                        value={editando.id_imoview}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, id_imoview: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Permissão</label>
                      <select
                        className="controle-corretores__select"
                        value={editando.permissao}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, permissao: e.target.value }))
                        }
                      >
                        <option value="corretor">Corretor</option>
                        <option value="gerente">Gerente</option>
                        <option value="administrador">Administrador</option>
                        <option value="diretor">Diretor</option>
                      </select>
                    </div>

                    <div className="controle-corretores__field">
                      <label className="controle-corretores__label">Equipe</label>
                      <select
                        className="controle-corretores__select"
                        value={editando.team}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, team: e.target.value }))
                        }
                      >
                        <option value="">Sem equipe</option>
                        {equipesOpcoes.map((op) => (
                          <option key={op.value} value={op.value}>
                            {op.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="controle-corretores__field controle-corretores__field--full">
                      <label className="controle-corretores__label">Descrição</label>
                      <input
                        className="controle-corretores__search"
                        value={editando.descricao}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, descricao: e.target.value }))
                        }
                      />
                    </div>

                    <div className="controle-corretores__field controle-corretores__field--full">
                      <label className="controle-corretores__label">
                        Nova senha (deixe em branco para não alterar)
                      </label>
                      <input
                        type="password"
                        className="controle-corretores__search"
                        value={editando.novaSenha}
                        onChange={(e) =>
                          setEditando((prev) => ({ ...prev, novaSenha: e.target.value }))
                        }
                      />
                    </div>
                  </div>

                  <div className="controle-corretores__modal-actions">
                    <button
                      type="button"
                      className="controle-corretores__button controle-corretores__button--ghost-light"
                      onClick={fecharEdicao}
                      disabled={salvandoEdicao}
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      className="controle-corretores__button controle-corretores__button--primary"
                      onClick={salvarEdicaoUsuario}
                      disabled={salvandoEdicao}
                    >
                      {salvandoEdicao ? "Salvando..." : "Salvar"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ControleCorretores;
