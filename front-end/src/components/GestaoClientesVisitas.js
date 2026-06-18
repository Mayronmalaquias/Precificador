import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
import { useAuth } from "../context/AuthContext";
import "../assets/css/GestaoClientesVisitas.css";

const hoje = new Date();
const hojeStr = hoje.toISOString().slice(0, 10);
const primeiroDiaMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
  .toISOString()
  .slice(0, 10);
const mesAtualStr = hojeStr.slice(0, 7);

const statusAcaoConfig = {
  pendente: { label: "Pendente", className: "is-pending" },
  a_fazer: { label: "A fazer", className: "is-todo" },
  feita: { label: "Feita", className: "is-done" },
};

const gerentesFixos = [
  { id: "G61010", nome: "Thais Tannus" },
  { id: "G61001", nome: "Jose Marques" },
  { id: "G61002", nome: "Marcelo Souza" },
  { id: "G61003", nome: "Luana Salvinski" },
  { id: "G61014", nome: "Marcelo Pincinato" },
  { id: "G61015", nome: "Helio Junio" },
  { id: "G61016", nome: "Paolla Gardenia" },
];

function texto(valor, fallback = "-") {
  const limpo = String(valor ?? "").trim();
  return limpo || fallback;
}

function propostaClasse(valor) {
  const norm = normalizarProposta(valor);
  if (["sim", "proposta", "fez proposta"].includes(norm)) return "is-positive";
  if (norm === "talvez") return "is-warning";
  if (norm === "nao") return "is-muted";
  return "is-neutral";
}

function normalizarProposta(valor) {
  const norm = String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
  if (norm.startsWith("talve")) return "talvez";
  if (norm === "sim" || norm.includes("proposta")) return "sim";
  if (norm === "nao") return "nao";
  return norm || "sem_info";
}

function parseDataBr(valor) {
  const textoData = String(valor || "").trim();
  if (!textoData) return null;
  if (textoData.includes("/")) {
    const [dd, mm, yyyy] = textoData.split("/");
    const data = new Date(Number(yyyy), Number(mm) - 1, Number(dd));
    return Number.isNaN(data.getTime()) ? null : data;
  }
  const data = new Date(textoData);
  return Number.isNaN(data.getTime()) ? null : data;
}

function inicioDoDia(data) {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate());
}

function parseDataIso(valor) {
  const textoData = String(valor || "").trim();
  if (!textoData) return null;
  const [yyyy, mm, dd] = textoData.split("-").map(Number);
  if (!yyyy || !mm || !dd) return null;
  const data = new Date(yyyy, mm - 1, dd);
  return Number.isNaN(data.getTime()) ? null : data;
}

function formatarDataCurta(valor) {
  const data = parseDataIso(valor);
  if (!data) return texto(valor);
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function statusClasseAcao(status) {
  return statusAcaoConfig[status]?.className || statusAcaoConfig.a_fazer.className;
}

function statusLabelAcao(status) {
  return statusAcaoConfig[status]?.label || statusAcaoConfig.a_fazer.label;
}

function statusEfetivoAcao(acao) {
  if (acao?.status === "feita") return "feita";
  const data = parseDataIso(acao?.data_acao);
  if (data && inicioDoDia(data) < inicioDoDia(new Date())) return "pendente";
  return "a_fazer";
}

function resumoAcoes(acoes = []) {
  const pendentes = acoes.filter((acao) => statusEfetivoAcao(acao) === "pendente").length;
  const aFazer = acoes.filter((acao) => statusEfetivoAcao(acao) === "a_fazer").length;
  const feitas = acoes.filter((acao) => statusEfetivoAcao(acao) === "feita").length;
  return { pendentes, aFazer, feitas, total: acoes.length };
}

function montarCalendarioAcoes(mes, acoes = []) {
  const [ano, mesNumero] = String(mes || mesAtualStr).split("-").map(Number);
  const primeiro = new Date(ano, mesNumero - 1, 1);
  const inicio = new Date(primeiro);
  inicio.setDate(primeiro.getDate() - primeiro.getDay());

  const porDia = acoes.reduce((acc, acao) => {
    if (!acao.data_acao) return acc;
    acc[acao.data_acao] = acc[acao.data_acao] || [];
    acc[acao.data_acao].push(acao);
    return acc;
  }, {});

  return Array.from({ length: 42 }, (_, index) => {
    const data = new Date(inicio);
    data.setDate(inicio.getDate() + index);
    const iso = data.toISOString().slice(0, 10);
    return {
      iso,
      dia: data.getDate(),
      foraDoMes: data.getMonth() !== primeiro.getMonth(),
      hoje: iso === hojeStr,
      acoes: porDia[iso] || [],
    };
  });
}

function montarResumoPeriodo(clientes) {
  const agora = inicioDoDia(new Date());
  const inicioSemana = new Date(agora);
  inicioSemana.setDate(agora.getDate() - 6);
  const inicioMes = new Date(agora.getFullYear(), agora.getMonth(), 1);
  const trimestreAtual = Math.floor(agora.getMonth() / 3);
  const inicioTrimestre = new Date(agora.getFullYear(), trimestreAtual * 3, 1);
  const inicioAno = new Date(agora.getFullYear(), 0, 1);
  const visitasUnicas = new Map();

  clientes.forEach((cliente) => {
    (cliente.visitas || []).forEach((visita) => {
      if (visita.id_visita) visitasUnicas.set(visita.id_visita, visita);
    });
  });

  const visitas = Array.from(visitasUnicas.values());
  const contarDesde = (inicio) =>
    visitas.filter((visita) => {
      const data = parseDataBr(visita.data_visita);
      return data && inicioDoDia(data) >= inicio && inicioDoDia(data) <= agora;
    }).length;

  return [
    { id: "semana", label: "Ultimos 7 dias", total: contarDesde(inicioSemana) },
    { id: "mes", label: "Mes atual", total: contarDesde(inicioMes) },
    { id: "trimestre", label: "Trimestre atual", total: contarDesde(inicioTrimestre) },
    { id: "ano", label: "Ano atual", total: contarDesde(inicioAno) },
  ];
}

function ResumoVisitasPeriodo({ serie }) {
  const max = Math.max(1, ...serie.map((item) => Number(item.total) || 0));
  return (
    <section className="gcv-panel gcv-period-panel">
      <div className="gcv-panel-head">
        <h2>Quantidade de visitas pela data</h2>
        <span>Dentro dos filtros aplicados</span>
      </div>
      <div className="gcv-period-grid" role="list">
        {serie.map((item) => (
          <div className="gcv-period-item" key={item.id} role="listitem">
            <div className="gcv-period-top">
              <span>{item.label}</span>
              <strong>{item.total}</strong>
            </div>
            <div className="gcv-bar-track">
              <span
                className="gcv-bar-fill"
                style={{ width: `${Math.max(8, (Number(item.total || 0) / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CalendarioAcoes({ mes, setMes, dias, onSelecionarCliente, onAtualizarStatus, atualizandoAcaoId }) {
  const semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];
  const [diaSelecionado, setDiaSelecionado] = useState(hojeStr);
  const [diaPopup, setDiaPopup] = useState("");
  const diaDetalhe = dias.find((dia) => dia.iso === diaSelecionado) || dias.find((dia) => dia.acoes.length) || dias[0];
  const diaPopupDetalhe = diaPopup ? dias.find((dia) => dia.iso === diaPopup) : null;
  const abrirDia = (dia) => {
    setDiaSelecionado(dia.iso);
    setDiaPopup(dia.iso);
  };
  const fecharDia = () => setDiaPopup("");

  return (
    <section className="gcv-panel gcv-calendar-panel">
      <div className="gcv-panel-head">
        <div>
          <h2>Calendario de acoes</h2>
          <span>Acoes agendadas para os clientes</span>
        </div>
        <input
          className="gcv-month-input"
          type="month"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
        />
      </div>
      <div className="gcv-calendar-week">
        {semana.map((dia) => <span key={dia}>{dia}</span>)}
      </div>
      <div className="gcv-calendar-grid">
        {dias.map((dia) => (
          <div
            key={dia.iso}
            className={`gcv-calendar-day ${dia.foraDoMes ? "is-out" : ""} ${dia.hoje ? "is-today" : ""} ${dia.iso === diaDetalhe?.iso ? "is-selected" : ""} ${dia.acoes.length ? "has-actions" : ""}`}
            onClick={() => abrirDia(dia)}
          >
            <button
              type="button"
              className="gcv-calendar-date"
              onClick={(e) => {
                e.stopPropagation();
                abrirDia(dia);
              }}
            >
              {dia.dia}
            </button>
            <div className="gcv-calendar-actions">
              {dia.acoes.slice(0, 3).map((acao) => (
                <button
                  key={acao.id}
                  type="button"
                  className={`gcv-calendar-action ${statusClasseAcao(acao.status)}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    abrirDia(dia);
                  }}
                  title={`${acao.nome_cliente || "Cliente"} - ${acao.titulo}`}
                >
                  <span>{acao.nome_cliente || "Cliente"}</span>
                  <small>{acao.titulo}</small>
                </button>
              ))}
              {dia.acoes.length > 3 && (
                <button
                  type="button"
                  className="gcv-calendar-more"
                  onClick={(e) => {
                    e.stopPropagation();
                    abrirDia(dia);
                  }}
                >
                  +{dia.acoes.length - 3}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {diaPopupDetalhe && (
        <div className="gcv-modal-backdrop" role="presentation" onClick={fecharDia}>
          <div className="gcv-calendar-modal" role="dialog" aria-modal="true" aria-labelledby="gcv-calendar-modal-title" onClick={(e) => e.stopPropagation()}>
            <div className="gcv-calendar-modal-head">
              <div>
                <h3 id="gcv-calendar-modal-title">Acoes de {formatarDataCurta(diaPopupDetalhe.iso)}</h3>
                <span>{diaPopupDetalhe.acoes.length} acao{diaPopupDetalhe.acoes.length === 1 ? "" : "es"} nesse dia</span>
              </div>
              <button type="button" onClick={fecharDia} aria-label="Fechar">x</button>
            </div>
            {!diaPopupDetalhe.acoes.length ? (
              <div className="gcv-empty gcv-empty-compact">Nenhuma acao nesse dia.</div>
            ) : (
              <div className="gcv-calendar-modal-list">
                {diaPopupDetalhe.acoes.map((acao) => (
                  <article key={acao.id} className={`gcv-calendar-modal-action ${statusClasseAcao(acao.status)}`}>
                    <div className="gcv-calendar-modal-main">
                      <span>{statusLabelAcao(acao.status)}</span>
                      <strong>{acao.nome_cliente || "Cliente"}</strong>
                      <p>{acao.titulo}</p>
                      <small>{acao.descricao || "Sem observacao cadastrada."}</small>
                    </div>
                    <div className="gcv-calendar-modal-buttons">
                      <button
                        type="button"
                        onClick={() => {
                          onSelecionarCliente(acao.id_cliente);
                          fecharDia();
                        }}
                      >
                        Ver cliente
                      </button>
                      <button
                        type="button"
                        className={acao.status === "a_fazer" ? "is-active" : ""}
                        onClick={() => onAtualizarStatus(acao, "a_fazer")}
                        disabled={atualizandoAcaoId === String(acao.id)}
                      >
                        A fazer
                      </button>
                      <button
                        type="button"
                        className={acao.status === "feita" ? "is-active" : ""}
                        onClick={() => onAtualizarStatus(acao, "feita")}
                        disabled={atualizandoAcaoId === String(acao.id)}
                      >
                        Feita
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function GestaoClientesVisitas() {
  const { userData, permissao, isDiretor, isGerente, idCorretor } = useAuth();
  const [filtros, setFiltros] = useState({
    escopo: isDiretor ? "61" : isGerente ? "equipe" : "corretor",
    id_corretor: "",
    id_gerente: "",
    start: primeiroDiaMes,
    end: hojeStr,
    q: "",
    minVisitas: "0",
    proposta: "todas",
  });
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState(null);
  const [clienteSelecionadoId, setClienteSelecionadoId] = useState("");
  const [motivoPorVisita, setMotivoPorVisita] = useState({});
  const [editandoMotivoId, setEditandoMotivoId] = useState("");
  const [salvandoMotivoId, setSalvandoMotivoId] = useState("");
  const [calendarioMes, setCalendarioMes] = useState(mesAtualStr);
  const [abaAtiva, setAbaAtiva] = useState("clientes");
  const [salvandoAcao, setSalvandoAcao] = useState(false);
  const [atualizandoAcaoId, setAtualizandoAcaoId] = useState("");
  const [acaoForm, setAcaoForm] = useState({
    titulo: "",
    descricao: "",
    data_acao: hojeStr,
    status: "a_fazer",
  });

  const usuarioId = idCorretor || userData?.id_usuarios || "";

  const carregar = useCallback(async () => {
    if (!usuarioId || !permissao) return;
    setLoading(true);
    setErro("");
    try {
      const params = new URLSearchParams({
        usuario_id: usuarioId,
        permissao,
        team: userData?.team || "",
        escopo: filtros.escopo,
        id_corretor: filtros.id_corretor,
        id_gerente: filtros.id_gerente,
        start: filtros.start,
        end: filtros.end,
        q: filtros.q,
        limit: "500",
      });
      const resp = await fetch(`${BASE}/gerente-dashboard/gestao-clientes?${params.toString()}`);
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok || !json.ok) throw new Error(json.error || "Erro ao carregar gestao de clientes.");
      setDados(json);
      setClienteSelecionadoId((atual) => {
        if (atual && json.clientes?.some((c) => c.id_cliente === atual)) return atual;
        return json.clientes?.[0]?.id_cliente || "";
      });
    } catch (err) {
      setErro(err.message || "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [
    filtros.escopo,
    filtros.id_corretor,
    filtros.id_gerente,
    filtros.start,
    filtros.end,
    filtros.q,
    permissao,
    userData?.team,
    usuarioId,
  ]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const clientesBase = useMemo(() => dados?.clientes || [], [dados]);
  const corretores = dados?.corretores || [];
  const clientes = useMemo(() => {
    const minVisitas = Number(filtros.minVisitas || 0);
    const propostaFiltro = filtros.proposta;

    return clientesBase
      .filter((cliente) => {
        if ((Number(cliente.qtd_visitas) || 0) < minVisitas) return false;
        if (!propostaFiltro || propostaFiltro === "todas") return true;
        return Object.keys(cliente.propostas || {}).some(
          (proposta) => normalizarProposta(proposta) === propostaFiltro
        );
      })
      .sort((a, b) => {
        const visitasA = Number(a.qtd_visitas) || 0;
        const visitasB = Number(b.qtd_visitas) || 0;
        if (visitasA !== visitasB) return visitasB - visitasA;
        const dataA = parseDataBr(a.ultima_visita)?.getTime() || 0;
        const dataB = parseDataBr(b.ultima_visita)?.getTime() || 0;
        if (dataA !== dataB) return dataB - dataA;
        return String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR");
      });
  }, [clientesBase, filtros.minVisitas, filtros.proposta]);

  const dashboard = useMemo(() => {
    const notas = [];
    const propostas = {};
    let clientesComProposta = 0;
    let totalVisitas = 0;

    clientes.forEach((cliente) => {
      totalVisitas += Number(cliente.qtd_visitas) || 0;
      const nota = Number(cliente.nota_media);
      if (!Number.isNaN(nota)) notas.push(nota);
      if (cliente.houve_proposta) clientesComProposta += 1;
      Object.entries(cliente.propostas || {}).forEach(([proposta, total]) => {
        propostas[proposta] = (propostas[proposta] || 0) + (Number(total) || 0);
      });
    });

    return {
      total_clientes: clientes.length,
      total_visitas: totalVisitas,
      clientes_com_proposta: clientesComProposta,
      nota_media_geral: notas.length
        ? (notas.reduce((acc, nota) => acc + nota, 0) / notas.length).toFixed(1)
        : "-",
      propostas,
    };
  }, [clientes]);

  const clienteSelecionado = useMemo(
    () => clientes.find((item) => item.id_cliente === clienteSelecionadoId) || null,
    [clientes, clienteSelecionadoId]
  );

  const resumoPeriodo = useMemo(() => montarResumoPeriodo(clientes), [clientes]);
  const todasAcoes = useMemo(
    () =>
      clientes.flatMap((cliente) =>
        (cliente.acoes || []).map((acao) => ({
          ...acao,
          status: statusEfetivoAcao(acao),
          nome_cliente: cliente.nome,
          id_corretor: acao.id_corretor || cliente.id_corretor,
        }))
      ),
    [clientes]
  );
  const resumoTodasAcoes = useMemo(() => resumoAcoes(todasAcoes), [todasAcoes]);
  const diasCalendario = useMemo(
    () => montarCalendarioAcoes(calendarioMes, todasAcoes),
    [calendarioMes, todasAcoes]
  );

  useEffect(() => {
    if (!clientes.length) {
      setClienteSelecionadoId("");
      return;
    }
    if (!clientes.some((cliente) => cliente.id_cliente === clienteSelecionadoId)) {
      setClienteSelecionadoId(clientes[0].id_cliente);
    }
  }, [clientes, clienteSelecionadoId]);

  const aplicarMotivoTalvezLocal = (dadosAtual, idVisita, motivo, visitaRef) => {
    if (!dadosAtual?.clientes) return dadosAtual;
    const ehTalvez = String(visitaRef.proposta || "").trim().toLowerCase().startsWith("talve");

    const clientes = dadosAtual.clientes.map((cliente) => {
      const temVisita = (cliente.visitas || []).some((v) => v.id_visita === idVisita);
      if (!temVisita) return cliente;

      const visitas = cliente.visitas.map((v) =>
        v.id_visita === idVisita ? { ...v, motivo_talvez: motivo } : v
      );

      const motivosTalvez = (cliente.motivos_talvez || []).filter((m) => m.id_visita !== idVisita);
      if (ehTalvez && motivo) {
        motivosTalvez.push({
          motivo,
          id_imovel: visitaRef.id_imovel,
          endereco_externo: visitaRef.endereco_externo,
          id_visita: idVisita,
        });
      }

      return { ...cliente, visitas, motivos_talvez: motivosTalvez };
    });

    return { ...dadosAtual, clientes };
  };

  const salvarMotivoTalvez = async (visita) => {
    const idVisita = visita?.id_visita;
    if (!idVisita) return;
    const motivo = motivoPorVisita[idVisita] ?? visita.motivo_talvez ?? "";
    setSalvandoMotivoId(idVisita);
    setErro("");
    try {
      const resp = await fetch(`${BASE}/visitas/${encodeURIComponent(idVisita)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ motivoTalvez: motivo }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok || !json.ok) throw new Error(json.error || "Erro ao salvar motivo.");
      setEditandoMotivoId("");
      setDados((atual) => aplicarMotivoTalvezLocal(atual, idVisita, motivo, visita));
    } catch (err) {
      setErro(err.message || "Erro ao salvar motivo.");
    } finally {
      setSalvandoMotivoId("");
    }
  };

  const salvarAcaoCliente = async () => {
    if (!clienteSelecionado) return;
    setSalvandoAcao(true);
    setErro("");
    try {
      const resp = await fetch(`${BASE}/gerente-dashboard/gestao-clientes/acoes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...acaoForm,
          status: statusEfetivoAcao(acaoForm),
          id_cliente: clienteSelecionado.id_cliente,
          id_corretor: clienteSelecionado.id_corretor,
          criado_por: usuarioId,
        }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok || !json.ok) throw new Error(json.error || "Erro ao salvar acao.");
      setAcaoForm({ titulo: "", descricao: "", data_acao: acaoForm.data_acao, status: "a_fazer" });
      await carregar();
    } catch (err) {
      setErro(err.message || "Erro ao salvar acao.");
    } finally {
      setSalvandoAcao(false);
    }
  };

  const atualizarStatusAcao = async (acao, status) => {
    if (!acao?.id) return;
    setAtualizandoAcaoId(String(acao.id));
    setErro("");
    try {
      const resp = await fetch(`${BASE}/gerente-dashboard/gestao-clientes/acoes/${acao.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok || !json.ok) throw new Error(json.error || "Erro ao atualizar acao.");
      await carregar();
    } catch (err) {
      setErro(err.message || "Erro ao atualizar acao.");
    } finally {
      setAtualizandoAcaoId("");
    }
  };

  return (
    <div className="gcv-page">
      <header className="gcv-header">
        <div>
          <span className="gcv-kicker">Gestao comercial</span>
          <h1>Clientes em visita</h1>
          <p>Acompanhe carteira, historico de visitas, notas e propostas por corretor ou equipe.</p>
        </div>
        <button type="button" className="gcv-primary" onClick={carregar} disabled={loading}>
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </header>

      <section className="gcv-filters">
        <label>
          Escopo
          <select
            value={filtros.escopo}
            onChange={(e) => setFiltros((f) => ({ ...f, escopo: e.target.value, id_corretor: "" }))}
          >
            <option value="corretor">Corretor</option>
            {isGerente && <option value="equipe">Minha equipe</option>}
            {isDiretor && <option value="61">61 inteira</option>}
          </select>
        </label>

        {filtros.escopo === "equipe" && isDiretor && (
          <label>
            Equipe
            <select
              value={filtros.id_gerente}
              onChange={(e) => setFiltros((f) => ({ ...f, id_gerente: e.target.value }))}
            >
              <option value="">Todas as equipes</option>
              {gerentesFixos.map((g) => (
                <option key={g.id} value={g.id}>{g.id} - {g.nome}</option>
              ))}
            </select>
          </label>
        )}

        {filtros.escopo === "corretor" && (isGerente || isDiretor) && (
          <label>
            Corretor
            <select
              value={filtros.id_corretor}
              onChange={(e) => setFiltros((f) => ({ ...f, id_corretor: e.target.value }))}
            >
              <option value="">Selecione</option>
              {corretores.map((c) => (
                <option key={c.id_corretor} value={c.id_corretor}>
                  {c.id_corretor} - {texto(c.nome)}
                </option>
              ))}
            </select>
          </label>
        )}

        <label>
          Inicio
          <input type="date" value={filtros.start} onChange={(e) => setFiltros((f) => ({ ...f, start: e.target.value }))} />
        </label>
        <label>
          Fim
          <input type="date" value={filtros.end} onChange={(e) => setFiltros((f) => ({ ...f, end: e.target.value }))} />
        </label>
        <label>
          Visitas
          <select
            value={filtros.minVisitas}
            onChange={(e) => setFiltros((f) => ({ ...f, minVisitas: e.target.value }))}
          >
            <option value="0">Todas</option>
            <option value="1">1+</option>
            <option value="5">5+</option>
            <option value="10">10+</option>
            <option value="15">15+</option>
            <option value="20">20+</option>
          </select>
        </label>
        <label>
          Proposta
          <select
            value={filtros.proposta}
            onChange={(e) => setFiltros((f) => ({ ...f, proposta: e.target.value }))}
          >
            <option value="todas">Todas</option>
            <option value="sim">Sim</option>
            <option value="nao">Nao</option>
            <option value="talvez">Talvez</option>
          </select>
        </label>
        <label className="gcv-search">
          Buscar
          <input
            type="search"
            value={filtros.q}
            placeholder="Cliente, telefone, corretor..."
            onChange={(e) => setFiltros((f) => ({ ...f, q: e.target.value }))}
          />
        </label>
      </section>

      {erro && <div className="gcv-error">{erro}</div>}

      <div className="gcv-tabs" role="tablist" aria-label="Visoes da gestao de clientes">
        <button
          type="button"
          className={abaAtiva === "clientes" ? "is-active" : ""}
          onClick={() => setAbaAtiva("clientes")}
          role="tab"
          aria-selected={abaAtiva === "clientes"}
        >
          Clientes
        </button>
        <button
          type="button"
          className={abaAtiva === "calendario" ? "is-active" : ""}
          onClick={() => setAbaAtiva("calendario")}
          role="tab"
          aria-selected={abaAtiva === "calendario"}
        >
          Calendario
        </button>
      </div>

      {abaAtiva === "calendario" ? (
        <>
          <section className="gcv-metrics">
            <div><span>Acoes abertas</span><strong>{resumoTodasAcoes.pendentes + resumoTodasAcoes.aFazer}</strong></div>
            <div><span>Pendentes</span><strong>{resumoTodasAcoes.pendentes}</strong></div>
            <div><span>A fazer</span><strong>{resumoTodasAcoes.aFazer}</strong></div>
            <div><span>Feitas</span><strong>{resumoTodasAcoes.feitas}</strong></div>
          </section>

          <div className="gcv-action-status">
            <span className="gcv-action-pill is-pending">Pendente: {resumoTodasAcoes.pendentes}</span>
            <span className="gcv-action-pill is-todo">A fazer: {resumoTodasAcoes.aFazer}</span>
            <span className="gcv-action-pill is-done">Feita: {resumoTodasAcoes.feitas}</span>
          </div>

          <CalendarioAcoes
            mes={calendarioMes}
            setMes={setCalendarioMes}
            dias={diasCalendario}
            onAtualizarStatus={atualizarStatusAcao}
            atualizandoAcaoId={atualizandoAcaoId}
            onSelecionarCliente={(idCliente) => {
              setClienteSelecionadoId(idCliente);
              setAbaAtiva("clientes");
            }}
          />
        </>
      ) : (
        <>
          <section className="gcv-metrics">
            <div><span>Clientes</span><strong>{dashboard.total_clientes || 0}</strong></div>
            <div><span>Visitas</span><strong>{dashboard.total_visitas || 0}</strong></div>
            <div><span>Com proposta</span><strong>{dashboard.clientes_com_proposta || 0}</strong></div>
            <div><span>Nota media</span><strong>{dashboard.nota_media_geral ?? "-"}</strong></div>
          </section>

      <div className="gcv-layout">
        <section className="gcv-panel gcv-clientes-panel">
          <div className="gcv-panel-head">
            <h2>Clientes</h2>
            <span>{clientes.length} registro(s)</span>
          </div>
          <div className="gcv-client-list">
            {!clientes.length ? (
              <div className="gcv-empty">Nenhum cliente encontrado.</div>
            ) : (
              clientes.map((cliente) => (
                (() => {
                  const resumo = resumoAcoes(cliente.acoes || []);
                  return (
                <button
                  type="button"
                  key={cliente.id_cliente}
                  className={`gcv-client-row ${cliente.id_cliente === clienteSelecionadoId ? "is-active" : ""} ${resumo.pendentes ? "has-pending-action" : resumo.aFazer ? "has-todo-action" : resumo.feitas ? "has-done-action" : ""}`}
                  onClick={() => setClienteSelecionadoId(cliente.id_cliente)}
                >
                  <span>
                    <strong>{texto(cliente.nome, "Cliente sem nome")}</strong>
                    <small>{texto(cliente.telefone)} | {texto(cliente.email)}</small>
                    {!!resumo.total && (
                      <small className="gcv-client-action-summary">
                        {resumo.pendentes > 0 && (
                          <span className="gcv-client-action-badge is-pending">
                            {resumo.pendentes} pendente{resumo.pendentes !== 1 ? "s" : ""}
                          </span>
                        )}
                        {resumo.aFazer > 0 && (
                          <span className="gcv-client-action-badge is-todo">
                            {resumo.aFazer} a fazer
                          </span>
                        )}
                        {resumo.feitas > 0 && (
                          <span className="gcv-client-action-badge is-done">
                            {resumo.feitas} feita{resumo.feitas !== 1 ? "s" : ""}
                          </span>
                        )}
                      </small>
                    )}
                  </span>
                  <span className="gcv-row-meta">
                    <strong>{cliente.qtd_visitas}</strong>
                    <small>{texto(cliente.ultima_visita)}</small>
                  </span>
                </button>
                  );
                })()
              ))
            )}
          </div>
        </section>

        <section className="gcv-panel gcv-detail">
          <div className="gcv-panel-head">
            <h2>Detalhe do cliente</h2>
            <span>{texto(clienteSelecionado?.id_cliente)}</span>
          </div>
          {!clienteSelecionado ? (
            <div className="gcv-empty">Selecione um cliente.</div>
          ) : (
            <>
              <div className="gcv-client-summary">
                <div><span>Nome</span><strong>{texto(clienteSelecionado.nome)}</strong></div>
                <div><span>Corretor</span><strong>{texto(clienteSelecionado.corretor)}</strong></div>
                <div><span>Telefone</span><strong>{texto(clienteSelecionado.telefone)}</strong></div>
                <div><span>E-mail</span><strong>{texto(clienteSelecionado.email)}</strong></div>
                <div><span>Nota media</span><strong>{clienteSelecionado.nota_media ?? "-"}</strong></div>
                <div><span>Ultima visita</span><strong>{texto(clienteSelecionado.ultima_visita)}</strong></div>
              </div>

              <div className="gcv-propostas">
                {Object.entries(clienteSelecionado.propostas || {}).map(([nome, total]) => (
                  <span key={nome} className={`gcv-chip ${propostaClasse(nome)}`}>
                    {nome}: {total}
                  </span>
                ))}
              </div>

              <section className="gcv-actions-box">
                <div className="gcv-actions-head">
                  <h3>Acoes do cliente</h3>
                  <span>{(clienteSelecionado.acoes || []).length} registro(s)</span>
                </div>
                <div className="gcv-action-form">
                  <label>
                    Acao
                    <input
                      value={acaoForm.titulo}
                      onChange={(e) => setAcaoForm((f) => ({ ...f, titulo: e.target.value }))}
                      placeholder="Ex.: Ligar para retorno da visita"
                    />
                  </label>
                  <label>
                    Data
                    <input
                      type="date"
                      value={acaoForm.data_acao}
                      onChange={(e) => setAcaoForm((f) => ({ ...f, data_acao: e.target.value }))}
                    />
                  </label>
                  <label>
                    Status
                    <select
                      value={acaoForm.status}
                      onChange={(e) => setAcaoForm((f) => ({ ...f, status: e.target.value }))}
                    >
                      <option value="a_fazer">A fazer</option>
                      <option value="feita">Feita</option>
                    </select>
                  </label>
                  <label className="gcv-action-description">
                    Observacao
                    <textarea
                      value={acaoForm.descricao}
                      onChange={(e) => setAcaoForm((f) => ({ ...f, descricao: e.target.value }))}
                      placeholder="Detalhe rapido para orientar o proximo contato."
                      rows={2}
                    />
                  </label>
                  <button
                    type="button"
                    className="gcv-motive-save"
                    onClick={salvarAcaoCliente}
                    disabled={salvandoAcao || !acaoForm.titulo.trim() || !acaoForm.data_acao}
                  >
                    {salvandoAcao ? "Salvando..." : "Adicionar acao"}
                  </button>
                </div>
                <div className="gcv-actions-list">
                  {!(clienteSelecionado.acoes || []).length ? (
                    <div className="gcv-empty gcv-empty-compact">Nenhuma acao cadastrada.</div>
                  ) : (
                    clienteSelecionado.acoes.map((acao) => {
                        const status = statusEfetivoAcao(acao);
                        return (
                      <article key={acao.id} className={`gcv-action-item ${statusClasseAcao(status)}`}>
                        <div>
                          <strong>{acao.titulo}</strong>
                          <span>{formatarDataCurta(acao.data_acao)} | {statusLabelAcao(status)}</span>
                          {acao.descricao && <p>{acao.descricao}</p>}
                        </div>
                        <div className="gcv-action-buttons">
                          {["a_fazer", "feita"].map((statusOpcao) => (
                            <button
                              key={statusOpcao}
                              type="button"
                              className={status === statusOpcao ? "is-active" : ""}
                              onClick={() => atualizarStatusAcao(acao, statusOpcao)}
                              disabled={atualizandoAcaoId === String(acao.id)}
                            >
                              {statusLabelAcao(statusOpcao)}
                            </button>
                          ))}
                        </div>
                      </article>
                        );
                      })
                  )}
                </div>
              </section>

              {!!clienteSelecionado.motivos_talvez?.length && (
                <div className="gcv-note">
                  <strong>Motivos do talvez</strong>
                  {clienteSelecionado.motivos_talvez.map((item, index) => (
                    <p key={`${item.id_visita || index}-${index}`}>
                      <strong>Imovel {texto(item.id_imovel)}</strong>
                      {item.endereco_externo ? ` (${item.endereco_externo})` : ""}: {item.motivo}
                    </p>
                  ))}
                </div>
              )}

              <div className="gcv-visits">
                {clienteSelecionado.visitas.map((visita) => (
                  <article key={visita.id_visita} className="gcv-visit-card">
                    <div>
                      <strong>{texto(visita.data_visita)} | Imovel {texto(visita.id_imovel)}</strong>
                      <p>{texto(visita.endereco_externo)}</p>
                    </div>
                    <div className="gcv-visit-side">
                      <span className={`gcv-chip ${propostaClasse(visita.proposta)}`}>{texto(visita.proposta)}</span>
                      <strong>Nota {visita.nota_media ?? "-"}</strong>
                    </div>
                    {String(visita.proposta || "").trim().toLowerCase().startsWith("talve") && (
                      editandoMotivoId === visita.id_visita ? (
                        <div className="gcv-motive-editor">
                          <label htmlFor={`motivo-${visita.id_visita}`}>Motivo do talvez</label>
                          <textarea
                            id={`motivo-${visita.id_visita}`}
                            value={motivoPorVisita[visita.id_visita] ?? visita.motivo_talvez ?? ""}
                            onChange={(e) =>
                              setMotivoPorVisita((prev) => ({
                                ...prev,
                                [visita.id_visita]: e.target.value,
                              }))
                            }
                            placeholder="Informe por que o cliente ficou em talvez nessa visita."
                            rows={3}
                          />
                          <div className="gcv-motive-actions">
                            <button
                              type="button"
                              className="gcv-motive-cancel"
                              onClick={() => setEditandoMotivoId("")}
                              disabled={salvandoMotivoId === visita.id_visita}
                            >
                              Cancelar
                            </button>
                            <button
                              type="button"
                              className="gcv-motive-save"
                              onClick={() => salvarMotivoTalvez(visita)}
                              disabled={salvandoMotivoId === visita.id_visita}
                            >
                              {salvandoMotivoId === visita.id_visita ? "Salvando..." : "Salvar motivo"}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="gcv-motive-view">
                          <div>
                            <span>Motivo do talvez</span>
                            <p>{texto(visita.motivo_talvez, "Nenhum motivo informado.")}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setMotivoPorVisita((prev) => ({
                                ...prev,
                                [visita.id_visita]: prev[visita.id_visita] ?? visita.motivo_talvez ?? "",
                              }));
                              setEditandoMotivoId(visita.id_visita);
                            }}
                          >
                            {visita.motivo_talvez ? "Editar motivo" : "Adicionar motivo"}
                          </button>
                        </div>
                      )
                    )}
                    <div className="gcv-score-grid">
                      {(visita.avaliacoes || []).map((av, index) => (
                        <div key={`${visita.id_visita}-${index}`}>
                          <span>{texto(av.cliente, "Avaliacao")}</span>
                          <strong>{texto(av.notaGeral)}</strong>
                          <small>Localizacao {texto(av.localizacao)} | Preco {texto(av.preco)}</small>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </section>
      </div>

      <div className="gcv-charts">
        <ResumoVisitasPeriodo serie={resumoPeriodo} />
      </div>
        </>
      )}
    </div>
  );
}

export default GestaoClientesVisitas;
