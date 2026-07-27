import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { useToast } from "../context/ToastContext";
import "../assets/css/Vendas.css";

function useNotify() {
  const toast = useToast();
  return { success: (m) => toast(m, "success"), error: (m) => toast(m, "error") };
}

const fBRL = (v) =>
  v == null ? "—" : `R$ ${Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fBRLc = (v) => {
  if (v == null) return "—";
  const n = Number(v);
  if (n >= 1e9) return `R$ ${(n / 1e9).toFixed(2)} bi`;
  if (n >= 1e6) return `R$ ${(n / 1e6).toFixed(1)} mi`;
  if (n >= 1e3) return `R$ ${(n / 1e3).toFixed(0)} mil`;
  return fBRL(n);
};
const fData = (iso) => {
  if (!iso) return "—";
  const d = String(iso).slice(0, 10).split("-");
  return d.length === 3 ? `${d[2]}/${d[1]}/${d[0]}` : iso;
};
const fPct = (v) => (v == null ? "—" : `${Number(v).toFixed(2).replace(".", ",")}%`);
const titulo = (campo) =>
  campo.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

function Vendas() {
  const [aba, setAba] = useState("resumo");
  return (
    <div className="ds-page">
      <div className="ds-container-lg vd-wrap">
        <header className="vd-header">
          <h1>Vendas</h1>
          <p>Visão geral dos contratos, percentuais e resumos por mês — e detalhe completo de cada contrato.</p>
        </header>
        <nav className="vd-tabs">
          <button className={`vd-tab ${aba === "resumo" ? "active" : ""}`} onClick={() => setAba("resumo")}>Resumo</button>
          <button className={`vd-tab ${aba === "contratos" ? "active" : ""}`} onClick={() => setAba("contratos")}>Contratos</button>
        </nav>
        {aba === "resumo" ? <AbaResumo /> : <AbaContratos />}
      </div>
    </div>
  );
}

/* ===================== RESUMO ===================== */
function AbaResumo() {
  const toast = useNotify();
  const [filtros, setFiltros] = useState({ ano: "", bairro: "", tipo: "" });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const buscar = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      Object.entries(filtros).forEach(([k, v]) => v && qs.append(k, v));
      setData(await api.get(`/vendas/resumo?${qs.toString()}`));
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }, [filtros, toast]);

  useEffect(() => {
    buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const t = data?.totais;
  const maxMesVgv = useMemo(() => Math.max(1, ...(data?.por_mes || []).map((m) => m.vgv)), [data]);
  const anos = useMemo(() => (data?.por_ano || []).map((a) => a.ano), [data]);

  return (
    <div className="vd-stack">
      <div className="vd-filtros">
        <select className="ds-select" value={filtros.ano} onChange={(e) => setFiltros((p) => ({ ...p, ano: e.target.value }))}>
          <option value="">Todos os anos</option>
          {anos.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <input className="ds-input" placeholder="Bairro" value={filtros.bairro} onChange={(e) => setFiltros((p) => ({ ...p, bairro: e.target.value }))} />
        <input className="ds-input" placeholder="Tipo" value={filtros.tipo} onChange={(e) => setFiltros((p) => ({ ...p, tipo: e.target.value }))} />
        <button className="ds-btn ds-btn-primary ds-btn-sm" onClick={buscar} disabled={loading}>Aplicar</button>
      </div>

      {t && (
        <div className="vd-kpis">
          <Kpi label="Contratos" valor={t.contratos.toLocaleString("pt-BR")} />
          <Kpi label="VGV (valor de negócio)" valor={fBRLc(t.vgv)} dim={fBRL(t.vgv)} />
          <Kpi label="Comissão total" valor={fBRLc(t.comissao)} dim={fBRL(t.comissao)} />
          <Kpi label="Ticket médio" valor={fBRLc(t.ticket_medio)} />
          <Kpi label="Comissão média" valor={fPct(t.comissao_media_pct)} />
        </div>
      )}

      <div className="vd-grid2">
        <div className="ds-card">
          <h3>Por mês — VGV e contratos</h3>
          <div className="vd-bars">
            {(data?.por_mes || []).map((m) => (
              <div className="vd-bar-row" key={m.mes}>
                <span className="vd-bar-lbl">{m.mes}</span>
                <div className="vd-bar-track"><div className="vd-bar-fill" style={{ width: `${(m.vgv / maxMesVgv) * 100}%` }} /></div>
                <span className="vd-bar-val">{fBRLc(m.vgv)}</span>
                <span className="vd-bar-cnt">{m.contratos}</span>
              </div>
            ))}
            {!data?.por_mes?.length && <p className="vd-empty">Sem dados.</p>}
          </div>
        </div>

        <div className="ds-card">
          <h3>Por ano</h3>
          <table className="vd-table">
            <thead><tr><th>Ano</th><th>Contratos</th><th>VGV</th><th>Comissão</th></tr></thead>
            <tbody>
              {(data?.por_ano || []).map((a) => (
                <tr key={a.ano}><td>{a.ano}</td><td>{a.contratos}</td><td>{fBRLc(a.vgv)}</td><td>{fBRLc(a.comissao)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="vd-grid2">
        <TopTabela titulo="Top bairros" linhas={data?.por_bairro} />
        <TopTabela titulo="Por tipo" linhas={data?.por_tipo} />
      </div>
    </div>
  );
}

function Kpi({ label, valor, dim }) {
  return (
    <div className="vd-kpi">
      <span className="vd-kpi-lbl">{label}</span>
      <strong className="vd-kpi-val">{valor}</strong>
      {dim && <span className="vd-kpi-dim">{dim}</span>}
    </div>
  );
}

function TopTabela({ titulo: t, linhas }) {
  return (
    <div className="ds-card">
      <h3>{t}</h3>
      <table className="vd-table">
        <thead><tr><th>Nome</th><th>Contratos</th><th>VGV</th></tr></thead>
        <tbody>
          {(linhas || []).map((l, i) => (
            <tr key={i}><td>{l.nome}</td><td>{l.contratos}</td><td>{fBRLc(l.vgv)}</td></tr>
          ))}
          {!linhas?.length && <tr><td colSpan={3} className="vd-empty">Sem dados.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

/* ===================== CONTRATOS ===================== */
function AbaContratos() {
  const toast = useNotify();
  const [filtros, setFiltros] = useState({ q: "", ano: "", mes: "", bairro: "", tipo: "", fonte: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, per_page: 50 });
  const [loading, setLoading] = useState(false);
  const [selId, setSelId] = useState(null);

  const buscar = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ page: p, per_page: 50 });
      Object.entries(filtros).forEach(([k, v]) => v && qs.append(k, v));
      const res = await api.get(`/vendas?${qs.toString()}`);
      setData(res); setPage(p);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }, [filtros, toast]);

  useEffect(() => {
    buscar(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const totalPages = Math.max(1, Math.ceil((data.total || 0) / (data.per_page || 50)));
  const ANOS = useMemo(() => {
    const y = new Date().getFullYear();
    const a = [];
    for (let i = y; i >= 2015; i--) a.push(i);
    return a;
  }, []);
  const MESES = [
    [1, "Janeiro"], [2, "Fevereiro"], [3, "Março"], [4, "Abril"], [5, "Maio"], [6, "Junho"],
    [7, "Julho"], [8, "Agosto"], [9, "Setembro"], [10, "Outubro"], [11, "Novembro"], [12, "Dezembro"],
  ];

  return (
    <div className="ds-card">
      <div className="vd-filtros">
        <input className="ds-input" placeholder="Buscar (id, código, bairro, corretor)" value={filtros.q} onChange={(e) => setFiltros((p) => ({ ...p, q: e.target.value }))} onKeyDown={(e) => e.key === "Enter" && buscar(1)} />
        <select className="ds-select" value={filtros.ano} onChange={(e) => setFiltros((p) => ({ ...p, ano: e.target.value }))}>
          <option value="">Ano</option>
          {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select className="ds-select" value={filtros.mes} onChange={(e) => setFiltros((p) => ({ ...p, mes: e.target.value }))}>
          <option value="">Mês</option>
          {MESES.map(([n, nome]) => <option key={n} value={n}>{nome}</option>)}
        </select>
        <input className="ds-input" placeholder="Bairro" value={filtros.bairro} onChange={(e) => setFiltros((p) => ({ ...p, bairro: e.target.value }))} />
        <select className="ds-select" value={filtros.fonte} onChange={(e) => setFiltros((p) => ({ ...p, fonte: e.target.value }))}>
          <option value="">Toda fonte</option>
          <option value="planilha">Planilha (2024+)</option>
          <option value="legado_pre2024">Legado (pré-2024)</option>
        </select>
        <button className="ds-btn ds-btn-primary ds-btn-sm" onClick={() => buscar(1)} disabled={loading}>Filtrar</button>
      </div>

      <div className="vd-table-wrap">
        <table className="vd-table vd-clickable">
          <thead><tr>
            <th>Data</th><th>Contrato</th><th>Bairro</th><th>Tipo</th><th>Valor negócio</th>
            <th>Comissão</th><th>% Empresa 61</th>
            <th>% Cor.V1</th><th>% Cor.V2</th><th>% Cap.1</th><th>% Cap.2</th>
            <th>% Ger.V</th><th>% Ger.C</th><th>% Dir.</th>
            <th>Corretor venda</th><th>Gerente</th><th>Fonte</th>
          </tr></thead>
          <tbody>
            {data.items.length === 0 && <tr><td colSpan={17} className="vd-empty">{loading ? "Carregando..." : "Nenhum contrato"}</td></tr>}
            {data.items.map((c) => (
              <tr key={c.id_contrato} onClick={() => setSelId(c.id_contrato)}>
                <td>{fData(c.data_contrato)}</td>
                <td className="vd-contrato-cel">
                  <span className="vd-contrato-nome">{c.contrato || c.id_contrato}</span>
                  {c.contrato && <span className="vd-contrato-id">{c.id_contrato}</span>}
                </td>
                <td>{c.bairro || "—"}</td>
                <td>{c.tipo || "—"}</td>
                <td>{fBRL(c.valor_negocio)}</td>
                <td>{fBRL(c.valor_comissao)}</td>
                <td>{fPct(c.percentual_empresa_61)}</td>
                <td>{fPct(c.percentual_corretor_venda_1)}</td>
                <td>{fPct(c.percentual_corretor_venda_2)}</td>
                <td>{fPct(c.percentual_corretor_captacao_1)}</td>
                <td>{fPct(c.percentual_corretor_captacao_2)}</td>
                <td>{fPct(c.percentual_gerente_venda)}</td>
                <td>{fPct(c.percentual_gerente_captacao)}</td>
                <td>{fPct(c.percentual_diretor)}</td>
                <td>{c.corretor_venda_1_nome || "—"}</td>
                <td>{c.gerente_venda_nome || "—"}</td>
                <td><span className={`vd-chip ${c.fonte === "planilha" ? "ok" : "leg"}`}>{c.fonte === "planilha" ? "planilha" : "legado"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="vd-pag">
        <span>{data.total} contrato(s)</span>
        <div>
          <button className="ds-btn ds-btn-secondary ds-btn-sm" disabled={page <= 1 || loading} onClick={() => buscar(page - 1)}>Anterior</button>
          <span className="vd-pag-num">{page} / {totalPages}</span>
          <button className="ds-btn ds-btn-secondary ds-btn-sm" disabled={page >= totalPages || loading} onClick={() => buscar(page + 1)}>Próxima</button>
        </div>
      </div>

      {selId && <DetalheModal id={selId} onClose={() => setSelId(null)} />}
    </div>
  );
}

/* ===================== DETALHE (modal) ===================== */
const CAMPOS_MOEDA = new Set([
  "valor_negocio", "valor_comissao", "valor_total_61", "nf_61_imoveis", "liquido_61", "valor_empresa_61",
  "valor_corretor_venda_1", "valor_corretor_venda_2", "valor_corretor_captador_1", "valor_corretor_captador_2",
  "valor_gerente_venda", "valor_gerente_captacao", "valor_diretor",
  "valor_parcela_comissao_1", "valor_parcela_comissao_2", "valor_parcela_comissao_3",
]);
const ehData = (k) => k.startsWith("data_");
const ehPct = (k) => k.startsWith("percentual_");

function valorFmt(campo, v) {
  if (v == null || v === "") return "—";
  if (CAMPOS_MOEDA.has(campo)) return fBRL(v);
  if (ehPct(campo)) return fPct(v);
  if (ehData(campo)) return fData(v);
  return String(v);
}

const ehLink = (v) => v != null && /^https?:\/\//i.test(String(v).trim());

function CampoValor({ campo, valor }) {
  if (ehLink(valor)) {
    return (
      <a className="vd-campo-link" href={String(valor).trim()} target="_blank" rel="noopener noreferrer">
        Abrir link ↗
      </a>
    );
  }
  return <span className="vd-campo-val">{valorFmt(campo, valor)}</span>;
}

function DetalheModal({ id, onClose }) {
  const toast = useNotify();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const res = await api.get(`/vendas/${encodeURIComponent(id)}`);
        if (vivo) setData(res);
      } catch (e) { toast.error(e.message); onClose(); }
      finally { if (vivo) setLoading(false); }
    })();
    return () => { vivo = false; };
    // eslint-disable-next-line
  }, [id]);

  return (
    <div className="vd-modal-overlay" onClick={onClose}>
      <div className="vd-modal" onClick={(e) => e.stopPropagation()}>
        <div className="vd-modal-head">
          <div>
            <h2>{data?.full?.contrato || id}</h2>
            {data?.full?.contrato && <span className="vd-modal-sub">Contrato {id}</span>}
          </div>
          <button className="vd-modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="vd-modal-body">
          {loading && <p className="vd-empty">Carregando...</p>}
          {data?.grupos?.map((g) => (
            <div className="vd-grupo" key={g.titulo}>
              <h4>{g.titulo}</h4>
              <div className="vd-campos">
                {g.campos.map((c) => (
                  <div className="vd-campo" key={c.campo}>
                    <span className="vd-campo-lbl">{titulo(c.campo)}</span>
                    <CampoValor campo={c.campo} valor={c.valor} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Vendas;
