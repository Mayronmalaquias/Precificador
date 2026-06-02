import React, { useState, useEffect, useCallback, useMemo } from "react";
import { BASE } from "../services/api";
import { useToast } from "../context/ToastContext";
import "../assets/css/JornadaCaptacao.css";
import bookPdf from "../assets/pdf/Book Digital - Plano Piloto.pdf";

// ── Constantes ───────────────────────────────────────────────────────────────
const ETAPA_INFO = {
  escolha:      { label: "Escolha",      color: "#7c3aed", light: "#ede9fe", icon: "🔍" },
  prospeccao:   { label: "Prospecção",   color: "#2563eb", light: "#dbeafe", icon: "📍" },
  interacao:    { label: "Interação",    color: "#d97706", light: "#fef3c7", icon: "📞" },
  apresentacao: { label: "Apresentação", color: "#0d9488", light: "#ccfbf1", icon: "🏠" },
  captacao:     { label: "Captação",     color: "#16a34a", light: "#dcfce7", icon: "✅" },
};
const ETAPAS = Object.entries(ETAPA_INFO).map(([key, v]) => ({ key, ...v }));

const CORRETOR_PALETTE = [
  "#2563eb","#7c3aed","#16a34a","#d97706","#dc2626",
  "#0d9488","#db2777","#4f46e5","#65a30d","#ea580c",
];
const MESES      = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
const DIAS_SEM   = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];

// ── Utilitários ──────────────────────────────────────────────────────────────
function fmt(str) {
  if (!str) return "-";
  const p = str.split("T")[0].split("-");
  return `${p[2]}/${p[1]}/${p[0]}`;
}

function diasDesde(str) {
  if (!str) return null;
  return Math.floor((Date.now() - new Date(str)) / 86400000);
}

function corIdade(str) {
  const d = diasDesde(str);
  if (d === null) return "#94a3b8";
  if (d < 7)  return "#3b82f6";
  if (d < 14) return "#06b6d4";
  if (d < 21) return "#eab308";
  if (d < 30) return "#f97316";
  return "#ef4444";
}

function corretorColor(nome, lista) {
  if (!nome) return "#94a3b8";
  const idx = lista.indexOf(nome);
  if (idx === -1) return "#94a3b8";
  return CORRETOR_PALETTE[idx % CORRETOR_PALETTE.length];
}

function extrairEventos(captacoes) {
  const evts = [];
  captacoes.filter(c => c.status !== "fechado" && c.status !== "captado").forEach(c => {
    const add = (data, acao, etapa) => {
      if (data) evts.push({ data: data.split("T")[0], acao: acao || "", etapa, captacao: c });
    };
    add(c.data_acao_sem_numero,           c.acao_sem_numero,           "escolha");
    add(c.data_proxima_acao_interacao,    c.proxima_acao_interacao,    "interacao");
    add(c.data_proxima_acao_apresentacao, c.proxima_acao_apresentacao, "apresentacao");
    add(c.data_proxima_acao_captacao,     c.proxima_acao_captacao,     "captacao");
  });
  return evts;
}

// Histórico sintético de uma captação
function buildHistorico(c) {
  const items = [];
  const push = (data, desc, etapa, realizada, tipo = "acao") =>
    items.push({ data, desc, etapa, realizada, tipo });

  push(c.created_at?.split("T")[0], "Imóvel lançado na jornada", "escolha", true, "inicio");

  if (c.acao_sem_numero)
    push(c.data_acao_sem_numero, c.acao_sem_numero, "escolha", c.acao_escolha_realizada);

  if (c.nome_cliente)
    push(null, `Cliente: ${c.nome_cliente}${c.telefone_cliente ? " · " + c.telefone_cliente : ""}`, "prospeccao", true, "dado");

  if (c.book_enviado !== null && c.book_enviado !== undefined)
    push(null, c.book_enviado ? "Book enviado ao cliente" : "Book não enviado", "prospeccao", c.book_enviado, "book");

  if (c.motivo_nao_interacao)
    push(null, `Objeção: ${c.motivo_nao_interacao}`, "interacao", false, "objecao");

  if (c.proxima_acao_interacao)
    push(c.data_proxima_acao_interacao, c.proxima_acao_interacao, "interacao", c.acao_interacao_realizada);

  if (c.motivo_nao_apresentacao)
    push(null, `Objeção: ${c.motivo_nao_apresentacao}`, "apresentacao", false, "objecao");

  if (c.proxima_acao_apresentacao)
    push(c.data_proxima_acao_apresentacao, c.proxima_acao_apresentacao, "apresentacao", c.acao_apresentacao_realizada);

  if (c.objecao_captacao)
    push(null, `Objeção: ${c.objecao_captacao}`, "captacao", false, "objecao");

  if (c.proxima_acao_captacao)
    push(c.data_proxima_acao_captacao, c.proxima_acao_captacao, "captacao", c.acao_captacao_realizada);

  if (c.status === "fechado")
    push(c.data_fechamento, `Encerrado: ${c.motivo_fechamento}`, c.etapa_atual, false, "fechamento");

  if (c.status === "captado")
    push(null, "Imóvel captado com sucesso!", "captacao", true, "captado");

  return items;
}

// ── Componentes de formulário (módulo-level para não perder foco) ────────────
function CampoTexto({ label, value, onChange, placeholder, type = "text", autoFocus }) {
  return (
    <div className="cap-field">
      {label && <label className="cap-field-label">{label}</label>}
      <input className="cap-field-input" type={type} value={value ?? ""} onChange={onChange}
        placeholder={placeholder || ""} autoFocus={autoFocus} />
    </div>
  );
}
function CampoArea({ label, value, onChange, placeholder, rows = 3 }) {
  return (
    <div className="cap-field">
      {label && <label className="cap-field-label">{label}</label>}
      <textarea className="cap-field-input cap-textarea" rows={rows} value={value ?? ""}
        onChange={onChange} placeholder={placeholder || ""} />
    </div>
  );
}
function CorretorCombobox({ corretores, value, onChange }) {
  const [aberto, setAberto]   = useState(false);
  const [busca,  setBusca]    = useState("");
  const ref = React.useRef(null);

  // Fecha ao clicar fora
  useEffect(() => {
    const fn = (e) => { if (ref.current && !ref.current.contains(e.target)) setAberto(false); };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, []);

  const lista = corretores.filter(c =>
    (c.nome || c.username || "").toLowerCase().includes(busca.toLowerCase())
  );

  const selecionar = (c) => {
    onChange({ id_usuarios: c.id_usuarios, nome: c.nome || c.username, team: c.team });
    setAberto(false);
    setBusca("");
  };

  const limpar = (e) => { e.stopPropagation(); onChange(null); setBusca(""); };

  return (
    <div className="cap-combo" ref={ref}>
      <div className={`cap-combo-input${aberto ? " cap-combo-input--aberto" : ""}`} onClick={() => setAberto(o => !o)}>
        {value ? (
          <>
            <span className="cap-combo-valor">{value.nome}</span>
            <button className="cap-combo-limpar" onClick={limpar}>✕</button>
          </>
        ) : (
          <span className="cap-combo-placeholder">Selecionar corretor…</span>
        )}
        <span className="cap-combo-arrow">{aberto ? "▲" : "▼"}</span>
      </div>

      {aberto && (
        <div className="cap-combo-dropdown">
          <input
            className="cap-combo-busca"
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar por nome…"
            autoFocus
          />
          <div className="cap-combo-lista">
            {lista.length === 0
              ? <div className="cap-combo-vazio">Nenhum corretor encontrado</div>
              : lista.map(c => (
                  <button
                    key={c.id_usuarios}
                    className={`cap-combo-item${value?.id_usuarios === c.id_usuarios ? " active" : ""}`}
                    onClick={() => selecionar(c)}
                  >
                    <span className="cap-combo-item-nome">{c.nome || c.username}</span>
                    {c.team && <span className="cap-combo-item-team">{c.team}</span>}
                  </button>
                ))
            }
          </div>
        </div>
      )}
    </div>
  );
}

function BotaoResposta({ resp, onResp }) {
  return (
    <div className="cap-resp-btns">
      <button className={`cap-resp-btn cap-resp-btn--sim${resp === true  ? " active" : ""}`} onClick={() => onResp(true)}>Sim</button>
      <button className={`cap-resp-btn cap-resp-btn--nao${resp === false ? " active" : ""}`} onClick={() => onResp(false)}>Não</button>
    </div>
  );
}

// ── Histórico timeline ───────────────────────────────────────────────────────
const MAP_REALIZADA = {
  escolha:      "acao_escolha_realizada",
  prospeccao:   "acao_interacao_realizada",
  interacao:    "acao_interacao_realizada",
  apresentacao: "acao_apresentacao_realizada",
  captacao:     "acao_captacao_realizada",
};

// Lookup para badge de ação pendente no KanbanCard (módulo-level para não realocar a cada render)
const CAMP_ACAO_KANBAN = {
  escolha:      "acao_sem_numero",
  prospeccao:   "proxima_acao_interacao",
  interacao:    "proxima_acao_interacao",
  apresentacao: "proxima_acao_apresentacao",
  captacao:     "proxima_acao_captacao",
};
const CAMP_REAL_KANBAN = {
  escolha:      "acao_escolha_realizada",
  prospeccao:   "acao_interacao_realizada",
  interacao:    "acao_interacao_realizada",
  apresentacao: "acao_apresentacao_realizada",
  captacao:     "acao_captacao_realizada",
};

function HistoricoTimeline({ captacao, onMarcarRealizada }) {
  // Estado local para esconder o botão imediatamente ao clicar, sem esperar prop update
  const [marcadosLocal, setMarcadosLocal] = useState({});

  // Reseta ao abrir outro imóvel
  useEffect(() => { setMarcadosLocal({}); }, [captacao.id]);

  const items = buildHistorico(captacao);
  if (items.length === 0) return <p className="cap-hist-vazio">Nenhuma ação registrada.</p>;

  const icone = (tipo, realizada) => {
    if (tipo === "inicio")    return "🚀";
    if (tipo === "dado")      return "👤";
    if (tipo === "book")      return realizada ? "📗" : "📕";
    if (tipo === "objecao")   return "⚠️";
    if (tipo === "fechamento") return "🔴";
    if (tipo === "captado")   return "🏆";
    if (realizada === true)   return "✅";
    if (realizada === false)  return "❌";
    return "⏳";
  };

  return (
    <div className="cap-hist">
      {items.map((it, i) => {
        const cor          = ETAPA_INFO[it.etapa]?.color || "#94a3b8";
        const campoReal    = MAP_REALIZADA[it.etapa];
        // realizada = vem da prop OU foi marcado localmente agora
        const realizada    = it.realizada === true || marcadosLocal[i] === true;
        const podeMarcar   = it.tipo === "acao" && !realizada && onMarcarRealizada;

        const handleMarcar = () => {
          setMarcadosLocal(p => ({ ...p, [i]: true }));
          onMarcarRealizada({ [campoReal]: true });
        };

        return (
          <div key={i} className={`cap-hist-item${!realizada && it.tipo === "acao" ? " cap-hist-item--pendente" : ""}`}>
            <div className="cap-hist-linha" style={{ borderColor: cor }}>
              <span className="cap-hist-icone">{icone(it.tipo, realizada)}</span>
            </div>
            <div className="cap-hist-corpo">
              <div className="cap-hist-etapa" style={{ color: cor }}>{ETAPA_INFO[it.etapa]?.label}</div>
              <div className="cap-hist-desc">{it.desc}</div>
              {it.data && <div className="cap-hist-data">{fmt(it.data)}</div>}
              {podeMarcar && (
                <button className="cap-hist-marcar-btn" onClick={handleMarcar}>
                  Marcar como realizada
                </button>
              )}
              {it.tipo === "acao" && realizada && (
                <span className="cap-hist-ok">Realizada ✓</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Calendário ───────────────────────────────────────────────────────────────
function CalendarioView({ captacoes, isAdmin, onCardClick }) {
  const agora = new Date();
  const [mes, setMes] = useState(agora.getMonth());
  const [ano, setAno] = useState(agora.getFullYear());
  const [diaAtivo, setDiaAtivo] = useState(null);

  const eventos   = useMemo(() => extrairEventos(captacoes), [captacoes]);
  const corretores = useMemo(
    () => [...new Set(captacoes.map(c => c.nome_corretor).filter(Boolean))].sort(),
    [captacoes]
  );
  const evtsDoDia = useCallback((ds) => eventos.filter(e => e.data === ds), [eventos]);

  const navMes = (d) => {
    let m = mes + d, a = ano;
    if (m < 0)  { m = 11; a--; }
    if (m > 11) { m = 0;  a++; }
    setMes(m); setAno(a); setDiaAtivo(null);
  };

  const primeiro = new Date(ano, mes, 1).getDay();
  const ultimo   = new Date(ano, mes + 1, 0).getDate();
  const celulas  = [];
  for (let i = 0; i < primeiro; i++) celulas.push(null);
  for (let d = 1; d <= ultimo; d++)   celulas.push(d);
  while (celulas.length % 7 !== 0) celulas.push(null);

  const hojeStr = `${agora.getFullYear()}-${String(agora.getMonth()+1).padStart(2,"0")}-${String(agora.getDate()).padStart(2,"0")}`;
  const evtsAtivo = diaAtivo ? evtsDoDia(diaAtivo) : [];

  return (
    <div className="cap-cal-wrap">
      <div className="cap-cal-nav">
        <button className="cap-cal-nav-btn" onClick={() => navMes(-1)}>‹</button>
        <h2 className="cap-cal-mes-titulo">{MESES[mes]} {ano}</h2>
        <button className="cap-cal-nav-btn" onClick={() => navMes(1)}>›</button>
        <button className="cap-cal-hoje-btn" onClick={() => { setMes(agora.getMonth()); setAno(agora.getFullYear()); setDiaAtivo(hojeStr); }}>Hoje</button>
      </div>
      {isAdmin && corretores.length > 0 && (
        <div className="cap-cal-legenda">
          {corretores.map((n, i) => (
            <span key={n} className="cap-cal-leg-item">
              <span className="cap-cal-leg-dot" style={{ background: CORRETOR_PALETTE[i % CORRETOR_PALETTE.length] }} />
              {n}
            </span>
          ))}
        </div>
      )}
      <div className="cap-cal-grid">
        {DIAS_SEM.map(d => <div key={d} className="cap-cal-dow">{d}</div>)}
        {celulas.map((dia, i) => {
          if (!dia) return <div key={`e${i}`} className="cap-cal-celula cap-cal-celula--vazia" />;
          const ds   = `${ano}-${String(mes+1).padStart(2,"0")}-${String(dia).padStart(2,"0")}`;
          const evts = evtsDoDia(ds);
          const isH  = ds === hojeStr;
          const isA  = ds === diaAtivo;
          return (
            <div key={ds}
              className={`cap-cal-celula${isH?" cap-cal-celula--hoje":""}${isA?" cap-cal-celula--ativo":""}${evts.length>0?" cap-cal-celula--tem-evts":""}`}
              onClick={() => setDiaAtivo(isA ? null : ds)}
            >
              <span className="cap-cal-dia-num">{dia}</span>
              <div className="cap-cal-pips">
                {isAdmin
                  ? evts.slice(0,5).map((e,ei) => <span key={ei} className="cap-cal-pip" style={{ background: corretorColor(e.captacao.nome_corretor, corretores) }} />)
                  : evts.slice(0,4).map((e,ei) => <span key={ei} className="cap-cal-pip" style={{ background: ETAPA_INFO[e.etapa]?.color }} />)
                }
                {isAdmin
                  ? evts.length > 5 && <span className="cap-cal-mais-pip">+{evts.length-5}</span>
                  : evts.length > 4 && <span className="cap-cal-mais-pip">+{evts.length-4}</span>
                }
              </div>
            </div>
          );
        })}
      </div>
      {diaAtivo && (
        <div className="cap-cal-panel">
          <div className="cap-cal-panel-header">
            <span className="cap-cal-panel-data">{fmt(diaAtivo)}</span>
            <button className="cap-cal-panel-close" onClick={() => setDiaAtivo(null)}>✕</button>
          </div>
          {evtsAtivo.length === 0
            ? <p className="cap-cal-panel-vazio">Nenhuma ação agendada.</p>
            : <div className="cap-cal-panel-lista">
                {evtsAtivo.map((e, i) => (
                  <div key={i} className="cap-cal-panel-item"
                    style={{ borderLeftColor: isAdmin ? corretorColor(e.captacao.nome_corretor, corretores) : ETAPA_INFO[e.etapa]?.color }}
                    onClick={() => onCardClick(e.captacao)}
                  >
                    {isAdmin && <span className="cap-cal-panel-corretor" style={{ color: corretorColor(e.captacao.nome_corretor, corretores) }}>{e.captacao.nome_corretor || "—"}</span>}
                    <span className="cap-cal-panel-endereco">{e.captacao.endereco}</span>
                    <span className="cap-cal-panel-acao">{e.acao || "Ação agendada"}</span>
                    <span className="cap-cal-panel-etapa" style={{ background: ETAPA_INFO[e.etapa]?.light, color: ETAPA_INFO[e.etapa]?.color }}>
                      {ETAPA_INFO[e.etapa]?.icon} {ETAPA_INFO[e.etapa]?.label}
                    </span>
                  </div>
                ))}
              </div>
          }
        </div>
      )}
    </div>
  );
}

// ── Seção de avanço de etapa ─────────────────────────────────────────────────
function SecaoAvanco({ captacao, onSalvar, loading }) {
  const [form, setForm] = useState({});
  const [resp, setResp] = useState(null);
  const etapa = captacao.etapa_atual;

  // Inicializa resp com o valor já salvo na captação para cada etapa
  useEffect(() => {
    setForm({});
    const boolSalvo =
      etapa === "interacao"    ? (captacao.falou_proprietario ?? null) :
      etapa === "apresentacao" ? (captacao.visitou_imovel     ?? null) :
      etapa === "captacao"     ? (captacao.captou_imovel      ?? null) :
      null;
    setResp(boolSalvo);
  }, [captacao.id, captacao.etapa_atual]);

  const upStr = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  // Salva a ação e volta para a pergunta (Sim/Não)
  const salvarAcao = async (data) => {
    await onSalvar(data);
    setResp(null);
  };

  if (captacao.status === "fechado" || captacao.status === "captado") return null;

  // ── Escolha ──
  if (etapa === "escolha") {
    if (captacao.tem_numero === true) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-info">Número <strong>{captacao.numero_imovel || "—"}</strong> já registrado.</p>
        <button className="cap-action-btn cap-action-btn--primary" disabled={loading}
          onClick={() => onSalvar({ etapa_atual: "prospeccao" })}>
          {loading ? "…" : "Avançar para Prospecção →"}
        </button>
      </div>
    );
    if (resp === null) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-pergunta">Você tem o número do imóvel?</p>
        <BotaoResposta resp={resp} onResp={setResp} />
      </div>
    );
    if (resp === true) return (
      <div className="cap-avanco-box">
        <CampoTexto label="Número / apartamento" value={form.numero_imovel} onChange={upStr("numero_imovel")} placeholder="Ex: 302" autoFocus />
        <button className="cap-action-btn cap-action-btn--primary" disabled={loading}
          onClick={() => onSalvar({ tem_numero: true, numero_imovel: form.numero_imovel || "", etapa_atual: "prospeccao" })}>
          {loading ? "…" : "Salvar e ir para Prospecção →"}
        </button>
      </div>
    );
    return (
      <div className="cap-avanco-box">
        <CampoArea label="Objeção" value={form.acao_sem_numero} onChange={upStr("acao_sem_numero")} placeholder="Descreva o motivo ou próxima ação" />
        <CampoTexto label="Data da ação" value={form.data_acao_sem_numero} onChange={upStr("data_acao_sem_numero")} type="date" />
        <button className="cap-action-btn cap-action-btn--secondary" disabled={loading}
          onClick={() => salvarAcao({ tem_numero: false, acao_sem_numero: form.acao_sem_numero || "", data_acao_sem_numero: form.data_acao_sem_numero || null })}>
          {loading ? "…" : "Salvar ação"}
        </button>
      </div>
    );
  }

  // Botão discreto para alterar resposta já dada
  const BtnAlterar = () => (
    <button type="button" className="cap-alterar-resp-btn" onClick={() => setResp(null)}>
      ↩ Alterar resposta
    </button>
  );

  // ── Prospecção ──
  // Dados do proprietário (nome, telefone, book, número, link) ficam no painel lateral.
  // Aqui só gerenciamos o avanço de etapa: confirmação de contato com o proprietário.
  if (etapa === "prospeccao") {
    if (resp === null) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-info" style={{ fontSize: 13, color: "#64748b", marginBottom: 10 }}>
          Preencha os dados do proprietário no painel ao lado, depois responda:
        </p>
        <p className="cap-avanco-pergunta">Você já falou com o proprietário?</p>
        <BotaoResposta resp={resp} onResp={setResp} />
      </div>
    );
    if (resp === true) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-info">✓ Ótimo! Avançar para a fase de Interação.</p>
        <button className="cap-action-btn cap-action-btn--primary" disabled={loading}
          onClick={() => onSalvar({ etapa_atual: "interacao" })}>
          {loading ? "…" : "Ir para Interação →"}
        </button>
        <BtnAlterar />
      </div>
    );
    return (
      <div className="cap-avanco-box">
        <CampoArea label="Objeção" value={form.motivo_nao_interacao} onChange={upStr("motivo_nao_interacao")} placeholder="Por que não conseguiu falar?" />
        <CampoTexto label="Próxima tentativa" value={form.proxima_acao_interacao} onChange={upStr("proxima_acao_interacao")} placeholder="O que vai fazer?" />
        <CampoTexto label="Data" value={form.data_proxima_acao_interacao} onChange={upStr("data_proxima_acao_interacao")} type="date" />
        <button className="cap-action-btn cap-action-btn--secondary" disabled={loading}
          onClick={() => salvarAcao({ motivo_nao_interacao: form.motivo_nao_interacao || "", proxima_acao_interacao: form.proxima_acao_interacao || "", data_proxima_acao_interacao: form.data_proxima_acao_interacao || null })}>
          {loading ? "…" : "Salvar ação"}
        </button>
        <BtnAlterar />
      </div>
    );
  }

  // ── Interação ──
  if (etapa === "interacao") {
    if (resp === null) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-pergunta">Você falou com o proprietário?</p>
        <BotaoResposta resp={resp} onResp={setResp} />
      </div>
    );
    if (resp === true) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-info">✓ Proprietário contatado.</p>
        <button className="cap-action-btn cap-action-btn--primary" disabled={loading}
          onClick={() => onSalvar({ falou_proprietario: true, etapa_atual: "apresentacao" })}>
          {loading ? "…" : "Avançar para Apresentação →"}
        </button>
        <BtnAlterar />
      </div>
    );
    return (
      <div className="cap-avanco-box">
        <CampoArea label="Objeção" value={form.motivo_nao_interacao} onChange={upStr("motivo_nao_interacao")} placeholder="Por que não conseguiu falar?" />
        <CampoTexto label="Próxima ação" value={form.proxima_acao_interacao} onChange={upStr("proxima_acao_interacao")} placeholder="O que vai fazer?" />
        <CampoTexto label="Data" value={form.data_proxima_acao_interacao} onChange={upStr("data_proxima_acao_interacao")} type="date" />
        <button className="cap-action-btn cap-action-btn--secondary" disabled={loading}
          onClick={() => salvarAcao({ falou_proprietario: false, motivo_nao_interacao: form.motivo_nao_interacao || "", proxima_acao_interacao: form.proxima_acao_interacao || "", data_proxima_acao_interacao: form.data_proxima_acao_interacao || null })}>
          {loading ? "…" : "Salvar ação"}
        </button>
        <BtnAlterar />
      </div>
    );
  }

  // ── Apresentação ──
  if (etapa === "apresentacao") {
    if (resp === null) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-pergunta">Você visitou o imóvel?</p>
        <BotaoResposta resp={resp} onResp={setResp} />
      </div>
    );
    if (resp === true) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-info">✓ Imóvel visitado!</p>
        <button className="cap-action-btn cap-action-btn--primary" disabled={loading}
          onClick={() => onSalvar({ visitou_imovel: true, etapa_atual: "captacao" })}>
          {loading ? "…" : "Avançar para Captação →"}
        </button>
        <BtnAlterar />
      </div>
    );
    return (
      <div className="cap-avanco-box">
        <CampoArea label="Objeção" value={form.motivo_nao_apresentacao} onChange={upStr("motivo_nao_apresentacao")} placeholder="Por que não visitou?" />
        <CampoTexto label="Próxima ação" value={form.proxima_acao_apresentacao} onChange={upStr("proxima_acao_apresentacao")} placeholder="O que vai fazer?" />
        <CampoTexto label="Data" value={form.data_proxima_acao_apresentacao} onChange={upStr("data_proxima_acao_apresentacao")} type="date" />
        <button className="cap-action-btn cap-action-btn--secondary" disabled={loading}
          onClick={() => salvarAcao({ visitou_imovel: false, motivo_nao_apresentacao: form.motivo_nao_apresentacao || "", proxima_acao_apresentacao: form.proxima_acao_apresentacao || "", data_proxima_acao_apresentacao: form.data_proxima_acao_apresentacao || null })}>
          {loading ? "…" : "Salvar ação"}
        </button>
        <BtnAlterar />
      </div>
    );
  }

  // ── Captação ──
  if (etapa === "captacao") {
    if (resp === null) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-pergunta">Você captou o imóvel?</p>
        <BotaoResposta resp={resp} onResp={setResp} />
      </div>
    );
    if (resp === true) return (
      <div className="cap-avanco-box">
        <p className="cap-avanco-info cap-success">Parabéns! Registrar como captado.</p>
        <button className="cap-action-btn cap-action-btn--captado" disabled={loading}
          onClick={() => onSalvar({ captou_imovel: true, status: "captado" })}>
          {loading ? "…" : "✓ Confirmar Captação"}
        </button>
        <BtnAlterar />
      </div>
    );
    return (
      <div className="cap-avanco-box">
        <CampoArea label="Objeção" value={form.objecao_captacao} onChange={upStr("objecao_captacao")} placeholder="Qual foi a objeção?" />
        <CampoTexto label="Próxima ação" value={form.proxima_acao_captacao} onChange={upStr("proxima_acao_captacao")} placeholder="O que vai tentar?" />
        <CampoTexto label="Data" value={form.data_proxima_acao_captacao} onChange={upStr("data_proxima_acao_captacao")} type="date" />
        <button className="cap-action-btn cap-action-btn--secondary" disabled={loading}
          onClick={() => salvarAcao({ captou_imovel: false, objecao_captacao: form.objecao_captacao || "", proxima_acao_captacao: form.proxima_acao_captacao || "", data_proxima_acao_captacao: form.data_proxima_acao_captacao || null })}>
          {loading ? "…" : "Salvar ação"}
        </button>
        <BtnAlterar />
      </div>
    );
  }
  return null;
}

// ── Kanban Card ──────────────────────────────────────────────────────────────
function KanbanCard({ c, onClick, isAdmin }) {
  const etapa    = ETAPA_INFO[c.etapa_atual] || {};
  const isCaptado = c.status === "captado";
  const ageColor  = corIdade(c.data_entrada_etapa);
  const ageLabel  = diasDesde(c.data_entrada_etapa);

  const temAcao   = !!c[CAMP_ACAO_KANBAN[c.etapa_atual]];
  const acaoFeita = c[CAMP_REAL_KANBAN[c.etapa_atual]] === true;
  const acaoStatus  = temAcao ? (acaoFeita ? "feita" : "pendente") : null;

  return (
    <div className={`cap-kcard${isCaptado ? " cap-kcard--captado" : ""}`}
      style={{ borderLeftColor: etapa.color }} onClick={() => onClick(c)}>

      {/* Linha de topo: age indicator + book icon */}
      <div className="cap-kcard-top-row">
        {ageLabel !== null && (
          <span className="cap-kcard-age" style={{ color: ageColor, borderColor: ageColor }}>
            {ageLabel === 0 ? "Hoje" : `${ageLabel}d`}
          </span>
        )}
        {["prospeccao","interacao","apresentacao","captacao"].includes(c.etapa_atual) && (
          c.book_enviado === true
            ? <span className="cap-kcard-book cap-kcard-book--sim" title="Book enviado">B</span>
            : <span className="cap-kcard-book cap-kcard-book--nao" title="Book não enviado">B</span>
        )}
        {acaoStatus === "feita"    && <span className="cap-kcard-acao-badge cap-kcard-acao-badge--ok"  title="Ação realizada">✓</span>}
        {acaoStatus === "pendente" && <span className="cap-kcard-acao-badge cap-kcard-acao-badge--nok" title="Ação pendente">!</span>}
      </div>

      <div className="cap-kcard-endereco">{c.endereco}</div>
      {(c.bairro || c.bloco) && <div className="cap-kcard-loc">{[c.bairro, c.bloco].filter(Boolean).join(" · ")}</div>}
      {c.numero_imovel && <div className="cap-kcard-num">Nº {c.numero_imovel}</div>}
      {c.nome_cliente  && <div className="cap-kcard-cliente">👤 {c.nome_cliente}</div>}

      <div className="cap-kcard-footer">
        {isAdmin && c.nome_corretor && <span className="cap-kcard-corretor">{c.nome_corretor}</span>}
        <span className="cap-kcard-data">{fmt(c.updated_at)}</span>
      </div>
      {isCaptado && <span className="cap-kcard-badge cap-kcard-badge--captado">Captado ✓</span>}
    </div>
  );
}

// ── Modal detalhe ────────────────────────────────────────────────────────────
function ModalDetalhe({ captacao, onClose, onAvancar, onSave, avancarLoading, onFechar }) {
  // ── Estados de edição de endereço ──
  const [editBairro,  setEditBairro]  = useState(captacao.bairro          || "");
  const [editBloco,   setEditBloco]   = useState(captacao.bloco           || "");
  const [editNumero,  setEditNumero]  = useState(captacao.numero_imovel   || "");
  const [editLink,    setEditLink]    = useState(captacao.link_anuncio    || "");
  const [salvandoEnd, setSalvandoEnd] = useState(false);

  // ── Estados de edição de proprietário ──
  const [editNome,  setEditNome]  = useState(captacao.nome_cliente    || "");
  const [editTel,   setEditTel]   = useState(captacao.telefone_cliente || "");
  const [editBook,  setEditBook]  = useState(captacao.book_enviado);
  const [salvandoProp, setSalvandoProp] = useState(false);

  // Sincroniza campos ao trocar de captação ou de etapa (ex: escolha → prospecção)
  useEffect(() => {
    setEditBairro(captacao.bairro || "");
    setEditBloco(captacao.bloco || "");
    setEditNumero(captacao.numero_imovel || "");
    setEditLink(captacao.link_anuncio || "");
    setEditNome(captacao.nome_cliente || "");
    setEditTel(captacao.telefone_cliente || "");
    setEditBook(captacao.book_enviado);
  }, [captacao.id, captacao.etapa_atual]);

  const etapa    = ETAPA_INFO[captacao.etapa_atual] || {};
  const etapaIdx = ETAPAS.findIndex(e => e.key === captacao.etapa_atual);
  const ETAPAS_PROP = ["prospeccao","interacao","apresentacao","captacao"];
  const mostraProp  = ETAPAS_PROP.includes(captacao.etapa_atual);

  const emEscolha = captacao.etapa_atual === "escolha";

  // Detecta mudanças
  const endAlterado  = editBairro !== (captacao.bairro         || "")
                    || editBloco  !== (captacao.bloco          || "")
                    || (!emEscolha && editNumero !== (captacao.numero_imovel  || ""))
                    || (!emEscolha && editLink   !== (captacao.link_anuncio   || ""));

  const propAlterada = editNome  !== (captacao.nome_cliente    || "")
                    || editTel   !== (captacao.telefone_cliente || "")
                    || editBook  !== captacao.book_enviado;

  const salvarEndereco = async () => {
    setSalvandoEnd(true);
    try {
      await onSave({
        bairro: editBairro || null,
        bloco:  editBloco  || null,
        ...(!emEscolha && { numero_imovel: editNumero || null, link_anuncio: editLink || null }),
      });
    } finally {
      setSalvandoEnd(false);
    }
  };

  const salvarProprietario = async () => {
    setSalvandoProp(true);
    try {
      await onSave({
        nome_cliente:     editNome || null,
        telefone_cliente: editTel  || null,
        book_enviado:     editBook,
      });
    } finally {
      setSalvandoProp(false);
    }
  };

  // Confirmação de encerramento inline
  const [confirmEncerrar, setConfirmEncerrar] = useState(false);
  const podeEncerrar = captacao.status !== "fechado" && captacao.status !== "captado";

  return (
    <div className="cap-overlay" onClick={onClose}>
      <div className="cap-modal" onClick={e => e.stopPropagation()}>

        <div className="cap-modal-header" style={{ borderTopColor: etapa.color }}>
          <div className="cap-modal-header-main">
            <div className="cap-modal-etapa-tag" style={{ background: etapa.light, color: etapa.color }}>
              {etapa.icon} {etapa.label}
            </div>
            <h2 className="cap-modal-titulo">
              {captacao.endereco}
              {captacao.numero_imovel && <span className="cap-modal-num"> — Nº {captacao.numero_imovel}</span>}
            </h2>
            {(captacao.bairro || captacao.bloco) && (
              <p className="cap-modal-sub">{[captacao.bairro, captacao.bloco].filter(Boolean).join(" · ")}</p>
            )}
          </div>
          <div className="cap-modal-header-actions">
            {podeEncerrar && (
              <button
                className="cap-encerrar-btn"
                title="Encerrar captação"
                onClick={() => setConfirmEncerrar(true)}
              >
                ✕ Encerrar
              </button>
            )}
            <button className="cap-modal-close" onClick={onClose}>✕</button>
          </div>
        </div>

        {/* Confirmação de encerramento (inline, aparece abaixo do header) */}
        {confirmEncerrar && (
          <div className="cap-confirm-encerrar">
            <div className="cap-confirm-encerrar-icon">⚠️</div>
            <div className="cap-confirm-encerrar-texto">
              <strong>Tem certeza que quer encerrar este processo?</strong>
              <p>O imóvel não será apagado. O motivo ficará registrado no relatório do gerente.</p>
            </div>
            <div className="cap-confirm-encerrar-acoes">
              <button className="cap-ghost-btn" onClick={() => setConfirmEncerrar(false)}>Não, voltar</button>
              <button className="cap-danger-btn" onClick={() => { setConfirmEncerrar(false); onFechar(); }}>
                Sim, encerrar
              </button>
            </div>
          </div>
        )}

        {/* Progress */}
        <div className="cap-progress-bar">
          {ETAPAS.map((e, i) => (
            <div key={e.key}
              className={`cap-progress-step${i <= etapaIdx ? " cap-progress-step--done" : ""}${i === etapaIdx ? " cap-progress-step--ativo" : ""}`}
              style={i <= etapaIdx ? { background: e.color } : {}}>
              <span className="cap-progress-label">{e.label}</span>
            </div>
          ))}
        </div>

        <div className="cap-modal-cols">

          {/* ── Coluna esquerda: endereço + proprietário + histórico ── */}
          <div className="cap-modal-col-info">

            {/* Endereço — sempre editável */}
            <h3 className="cap-section-h">Endereço</h3>
            <div className="cap-endereco-bloco">
              <div className="cap-end-row">
                <span className="cap-end-label">Endereço</span>
                <span className="cap-end-val">{captacao.endereco}</span>
              </div>
              <div className="cap-end-row cap-end-row--edit">
                <span className="cap-end-label">Bairro</span>
                <input className="cap-end-input" value={editBairro} onChange={e => setEditBairro(e.target.value)} placeholder="Adicionar bairro" />
              </div>
              <div className="cap-end-row cap-end-row--edit">
                <span className="cap-end-label">Bloco</span>
                <input className="cap-end-input" value={editBloco} onChange={e => setEditBloco(e.target.value)} placeholder="Adicionar bloco" />
              </div>
              {!emEscolha && (
                <>
                  <div className="cap-end-row cap-end-row--edit">
                    <span className="cap-end-label">Número</span>
                    <input className="cap-end-input" value={editNumero} onChange={e => setEditNumero(e.target.value)} placeholder="Nº / ap." />
                  </div>
                  <div className="cap-end-row cap-end-row--edit">
                    <span className="cap-end-label">Anúncio</span>
                    <input className="cap-end-input" value={editLink} onChange={e => setEditLink(e.target.value)} placeholder="https://..." />
                  </div>
                  {editLink && (
                    <div className="cap-end-row">
                      <span className="cap-end-label" />
                      <a href={editLink} target="_blank" rel="noreferrer" className="cap-end-link">🔗 Abrir anúncio</a>
                    </div>
                  )}
                </>
              )}
              <button className="cap-end-save-btn" disabled={salvandoEnd || !endAlterado} onClick={salvarEndereco}>
                {salvandoEnd ? "Salvando…" : "Salvar endereço"}
              </button>
            </div>

            {/* Proprietário — sempre editável (prospeccao em diante) */}
            {mostraProp && (
              <>
                <h3 className="cap-section-h" style={{ marginTop: 16 }}>Proprietário</h3>
                <div className="cap-endereco-bloco">
                  <div className="cap-end-row cap-end-row--edit">
                    <span className="cap-end-label">Nome</span>
                    <input className="cap-end-input" value={editNome} onChange={e => setEditNome(e.target.value)} placeholder="Nome do proprietário" />
                  </div>
                  <div className="cap-end-row cap-end-row--edit">
                    <span className="cap-end-label">Telefone</span>
                    <input className="cap-end-input" value={editTel} onChange={e => setEditTel(e.target.value)} placeholder="(61) 9 0000-0000" />
                  </div>
                  <div className="cap-end-row cap-end-row--book">
                    <span className="cap-end-label">Book</span>
                    <div className="cap-end-book-toggle">
                      <button
                        className={`cap-end-book-btn cap-end-book-btn--sim${editBook === true ? " active" : ""}`}
                        onClick={() => setEditBook(true)}
                      >Sim</button>
                      <button
                        className={`cap-end-book-btn cap-end-book-btn--nao${editBook === false ? " active" : ""}`}
                        onClick={() => setEditBook(false)}
                      >Não</button>
                      <a href={bookPdf} target="_blank" rel="noreferrer" className="cap-ver-book-btn" style={{ marginLeft: 6 }}>
                        📄 Ver book
                      </a>
                    </div>
                  </div>
                  <button className="cap-end-save-btn" disabled={salvandoProp || !propAlterada} onClick={salvarProprietario}>
                    {salvandoProp ? "Salvando…" : "Salvar proprietário"}
                  </button>
                </div>
              </>
            )}

            {/* Histórico */}
            <h3 className="cap-section-h" style={{ marginTop: 20 }}>Histórico de ações</h3>
            <HistoricoTimeline captacao={captacao} onMarcarRealizada={onSave} />

            {captacao.status === "fechado" && (
              <div className="cap-fechado-box" style={{ marginTop: 16 }}>
                <h3 className="cap-section-h">Encerramento</h3>
                <p className="cap-fechado-motivo">{captacao.motivo_fechamento}</p>
                <p className="cap-fechado-data">Encerrado em {fmt(captacao.data_fechamento)}</p>
              </div>
            )}
          </div>

          {/* ── Coluna direita: próximo passo ── */}
          {captacao.status !== "fechado" && captacao.status !== "captado" && (
            <div className="cap-modal-col-avanco">
              <h3 className="cap-section-h">Próximo passo</h3>
              <SecaoAvanco captacao={captacao} onSalvar={onAvancar} loading={avancarLoading} />
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

// ── Modal fechar ─────────────────────────────────────────────────────────────
function ModalFechar({ onConfirmar, onCancelar, loading }) {
  const [motivo, setMotivo] = useState("");
  return (
    <div className="cap-overlay" onClick={onCancelar}>
      <div className="cap-modal cap-modal--sm" onClick={e => e.stopPropagation()}>
        <div className="cap-modal-header" style={{ borderTopColor: "#ef4444" }}>
          <div className="cap-modal-header-main">
            <div className="cap-modal-etapa-tag" style={{ background: "#fee2e2", color: "#ef4444" }}>Encerrar captação</div>
            <h2 className="cap-modal-titulo">Motivo do encerramento</h2>
            <p className="cap-modal-sub">O registro não será apagado — aparece no relatório do gerente.</p>
          </div>
          <button className="cap-modal-close" onClick={onCancelar}>✕</button>
        </div>
        <div className="cap-modal-body">
          <CampoArea label="Motivo *" value={motivo} onChange={e => setMotivo(e.target.value)} placeholder="Explique por que está encerrando esta captação..." rows={4} />
        </div>
        <div className="cap-modal-footer">
          <button className="cap-ghost-btn" onClick={onCancelar}>Cancelar</button>
          <button className="cap-danger-btn" disabled={loading || !motivo.trim()} onClick={() => onConfirmar(motivo)}>
            {loading ? "Encerrando…" : "Confirmar encerramento"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal novo imóvel ─────────────────────────────────────────────────────────
function ModalNovoImovel({ onSalvar, onCancelar, loading, isAdmin, corretores }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ endereco: "", bairro: "", bloco: "" });
  const [temNum, setTemNum] = useState(null);
  const [extra, setExtra] = useState({ numero_imovel: "", acao_sem_numero: "", data_acao_sem_numero: "" });
  const [corretorSel, setCorretorSel] = useState(null); // { id_usuarios, nome, team }

  const upForm  = k => e => setForm(p  => ({ ...p, [k]: e.target.value }));
  const upExtra = k => e => setExtra(p => ({ ...p, [k]: e.target.value }));

  // Admin deve selecionar um corretor antes de avançar
  const podeProsseguir = form.endereco.trim() && (!isAdmin || corretorSel);

  return (
    <div className="cap-overlay" onClick={onCancelar}>
      <div className="cap-modal cap-modal--sm" onClick={e => e.stopPropagation()}>
        <div className="cap-modal-header" style={{ borderTopColor: "#2563eb" }}>
          <div className="cap-modal-header-main">
            <div className="cap-modal-step-indicator">
              <span className={`cap-step-dot${step >= 1 ? " active" : ""}`} />
              <span className="cap-step-line" />
              <span className={`cap-step-dot${step >= 2 ? " active" : ""}`} />
            </div>
            <h2 className="cap-modal-titulo">{step === 1 ? "Endereço do imóvel" : "Número do imóvel"}</h2>
          </div>
          <button className="cap-modal-close" onClick={onCancelar}>✕</button>
        </div>

        <div className="cap-modal-body">
          {step === 1 && (
            <>
              {/* Seletor de corretor (só para admin) */}
              {isAdmin && (
                <div className="cap-field">
                  <label className="cap-field-label">Corretor responsável *</label>
                  <CorretorCombobox
                    corretores={corretores}
                    value={corretorSel}
                    onChange={setCorretorSel}
                  />
                </div>
              )}

              <CampoTexto label="Endereço *" value={form.endereco} onChange={upForm("endereco")} placeholder="Ex: SQN 308 Bloco A" autoFocus={!isAdmin} />
              <CampoTexto label="Bairro"     value={form.bairro}   onChange={upForm("bairro")}   placeholder="Ex: Asa Norte" />
              <CampoTexto label="Bloco / Complemento" value={form.bloco} onChange={upForm("bloco")} placeholder="Ex: Bloco B" />
            </>
          )}

          {step === 2 && (
            <>
              {/* Preview do que foi preenchido */}
              <div className="cap-novo-preview">
                <div className="cap-novo-preview-titulo">Imóvel sendo lançado</div>
                {isAdmin && corretorSel && (
                  <div className="cap-novo-preview-linha"><span>Corretor</span>{corretorSel.nome}</div>
                )}
                {form.endereco   && <div className="cap-novo-preview-linha"><span>Endereço</span>{form.endereco}</div>}
                {form.bairro     && <div className="cap-novo-preview-linha"><span>Bairro</span>{form.bairro}</div>}
                {form.bloco      && <div className="cap-novo-preview-linha"><span>Bloco</span>{form.bloco}</div>}
                {extra.numero_imovel && <div className="cap-novo-preview-linha"><span>Número</span>{extra.numero_imovel}</div>}
              </div>

              {temNum === null && (
                <div style={{ textAlign: "center", padding: "8px 0" }}>
                  <p className="cap-avanco-pergunta">Você tem o número do imóvel?</p>
                  <BotaoResposta resp={temNum} onResp={setTemNum} />
                </div>
              )}
              {temNum === true && (
                <CampoTexto label="Número / apartamento" value={extra.numero_imovel} onChange={upExtra("numero_imovel")} placeholder="Ex: 302" autoFocus />
              )}
              {temNum === false && (
                <>
                  <p className="cap-avanco-info">Registre a próxima ação para descobrir o número.</p>
                  <CampoArea label="Objeção / próxima ação" value={extra.acao_sem_numero} onChange={upExtra("acao_sem_numero")} placeholder="O que vai fazer?" />
                  <CampoTexto label="Data da ação" value={extra.data_acao_sem_numero} onChange={upExtra("data_acao_sem_numero")} type="date" />
                </>
              )}
            </>
          )}
        </div>

        <div className="cap-modal-footer">
          {step === 1 ? (
            <>
              <button className="cap-ghost-btn" onClick={onCancelar}>Cancelar</button>
              <button
                className="cap-primary-btn"
                disabled={!podeProsseguir}
                title={isAdmin && !corretorSel ? "Selecione um corretor antes de continuar" : ""}
                onClick={() => setStep(2)}
              >
                Próximo →
              </button>
            </>
          ) : (
            <>
              <button className="cap-ghost-btn" onClick={() => { setStep(1); setTemNum(null); }}>← Voltar</button>
              <button
                className="cap-primary-btn"
                disabled={loading || temNum === null || (temNum === true && !extra.numero_imovel.trim())}
                onClick={() => onSalvar({
                  ...form, temNum, extra,
                  corretorId:   corretorSel?.id_usuarios,
                  corretorNome: corretorSel?.nome,
                  corretorTeam: corretorSel?.team,
                })}
              >
                {loading ? "Lançando…" : "Lançar imóvel"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard gerente ─────────────────────────────────────────────────────────
function BarraHorizontal({ valor, max, color }) {
  const pct = max > 0 ? Math.round((valor / max) * 100) : 0;
  return (
    <div className="dash-barra-bg">
      <div className="dash-barra-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function DashboardGerente({ captacoes }) {
  const agora   = new Date();
  const hojeStr = `${agora.getFullYear()}-${String(agora.getMonth()+1).padStart(2,"0")}-${String(agora.getDate()).padStart(2,"0")}`;
  const em7     = new Date(agora); em7.setDate(em7.getDate() + 7);
  const em7Str  = em7.toISOString().split("T")[0];

  const total    = captacoes.length;
  const captados = captacoes.filter(c => c.status === "captado").length;
  const fechados = captacoes.filter(c => c.status === "fechado").length;
  const ativos   = total - captados - fechados;
  const taxa     = total > 0 ? Math.round((captados / total) * 100) : 0;

  const funil = [
    ...ETAPAS.map(e => ({ label: e.label, color: e.color, n: captacoes.filter(c => c.etapa_atual === e.key && c.status !== "fechado").length })),
    { label: "Captados ✓", color: "#15803d", n: captados },
  ];
  const maxFunil = Math.max(...funil.map(f => f.n), 1);

  const corretoresMap = {};
  captacoes.forEach(c => {
    const nome = c.nome_corretor || "Sem nome";
    if (!corretoresMap[nome]) corretoresMap[nome] = { ativos: 0, captados: 0, fechados: 0, total: 0 };
    corretoresMap[nome].total++;
    if (c.status === "captado") corretoresMap[nome].captados++;
    else if (c.status === "fechado") corretoresMap[nome].fechados++;
    else corretoresMap[nome].ativos++;
  });
  const corretoresLista = Object.entries(corretoresMap)
    .map(([nome, v]) => ({ nome, ...v, taxa: v.total > 0 ? Math.round((v.captados / v.total) * 100) : 0 }))
    .sort((a, b) => b.captados - a.captados || b.ativos - a.ativos);

  const motivosMap = {};
  captacoes.forEach(c => {
    [c.motivo_fechamento, c.motivo_nao_interacao, c.motivo_nao_apresentacao, c.objecao_captacao].forEach(m => {
      if (m?.trim()) motivosMap[m.trim()] = (motivosMap[m.trim()] || 0) + 1;
    });
  });
  const motivosLista = Object.entries(motivosMap).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxMotivo    = motivosLista[0]?.[1] || 1;

  const proximasAcoes = extrairEventos(captacoes)
    .filter(e => e.data >= hojeStr && e.data <= em7Str)
    .sort((a, b) => a.data.localeCompare(b.data));

  return (
    <div className="dash-wrap">
      <div className="dash-kpis">
        {[
          { label: "Total",        num: total,    cls: "dash-kpi--blue"   },
          { label: "Em andamento", num: ativos,   cls: "dash-kpi--amber"  },
          { label: "Captados",     num: captados, cls: "dash-kpi--green"  },
          { label: "Encerrados",   num: fechados, cls: "dash-kpi--red"    },
          { label: "Conversão",    num: `${taxa}%`, cls: "dash-kpi--purple" },
        ].map(k => (
          <div key={k.label} className={`dash-kpi ${k.cls}`}>
            <span className="dash-kpi-num">{k.num}</span>
            <span className="dash-kpi-label">{k.label}</span>
          </div>
        ))}
      </div>

      <div className="dash-grid">
        <div className="dash-card">
          <h3 className="dash-card-titulo">Funil de conversão</h3>
          <div className="dash-funil">
            {funil.map(f => (
              <div key={f.label} className="dash-funil-row">
                <span className="dash-funil-label">{f.label}</span>
                <BarraHorizontal valor={f.n} max={maxFunil} color={f.color} />
                <span className="dash-funil-num" style={{ color: f.color }}>{f.n}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="dash-card">
          <h3 className="dash-card-titulo">Principais objeções / perdas</h3>
          {motivosLista.length === 0
            ? <p className="dash-vazio">Nenhuma objeção registrada.</p>
            : <div className="dash-motivos">
                {motivosLista.map(([m, n]) => (
                  <div key={m} className="dash-motivo-row">
                    <span className="dash-motivo-label">{m}</span>
                    <BarraHorizontal valor={n} max={maxMotivo} color="#ef4444" />
                    <span className="dash-motivo-num">{n}</span>
                  </div>
                ))}
              </div>
          }
        </div>

        <div className="dash-card dash-card--full">
          <h3 className="dash-card-titulo">Desempenho por corretor</h3>
          {corretoresLista.length === 0
            ? <p className="dash-vazio">Sem dados.</p>
            : <div className="dash-table-wrap">
                <table className="dash-table">
                  <thead><tr><th>Corretor</th><th>Total</th><th>Ativos</th><th>Captados</th><th>Encerrados</th><th>Conversão</th></tr></thead>
                  <tbody>
                    {corretoresLista.map((c, i) => (
                      <tr key={c.nome}>
                        <td><span className="dash-corretor-dot" style={{ background: CORRETOR_PALETTE[i % CORRETOR_PALETTE.length] }} />{c.nome}</td>
                        <td className="dash-td-num">{c.total}</td>
                        <td className="dash-td-num dash-td--blue">{c.ativos}</td>
                        <td className="dash-td-num dash-td--green">{c.captados}</td>
                        <td className="dash-td-num dash-td--red">{c.fechados}</td>
                        <td><span className={`dash-taxa-badge${c.taxa>=50?" dash-taxa--alta":c.taxa>=20?" dash-taxa--media":" dash-taxa--baixa"}`}>{c.taxa}%</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
          }
        </div>

        <div className="dash-card dash-card--full">
          <h3 className="dash-card-titulo">Próximas ações — 7 dias</h3>
          {proximasAcoes.length === 0
            ? <p className="dash-vazio">Nenhuma ação agendada.</p>
            : <div className="dash-acoes-lista">
                {proximasAcoes.map((e, i) => (
                  <div key={i} className="dash-acao-item" style={{ borderLeftColor: ETAPA_INFO[e.etapa]?.color }}>
                    <div className="dash-acao-data">{fmt(e.data)}</div>
                    <div className="dash-acao-info">
                      <span className="dash-acao-corretor">{e.captacao.nome_corretor || "—"}</span>
                      <span className="dash-acao-endereco">{e.captacao.endereco}</span>
                      <span className="dash-acao-desc">{e.acao || "Ação agendada"}</span>
                    </div>
                    <span className="dash-acao-etapa" style={{ background: ETAPA_INFO[e.etapa]?.light, color: ETAPA_INFO[e.etapa]?.color }}>
                      {ETAPA_INFO[e.etapa]?.icon} {ETAPA_INFO[e.etapa]?.label}
                    </span>
                  </div>
                ))}
              </div>
          }
        </div>
      </div>
    </div>
  );
}

// ── Componente principal ─────────────────────────────────────────────────────
export default function JornadaCaptacao() {
  const toast = useToast();
  const [userInfo, setUserInfo] = useState({ id: "", nome: "", team: "", permissao: "" });
  const [captacoes, setCaptacoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [aba, setAba] = useState("kanban");

  const [corretoresAtivos, setCorretoresAtivos] = useState([]);

  const [showNovo, setShowNovo]         = useState(false);
  const [novoLoading, setNovoLoading]   = useState(false);
  const [selecionada, setSelecionada]   = useState(null);
  const [avancarLoading, setAvancarLoading] = useState(false);
  const [showFechar, setShowFechar]     = useState(false);
  const [fecharLoading, setFecharLoading] = useState(false);

  const [filtroCorretor, setFiltroCorretor] = useState("");
  const [filtroDataDe,   setFiltroDataDe]   = useState("");
  const [filtroDataAte,  setFiltroDataAte]  = useState("");
  const [abaGerente, setAbaGerente]         = useState("ativo");

  const isAdmin = userInfo.permissao === "admin";

  useEffect(() => {
    const raw = localStorage.getItem("userData");
    if (!raw) return;
    try {
      const u = JSON.parse(raw);
      setUserInfo({
        id: u.idCorretor || u.id_corretor || u.codigo || u.id_usuarios || "",
        nome: u.nome || u.username || "",
        team: u.team || "",
        permissao: u.permissao || "",
      });
    } catch (e) { console.error(e); }
  }, []);

  const carregarCaptacoes = useCallback(async () => {
    if (!userInfo.id) return;
    setLoading(true);
    try {
      const url = isAdmin
        ? `${BASE}/captacoes?gerente=true${userInfo.team ? `&team=${encodeURIComponent(userInfo.team)}` : ""}`
        : `${BASE}/captacoes?id_corretor=${encodeURIComponent(userInfo.id)}`;
      const r = await fetch(url);
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) setCaptacoes(d.captacoes || []);
      else toast(d.error || "Erro ao carregar", "error");
    } catch { toast("Erro ao carregar captações", "error"); }
    finally { setLoading(false); }
  }, [userInfo.id, userInfo.team, isAdmin, toast]);

  useEffect(() => { if (userInfo.id) carregarCaptacoes(); }, [userInfo.id, carregarCaptacoes]);

  // Carrega corretores ativos (apenas para admin, ao montar)
  useEffect(() => {
    if (!isAdmin || !userInfo.id) return;
    fetch(`${BASE}/corretor/retornar-lista?ativo=true&gerente=${encodeURIComponent(userInfo.id)}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          const lista = (d.lista || []).filter(c => c.permissao !== "admin");
          setCorretoresAtivos(lista);
        }
      })
      .catch(() => {});
  }, [isAdmin, userInfo.id]);

  // Stats
  const stats = useMemo(() => {
    const ativas = captacoes.filter(c => c.status !== "fechado");
    return {
      total: captacoes.length,
      captadas: captacoes.filter(c => c.status === "captado").length,
      fechadas: captacoes.filter(c => c.status === "fechado").length,
      porEtapa: ETAPAS.reduce((acc, e) => { acc[e.key] = ativas.filter(c => c.etapa_atual === e.key).length; return acc; }, {}),
    };
  }, [captacoes]);

  // Filtros
  const captacoesFiltradas = useMemo(() => captacoes.filter(c => {
    if (filtroCorretor && !((c.nome_corretor || "").toLowerCase().includes(filtroCorretor.toLowerCase()))) return false;
    if (filtroDataDe  && c.created_at < filtroDataDe)  return false;
    if (filtroDataAte && c.created_at > filtroDataAte + "T23:59:59") return false;
    return true;
  }), [captacoes, filtroCorretor, filtroDataDe, filtroDataAte]);

  const captacoesAtivas   = useMemo(() => captacoesFiltradas.filter(c => c.status !== "fechado"), [captacoesFiltradas]);
  const captacoesFechadas = useMemo(() => captacoesFiltradas.filter(c => c.status === "fechado"),  [captacoesFiltradas]);
  const porEtapa = useMemo(() => ETAPAS.reduce((acc, e) => {
    acc[e.key] = captacoesAtivas.filter(c => c.etapa_atual === e.key);
    return acc;
  }, {}), [captacoesAtivas]);

  // Handlers
  const handleNovoSalvar = async ({ endereco, bairro, bloco, temNum, extra, corretorId, corretorNome, corretorTeam }) => {
    setNovoLoading(true);
    try {
      const payload = {
        id_corretor:   corretorId   || userInfo.id,
        nome_corretor: corretorNome || userInfo.nome,
        team:          corretorTeam || userInfo.team,
        endereco, bairro: bairro || null, bloco: bloco || null,
        etapa_atual: temNum ? "prospeccao" : "escolha", tem_numero: temNum,
        ...(temNum
          ? { numero_imovel: extra.numero_imovel || null }
          : { acao_sem_numero: extra.acao_sem_numero || null, data_acao_sem_numero: extra.data_acao_sem_numero || null }),
      };
      const r = await fetch(`${BASE}/captacoes`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) { toast("Imóvel lançado!", "success"); setShowNovo(false); carregarCaptacoes(); }
      else toast(d.error || "Erro ao criar", "error");
    } catch { toast("Erro ao criar captação", "error"); }
    finally { setNovoLoading(false); }
  };

  const apiAtualizar = async (id, data) => {
    const r = await fetch(`${BASE}/captacoes/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    const d = await r.json().catch(() => ({}));
    if (r.ok && d.ok) {
      setSelecionada(d.captacao);
      carregarCaptacoes();
      return true;
    }
    toast(d.error || "Erro ao atualizar", "error");
    return false;
  };

  const handleAvancar = async (data) => {
    if (!selecionada) return;
    setAvancarLoading(true);
    await apiAtualizar(selecionada.id, data);
    setAvancarLoading(false);
  };

  const handleSave = async (data) => {
    if (!selecionada) return;
    await apiAtualizar(selecionada.id, data);
  };

  const handleFecharConfirmar = async (motivo) => {
    if (!selecionada) return;
    setFecharLoading(true);
    try {
      const r = await fetch(`${BASE}/captacoes/${selecionada.id}/fechar`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ motivo }),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) { toast("Captação encerrada", "success"); setShowFechar(false); setSelecionada(null); carregarCaptacoes(); }
      else toast(d.error || "Erro", "error");
    } catch { toast("Erro ao encerrar", "error"); }
    finally { setFecharLoading(false); }
  };

  return (
    <div className="cap-page">

      {/* Top bar */}
      <div className="cap-topbar">
        <div className="cap-topbar-left">
          <h1 className="cap-page-titulo">Jornada de Captação</h1>
          <div className="cap-abas-inline">
            <button className={`cap-aba-btn${aba==="kanban"?" cap-aba-btn--ativa":""}`} onClick={() => setAba("kanban")}>▦ Kanban</button>
            <button className={`cap-aba-btn${aba==="calendario"?" cap-aba-btn--ativa":""}`} onClick={() => setAba("calendario")}>📅 Calendário</button>
            {isAdmin && <button className={`cap-aba-btn${aba==="dashboard"?" cap-aba-btn--ativa":""}`} onClick={() => setAba("dashboard")}>📊 Dashboard</button>}
          </div>
        </div>
        <div className="cap-topbar-right">
          {isAdmin && (
            <input className="cap-search-input" placeholder="Filtrar corretor…" value={filtroCorretor} onChange={e => setFiltroCorretor(e.target.value)} />
          )}
          <div className="cap-filtro-data">
            <label className="cap-filtro-data-label">De</label>
            <input className="cap-filtro-data-input" type="date" value={filtroDataDe}  onChange={e => setFiltroDataDe(e.target.value)}  />
            <label className="cap-filtro-data-label">Até</label>
            <input className="cap-filtro-data-input" type="date" value={filtroDataAte} onChange={e => setFiltroDataAte(e.target.value)} />
            {(filtroDataDe || filtroDataAte) && (
              <button className="cap-filtro-limpar" onClick={() => { setFiltroDataDe(""); setFiltroDataAte(""); }} title="Limpar filtro">✕</button>
            )}
          </div>
          {!isAdmin && <button className="cap-primary-btn" onClick={() => setShowNovo(true)}>+ Novo imóvel</button>}
          {isAdmin  && <button className="cap-primary-btn" onClick={() => setShowNovo(true)}>+ Novo imóvel</button>}
          <button className="cap-refresh-btn" onClick={carregarCaptacoes} title="Atualizar">↻</button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="cap-stats-bar">
        {ETAPAS.map(e => (
          <div key={e.key} className="cap-stat-chip" style={{ borderColor: e.color }}>
            <span className="cap-stat-icon">{e.icon}</span>
            <span className="cap-stat-label">{e.label}</span>
            <span className="cap-stat-num" style={{ color: e.color }}>{stats.porEtapa[e.key] || 0}</span>
          </div>
        ))}
        <div className="cap-stat-chip cap-stat-chip--captado">
          <span className="cap-stat-icon">🏆</span>
          <span className="cap-stat-label">Captados</span>
          <span className="cap-stat-num">{stats.captadas}</span>
        </div>
        <div className="cap-stat-chip cap-stat-chip--fechado">
          <span className="cap-stat-icon">✖</span>
          <span className="cap-stat-label">Encerrados</span>
          <span className="cap-stat-num">{stats.fechadas}</span>
        </div>
      </div>

      {loading && <div className="cap-loading-bar"><div className="cap-loading-bar-inner" /></div>}

      {/* Kanban */}
      {aba === "kanban" && (
        <>
          {isAdmin && (
            <div className="cap-gerente-abas">
              <button className={`cap-gaba${abaGerente==="ativo"?" cap-gaba--ativa":""}`} onClick={() => setAbaGerente("ativo")}>Ativos</button>
              <button className={`cap-gaba${abaGerente==="fechado"?" cap-gaba--ativa":""}`} onClick={() => setAbaGerente("fechado")}>Encerrados</button>
            </div>
          )}

          {(!isAdmin || abaGerente === "ativo") && (
            <div className="cap-board">
              {ETAPAS.map(etapa => (
                <div key={etapa.key} className="cap-coluna">
                  <div className="cap-coluna-header" style={{ borderTopColor: etapa.color }}>
                    <span className="cap-coluna-icon">{etapa.icon}</span>
                    <span className="cap-coluna-titulo">{etapa.label}</span>
                    <span className="cap-coluna-count" style={{ background: etapa.color }}>{porEtapa[etapa.key]?.length || 0}</span>
                  </div>
                  <div className="cap-coluna-body">
                    {(porEtapa[etapa.key] || []).length === 0
                      ? <div className="cap-empty-col">Nenhum imóvel</div>
                      : (porEtapa[etapa.key] || []).map(c => (
                          <KanbanCard key={c.id} c={c} onClick={setSelecionada} isAdmin={isAdmin} />
                        ))
                    }
                  </div>
                </div>
              ))}
            </div>
          )}

          {isAdmin && abaGerente === "fechado" && (
            <div className="cap-fechados-lista">
              {captacoesFechadas.length === 0
                ? <div className="cap-empty-state">Nenhuma captação encerrada.</div>
                : captacoesFechadas.map(c => (
                    <div key={c.id} className="cap-fechado-card" onClick={() => setSelecionada(c)}>
                      <div className="cap-fechado-card-top">
                        <span className="cap-fechado-endereco">{c.endereco}</span>
                        <span className="cap-fechado-etapa-tag" style={{ color: ETAPA_INFO[c.etapa_atual]?.color }}>
                          {ETAPA_INFO[c.etapa_atual]?.icon} {ETAPA_INFO[c.etapa_atual]?.label}
                        </span>
                      </div>
                      <div className="cap-fechado-card-mid">
                        {c.nome_corretor && <span className="cap-fechado-corretor">👤 {c.nome_corretor}</span>}
                        <span className="cap-fechado-data">Encerrado em {fmt(c.data_fechamento)}</span>
                      </div>
                      <div className="cap-fechado-motivo">"{c.motivo_fechamento}"</div>
                    </div>
                  ))
              }
            </div>
          )}
        </>
      )}

      {aba === "calendario" && (
        <CalendarioView captacoes={captacoesFiltradas} isAdmin={isAdmin} onCardClick={setSelecionada} />
      )}

      {aba === "dashboard" && isAdmin && (
        <DashboardGerente captacoes={captacoesFiltradas} />
      )}

      {showNovo && (
        <ModalNovoImovel
          onSalvar={handleNovoSalvar}
          onCancelar={() => setShowNovo(false)}
          loading={novoLoading}
          isAdmin={isAdmin}
          corretores={corretoresAtivos}
        />
      )}
      {selecionada && !showFechar && (
        <ModalDetalhe
          captacao={selecionada}
          onClose={() => setSelecionada(null)}
          onAvancar={handleAvancar}
          onSave={handleSave}
          avancarLoading={avancarLoading}
          onFechar={() => setShowFechar(true)}
        />
      )}
      {selecionada && showFechar && (
        <ModalFechar onConfirmar={handleFecharConfirmar} onCancelar={() => setShowFechar(false)} loading={fecharLoading} />
      )}
    </div>
  );
}
