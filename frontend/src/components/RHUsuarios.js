import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE as API_BASE } from "../services/api";
import { useToast } from "../context/ToastContext";
import {
  RH_FIELDS,
  RH_REQUIRED_FIELDS,
  camposFaltantes,
} from "./rhFields";
import { useEquipes } from "../context/EquipesContext";
import "../assets/css/ControleCorretores.css";
import "../assets/css/RHUsuarios.css";

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

function usuarioEmSaida(usuario) {
  return usuario?.desligado === true || String(usuario?.desligado) === "true";
}

const MESES = [
  "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];

function dateKey(date) {
  const ano = date.getFullYear();
  const mes = String(date.getMonth() + 1).padStart(2, "0");
  const dia = String(date.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function calcularPascoa(ano) {
  const a = ano % 19;
  const b = Math.floor(ano / 100);
  const c = ano % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31);
  const dia = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(ano, mes - 1, dia);
}

function feriadosBrasil(ano) {
  const pascoa = calcularPascoa(ano);
  const fixos = [
    [1, 1, "Confraternizacao Universal"],
    [4, 21, "Tiradentes"],
    [5, 1, "Dia do Trabalho"],
    [9, 7, "Independencia do Brasil"],
    [10, 12, "Nossa Senhora Aparecida"],
    [11, 2, "Finados"],
    [11, 15, "Proclamacao da Republica"],
    [11, 20, "Consciencia Negra"],
    [12, 25, "Natal"],
  ].map(([mes, dia, titulo]) => ({
    key: dateKey(new Date(ano, mes - 1, dia)),
    titulo,
    tipo: "feriado",
  }));

  const moveis = [
    [addDays(pascoa, -48), "Carnaval"],
    [addDays(pascoa, -47), "Carnaval"],
    [addDays(pascoa, -2), "Sexta-feira Santa"],
    [pascoa, "Pascoa"],
    [addDays(pascoa, 60), "Corpus Christi"],
  ].map(([data, titulo]) => ({
    key: dateKey(data),
    titulo,
    tipo: "feriado",
  }));

  return [...fixos, ...moveis];
}

function RHUsuarios() {
  const toast = useToast();
  const { equipesOpcoes, getNomeEquipe } = useEquipes();
  const [usuario, setUsuario] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("pendentes");
  const [busca, setBusca] = useState("");
  const [filtroEquipe, setFiltroEquipe] = useState("");
  const [filtroAtivo, setFiltroAtivo] = useState("");
  const [filtroPermissao, setFiltroPermissao] = useState("");
  const [filtroPendencia, setFiltroPendencia] = useState("");
  const [filtroStatusRh, setFiltroStatusRh] = useState("");
  const [filtroEntradaInicio, setFiltroEntradaInicio] = useState("");
  const [filtroEntradaFim, setFiltroEntradaFim] = useState("");
  const [filtroDesligamento, setFiltroDesligamento] = useState("");
  const [filtroCreci, setFiltroCreci] = useState("");
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const [calendarioData, setCalendarioData] = useState(() => new Date());
  const [calendarioAberto, setCalendarioAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [detalhando, setDetalhando] = useState(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("userData");
      if (!raw) return;
      const data = JSON.parse(raw);
      setUsuario({
        id_usuarios: data.id_usuarios || data.idCorretor || data.id || "",
        nome: data.nome || data.username || "Usuario",
        permissao: data.permissao || "",
        team: data.team || "",
      });
    } catch {
      setUsuario(null);
    }
  }, []);

  const carregarUsuarios = useCallback(async () => {
    setLoading(true);
    try {
      const { ok, data } = await apiFetch("/corretor/retornar-lista?per_page=1000");
      if (!ok || data?.error) {
        toast(data?.error || "Erro ao carregar usuários.", "error");
        return;
      }
      setUsuarios(data.lista || []);
    } catch {
      toast("Erro de comunicação com a API.", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    carregarUsuarios();
  }, [carregarUsuarios]);

  const equipes = useMemo(() => {
    const usadas = new Set(usuarios.map((u) => String(u.team || "")).filter(Boolean));
    return equipesOpcoes.filter((equipe) => usadas.has(equipe.value));
  }, [usuarios, equipesOpcoes]);

  const usuariosFiltrados = useMemo(() => {
    let lista = [...usuarios];
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);

    if (viewMode === "pendentes") lista = lista.filter((u) => u.ativo === false && !usuarioEmSaida(u));
    if (viewMode === "todos") lista = lista.filter((u) => u.ativo === true && !usuarioEmSaida(u));
    if (viewMode === "pendencias") lista = lista.filter((u) => u.ativo === true && !usuarioEmSaida(u) && camposFaltantes(u).length > 0);
    if (viewMode === "saidas") lista = lista.filter((u) => usuarioEmSaida(u));

    if (filtroEquipe) lista = lista.filter((u) => String(u.team || "") === filtroEquipe);
    if (filtroAtivo) lista = lista.filter((u) => String(Boolean(u.ativo)) === filtroAtivo);
    if (filtroPermissao) lista = lista.filter((u) => String(u.permissao || "") === filtroPermissao);
    if (filtroPendencia === "faltando") lista = lista.filter((u) => camposFaltantes(u).length > 0);
    if (filtroPendencia === "completo") lista = lista.filter((u) => camposFaltantes(u).length === 0);
    if (filtroStatusRh) lista = lista.filter((u) => String(u.status || "") === filtroStatusRh);
    if (filtroEntradaInicio) lista = lista.filter((u) => u.data_entrada_61 && u.data_entrada_61 >= filtroEntradaInicio);
    if (filtroEntradaFim) lista = lista.filter((u) => u.data_entrada_61 && u.data_entrada_61 <= filtroEntradaFim);
    if (filtroDesligamento === "desligado") lista = lista.filter((u) => usuarioEmSaida(u));
    if (filtroDesligamento === "nao_desligado") lista = lista.filter((u) => !usuarioEmSaida(u));
    if (filtroDesligamento === "com_data") lista = lista.filter((u) => Boolean(u.data_desligamento));
    if (filtroDesligamento === "sem_data") lista = lista.filter((u) => !u.data_desligamento);
    if (filtroCreci) {
      lista = lista.filter((u) => {
        if (!u.validade_creci) return filtroCreci === "sem_validade";
        const validade = new Date(`${u.validade_creci}T00:00:00`);
        const diffDias = Math.ceil((validade - hoje) / 86400000);
        if (filtroCreci === "vencido") return diffDias < 0;
        if (filtroCreci === "vence_30") return diffDias >= 0 && diffDias <= 30;
        if (filtroCreci === "valido") return diffDias > 30;
        return true;
      });
    }

    const termo = busca.trim().toLowerCase();
    if (termo) {
      lista = lista.filter((u) =>
        [
          u.nome,
          u.username,
          u.id_usuarios,
          u.email_corporativo,
          u.cpf,
          getNomeEquipe(u.team),
          u.permissao,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(termo)
      );
    }

    return lista;
  }, [
    usuarios, viewMode, filtroEquipe, filtroAtivo, filtroPermissao, filtroPendencia,
    filtroStatusRh, filtroEntradaInicio, filtroEntradaFim, filtroDesligamento,
    filtroCreci, busca, getNomeEquipe,
  ]);

  const painelRh = useMemo(() => ({
    pendentesAtivacao: usuarios.filter((u) => u.ativo === false && !usuarioEmSaida(u)).length,
    ativos: usuarios.filter((u) => u.ativo === true && !usuarioEmSaida(u)).length,
    pendencias: usuarios.filter((u) => u.ativo === true && !usuarioEmSaida(u) && camposFaltantes(u).length > 0).length,
    saidas: usuarios.filter((u) => usuarioEmSaida(u)).length,
    diretores: usuarios.filter((u) => u.permissao === "diretor").length,
  }), [usuarios]);

  const totais = useMemo(() => {
    const pendentes = usuariosFiltrados.filter((u) => camposFaltantes(u).length > 0).length;
    return {
      total: usuariosFiltrados.length,
      ativos: usuariosFiltrados.filter((u) => u.ativo === true).length,
      inativos: usuariosFiltrados.filter((u) => u.ativo === false).length,
      pendentes,
      desligados: usuariosFiltrados.filter((u) => usuarioEmSaida(u)).length,
    };
  }, [usuariosFiltrados]);

  const limparFiltros = () => {
    setBusca("");
    setFiltroEquipe("");
    setFiltroAtivo("");
    setFiltroPermissao("");
    setFiltroPendencia("");
    setFiltroStatusRh("");
    setFiltroEntradaInicio("");
    setFiltroEntradaFim("");
    setFiltroDesligamento("");
    setFiltroCreci("");
  };

  const calendarioAno = calendarioData.getFullYear();
  const calendarioMes = calendarioData.getMonth();

  const eventosCalendario = useMemo(() => {
    const eventosPorDia = {};
    const anos = [calendarioAno - 1, calendarioAno, calendarioAno + 1];

    const adicionarEvento = (key, evento) => {
      if (!eventosPorDia[key]) eventosPorDia[key] = [];
      eventosPorDia[key].push(evento);
    };

    anos.forEach((ano) => {
      feriadosBrasil(ano).forEach((feriado) => {
        adicionarEvento(feriado.key, feriado);
      });

      usuarios.forEach((item) => {
        if (!item.data_nascimento || usuarioEmSaida(item)) return;
        const [, mes, dia] = String(item.data_nascimento).split("-");
        if (!mes || !dia) return;
        adicionarEvento(`${ano}-${mes}-${dia}`, {
          tipo: "aniversario",
          titulo: item.nome || item.username || "Usuario",
          detalhe: getNomeEquipe(item.team),
        });
      });
    });

    return eventosPorDia;
  }, [usuarios, calendarioAno, getNomeEquipe]);

  const diasCalendario = useMemo(() => {
    const primeiroDiaMes = new Date(calendarioAno, calendarioMes, 1);
    const inicio = addDays(primeiroDiaMes, -primeiroDiaMes.getDay());
    const hojeKey = dateKey(new Date());

    return Array.from({ length: 42 }, (_, index) => {
      const data = addDays(inicio, index);
      const key = dateKey(data);
      const eventos = [...(eventosCalendario[key] || [])];
      if (data.getDay() === 1) {
        eventos.unshift({ tipo: "smart", titulo: "Smart Monday" });
      }
      return {
        key,
        data,
        dia: data.getDate(),
        mesAtual: data.getMonth() === calendarioMes,
        hoje: key === hojeKey,
        eventos,
      };
    });
  }, [calendarioAno, calendarioMes, eventosCalendario]);

  const proximosEventosCalendario = useMemo(() => (
    diasCalendario
      .filter((dia) => dia.mesAtual && dia.eventos.length > 0)
      .flatMap((dia) => dia.eventos.map((evento) => ({ ...evento, dia: dia.dia, key: dia.key })))
      .slice(0, 12)
  ), [diasCalendario]);

  const navegarMes = (delta) => {
    setCalendarioData((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  };

  const abrirEdicao = (usuarioEditado) => {
    const form = {
      ...usuarioEditado,
      novaSenha: "",
    };
    RH_FIELDS.forEach((field) => {
      form[field.name] = inputValue(usuarioEditado[field.name]);
    });
    setEditando(form);
  };

  const abrirDetalhes = (usuarioDetalhado) => {
    setDetalhando(usuarioDetalhado);
  };

  const alterarAtivo = async (item, novoAtivo) => {
    const { ok, data } = await apiFetch("/corretor/alterar-ativo", {
      method: "POST",
      body: JSON.stringify({ id_corretor: item.id_usuarios, new_ativo: novoAtivo }),
    });
    if (!ok || data?.error) {
      toast(data?.error || "Erro ao alterar status.", "error");
      return;
    }
    setUsuarios((prev) =>
      prev.map((u) => (
        u.id_usuarios === item.id_usuarios
          ? { ...u, ativo: novoAtivo, status: data.status || (novoAtivo ? "Ativo" : "Inativo") }
          : u
      ))
    );
  };

  const salvarEdicao = async () => {
    if (!editando || !usuario) return;
    setSalvando(true);
    try {
      const payload = {
        solicitante_id: usuario.id_usuarios,
        id_corretor: editando.id_usuarios,
        username: editando.username,
        nome: editando.nome,
        email: editando.email,
        telefone: editando.telefone,
        instagram: editando.instagram,
        descricao: editando.descricao,
        permissao: editando.permissao,
        team: editando.team,
        id_imoview: editando.id_imoview,
      };

      RH_FIELDS.forEach((field) => {
        payload[field.name] = editando[field.name] ?? "";
      });

      if (editando.novaSenha) payload.nova_senha = editando.novaSenha;

      const { ok, data } = await apiFetch("/corretor/editar-usuario", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!ok || data?.error) {
        toast(data?.error || "Erro ao salvar usuário.", "error");
        return;
      }

      setUsuarios((prev) =>
        prev.map((u) => (u.id_usuarios === editando.id_usuarios ? { ...u, ...data.usuario } : u))
      );
      setEditando(null);
      toast("Usuário atualizado.", "success");
    } catch {
      toast("Erro de comunicação com a API.", "error");
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
            <option value="false">Não</option>
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

  const formatarValorDetalhe = (value) => {
    if (value === true || value === "true") return "Sim";
    if (value === false || value === "false") return "Nao";
    return value || "-";
  };

  const renderDetalheItem = (label, value) => (
    <div className="rh-usuarios__detail-item">
      <span>{label}</span>
      <strong>{formatarValorDetalhe(value)}</strong>
    </div>
  );

  const renderDetalheSecao = (titulo, itens) => (
    <section className="rh-usuarios__detail-section">
      <h4>{titulo}</h4>
      <div className="rh-usuarios__detail-grid">
        {itens.map(([label, value]) => (
          <React.Fragment key={label}>{renderDetalheItem(label, value)}</React.Fragment>
        ))}
      </div>
    </section>
  );

  return (
    <div className="controle-corretores rh-usuarios">
      <div className="controle-corretores__container">
        <section className="rh-usuarios__hero">
          <div>
            <span className="rh-usuarios__eyebrow">People Operations</span>
            <h1 className="rh-usuarios__title">Gestao de usuarios RH</h1>
            <p className="rh-usuarios__subtitle">
              Validacao de novos cadastros, documentacao obrigatoria, equipes, saidas e status operacional em uma fila unica de trabalho.
            </p>
          </div>
          <div className="rh-usuarios__hero-panel">
            <span className="rh-usuarios__hero-label">Aguardando ativacao</span>
            <strong>{loading ? "..." : painelRh.pendentesAtivacao}</strong>
            <span>Novos usuarios sem acesso interno ate validacao do RH.</span>
          </div>
        </section>

        <div className="rh-usuarios__workspace">
          <aside className="rh-usuarios__nav" aria-label="Filas de RH">
            <div className="rh-usuarios__nav-title">Filas de trabalho</div>
            {[
              ["pendentes", "Pendentes de ativacao", painelRh.pendentesAtivacao],
              ["todos", "Usuarios ativos", painelRh.ativos],
              ["pendencias", "Documentacao pendente", painelRh.pendencias],
              ["saidas", "Saidas e desligamentos", painelRh.saidas],
            ].map(([key, label, count]) => (
              <button
                key={key}
                type="button"
                className={`rh-usuarios__nav-btn ${viewMode === key ? "rh-usuarios__nav-btn--active" : ""}`}
                onClick={() => setViewMode(key)}
              >
                <span>{label}</span>
                <strong>{loading ? "..." : count}</strong>
              </button>
            ))}
            <div className="rh-usuarios__nav-divider" />
            <div className="rh-usuarios__nav-metric">
              <span>Diretores</span>
              <strong>{loading ? "..." : painelRh.diretores}</strong>
            </div>
            <div className="rh-usuarios__nav-metric">
              <span>Ativos</span>
              <strong>{loading ? "..." : painelRh.ativos}</strong>
            </div>
          </aside>

          <main className="rh-usuarios__content">
        <section className="controle-corretores__summary rh-usuarios__summary">
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Total exibido</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.total}</div>
            <div className="controle-corretores__summary-helper">Usuários no filtro atual</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Ativos</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.ativos}</div>
            <div className="controle-corretores__summary-helper">Em atividade</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Inativos</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.inativos}</div>
            <div className="controle-corretores__summary-helper">Fora de atividade</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Com pendências</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.pendentes}</div>
            <div className="controle-corretores__summary-helper">Campos obrigatórios faltando</div>
          </div>
          <div className="controle-corretores__summary-card">
            <span className="controle-corretores__summary-label">Saídas</span>
            <div className="controle-corretores__summary-value">{loading ? "..." : totais.desligados}</div>
            <div className="controle-corretores__summary-helper">Com desligamento registrado</div>
          </div>
        </section>

        <section className="rh-usuarios__calendar-shell">
          <button
            type="button"
            className="rh-usuarios__calendar-toggle"
            onClick={() => setCalendarioAberto((prev) => !prev)}
            aria-expanded={calendarioAberto}
          >
            <span>
              <strong>Calendario RH</strong>
              <small>{MESES[calendarioMes]} {calendarioAno} · {proximosEventosCalendario.length} evento(s) no mes</small>
            </span>
            <b>{calendarioAberto ? "Ocultar" : "Ver calendario"}</b>
          </button>

          {calendarioAberto && (
        <div className="rh-usuarios__calendar">
          <div className="rh-usuarios__calendar-main">
            <div className="rh-usuarios__calendar-head">
              <div>
                <span className="rh-usuarios__calendar-kicker">Calendario RH</span>
                <h3>{MESES[calendarioMes]} {calendarioAno}</h3>
              </div>
              <div className="rh-usuarios__calendar-actions">
                <button type="button" onClick={() => navegarMes(-1)} aria-label="Mes anterior">{"<"}</button>
                <button type="button" onClick={() => setCalendarioData(new Date())}>Hoje</button>
                <button type="button" onClick={() => navegarMes(1)} aria-label="Proximo mes">{">"}</button>
              </div>
            </div>

            <div className="rh-usuarios__calendar-week">
              {DIAS_SEMANA.map((dia) => <span key={dia}>{dia}</span>)}
            </div>
            <div className="rh-usuarios__calendar-grid">
              {diasCalendario.map((dia) => (
                <div
                  key={dia.key}
                  className={`rh-usuarios__calendar-day ${dia.mesAtual ? "" : "rh-usuarios__calendar-day--muted"} ${dia.hoje ? "rh-usuarios__calendar-day--today" : ""}`}
                >
                  <span className="rh-usuarios__calendar-number">{dia.dia}</span>
                  <div className="rh-usuarios__calendar-events">
                    {dia.eventos.slice(0, 3).map((evento, index) => (
                      <span key={`${evento.tipo}-${evento.titulo}-${index}`} className={`rh-usuarios__event rh-usuarios__event--${evento.tipo}`}>
                        {evento.titulo}
                      </span>
                    ))}
                    {dia.eventos.length > 3 && (
                      <span className="rh-usuarios__event-more">+{dia.eventos.length - 3}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <aside className="rh-usuarios__calendar-side">
            <div>
              <span className="rh-usuarios__calendar-kicker">Eventos do mes</span>
              <h4>Feriados e aniversarios</h4>
            </div>
            <div className="rh-usuarios__legend">
              <span><i className="rh-usuarios__dot rh-usuarios__dot--smart" /> Smart Monday</span>
              <span><i className="rh-usuarios__dot rh-usuarios__dot--feriado" /> Feriado</span>
              <span><i className="rh-usuarios__dot rh-usuarios__dot--aniversario" /> Aniversario</span>
            </div>
            <div className="rh-usuarios__event-list">
              {proximosEventosCalendario.length === 0 ? (
                <span className="rh-usuarios__event-empty">Nenhum evento neste mes.</span>
              ) : proximosEventosCalendario.map((evento, index) => (
                <div key={`${evento.key}-${evento.tipo}-${evento.titulo}-${index}`} className="rh-usuarios__event-row">
                  <strong>{String(evento.dia).padStart(2, "0")}</strong>
                  <div>
                    <span>{evento.titulo}</span>
                    {evento.detalhe && <small>{evento.detalhe}</small>}
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>
          )}
        </section>

        <section className="controle-corretores__panel rh-usuarios__panel">
          <div className="controle-corretores__panel-top">
            <div>
              <h3 className="controle-corretores__panel-title">Usuários</h3>
              <p className="controle-corretores__panel-subtitle">Filtre por equipe, status, permissão e pendências.</p>
            </div>
            <div className="rh-usuarios__panel-actions">
              <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={limparFiltros}>
                Limpar filtros
              </button>
              <div className="controle-corretores__count-badge">{usuariosFiltrados.length} registro(s)</div>
            </div>
          </div>

          <div className="rh-filtros">
            <div className="rh-filtros__search-row">
              <div className="rh-filtros__searchbox">
                <span className="rh-filtros__search-icon" aria-hidden="true">🔍</span>
                <input
                  className="rh-filtros__search-input"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Buscar por nome, CPF, ID ou e-mail…"
                />
                {busca && <button type="button" className="rh-filtros__search-clear" onClick={() => setBusca("")} aria-label="Limpar busca">✕</button>}
              </div>
              <button
                type="button"
                className={`rh-filtros__toggle ${filtrosAbertos ? "is-open" : ""}`}
                onClick={() => setFiltrosAbertos((v) => !v)}
                aria-expanded={filtrosAbertos}
              >
                {filtrosAbertos ? "Menos filtros" : "Mais filtros"}
                <span className="rh-filtros__toggle-caret">{filtrosAbertos ? "▲" : "▼"}</span>
              </button>
            </div>

            <div className="rh-filtros__grid">
              <div className="rh-filtros__field">
                <label>Equipe</label>
                <select value={filtroEquipe} onChange={(e) => setFiltroEquipe(e.target.value)}>
                  <option value="">Todas</option>
                  {equipes.map((eq) => <option key={eq.value} value={eq.value}>{eq.label}</option>)}
                </select>
              </div>
              <div className="rh-filtros__field">
                <label>Permissão</label>
                <select value={filtroPermissao} onChange={(e) => setFiltroPermissao(e.target.value)}>
                  <option value="">Todas</option>
                  <option value="corretor">Corretores</option>
                  <option value="gerente">Gerentes</option>
                  <option value="administrativo">Administrativo</option>
                  <option value="administrador">Administradores</option>
                  <option value="diretor">Diretores</option>
                </select>
              </div>
              <div className="rh-filtros__field">
                <label>Status</label>
                <select value={filtroAtivo} onChange={(e) => setFiltroAtivo(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="true">Ativos</option>
                  <option value="false">Inativos</option>
                </select>
              </div>
              <div className="rh-filtros__field">
                <label>Cadastro</label>
                <select value={filtroPendencia} onChange={(e) => setFiltroPendencia(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="faltando">Com pendências</option>
                  <option value="completo">Completos</option>
                </select>
              </div>

              {filtrosAbertos && (
                <>
                  <div className="rh-filtros__field">
                    <label>Status RH</label>
                    <select value={filtroStatusRh} onChange={(e) => setFiltroStatusRh(e.target.value)}>
                      <option value="">Todos</option>
                      <option value="Ativo">Ativo</option>
                      <option value="Inativo">Inativo</option>
                      <option value="Desligado">Desligado</option>
                    </select>
                  </div>
                  <div className="rh-filtros__field">
                    <label>Entrada de</label>
                    <input type="date" value={filtroEntradaInicio} onChange={(e) => setFiltroEntradaInicio(e.target.value)} />
                  </div>
                  <div className="rh-filtros__field">
                    <label>Entrada até</label>
                    <input type="date" value={filtroEntradaFim} onChange={(e) => setFiltroEntradaFim(e.target.value)} />
                  </div>
                  <div className="rh-filtros__field">
                    <label>Saída</label>
                    <select value={filtroDesligamento} onChange={(e) => setFiltroDesligamento(e.target.value)}>
                      <option value="">Todos</option>
                      <option value="desligado">Desligado: sim</option>
                      <option value="nao_desligado">Desligado: não</option>
                      <option value="com_data">Com data registrada</option>
                      <option value="sem_data">Sem data registrada</option>
                    </select>
                  </div>
                  <div className="rh-filtros__field">
                    <label>CRECI</label>
                    <select value={filtroCreci} onChange={(e) => setFiltroCreci(e.target.value)}>
                      <option value="">Todos</option>
                      <option value="sem_validade">Sem validade</option>
                      <option value="vencido">Vencido</option>
                      <option value="vence_30">Vence em 30 dias</option>
                      <option value="valido">Válido</option>
                    </select>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="controle-corretores__table-wrapper">
            <div className="controle-corretores__table-scroll">
              <table className="controle-corretores__table rh-usuarios__table">
                <thead>
                  <tr>
                    <th>Usuário</th>
                    <th>Equipe</th>
                    <th>Permissão</th>
                    <th>Ativo</th>
                    <th>Contato</th>
                    <th>Pendências</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan="7" className="controle-corretores__empty">Carregando...</td></tr>
                  ) : usuariosFiltrados.length === 0 ? (
                    <tr><td colSpan="7" className="controle-corretores__empty">Nenhum usuário encontrado.</td></tr>
                  ) : usuariosFiltrados.map((item) => {
                    const faltantes = camposFaltantes(item);
                    const statusOperacional = usuarioEmSaida(item) ? "Desligado" : item.ativo ? "Ativo" : "Pendente ativacao";
                    const contatoPrincipal = item.telefone_corporativo || item.telefone_pessoal || item.telefone || "-";
                    const emailPrincipal = item.email_corporativo || item.email_pessoal || item.email || "-";
                    return (
                      <tr key={item.id_usuarios || item.id}>
                        <td data-label="Usuário">
                          <div className="controle-corretores__nome-wrap">
                            <span className="controle-corretores__nome">{item.nome || item.username || "-"}</span>
                            <span className="controle-corretores__nome-sub">{item.id_usuarios || "-"} · {item.email_corporativo || item.email || "-"}</span>
                          </div>
                        </td>
                        <td data-label="Equipe"><span className="controle-corretores__team">{getNomeEquipe(item.team)}</span></td>
                        <td data-label="Permissão">{item.permissao || "-"}</td>
                        <td data-label="Status">
                          <span className={`controle-corretores__badge ${item.ativo ? "controle-corretores__badge--ativo" : "controle-corretores__badge--inativo"}`}>
                            {statusOperacional}
                          </span>
                        </td>
                        <td data-label="Contato">
                          <div className="rh-usuarios__contact">
                            <span>{contatoPrincipal}</span>
                            <small>{emailPrincipal}</small>
                          </div>
                        </td>
                        <td data-label="Pendências">
                          {faltantes.length === 0 ? (
                            <span className="rh-usuarios__ok">Completo</span>
                          ) : (
                            <div className="rh-usuarios__missing">{faltantes.slice(0, 4).map((f) => f.label).join(", ")}{faltantes.length > 4 ? ` +${faltantes.length - 4}` : ""}</div>
                          )}
                        </td>
                        <td data-label="Ações">
                          <div className="rh-usuarios__actions">
                            <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={() => abrirDetalhes(item)}>Detalhes</button>
                            <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={() => abrirEdicao(item)}>Editar</button>
                            <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={() => alterarAtivo(item, !item.ativo)}>
                              {item.ativo ? "Desativar" : "Ativar cadastro"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
          </main>
        </div>

        {detalhando && (
          <div className="controle-corretores__modal-overlay" onClick={() => setDetalhando(null)}>
            <div className="controle-corretores__modal rh-usuarios__modal rh-usuarios__detail-modal" onClick={(e) => e.stopPropagation()}>
              <div className="rh-usuarios__detail-head">
                <div>
                  <span className="rh-usuarios__detail-kicker">Detalhes do usuario</span>
                  <h3>{detalhando.nome || detalhando.username || "-"}</h3>
                  <p>{detalhando.id_usuarios || "-"} · {getNomeEquipe(detalhando.team)} · {detalhando.permissao || "sem permissao"}</p>
                </div>
                <span className={`controle-corretores__badge ${detalhando.ativo ? "controle-corretores__badge--ativo" : "controle-corretores__badge--inativo"}`}>
                  {usuarioEmSaida(detalhando) ? "Desligado" : detalhando.ativo ? "Ativo" : "Pendente ativacao"}
                </span>
              </div>

              <div className="rh-usuarios__detail-alert">
                {camposFaltantes(detalhando).length === 0 ? (
                  <span className="rh-usuarios__ok">Cadastro completo para o RH.</span>
                ) : (
                  <>
                    <strong>{camposFaltantes(detalhando).length} pendencia(s)</strong>
                    <span>{camposFaltantes(detalhando).map((f) => f.label).join(", ")}</span>
                  </>
                )}
              </div>

              <div className="rh-usuarios__detail-sections">
                {renderDetalheSecao("Dados principais", [
                  ["Username", detalhando.username],
                  ["Nome completo", detalhando.nome],
                  ["Unidade", detalhando.unidade],
                  ["Gerente responsavel", detalhando.gerente_responsavel],
                  ["Data de entrada", detalhando.data_entrada_61],
                  ["Status RH", detalhando.status],
                  ["Codigo Imoview", detalhando.id_imoview],
                ])}
                {renderDetalheSecao("Contatos", [
                  ["Telefone corporativo", detalhando.telefone_corporativo],
                  ["Telefone pessoal", detalhando.telefone_pessoal],
                  ["E-mail corporativo", detalhando.email_corporativo],
                  ["E-mail pessoal", detalhando.email_pessoal],
                  ["Contato emergencia", detalhando.contato_emergencia],
                  ["Endereco", detalhando.endereco],
                ])}
                {renderDetalheSecao("Documentos e dados pessoais", [
                  ["CPF", detalhando.cpf],
                  ["RG", detalhando.rg],
                  ["CRECI", detalhando.creci],
                  ["Validade CRECI", detalhando.validade_creci],
                  ["Data nascimento", detalhando.data_nascimento],
                  ["Estado civil", detalhando.estado_civil],
                  ["Possui filhos", detalhando.possui_filhos],
                ])}
                {renderDetalheSecao("Financeiro e contratos", [
                  ["CNPJ", detalhando.cnpj],
                  ["Razao social", detalhando.razao_social],
                  ["Banco", detalhando.banco],
                  ["Agencia", detalhando.agencia],
                  ["Conta", detalhando.conta],
                  ["Tipo de conta", detalhando.tipo_conta],
                  ["Chave PIX", detalhando.chave_pix],
                  ["Contrato assinado", detalhando.contrato_assinado],
                  ["Codigo de conduta", detalhando.codigo_conduta_assinado],
                  ["LGPD assinada", detalhando.lgpd_assinada],
                  ["Onboarding", detalhando.onboarding_realizado],
                ])}
                {usuarioEmSaida(detalhando) && renderDetalheSecao("Desligamento", [
                  ["Desligado", detalhando.desligado],
                  ["Data desligamento", detalhando.data_desligamento],
                  ["Observacoes", detalhando.observacoes],
                ])}
              </div>

              <div className="controle-corretores__modal-actions">
                <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={() => setDetalhando(null)}>Fechar</button>
                <button type="button" className="controle-corretores__button controle-corretores__button--primary" onClick={() => { abrirEdicao(detalhando); setDetalhando(null); }}>
                  Editar usuario
                </button>
              </div>
            </div>
          </div>
        )}

        {editando && (
          <div className="controle-corretores__modal-overlay" onClick={() => setEditando(null)}>
            <div className="controle-corretores__modal rh-usuarios__modal" onClick={(e) => e.stopPropagation()}>
              <h3 className="controle-corretores__panel-title">Editar usuário</h3>
              <p className="controle-corretores__panel-subtitle">Campos com * são obrigatórios no controle do RH.</p>

              <div className="controle-corretores__modal-grid">
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">Username</label>
                  <input className="controle-corretores__search" value={editando.username || ""} onChange={(e) => setEditando((prev) => ({ ...prev, username: e.target.value }))} />
                </div>
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">ID usuário</label>
                  <input className="controle-corretores__search" value={editando.id_usuarios || ""} disabled />
                </div>
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">Código Imoview</label>
                  <input
                    className="controle-corretores__search"
                    inputMode="numeric"
                    placeholder="Ex: 112"
                    value={editando.id_imoview || ""}
                    onChange={(e) => setEditando((prev) => ({ ...prev, id_imoview: e.target.value }))}
                  />
                </div>
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">Permissão</label>
                  <select className="controle-corretores__select" value={editando.permissao || ""} onChange={(e) => setEditando((prev) => ({ ...prev, permissao: e.target.value }))}>
                    <option value="">Selecione...</option>
                    <option value="corretor">Corretor</option>
                    <option value="gerente">Gerente</option>
                    <option value="administrativo">Administrativo</option>
                    <option value="administrador">Administrador</option>
                    <option value="diretor">Diretor</option>
                  </select>
                </div>
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">Equipe</label>
                  <select className="controle-corretores__select" value={editando.team || ""} onChange={(e) => setEditando((prev) => ({ ...prev, team: e.target.value }))}>
                    <option value="">Sem equipe</option>
                    {equipesOpcoes.map((eq) => <option key={eq.value} value={eq.value}>{eq.label}</option>)}
                  </select>
                </div>
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">E-mail login</label>
                  <input className="controle-corretores__search" value={editando.email || ""} onChange={(e) => setEditando((prev) => ({ ...prev, email: e.target.value }))} />
                </div>
                <div className="controle-corretores__field">
                  <label className="controle-corretores__label">Telefone login</label>
                  <input className="controle-corretores__search" value={editando.telefone || ""} onChange={(e) => setEditando((prev) => ({ ...prev, telefone: e.target.value }))} />
                </div>
                {RH_FIELDS.map(renderField)}
                <div className="controle-corretores__field controle-corretores__field--full">
                  <label className="controle-corretores__label">Nova senha</label>
                  <input className="controle-corretores__search" type="password" value={editando.novaSenha || ""} onChange={(e) => setEditando((prev) => ({ ...prev, novaSenha: e.target.value }))} />
                </div>
              </div>

              <div className="controle-corretores__modal-actions">
                <button type="button" className="controle-corretores__button controle-corretores__button--ghost-light" onClick={() => setEditando(null)} disabled={salvando}>Cancelar</button>
                <button type="button" className="controle-corretores__button controle-corretores__button--primary" onClick={salvarEdicao} disabled={salvando}>
                  {salvando ? "Salvando..." : "Salvar"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default RHUsuarios;
