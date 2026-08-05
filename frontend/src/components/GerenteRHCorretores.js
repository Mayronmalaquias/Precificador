import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE as API_BASE } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useEquipes } from "../context/EquipesContext";
import { useToast } from "../context/ToastContext";
import {
  RH_FIELDS,
  RH_REQUIRED_FIELDS,
  camposFaltantes,
} from "./rhFields";
import { nomeEquipe as getNomeEquipe } from "../services/equipes";
import "../assets/css/ControleCorretores.css";

const GERENTE_RH_FIELDS = RH_FIELDS.filter(
  (field) => !["desligado", "data_desligamento"].includes(field.name)
);

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
}

function inputValue(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return value ?? "";
}

function formatarBoolean(value) {
  if (value === true || value === "true") return "Sim";
  if (value === false || value === "false") return "Nao";
  return "-";
}

function GerenteRHCorretores() {
  const toast = useToast();
  const { userData, permissao, isGerente, isDiretor } = useAuth();
  const { equipesOpcoes } = useEquipes();
  // gerenteId = id do usuário logado (usado como solicitante_id nas edições de RH).
  const gerenteId = String(
    userData?.id_usuarios ||
    userData?.idCorretor ||
    userData?.id_corretor ||
    userData?.codigo ||
    ""
  );
  // equipeId = a equipe do gerente (`team`). Os corretores compartilham esse team, então o
  // escopo da lista é por team, não pelo id do gerente (ex.: Fernando id C61134 / team G61017).
  const equipeId = String(userData?.team || gerenteId);

  // Diretor não tem equipe fixa: escolhe qual equipe ver. Gerente usa a própria (equipeId).
  const [equipeSelecionada, setEquipeSelecionada] = useState("");
  const escopoTeam = isDiretor ? equipeSelecionada : equipeId;

  const [corretores, setCorretores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busca, setBusca] = useState("");
  const [editando, setEditando] = useState(null);
  const [salvando, setSalvando] = useState(false);

  const carregarCorretores = useCallback(async () => {
    if (!escopoTeam) { setCorretores([]); return; }  // diretor sem equipe escolhida: nada a carregar
    setLoading(true);
    try {
      const query = new URLSearchParams({
        gerente: escopoTeam,
        ativo: "true",
        per_page: "1000",
      });
      const { ok, data } = await apiFetch(`/corretor/retornar-lista?${query.toString()}`);
      if (!ok || data?.error) {
        toast(data?.error || "Erro ao carregar corretores.", "error");
        return;
      }

      const lista = (data.lista || []).filter((item) =>
        item.ativo === true && String(item.permissao || "").toLowerCase() === "corretor"
      );
      setCorretores(lista);
    } catch {
      toast("Erro de comunicacao com a API.", "error");
    } finally {
      setLoading(false);
    }
  }, [escopoTeam, toast]);

  useEffect(() => {
    carregarCorretores();
  }, [carregarCorretores]);

  const corretoresFiltrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return corretores;

    return corretores.filter((item) =>
      [
        item.nome,
        item.username,
        item.id_usuarios,
        item.email_corporativo,
        item.email_pessoal,
        item.telefone_corporativo,
        item.telefone_pessoal,
        item.cpf,
        item.creci,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(termo)
    );
  }, [corretores, busca]);

  const totais = useMemo(() => {
    const comPendencias = corretores.filter((item) => camposFaltantes(item).length > 0).length;
    return {
      total: corretores.length,
      completos: corretores.length - comPendencias,
      comPendencias,
      exibidos: corretoresFiltrados.length,
    };
  }, [corretores, corretoresFiltrados]);

  const abrirEdicao = (corretor) => {
    const form = { ...corretor };
    GERENTE_RH_FIELDS.forEach((field) => {
      form[field.name] = inputValue(corretor[field.name]);
    });
    setEditando(form);
  };

  const salvarEdicao = async () => {
    if (!editando || !gerenteId) return;
    setSalvando(true);
    try {
      const payload = {
        solicitante_id: gerenteId,
        id_corretor: editando.id_usuarios,
      };

      GERENTE_RH_FIELDS.forEach((field) => {
        payload[field.name] = editando[field.name] ?? "";
      });

      const { ok, data } = await apiFetch("/corretor/editar-rh-gerente", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!ok || data?.error) {
        toast(data?.error || "Erro ao salvar dados de RH.", "error");
        return;
      }

      setCorretores((prev) =>
        prev.map((item) => item.id_usuarios === editando.id_usuarios ? { ...item, ...data.usuario } : item)
      );
      setEditando(null);
      toast("Dados de RH atualizados.", "success");
    } catch {
      toast("Erro de comunicacao com a API.", "error");
    } finally {
      setSalvando(false);
    }
  };

  const renderField = (field) => {
    const required = RH_REQUIRED_FIELDS.includes(field.name);
    const value = editando?.[field.name] ?? "";
    const label = `${field.label}${required ? " *" : ""}`;

    if (field.type === "textarea") {
      return (
        <div key={field.name} className="controle-corretores__field controle-corretores__field--full">
          <label className="controle-corretores__label">{label}</label>
          <textarea
            className="controle-corretores__search rh-usuarios__textarea"
            value={value}
            onChange={(e) => setEditando((prev) => ({ ...prev, [field.name]: e.target.value }))}
          />
        </div>
      );
    }

    if (field.type === "boolean") {
      return (
        <div key={field.name} className="controle-corretores__field">
          <label className="controle-corretores__label">{label}</label>
          <select
            className="controle-corretores__select"
            value={value}
            onChange={(e) => setEditando((prev) => ({ ...prev, [field.name]: e.target.value }))}
          >
            <option value="">Selecione...</option>
            <option value="true">Sim</option>
            <option value="false">Nao</option>
          </select>
        </div>
      );
    }

    if (field.type === "select") {
      return (
        <div key={field.name} className="controle-corretores__field">
          <label className="controle-corretores__label">{label}</label>
          <select
            className="controle-corretores__select"
            value={value}
            onChange={(e) => setEditando((prev) => ({ ...prev, [field.name]: e.target.value }))}
          >
            <option value="">Selecione...</option>
            {(field.options || []).map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
      );
    }

    return (
      <div key={field.name} className="controle-corretores__field">
        <label className="controle-corretores__label">{label}</label>
        <input
          className="controle-corretores__search"
          type={field.type || "text"}
          value={value}
          onChange={(e) => setEditando((prev) => ({ ...prev, [field.name]: e.target.value }))}
        />
      </div>
    );
  };

  if (!isGerente && !isDiretor) {
    return (
      <div className="controle-corretores rh-usuarios">
        <div className="controle-corretores__container">
          <section className="controle-corretores__panel">
            <h1 className="controle-corretores__panel-title">Acesso restrito</h1>
            <p className="controle-corretores__panel-subtitle">Esta tela é exclusiva para gerentes e perfis administrativos.</p>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="controle-corretores rh-usuarios gerente-rh">
      <div className="controle-corretores__container">
        <section className="rh-usuarios__hero gerente-rh__hero">
          <div>
            <span className="rh-usuarios__eyebrow">Gerente</span>
            <h1 className="rh-usuarios__title">Dados de RH da equipe</h1>
            <p className="rh-usuarios__subtitle">
              Veja os corretores ativos da sua equipe e preencha as informacoes cadastrais que o RH precisa manter atualizadas.
            </p>
          </div>
          <div className="rh-usuarios__hero-panel">
            <span className="rh-usuarios__hero-label">Equipe</span>
            {isDiretor ? (
              <select
                className="rh-usuarios__hero-select"
                value={equipeSelecionada}
                onChange={(e) => setEquipeSelecionada(e.target.value)}
              >
                <option value="">Selecione uma equipe…</option>
                {equipesOpcoes.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            ) : (
              <strong>{getNomeEquipe(equipeId)}</strong>
            )}
            <span>{userData?.nome || userData?.username || gerenteId} - {permissao || "gerente"}</span>
          </div>
        </section>

        <section className="controle-corretores__summary rh-usuarios__summary gerente-rh__summary">
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Corretores ativos</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.total}</div>
            <div className="controle-corretores__summary-helper">Na sua equipe</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Com pendencias</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.comPendencias}</div>
            <div className="controle-corretores__summary-helper">Campos obrigatorios faltando</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Completos</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.completos}</div>
            <div className="controle-corretores__summary-helper">Sem pendencias de RH</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Exibidos</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.exibidos}</div>
            <div className="controle-corretores__summary-helper">Resultado da busca</div>
          </div>
        </section>

        <section className="controle-corretores__panel rh-usuarios__panel">
          <div className="controle-corretores__panel-top">
            <div>
              <h3 className="controle-corretores__panel-title">Corretores ativos</h3>
              <p className="controle-corretores__panel-subtitle">Clique em um corretor para completar ou revisar os dados de RH.</p>
            </div>
            <div className="rh-usuarios__panel-actions">
              <input
                className="controle-corretores__search gerente-rh__search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por nome, CPF, CRECI, e-mail"
              />
              <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={carregarCorretores}>
                Atualizar
              </button>
            </div>
          </div>

          <div className="controle-corretores__table-wrapper">
            <div className="controle-corretores__table-scroll">
              <table className="controle-corretores__table rh-usuarios__table gerente-rh__table">
                <thead>
                  <tr>
                    <th>Corretor</th>
                    <th>Contato</th>
                    <th>Documentos</th>
                    <th>Status RH</th>
                    <th>Pendencias</th>
                    <th>Acao</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan="6" className="controle-corretores__empty">Carregando...</td></tr>
                  ) : corretoresFiltrados.length === 0 ? (
                    <tr><td colSpan="6" className="controle-corretores__empty">Nenhum corretor ativo encontrado.</td></tr>
                  ) : corretoresFiltrados.map((item) => {
                    const faltantes = camposFaltantes(item);
                    const contato = item.telefone_corporativo || item.telefone_pessoal || item.telefone || "-";
                    const email = item.email_corporativo || item.email_pessoal || item.email || "-";
                    return (
                      <tr key={item.id_usuarios || item.id} onClick={() => abrirEdicao(item)} className="gerente-rh__row">
                        <td>
                          <div className="controle-corretores__nome-wrap">
                            <span className="controle-corretores__nome">{item.nome || item.username || "-"}</span>
                            <span className="controle-corretores__nome-sub">{item.id_usuarios || "-"} - {getNomeEquipe(item.team)}</span>
                          </div>
                        </td>
                        <td>
                          <div className="rh-usuarios__contact">
                            <span>{contato}</span>
                            <small>{email}</small>
                          </div>
                        </td>
                        <td>
                          <div className="rh-usuarios__contact">
                            <span>CPF: {item.cpf || "-"}</span>
                            <small>CRECI: {item.creci || "-"}</small>
                          </div>
                        </td>
                        <td>
                          <span className={`controle-corretores__badge ${faltantes.length === 0 ? "controle-corretores__badge--ativo" : "controle-corretores__badge--inativo"}`}>
                            {faltantes.length === 0 ? "Completo" : "Pendente"}
                          </span>
                        </td>
                        <td>
                          {faltantes.length === 0 ? (
                            <span className="rh-usuarios__ok">Sem pendencias</span>
                          ) : (
                            <div className="rh-usuarios__missing">
                              {faltantes.slice(0, 4).map((field) => field.label).join(", ")}
                              {faltantes.length > 4 ? ` +${faltantes.length - 4}` : ""}
                            </div>
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="controle-corretores__button controle-corretores__button--primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              abrirEdicao(item);
                            }}
                          >
                            Preencher RH
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {editando && (
          <div className="controle-corretores__modal-overlay" onClick={() => setEditando(null)}>
            <div className="controle-corretores__modal rh-usuarios__modal gerente-rh__modal" onClick={(e) => e.stopPropagation()}>
              <h3 className="controle-corretores__panel-title">Dados de RH</h3>
              <p className="controle-corretores__panel-subtitle">
                {editando.nome || editando.username || "-"} - {editando.id_usuarios || "-"} - campos com * sao obrigatorios.
              </p>

              <div className="gerente-rh__modal-alert">
                {camposFaltantes(editando).length === 0 ? (
                  <span className="rh-usuarios__ok">Cadastro completo para o RH.</span>
                ) : (
                  <span>{camposFaltantes(editando).length} pendencia(s): {camposFaltantes(editando).slice(0, 5).map((field) => field.label).join(", ")}</span>
                )}
              </div>

              <div className="controle-corretores__modal-grid">
                {GERENTE_RH_FIELDS.map(renderField)}
              </div>

              <div className="gerente-rh__quick-status">
                <span>Contrato: {formatarBoolean(editando.contrato_assinado)}</span>
                <span>Conduta: {formatarBoolean(editando.codigo_conduta_assinado)}</span>
                <span>LGPD: {formatarBoolean(editando.lgpd_assinada)}</span>
                <span>Onboarding: {formatarBoolean(editando.onboarding_realizado)}</span>
              </div>

              <div className="controle-corretores__modal-actions">
                <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={() => setEditando(null)} disabled={salvando}>
                  Cancelar
                </button>
                <button type="button" className="controle-corretores__button controle-corretores__button--primary" onClick={salvarEdicao} disabled={salvando}>
                  {salvando ? "Salvando..." : "Salvar dados"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default GerenteRHCorretores;
