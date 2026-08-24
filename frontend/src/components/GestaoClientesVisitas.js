import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useEquipes } from "../context/EquipesContext";
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

/** Barras horizontais para distribuicoes por faixa.
 *
 * O denominador e o total de clientes, nao o maior balde: com o maior balde a barra
 * cheia significaria coisas diferentes em cada grafico e daria a impressao de "todo
 * mundo esta aqui" mesmo quando a faixa tem 20% da carteira.
 */
function BarrasFaixa({ titulo, legenda, dados, total, destaque }) {
  const base = Math.max(1, Number(total) || 0);
  return (
    <section className="gcv-panel gcv-analise-panel">
      <div className="gcv-panel-head">
        <h2>{titulo}</h2>
        {legenda && <span>{legenda}</span>}
      </div>
      <div className="gcv-analise-lista" role="list">
        {dados.map((item) => {
          const valor = Number(item.total) || 0;
          const pct = Math.round((valor / base) * 1000) / 10;
          return (
            <div className="gcv-analise-linha" key={item.faixa} role="listitem">
              <span className="gcv-analise-rotulo">{item.faixa}</span>
              <div className="gcv-bar-track">
                <span
                  className={`gcv-bar-fill ${destaque === item.faixa ? "is-alerta" : ""}`}
                  style={{ width: `${valor ? Math.max(3, pct) : 0}%` }}
                />
              </div>
              <span className="gcv-analise-valor">
                {valor} <em>{pct}%</em>
              </span>
            </div>
          );
        })}
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
  const { equipesOpcoes } = useEquipes();
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
  // paralelo p/ o motivo do "sim"
  const [motivoSimPorVisita, setMotivoSimPorVisita] = useState({});
  const [editandoMotivoSimId, setEditandoMotivoSimId] = useState("");
  const [salvandoMotivoSimId, setSalvandoMotivoSimId] = useState("");
  // Ver/editar a visita sem sair da ficha do cliente.
  const [clienteEdicao, setClienteEdicao] = useState(null);
  const [formCliente, setFormCliente] = useState({ nome: "", telefone: "", email: "" });
  const [salvandoCliente, setSalvandoCliente] = useState(false);

  const [visitaEdicao, setVisitaEdicao] = useState(null);
  const [formVisita, setFormVisita] = useState({});
  const [salvandoVisita, setSalvandoVisita] = useState(false);
  const [baixandoPdf, setBaixandoPdf] = useState("");
  // overrides otimistas das flags de revisão (viu_anexo/viu_notas/add_motivo) por visita
  const [flagOverrides, setFlagOverrides] = useState({});
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
    // Filtro de visitas: "N" = N ou mais (N+); "=N" = exatamente N.
    const filtroVisitas = String(filtros.minVisitas || "0");
    const visitasExato = filtroVisitas.startsWith("=");
    const nVisitas = Number(visitasExato ? filtroVisitas.slice(1) : filtroVisitas) || 0;
    const propostaFiltro = filtros.proposta;

    return clientesBase
      .filter((cliente) => {
        const qtd = Number(cliente.qtd_visitas) || 0;
        if (visitasExato) { if (qtd !== nVisitas) return false; }
        else if (qtd < nVisitas) return false;
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

    // Recorrencia — faixas disjuntas: "6 ou mais" comeca acima do teto da faixa
    // anterior, senao um cliente com 6 visitas conta duas vezes e o total estoura.
    const faixasRecorrencia = [
      { faixa: "1 visita", min: 1, max: 1 },
      { faixa: "2 visitas", min: 2, max: 2 },
      { faixa: "3 a 5", min: 3, max: 5 },
      { faixa: "6 ou mais", min: 6, max: null },
    ].map(({ faixa, min, max }) => ({
      faixa,
      total: clientes.filter((c) => {
        const n = Number(c.qtd_visitas) || 0;
        return n >= min && (max === null || n <= max);
      }).length,
    }));

    // Faixas de nota. Cliente sem avaliacao fica fora em vez de virar zero:
    // "nao avaliou" nao e a mesma coisa que "avaliou mal".
    const faixasNota = [
      { faixa: "Ate 5", min: 0, max: 5 },
      { faixa: "5 a 7", min: 5, max: 7 },
      { faixa: "7 a 8,5", min: 7, max: 8.5 },
      { faixa: "8,5 a 10", min: 8.5, max: 10.01 },
    ].map(({ faixa, min, max }) => ({
      faixa,
      total: clientes.filter((c) => {
        const n = Number(c.nota_media);
        return c.nota_media != null && !Number.isNaN(n) && n >= min && n < max;
      }).length,
    }));
    const semNota = clientes.filter(
      (c) => c.nota_media == null || Number.isNaN(Number(c.nota_media)),
    ).length;

    // Carteira parada: dias desde a ultima visita. E o numero que vira acao —
    // os outros sao diagnostico.
    const hojeRef = inicioDoDia(new Date());
    const diasDesde = (cliente) => {
      const d = parseDataBr(cliente.ultima_visita) || parseDataIso(cliente.ultima_visita);
      if (!d) return null;
      return Math.floor((hojeRef - inicioDoDia(d)) / 86400000);
    };
    const faixasRecencia = [
      { faixa: "Ate 15 dias", min: 0, max: 15 },
      { faixa: "16 a 30", min: 16, max: 30 },
      { faixa: "31 a 60", min: 31, max: 60 },
      { faixa: "Mais de 60", min: 61, max: null },
    ].map(({ faixa, min, max }) => ({
      faixa,
      total: clientes.filter((c) => {
        const d = diasDesde(c);
        return d !== null && d >= min && (max === null || d <= max);
      }).length,
    }));
    const semRetorno30 = clientes.filter((c) => {
      const d = diasDesde(c);
      return d !== null && d > 30;
    }).length;

    // Conversao por corretor: quem transforma visita em interesse (SIM ou TALVEZ).
    const porCorretor = {};
    clientes.forEach((cliente) => {
      const chave = cliente.corretor || "Sem corretor";
      if (!porCorretor[chave]) {
        porCorretor[chave] = { corretor: chave, clientes: 0, visitas: 0, comInteresse: 0 };
      }
      const alvo = porCorretor[chave];
      alvo.clientes += 1;
      alvo.visitas += Number(cliente.qtd_visitas) || 0;
      if (cliente.houve_proposta) alvo.comInteresse += 1;
    });
    const rankingCorretor = Object.values(porCorretor)
      .map((item) => ({
        ...item,
        taxa: item.clientes ? Math.round((item.comInteresse / item.clientes) * 1000) / 10 : 0,
      }))
      .sort((a, b) => b.clientes - a.clientes || a.corretor.localeCompare(b.corretor));

    // Qualidade do cadastro: sem telefone nao da para retomar o contato.
    const semContato = clientes.filter(
      (c) => !String(c.telefone || "").trim() && !String(c.email || "").trim(),
    ).length;

    return {
      total_clientes: clientes.length,
      total_visitas: totalVisitas,
      clientes_com_proposta: clientesComProposta,
      nota_media_geral: notas.length
        ? (notas.reduce((acc, nota) => acc + nota, 0) / notas.length).toFixed(1)
        : "-",
      propostas,
      taxa_interesse: clientes.length
        ? Math.round((clientesComProposta / clientes.length) * 1000) / 10
        : 0,
      visitas_por_cliente: clientes.length
        ? (totalVisitas / clientes.length).toFixed(1)
        : "-",
      recorrencia: faixasRecorrencia,
      notas_faixa: faixasNota,
      clientes_sem_nota: semNota,
      recencia: faixasRecencia,
      sem_retorno_30: semRetorno30,
      ranking_corretor: rankingCorretor,
      sem_contato: semContato,
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

  const abrirEdicaoVisita = (visita) => {
    setVisitaEdicao(visita);
    setFormVisita({
      dataVisita: String(visita.data_visita || "").slice(0, 10),
      proposta: visita.proposta || "",
      motivoSim: visita.motivo_sim || "",
      motivoTalvez: visita.motivo_talvez || "",
      enderecoExterno: visita.endereco_externo || "",
      linkImagem: visita.link_imagem || "",
      linkAudio: visita.link_audio || "",
    });
  };

  const fecharEdicaoVisita = () => { setVisitaEdicao(null); setFormVisita({}); };

  const abrirEdicaoCliente = (cliente) => {
    if (!cliente) return;
    setErro("");
    setClienteEdicao(cliente);
    setFormCliente({
      nome: cliente.nome || "",
      telefone: cliente.telefone || "",
      email: cliente.email || "",
    });
  };

  const fecharEdicaoCliente = () => {
    setClienteEdicao(null);
    setFormCliente({ nome: "", telefone: "", email: "" });
  };

  const salvarCliente = async (event) => {
    event.preventDefault();
    if (salvandoCliente || !clienteEdicao) return;
    if (!String(formCliente.nome).trim()) {
      setErro("Nome do cliente nao pode ficar vazio.");
      return;
    }
    setSalvandoCliente(true);
    setErro("");
    try {
      const r = await fetch(`${BASE}/clientes/${encodeURIComponent(clienteEdicao.id_cliente)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: String(formCliente.nome).trim(),
          telefone: String(formCliente.telefone).trim(),
          email: String(formCliente.email).trim(),
          solicitante_id: usuarioId,
        }),
      });
      const json = await r.json().catch(() => ({}));
      if (!r.ok || !json.ok) throw new Error(json.error || "Erro ao salvar cliente.");
      fecharEdicaoCliente();
      carregar();
    } catch (err) {
      setErro(err.message || "Erro ao salvar cliente.");
    } finally {
      setSalvandoCliente(false);
    }
  };

  const salvarVisita = async (event) => {
    event.preventDefault();
    if (salvandoVisita || !visitaEdicao) return;
    const resp = String(formVisita.proposta || "").trim().toLowerCase();
    // Mesma regra do servidor: o campo cobrado depende da resposta.
    if (resp === "sim" && !String(formVisita.motivoSim).trim()) {
      setErro("Resposta SIM exige o motivo."); return;
    }
    if (resp === "talvez" && !String(formVisita.motivoTalvez).trim()) {
      setErro("Resposta TALVEZ exige o motivo."); return;
    }
    setSalvandoVisita(true);
    setErro("");
    try {
      const r = await fetch(`${BASE}/visitas/${encodeURIComponent(visitaEdicao.id_visita)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formVisita),
      });
      const json = await r.json().catch(() => ({}));
      if (!r.ok || !json.ok) throw new Error(json.error || "Erro ao salvar visita.");
      if (String(formVisita.motivoSim || formVisita.motivoTalvez).trim()) {
        marcarFlagVisita(visitaEdicao, { add_motivo: true });
      }
      fecharEdicaoVisita();
      carregar();
    } catch (err) {
      setErro(err.message || "Erro ao salvar visita.");
    } finally {
      setSalvandoVisita(false);
    }
  };

  /** PDF por fetch, não por link: a API exige X-API-KEY, injetado no `fetch` global. */
  const baixarPdfVisita = async (visita) => {
    if (baixandoPdf) return;
    setBaixandoPdf(visita.id_visita);
    setErro("");
    try {
      const r = await fetch(`${BASE}/visitas/pdf/download?visita_id=${encodeURIComponent(visita.id_visita)}`);
      if (!r.ok) throw new Error("Não consegui gerar o PDF.");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `visita-${visita.id_visita}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setErro(err.message);
    } finally {
      setBaixandoPdf("");
    }
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
      if (motivo.trim()) marcarFlagVisita(visita, { add_motivo: true });
    } catch (err) {
      setErro(err.message || "Erro ao salvar motivo.");
    } finally {
      setSalvandoMotivoId("");
    }
  };

  // Flags efetivas = as do banco (visita.flags) + overrides otimistas locais.
  const flagsDaVisita = (visita) => ({
    ...(visita?.flags || {}),
    ...(flagOverrides[visita?.id_visita] || {}),
  });

  // Marca flag(s) de revisão do gerente. Grava sob o gerente RESPONSÁVEL pelo corretor
  // (id_gerente_corretor) p/ o diretor enxergar; cai no usuário logado se faltar.
  const marcarFlagVisita = (visita, flags = {}) => {
    const idVisita = visita?.id_visita;
    if (!idVisita) return;
    const gerenteKey = visita?.id_gerente_corretor || usuarioId;
    if (!gerenteKey) return;
    const viu_anexo = !!flags.viu_anexo;
    const viu_notas = !!flags.viu_notas;
    const add_motivo = !!flags.add_motivo;
    setFlagOverrides((prev) => {
      const cur = prev[idVisita] || {};
      return {
        ...prev,
        [idVisita]: {
          viu_anexo: cur.viu_anexo || viu_anexo || !!(visita.flags || {}).viu_anexo,
          viu_notas: cur.viu_notas || viu_notas || !!(visita.flags || {}).viu_notas,
          add_motivo: cur.add_motivo || add_motivo || !!(visita.flags || {}).add_motivo,
        },
      };
    });
    fetch(`${BASE}/visitas/vistas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_gerente: gerenteKey, id_visita: idVisita, viu_anexo, viu_notas, add_motivo }),
    })
      .then((r) => r.json())
      .then((d) => { if (!d.ok) console.error("[vistas POST] erro:", d); })
      .catch((e) => console.error("[vistas POST] fetch falhou:", e));
  };

  const aplicarMotivoSimLocal = (dadosAtual, idVisita, motivo, visitaRef) => {
    if (!dadosAtual?.clientes) return dadosAtual;
    const clientes = dadosAtual.clientes.map((cliente) => {
      const temVisita = (cliente.visitas || []).some((v) => v.id_visita === idVisita);
      if (!temVisita) return cliente;
      const visitas = cliente.visitas.map((v) =>
        v.id_visita === idVisita ? { ...v, motivo_sim: motivo } : v
      );
      const motivosSim = (cliente.motivos_sim || []).filter((m) => m.id_visita !== idVisita);
      if (motivo) {
        motivosSim.push({
          motivo,
          id_imovel: visitaRef.id_imovel,
          endereco_externo: visitaRef.endereco_externo,
          id_visita: idVisita,
        });
      }
      return { ...cliente, visitas, motivos_sim: motivosSim };
    });
    return { ...dadosAtual, clientes };
  };

  const salvarMotivoSim = async (visita) => {
    const idVisita = visita?.id_visita;
    if (!idVisita) return;
    const motivo = motivoSimPorVisita[idVisita] ?? visita.motivo_sim ?? "";
    setSalvandoMotivoSimId(idVisita);
    setErro("");
    try {
      const resp = await fetch(`${BASE}/visitas/${encodeURIComponent(idVisita)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ motivoSim: motivo }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok || !json.ok) throw new Error(json.error || "Erro ao salvar motivo.");
      setEditandoMotivoSimId("");
      setDados((atual) => aplicarMotivoSimLocal(atual, idVisita, motivo, visita));
      if (motivo.trim()) marcarFlagVisita(visita, { add_motivo: true });
    } catch (err) {
      setErro(err.message || "Erro ao salvar motivo.");
    } finally {
      setSalvandoMotivoSimId("");
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
              {equipesOpcoes.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
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
            <option value="=1">Exatamente 1</option>
            <option value="=3">Exatamente 3</option>
            <option value="1">1+</option>
            <option value="3">3+</option>
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
        <button
          type="button"
          className={abaAtiva === "analise" ? "is-active" : ""}
          onClick={() => setAbaAtiva("analise")}
          role="tab"
          aria-selected={abaAtiva === "analise"}
        >
          Analise
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
      ) : abaAtiva === "analise" ? (
        <>
          <section className="gcv-metrics">
            <div><span>Clientes</span><strong>{dashboard.total_clientes || 0}</strong></div>
            <div><span>Taxa de interesse</span><strong>{dashboard.taxa_interesse}%</strong></div>
            <div><span>Visitas por cliente</span><strong>{dashboard.visitas_por_cliente}</strong></div>
            <div><span>Nota media</span><strong>{dashboard.nota_media_geral ?? "-"}</strong></div>
            <div><span>Sem retorno 30d</span><strong>{dashboard.sem_retorno_30}</strong></div>
            <div><span>Sem telefone/e-mail</span><strong>{dashboard.sem_contato}</strong></div>
          </section>

          <p className="gcv-analise-nota">
            Tudo abaixo responde aos mesmos filtros da aba Clientes, inclusive a busca.
            &quot;Interesse&quot; e a visita que terminou em SIM ou TALVEZ — nao e proposta
            lancada.
          </p>

          <div className="gcv-analise-grid">
            <BarrasFaixa
              titulo="Recorrencia"
              legenda="Visitas por cliente no periodo"
              dados={dashboard.recorrencia}
              total={dashboard.total_clientes}
              destaque="1 visita"
            />
            <BarrasFaixa
              titulo="Ultima visita"
              legenda="Quanto tempo faz que o cliente nao e visitado"
              dados={dashboard.recencia}
              total={dashboard.total_clientes}
              destaque="Mais de 60"
            />
            <BarrasFaixa
              titulo="Nota do imovel"
              legenda={`${dashboard.clientes_sem_nota} sem avaliacao (fora do grafico)`}
              dados={dashboard.notas_faixa}
              total={dashboard.total_clientes - dashboard.clientes_sem_nota}
              destaque="Ate 5"
            />
            <section className="gcv-panel gcv-analise-panel">
              <div className="gcv-panel-head">
                <h2>Resposta da visita</h2>
                <span>Somando todas as visitas do periodo</span>
              </div>
              <div className="gcv-analise-lista" role="list">
                {["Sim", "Talvez", "Nao"].map((chave) => {
                  const valor = Number(dashboard.propostas?.[chave]) || 0;
                  const soma = Object.values(dashboard.propostas || {}).reduce(
                    (acc, n) => acc + (Number(n) || 0),
                    0,
                  );
                  const pct = soma ? Math.round((valor / soma) * 1000) / 10 : 0;
                  return (
                    <div className="gcv-analise-linha" key={chave} role="listitem">
                      <span className="gcv-analise-rotulo">{chave}</span>
                      <div className="gcv-bar-track">
                        <span
                          className={`gcv-bar-fill ${chave === "Nao" ? "is-alerta" : ""}`}
                          style={{ width: `${valor ? Math.max(3, pct) : 0}%` }}
                        />
                      </div>
                      <span className="gcv-analise-valor">{valor} <em>{pct}%</em></span>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <section className="gcv-panel gcv-analise-panel">
            <div className="gcv-panel-head">
              <h2>Por corretor</h2>
              <span>Ordenado por carteira no periodo</span>
            </div>
            <div className="gcv-tabela-wrap">
              <table className="gcv-analise-tabela">
                <thead>
                  <tr>
                    <th>Corretor</th>
                    <th>Clientes</th>
                    <th>Visitas</th>
                    <th>Visitas/cliente</th>
                    <th>Com interesse</th>
                    <th>Taxa</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.ranking_corretor.length === 0 ? (
                    <tr><td colSpan={6}>Nenhum cliente nos filtros aplicados.</td></tr>
                  ) : (
                    dashboard.ranking_corretor.map((item) => (
                      <tr key={item.corretor}>
                        <td>{item.corretor}</td>
                        <td>{item.clientes}</td>
                        <td>{item.visitas}</td>
                        <td>{(item.visitas / item.clientes).toFixed(1)}</td>
                        <td>{item.comInteresse}</td>
                        <td>
                          <span className={`gcv-taxa ${item.taxa < 50 ? "is-baixa" : ""}`}>
                            {item.taxa}%
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
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
            <div className="gcv-panel-head-acoes">
              <span>{texto(clienteSelecionado?.id_cliente)}</span>
              {clienteSelecionado && (
                <button
                  type="button"
                  className="gcv-motive-save"
                  onClick={() => abrirEdicaoCliente(clienteSelecionado)}
                >
                  Editar cliente
                </button>
              )}
            </div>
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

              {!!clienteSelecionado.motivos_sim?.length && (
                <div className="gcv-note">
                  <strong>Motivos do sim</strong>
                  {clienteSelecionado.motivos_sim.map((item, index) => (
                    <p key={`sim-${item.id_visita || index}-${index}`}>
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

                    {normalizarProposta(visita.proposta) === "sim" && (
                      editandoMotivoSimId === visita.id_visita ? (
                        <div className="gcv-motive-editor">
                          <label htmlFor={`motivosim-${visita.id_visita}`}>Motivo do sim</label>
                          <textarea
                            id={`motivosim-${visita.id_visita}`}
                            value={motivoSimPorVisita[visita.id_visita] ?? visita.motivo_sim ?? ""}
                            onChange={(e) =>
                              setMotivoSimPorVisita((prev) => ({
                                ...prev,
                                [visita.id_visita]: e.target.value,
                              }))
                            }
                            placeholder="Informe por que o cliente disse sim nessa visita."
                            rows={3}
                          />
                          <div className="gcv-motive-actions">
                            <button
                              type="button"
                              className="gcv-motive-cancel"
                              onClick={() => setEditandoMotivoSimId("")}
                              disabled={salvandoMotivoSimId === visita.id_visita}
                            >
                              Cancelar
                            </button>
                            <button
                              type="button"
                              className="gcv-motive-save"
                              onClick={() => salvarMotivoSim(visita)}
                              disabled={salvandoMotivoSimId === visita.id_visita}
                            >
                              {salvandoMotivoSimId === visita.id_visita ? "Salvando..." : "Salvar motivo"}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="gcv-motive-view">
                          <div>
                            <span>Motivo do sim</span>
                            <p>{texto(visita.motivo_sim, "Nenhum motivo informado.")}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setMotivoSimPorVisita((prev) => ({
                                ...prev,
                                [visita.id_visita]: prev[visita.id_visita] ?? visita.motivo_sim ?? "",
                              }));
                              setEditandoMotivoSimId(visita.id_visita);
                            }}
                          >
                            {visita.motivo_sim ? "Editar motivo" : "Adicionar motivo"}
                          </button>
                        </div>
                      )
                    )}

                    <div className="gcv-review" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginTop: 8 }}>
                      {/* O anexo que abre e `link_imagem`. `anexo_ficha` e caminho
                          relativo do AppSheet e NUNCA e URL — o botao marcava a flag e
                          nao abria nada. */}
                      {(visita.link_imagem || visita.anexo_ficha) && (
                        <button
                          type="button"
                          className="gcv-motive-save"
                          onClick={() => {
                            marcarFlagVisita(visita, { viu_anexo: true });
                            const alvo = visita.link_imagem || visita.anexo_ficha;
                            if (/^https?:/i.test(alvo)) window.open(alvo, "_blank", "noopener");
                            else setErro("Esta visita não tem link de anexo utilizável. Edite a visita para adicionar.");
                          }}
                        >
                          Ver anexo
                        </button>
                      )}
                      <button type="button" className="gcv-motive-save" onClick={() => abrirEdicaoVisita(visita)}>
                        Ver / editar visita
                      </button>
                      <button
                        type="button"
                        className="gcv-motive-save"
                        onClick={() => baixarPdfVisita(visita)}
                        disabled={baixandoPdf === visita.id_visita}
                      >
                        {baixandoPdf === visita.id_visita ? "Gerando…" : "PDF"}
                      </button>
                      {visita.notas && (
                        <details onToggle={(e) => { if (e.currentTarget.open) marcarFlagVisita(visita, { viu_notas: true }); }}>
                          <summary style={{ cursor: "pointer" }}>Ver notas</summary>
                          <p style={{ whiteSpace: "pre-wrap" }}>{visita.notas}</p>
                        </details>
                      )}
                      {(() => {
                        const f = flagsDaVisita(visita);
                        const badge = (ok, label, short) => (
                          <span
                            key={short}
                            title={`${label}: ${ok ? "sim" : "pendente"}`}
                            style={{ display: "inline-block", minWidth: 22, textAlign: "center", padding: "1px 6px", borderRadius: 6, fontSize: 11, fontWeight: 700, background: ok ? "#dcfce7" : "#fee2e2", color: ok ? "#15803d" : "#b91c1c" }}
                          >
                            {short}{ok ? "✓" : "!"}
                          </span>
                        );
                        return (
                          <span style={{ display: "inline-flex", gap: 4, marginLeft: "auto" }}>
                            {badge(f.viu_anexo, "Viu anexo", "A")}
                            {badge(f.viu_notas, "Viu notas", "N")}
                            {badge(f.add_motivo, "Adicionou motivo", "M")}
                          </span>
                        );
                      })()}
                    </div>

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

      {clienteEdicao && (
        <div className="gcv-modal-bg" onClick={fecharEdicaoCliente}>
          <form className="gcv-modal" onClick={(e) => e.stopPropagation()} onSubmit={salvarCliente}>
            <header>
              <div>
                <span className="gcv-modal-eyebrow">Cliente {clienteEdicao.id_cliente}</span>
                <h3>{clienteEdicao.nome || "Editar cliente"}</h3>
              </div>
              <button type="button" onClick={fecharEdicaoCliente} aria-label="Fechar">✕</button>
            </header>

            <p className="gcv-modal-alvo">
              {clienteEdicao.corretor || "Sem corretor"}
              <small>{clienteEdicao.qtd_visitas || 0} visita(s) no periodo</small>
            </p>

            <div className="gcv-modal-grid">
              <label className="gcv-largo">Nome
                <input type="text" value={formCliente.nome}
                  onChange={(e) => setFormCliente((f) => ({ ...f, nome: e.target.value }))} />
              </label>
              <label>Telefone
                <input type="text" value={formCliente.telefone} placeholder="61999999999"
                  onChange={(e) => setFormCliente((f) => ({ ...f, telefone: e.target.value }))} />
              </label>
              <label>E-mail
                <input type="email" value={formCliente.email} placeholder="cliente@email.com"
                  onChange={(e) => setFormCliente((f) => ({ ...f, email: e.target.value }))} />
              </label>
            </div>

            <p className="gcv-modal-dica">
              Corrigir aqui vale para todo o historico do cliente — as visitas antigas
              passam a mostrar o nome novo.
            </p>

            <footer>
              <span className="gcv-espaco" />
              <button type="button" className="gcv-motive-save" onClick={fecharEdicaoCliente}>
                Cancelar
              </button>
              <button type="submit" className="gcv-modal-primario" disabled={salvandoCliente}>
                {salvandoCliente ? "Salvando..." : "Salvar cliente"}
              </button>
            </footer>
          </form>
        </div>
      )}

      {visitaEdicao && (
        <div className="gcv-modal-bg" onClick={fecharEdicaoVisita}>
          <form className="gcv-modal" onClick={(e) => e.stopPropagation()} onSubmit={salvarVisita}>
            <header>
              <div>
                <span className="gcv-modal-eyebrow">Visita {visitaEdicao.id_visita}</span>
                <h3>{visitaEdicao.id_imovel || visitaEdicao.endereco_externo || "Editar visita"}</h3>
              </div>
              <button type="button" onClick={fecharEdicaoVisita} aria-label="Fechar">✕</button>
            </header>

            <p className="gcv-modal-alvo">
              {(visitaEdicao.clientes || []).join(", ") || "Sem cliente"}
              <small>{visitaEdicao.corretor || ""}</small>
            </p>

            <div className="gcv-modal-grid">
              <label>Data da visita
                <input type="date" value={formVisita.dataVisita || ""}
                  onChange={(e) => setFormVisita((f) => ({ ...f, dataVisita: e.target.value }))} />
              </label>
              <label>Resposta do cliente
                <select value={formVisita.proposta || ""}
                  onChange={(e) => setFormVisita((f) => ({ ...f, proposta: e.target.value }))}>
                  <option value="">Não respondido</option>
                  <option value="Sim">SIM</option>
                  <option value="Talvez">TALVEZ</option>
                  <option value="Nao">NÃO</option>
                </select>
              </label>

              {/* Só o motivo da resposta escolhida — pedir os dois convida a preencher o
                  errado, e é o campo errado que deixa a pendência de pé. */}
              {String(formVisita.proposta || "").toLowerCase() === "sim" && (
                <label className="gcv-largo">Motivo do SIM *
                  <textarea rows={2} value={formVisita.motivoSim || ""}
                    onChange={(e) => setFormVisita((f) => ({ ...f, motivoSim: e.target.value }))} />
                </label>
              )}
              {String(formVisita.proposta || "").toLowerCase() === "talvez" && (
                <label className="gcv-largo">Motivo do TALVEZ *
                  <textarea rows={2} value={formVisita.motivoTalvez || ""}
                    onChange={(e) => setFormVisita((f) => ({ ...f, motivoTalvez: e.target.value }))} />
                </label>
              )}

              <label className="gcv-largo">Link da imagem (anexo)
                <input value={formVisita.linkImagem || ""} placeholder="https://drive.google.com/…"
                  onChange={(e) => setFormVisita((f) => ({ ...f, linkImagem: e.target.value }))} />
              </label>
              <label className="gcv-largo">Link do áudio
                <input value={formVisita.linkAudio || ""} placeholder="https://drive.google.com/…"
                  onChange={(e) => setFormVisita((f) => ({ ...f, linkAudio: e.target.value }))} />
              </label>
              <label className="gcv-largo">Endereço externo
                <input value={formVisita.enderecoExterno || ""}
                  placeholder="Só para imóvel fora do CRM"
                  onChange={(e) => setFormVisita((f) => ({ ...f, enderecoExterno: e.target.value }))} />
              </label>
            </div>

            <footer>
              <button type="button" className="gcv-motive-save"
                onClick={() => baixarPdfVisita(visitaEdicao)}
                disabled={baixandoPdf === visitaEdicao.id_visita}>
                {baixandoPdf === visitaEdicao.id_visita ? "Gerando…" : "Baixar PDF"}
              </button>
              <span className="gcv-espaco" />
              <button type="button" className="gcv-motive-save" onClick={fecharEdicaoVisita}
                disabled={salvandoVisita}>Cancelar</button>
              <button type="submit" className="gcv-modal-primario" disabled={salvandoVisita}>
                {salvandoVisita ? "Salvando…" : "Salvar visita"}
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
}

export default GestaoClientesVisitas;
