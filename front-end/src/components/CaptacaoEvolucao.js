import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BASE } from "../services/api";
import { useToast } from "../context/ToastContext";
import "../assets/css/captacaoEvolucao.css";

const CORES = [
  "#e1005b", "#2563eb", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#dc2626",
  "#059669", "#db2777", "#4f46e5", "#ca8a04", "#0d9488", "#9333ea",
];
const DIMENSOES = [
  ["equipe", "Equipe"], ["corretor", "Corretor"], ["bairro", "Bairro"],
  ["endereco", "Endereço"], ["categoria", "Categoria"],
];
const CATEGORIAS = ["escolha", "prospeccao", "interacao", "apresentacao", "captacao"];

const fmtDataCurta = (iso) => {
  const p = String(iso).split("-");
  return p.length === 3 ? `${p[2]}/${p[1]}` : iso;
};

// ---- Gráfico de linha SVG interativo ----
function LineChart({ datas, series, cores }) {
  const W = 820, H = 360, padL = 46, padR = 16, padT = 16, padB = 34;
  const svgRef = useRef(null);
  const [hover, setHover] = useState(null); // índice

  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = datas.length;
  const stepX = n > 1 ? innerW / (n - 1) : 0;
  const maxY = Math.max(1, ...series.flatMap((s) => s.pontos));
  const x = (i) => padL + (n > 1 ? i * stepX : innerW / 2);
  const y = (v) => padT + innerH - (v / maxY) * innerH;

  const yTicks = 4;
  const ticks = Array.from({ length: yTicks + 1 }, (_, k) => Math.round((maxY / yTicks) * k));
  const labelsX = useMemo(() => {
    if (n <= 8) return datas.map((d, i) => i);
    const step = Math.ceil(n / 8);
    return datas.map((_, i) => i).filter((i) => i % step === 0 || i === n - 1);
  }, [datas, n]);

  const onMove = (e) => {
    const svg = svgRef.current;
    if (!svg || n === 0) return;
    const rect = svg.getBoundingClientRect();
    const scale = rect.width / W;
    const dataX = (e.clientX - rect.left) / scale;
    let i = stepX ? Math.round((dataX - padL) / stepX) : 0;
    i = Math.max(0, Math.min(n - 1, i));
    setHover(i);
  };

  return (
    <div className="ce-chart">
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {ticks.map((t, k) => (
          <g key={k}>
            <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="#eef0f4" />
            <text x={padL - 6} y={y(t) + 3} textAnchor="end" fontSize="9" fill="#9ca3af">{t}</text>
          </g>
        ))}
        {labelsX.map((i) => (
          <text key={i} x={x(i)} y={H - 12} textAnchor="middle" fontSize="9" fill="#9ca3af">{fmtDataCurta(datas[i])}</text>
        ))}
        {series.map((s, si) => (
          <polyline
            key={s.nome}
            fill="none"
            stroke={s.cor || cores[si % cores.length]}
            strokeWidth="2"
            points={s.pontos.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
          />
        ))}
        {hover != null && (
          <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + innerH} stroke="#cbd5e1" strokeDasharray="3 3" />
        )}
        {hover != null && series.map((s, si) => (
          <circle key={s.nome} cx={x(hover)} cy={y(s.pontos[hover])} r="3" fill={s.cor || cores[si % cores.length]} />
        ))}
      </svg>

      {hover != null && (
        <div className="ce-tip" style={{ left: `${(x(hover) / W) * 100}%` }}>
          <div className="ce-tip-data">{fmtDataCurta(datas[hover])}</div>
          {series
            .map((s, si) => ({ nome: s.label || s.nome, v: s.pontos[hover], cor: s.cor || cores[si % cores.length] }))
            .filter((r) => r.v > 0)
            .sort((a, b) => b.v - a.v)
            .slice(0, 10)
            .map((r) => (
              <div key={r.nome} className="ce-tip-row">
                <span className="ce-dot" style={{ background: r.cor }} />
                <span className="ce-tip-nome">{r.nome}</span>
                <strong>{r.v}</strong>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export default function CaptacaoEvolucao({ nomeEquipe }) {
  const toast = useToast();
  const [dimensao, setDimensao] = useState("equipe");
  const [filtros, setFiltros] = useState({ equipe: "", corretor: "", bairro: "", endereco: "", categoria: "", status: "", data_de: "", data_ate: "" });
  const [data, setData] = useState({ datas: [], series: [] });
  const [loading, setLoading] = useState(false);
  const [ocultas, setOcultas] = useState(() => new Set());
  const [porEstado, setPorEstado] = useState(false);
  const [opcoes, setOpcoes] = useState({ equipes: [], corretores: [], bairros: [] });

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${BASE}/captacoes/evolucao/opcoes`);
        const d = await r.json();
        if (r.ok && d.ok) setOpcoes({ equipes: d.equipes || [], corretores: d.corretores || [], bairros: d.bairros || [] });
      } catch { /* silencioso */ }
    })();
  }, []);

  const buscar = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ dimensao });
      Object.entries(filtros).forEach(([k, v]) => v && qs.append(k, v));
      if (porEstado && dimensao !== "categoria") qs.append("por_estado", "true");
      const r = await fetch(`${BASE}/captacoes/evolucao?${qs.toString()}`);
      const d = await r.json();
      if (r.ok && d.ok) { setData({ datas: d.datas || [], series: d.series || [] }); setOcultas(new Set()); }
      else toast(d.error || "Erro ao carregar evolução", "error");
    } catch { toast("Erro de conexão", "error"); }
    finally { setLoading(false); }
  }, [dimensao, filtros, porEstado, toast]);

  useEffect(() => {
    buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dimensao, porEstado]);

  const label = useCallback(
    (nome) => {
      if (dimensao === "equipe" && nomeEquipe) {
        const i = String(nome).indexOf(" — ");
        return i >= 0 ? `${nomeEquipe(nome.slice(0, i))}${nome.slice(i)}` : nomeEquipe(nome);
      }
      return nome || "—";
    },
    [dimensao, nomeEquipe]
  );

  const corPorNome = useMemo(() => {
    const m = {};
    data.series.forEach((s, i) => { m[s.nome] = CORES[i % CORES.length]; });
    return m;
  }, [data.series]);

  const seriesVisiveis = useMemo(
    () => data.series.filter((s) => !ocultas.has(s.nome)).map((s) => ({ ...s, label: label(s.nome), cor: corPorNome[s.nome] })),
    [data.series, ocultas, label, corPorNome]
  );
  const cores = CORES;

  const setF = (k) => (e) => setFiltros((p) => ({ ...p, [k]: e.target.value }));
  const toggle = (nome) => setOcultas((prev) => { const n = new Set(prev); n.has(nome) ? n.delete(nome) : n.add(nome); return n; });

  return (
    <div className="ce-wrap">
      <div className="ce-controls">
        <div className="ce-dims">
          {DIMENSOES.map(([id, lbl]) => (
            <button key={id} className={`ce-dim ${dimensao === id ? "is-active" : ""}`} onClick={() => setDimensao(id)}>{lbl}</button>
          ))}
          {dimensao !== "categoria" && (
            <label className="ce-check" title="Uma linha por estado (etapa) dentro de cada grupo">
              <input type="checkbox" checked={porEstado} onChange={(e) => setPorEstado(e.target.checked)} />
              Separar por estado
            </label>
          )}
        </div>
        <div className="ce-filtros">
          <select className="ce-input" value={filtros.equipe} onChange={setF("equipe")}>
            <option value="">Equipe (todas)</option>
            {opcoes.equipes.map((o) => <option key={o.value} value={o.value}>{nomeEquipe ? nomeEquipe(o.value) : o.label}</option>)}
          </select>
          <select className="ce-input" value={filtros.corretor} onChange={setF("corretor")}>
            <option value="">Corretor (todos)</option>
            {opcoes.corretores.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="ce-input" value={filtros.bairro} onChange={setF("bairro")}>
            <option value="">Bairro (todos)</option>
            {opcoes.bairros.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <input className="ce-input" placeholder="Endereço" value={filtros.endereco} onChange={setF("endereco")} />
          <select className="ce-input" value={filtros.categoria} onChange={setF("categoria")}>
            <option value="">Categoria (todas)</option>
            {CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select className="ce-input" value={filtros.status} onChange={setF("status")}>
            <option value="">Status (todos)</option>
            <option value="ativo">Ativo</option>
            <option value="fechado">Fechado</option>
          </select>
          <input className="ce-input" type="date" value={filtros.data_de} onChange={setF("data_de")} />
          <input className="ce-input" type="date" value={filtros.data_ate} onChange={setF("data_ate")} />
          <button className="ce-btn" onClick={buscar} disabled={loading}>{loading ? "..." : "Aplicar"}</button>
        </div>
      </div>

      {data.datas.length === 0 ? (
        <div className="ce-empty">{loading ? "Carregando..." : "Sem dados no período. (snapshots acumulam por dia)"}</div>
      ) : (
        <>
          <LineChart datas={data.datas} series={seriesVisiveis} cores={cores} />
          <div className="ce-legend">
            {data.series.map((s) => (
              <button
                key={s.nome}
                className={`ce-leg ${ocultas.has(s.nome) ? "is-off" : ""}`}
                onClick={() => toggle(s.nome)}
                title="Mostrar/ocultar"
              >
                <span className="ce-dot" style={{ background: corPorNome[s.nome] }} />
                {label(s.nome)}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
