import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BASE as API_BASE } from '../services/api';
import '../assets/css/ranking.css';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';

const LOCAL_KEY = '61e_metas_form';

const MESES = [
  'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
  'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro',
];

function MetaBar({ label, realizado, meta, moeda }) {
  const hasMeta = meta > 0;
  const pct = hasMeta ? (realizado / meta) * 100 : 0;
  // Track representa 0 a 150% da meta; marcador fica em 66.67%
  const SCALE = 1.5;
  const fillPct = hasMeta ? Math.min((realizado / meta) / SCALE * 100, 100) : 0;
  const markPct = hasMeta ? (1 / SCALE) * 100 : 0; // 66.67%

  const cor = !hasMeta
    ? '#94a3b8'
    : realizado >= meta
    ? '#16a34a'
    : pct >= 60
    ? '#2563eb'
    : '#ef4444';

  const fmt = (v) => {
    if (!moeda) return Math.round(v).toLocaleString('pt-BR');
    if (v >= 1e6) return `R$ ${(v / 1e6).toFixed(1)}M`;
    if (v >= 1e3) return `R$ ${(v / 1e3).toFixed(0)}k`;
    return `R$ ${Math.round(v)}`;
  };

  return (
    <div className="mp-bar">
      <div className="mp-bar__head">
        <span className="mp-bar__label">{label}</span>
        <b className="mp-bar__pct" style={{ color: cor }}>
          {hasMeta ? `${pct.toFixed(0)}%` : 'sem meta'}
        </b>
      </div>
      <div className="mp-bar__track">
        <div className="mp-bar__fill" style={{ width: `${fillPct}%`, background: cor }} />
        {hasMeta && (
          <div className="mp-bar__meta-mark" style={{ left: `${markPct}%` }} />
        )}
      </div>
      <div className="mp-bar__vals">
        <span style={{ color: cor, fontWeight: 700 }}>{fmt(realizado)}</span>
        {hasMeta && <span className="mp-bar__sep"> / {fmt(meta)}</span>}
      </div>
    </div>
  );
}

function MetaCard({ row, ano, mes }) {
  const p = String(mes).padStart(2, '0');
  const colVGV = `VGV_Realizado_${ano}_${p}`;
  const colCap = `Cap_Realizada_${ano}_${p}`;
  const colVGC = `VGC_Realizado_${ano}_${p}`;
  const colVis = `Vis_Realizada_${ano}_${p}`;

  const metasKeys = [
    ['VGV', 'Meta_VGV_Mes'],
    ['Cap', 'Meta_Cap_Mes'],
    ['VGC', 'Meta_VGC_Mes'],
    ['Vis', 'Meta_Vis_Mes'],
  ];
  const algumMetaSet = metasKeys.some(([, col]) => (row[col] || 0) > 0);
  const todasBateram = algumMetaSet && metasKeys.every(
    ([status, col]) => !(row[col] > 0) || row[`Status_${status}`] === 'BATEU'
  );

  const nomeTratado = String(row.Gerente || '')
    .split(' ')
    .map((w) => w[0]?.toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');

  return (
    <div className="mp-card">
      <div className="mp-card__header">
        <span>{nomeTratado}</span>
        {todasBateram && <span className="mp-badge mp-badge--ok">✓ TODAS</span>}
      </div>
      <div className="mp-card__body">
        <MetaBar label="VGV"       realizado={row[colVGV] || 0} meta={row.Meta_VGV_Mes || 0} moeda />
        <MetaBar label="Captações" realizado={row[colCap] || 0} meta={row.Meta_Cap_Mes || 0} />
        <MetaBar label="VGC"       realizado={row[colVGC] || 0} meta={row.Meta_VGC_Mes || 0} moeda />
        <MetaBar label="Visitas"   realizado={row[colVis] || 0} meta={row.Meta_Vis_Mes || 0} />
      </div>
    </div>
  );
}

const RANKING_TABS = [
  { id: 'vgc_geral', label: 'VGC', title: 'Ranking VGC', unit: 'currency' },
  { id: 'vgv_geral', label: 'VGV', title: 'Ranking VGV', unit: 'currency' },
  { id: 'captacao', label: 'Captacao', title: 'Ranking Captacao', unit: 'number' },
  { id: 'visitas', label: 'Visitas', title: 'Ranking Visitas', unit: 'number' },
];

function formatDateInput(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getLastWeekRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  return {
    start: formatDateInput(start),
    end: formatDateInput(end),
  };
}

// Gerador do texto de fechamento do mês (por equipe) p/ copiar no grupo.
function FechamentoMes({ apiBase, toast }) {
  const hoje = new Date();
  const mesAtual = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`;
  const [mes, setMes] = useState(mesAtual);
  const [texto, setTexto] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiado, setCopiado] = useState(false);

  const gerar = useCallback(async () => {
    setLoading(true);
    setCopiado(false);
    try {
      const r = await fetch(`${apiBase}/rankings/fechamento?mes=${encodeURIComponent(mes)}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao gerar fechamento.');
      setTexto(d.texto || '');
    } catch (e) {
      toast(e.message || 'Erro ao gerar fechamento.', 'error');
    } finally {
      setLoading(false);
    }
  }, [apiBase, mes, toast]);

  const copiar = () => {
    if (!texto) return;
    navigator.clipboard.writeText(texto)
      .then(() => { setCopiado(true); toast('Texto copiado!', 'success'); })
      .catch(() => toast('Não consegui copiar — selecione e copie manual.', 'error'));
  };

  return (
    <div className="ranking__panel" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13, fontWeight: 600, color: '#475569' }}>
          Mês do fechamento
          <input type="month" value={mes} onChange={(e) => setMes(e.target.value)}
            style={{ height: 40, padding: '0 10px', border: '1.5px solid #e5e7eb', borderRadius: 8 }} />
        </label>
        <button type="button" onClick={gerar} disabled={loading}
          style={{ height: 40, padding: '0 22px', border: 'none', borderRadius: 8, background: '#e1005b', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          {loading ? 'Gerando…' : 'Gerar texto'}
        </button>
        {texto && (
          <button type="button" onClick={copiar}
            style={{ height: 40, padding: '0 22px', border: 'none', borderRadius: 8, background: '#111827', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
            {copiado ? '✓ Copiado' : 'Copiar'}
          </button>
        )}
      </div>
      {texto && (
        <textarea readOnly value={texto} rows={Math.min(30, texto.split('\n').length + 1)}
          style={{ width: '100%', fontFamily: 'ui-monospace, Consolas, monospace', fontSize: 13, lineHeight: 1.55,
            padding: 14, border: '1px dashed #e5e7eb', borderRadius: 12, background: '#f8fafc', color: '#111827', resize: 'vertical' }} />
      )}
      <p className="ranking__hint" style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
        Captações vêm da planilha de estoque (mês selecionado); corretor com 0 aparece como <code>/4</code>. Nome que não bate no cadastro pode não contar.
      </p>
    </div>
  );
}

function Ranking() {
  const toast = useToast();
  const { permissao } = useAuth();
  const podeOcultar = ['administrador', 'diretor'].includes(permissao);

  const GERENTES = useMemo(
    () => [
      'Jose Marques',
      'Marcelo Souza',
      'Luana Salvinski',
      'Thais Tannus',
      'Marcelo Pincinato',
      'Helio Junio',
      'Paolla Gardenia',
    ],
    []
  );

  const initialRange = useMemo(() => getLastWeekRange(), []);

  const [formData, setFormData] = useState({
    start: initialRange.start,
    end: initialRange.end,
    include_pending: false,
    apply_factor: false,
  });

  const [appliedFormData, setAppliedFormData] = useState({
    start: initialRange.start,
    end: initialRange.end,
    include_pending: false,
    apply_factor: false,
  });

  const defaultMetas = useMemo(() => GERENTES.reduce((acc, g) => {
    acc[g] = { Meta_VGV_Mes: '', Meta_Cap_Mes: '', Meta_VGC_Mes: '', Meta_Vis_Mes: '' };
    return acc;
  }, {}), [GERENTES]);

  const [metaForm, setMetaForm] = useState(() => {
    const base = {
      ano_relatorio: new Date().getFullYear(),
      mes_relatorio: new Date().getMonth() + 1,
      metas_mensais: defaultMetas,
    };
    try {
      const saved = localStorage.getItem(LOCAL_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          ...base,
          ...parsed,
          metas_mensais: { ...base.metas_mensais, ...(parsed.metas_mensais || {}) },
        };
      }
    } catch {}
    return base;
  });

  const [previewData, setPreviewData] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const metasSavedRef = useRef(false);

  const [section, setSection] = useState('rankings');
  const [tab, setTab] = useState('vgc_geral');
  const [viewMode, setViewMode] = useState('corretor'); // 'corretor' | 'equipe'
  const [dataByTab, setDataByTab] = useState({});
  const [loadedKeyByTab, setLoadedKeyByTab] = useState({});
  const [dataByTabEquipe, setDataByTabEquipe] = useState({});
  const [loadedKeyByTabEquipe, setLoadedKeyByTabEquipe] = useState({});
  const [hasApplied, setHasApplied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);

  const [ocultos, setOcultos] = useState([]);
  const [showOcultos, setShowOcultos] = useState(false);

  const [detalheCorretor, setDetalheCorretor] = useState(null);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);
  const [loadingPdfCorretor, setLoadingPdfCorretor] = useState(false);
  const [loadingPdfTodos, setLoadingPdfTodos] = useState(false);

  const activeTab = RANKING_TABS.find((item) => item.id === tab) || RANKING_TABS[0];
  const currentRows = viewMode === 'equipe' ? (dataByTabEquipe[tab] || []) : (dataByTab[tab] || []);
  const currentLoadKey = `${appliedFormData.start}|${appliedFormData.end}|${appliedFormData.include_pending}|${appliedFormData.apply_factor}`;

  const handleChange = (e) => {
    const { name, type, value, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const setLastWeek = () => {
    const range = getLastWeekRange();
    setFormData((prev) => ({
      ...prev,
      start: range.start,
      end: range.end,
    }));
  };

  const handleMetaHeaderChange = (e) => {
    const { name, value } = e.target;
    setMetaForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  useEffect(() => {
    if (metasSavedRef.current) {
      localStorage.setItem(LOCAL_KEY, JSON.stringify(metaForm));
    }
    metasSavedRef.current = true;
  }, [metaForm]);

  const buildMetasPayload = useCallback(() => {
    const payload = {
      ano_relatorio: Number(metaForm.ano_relatorio),
      mes_relatorio: Number(metaForm.mes_relatorio),
      metas_mensais: {},
    };
    GERENTES.forEach((gerente) => {
      payload.metas_mensais[gerente.toUpperCase()] = {
        Meta_VGV_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_VGV_Mes || 0),
        Meta_Cap_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_Cap_Mes || 0),
        Meta_VGC_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_VGC_Mes || 0),
        Meta_Vis_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_Vis_Mes || 0),
      };
    });
    return payload;
  }, [metaForm, GERENTES]);

  const visualizarMetas = useCallback(async (e) => {
    e.preventDefault();
    setLoadingPreview(true);
    setPreviewData(null);
    setShowPreview(true);
    try {
      const response = await fetch(`${API_BASE}/relatorio/metas-gerentes/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildMetasPayload()),
      });
      const json = await response.json();
      if (!response.ok) {
        toast(json?.error || json?.message || 'Erro ao carregar preview', 'error');
        setShowPreview(false);
        return;
      }
      setPreviewData(json);
    } catch {
      toast('Erro de conexão ao carregar preview.', 'error');
      setShowPreview(false);
    } finally {
      setLoadingPreview(false);
    }
  }, [buildMetasPayload, toast]);

  const handleMetaGerenteChange = (gerente, campo, valor) => {
    setMetaForm((prev) => ({
      ...prev,
      metas_mensais: {
        ...prev.metas_mensais,
        [gerente]: {
          ...prev.metas_mensais[gerente],
          [campo]: valor,
        },
      },
    }));
  };

  const buildUrl = useCallback(
    (kind) => {
      const params = new URLSearchParams();

      if (appliedFormData.start) params.set('start', appliedFormData.start);
      if (appliedFormData.end) params.set('end', appliedFormData.end);

      params.set('include_pending', appliedFormData.include_pending ? 'true' : 'false');

      if (kind === 'vgc_geral' && appliedFormData.apply_factor) {
        params.set('apply_factor', 'true');
      }

      return `${API_BASE}/rankings/${kind}?${params.toString()}`;
    },
    [appliedFormData]
  );

  const fetchRanking = useCallback(
    async (kind = tab, force = false) => {
      if (!force && loadedKeyByTab[kind] === currentLoadKey) return;

      setLoading(true);
      try {
        const response = await fetch(buildUrl(kind), {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        const json = await response.json();

        if (!response.ok) {
          toast(json?.message || json?.error || 'Erro ao buscar ranking', 'error');
          return;
        }

        setDataByTab((prev) => ({
          ...prev,
          [kind]: Array.isArray(json) ? json : [],
        }));
        setLoadedKeyByTab((prev) => ({
          ...prev,
          [kind]: currentLoadKey,
        }));
      } catch (err) {
        console.error('Erro na requisicao:', err);
        toast('Erro de conexao com o servidor.', 'error');
      } finally {
        setLoading(false);
      }
    },
    [buildUrl, currentLoadKey, loadedKeyByTab, tab, toast]
  );

  const fetchRankingEquipe = useCallback(
    async (kind = tab, force = false) => {
      if (!force && loadedKeyByTabEquipe[kind] === currentLoadKey) return;

      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (appliedFormData.start) params.set('start', appliedFormData.start);
        if (appliedFormData.end) params.set('end', appliedFormData.end);
        params.set('include_pending', appliedFormData.include_pending ? 'true' : 'false');
        if (kind === 'vgc_geral' && appliedFormData.apply_factor) params.set('apply_factor', 'true');

        const response = await fetch(`${API_BASE}/rankings/${kind}/equipe?${params.toString()}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        const json = await response.json();

        if (!response.ok) {
          toast(json?.message || json?.error || 'Erro ao buscar ranking por equipe', 'error');
          return;
        }

        setDataByTabEquipe((prev) => ({ ...prev, [kind]: Array.isArray(json) ? json : [] }));
        setLoadedKeyByTabEquipe((prev) => ({ ...prev, [kind]: currentLoadKey }));
      } catch (err) {
        console.error('Erro na requisicao equipe:', err);
        toast('Erro de conexao com o servidor.', 'error');
      } finally {
        setLoading(false);
      }
    },
    [appliedFormData, currentLoadKey, loadedKeyByTabEquipe, tab, toast]
  );

  const baixarPdfTodos = async () => {
    const kindDetalhe = tab === 'vgv_geral' ? 'vgv_geral' : 'vgc_geral';
    const params = new URLSearchParams({
      kind: kindDetalhe,
      ...(appliedFormData.start && { start: appliedFormData.start }),
      ...(appliedFormData.end && { end: appliedFormData.end }),
      apply_factor: appliedFormData.apply_factor ? 'true' : 'false',
    });

    setLoadingPdfTodos(true);
    try {
      const res = await fetch(`${API_BASE}/rankings/todos/pdf?${params}`);
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        toast(json?.error || 'Erro ao gerar relatório.', 'error');
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `relatorio_${kindDetalhe}_${appliedFormData.start}_${appliedFormData.end}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast('Erro de conexão ao gerar relatório.', 'error');
    } finally {
      setLoadingPdfTodos(false);
    }
  };

  const fetchOcultos = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/rankings/ocultos`);
      const json = await res.json();
      if (res.ok) setOcultos(Array.isArray(json.ocultos) ? json.ocultos : []);
    } catch { /* silencioso */ }
  }, []);

  useEffect(() => { if (podeOcultar) fetchOcultos(); }, [podeOcultar, fetchOcultos]);

  const refetchRankings = () => {
    fetchRanking(tab, true);
    fetchRankingEquipe(tab, true);
  };

  const ocultarCorretor = async (row) => {
    if (!row.id_corretor) { toast('Corretor sem ID; não dá pra ocultar.', 'error'); return; }
    try {
      const res = await fetch(`${API_BASE}/rankings/ocultos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_corretor: row.id_corretor, nome: row.corretor }),
      });
      if (!res.ok) { const j = await res.json().catch(() => ({})); toast(j.error || 'Erro ao ocultar.', 'error'); return; }
      toast(`${row.corretor} ocultado do ranking.`, 'success');
      fetchOcultos();
      refetchRankings();
    } catch { toast('Erro ao ocultar.', 'error'); }
  };

  const mostrarCorretor = async (idCorretor) => {
    try {
      const res = await fetch(`${API_BASE}/rankings/ocultos/${encodeURIComponent(idCorretor)}`, { method: 'DELETE' });
      if (!res.ok) { toast('Erro ao mostrar.', 'error'); return; }
      toast('Corretor de volta ao ranking.', 'success');
      fetchOcultos();
      refetchRankings();
    } catch { toast('Erro ao mostrar.', 'error'); }
  };

  const abrirDetalheCorretor = async (nomeCorretor) => {
    if (!nomeCorretor) return;
    const kindDetalhe = tab === 'vgv_geral' ? 'vgv_geral' : 'vgc_geral';
    const params = new URLSearchParams({
      nome: nomeCorretor,
      kind: kindDetalhe,
      ...(appliedFormData.start && { start: appliedFormData.start }),
      ...(appliedFormData.end && { end: appliedFormData.end }),
      apply_factor: appliedFormData.apply_factor ? 'true' : 'false',
    });

    setLoadingDetalhe(true);
    setDetalheCorretor(null);
    try {
      const res = await fetch(`${API_BASE}/rankings/corretor/detalhe?${params}`);
      const json = await res.json();
      if (!res.ok) {
        toast(json?.error || 'Erro ao buscar detalhe do corretor.', 'error');
        return;
      }
      setDetalheCorretor(json);
    } catch {
      toast('Erro de conexão ao buscar detalhe.', 'error');
    } finally {
      setLoadingDetalhe(false);
    }
  };

  const baixarPdfCorretor = async () => {
    if (!detalheCorretor) return;
    const params = new URLSearchParams({
      nome: detalheCorretor.corretor,
      kind: detalheCorretor.kind,
      ...(detalheCorretor.start && { start: detalheCorretor.start }),
      ...(detalheCorretor.end && { end: detalheCorretor.end }),
      apply_factor: detalheCorretor.apply_factor ? 'true' : 'false',
    });

    setLoadingPdfCorretor(true);
    try {
      const res = await fetch(`${API_BASE}/rankings/corretor/pdf?${params}`);
      if (!res.ok) {
        toast('Erro ao gerar PDF.', 'error');
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comissoes_${detalheCorretor.corretor.replace(/\s+/g, '_').toLowerCase()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast('Erro de conexão ao gerar PDF.', 'error');
    } finally {
      setLoadingPdfCorretor(false);
    }
  };

  const gerarPdfMetas = useCallback(async (e) => {
    if (e) e.preventDefault();
    setLoadingPdf(true);

    try {
      const payload = buildMetasPayload();

      const response = await fetch(`${API_BASE}/relatorio/metas-gerentes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let erroTexto = 'Erro ao gerar PDF';
        try {
          const erroJson = await response.json();
          erroTexto = erroJson?.message || erroJson?.error || erroTexto;
        } catch {
          // Mantem a mensagem padrao quando o erro nao vier em JSON.
        }
        toast(erroTexto, 'error');
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `relatorio_metas_gerentes_${metaForm.ano_relatorio}_${String(
        metaForm.mes_relatorio
      ).padStart(2, '0')}.pdf`;

      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Erro ao gerar PDF:', err);
      toast('Erro de conexao ao gerar o PDF.', 'error');
    } finally {
      setLoadingPdf(false);
    }
  }, [buildMetasPayload, metaForm, toast]);

  useEffect(() => {
    if (!hasApplied) return;
    if (section !== 'rankings') return;
    if (viewMode === 'equipe') {
      fetchRankingEquipe(tab);
    } else {
      fetchRanking(tab);
    }
  }, [fetchRanking, fetchRankingEquipe, hasApplied, section, tab, viewMode]);

  const formatCurrency = (n) => {
    const num = Number(n);
    if (Number.isNaN(num)) return 'R$ 0,00';
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const formatNumber = (n) => {
    const num = Number(n);
    if (Number.isNaN(num)) return '0';
    return num.toLocaleString('pt-BR');
  };

  const renderTotal = (row) =>
    activeTab.unit === 'currency' ? formatCurrency(row.total) : formatNumber(row.total);

  const topRows = currentRows.slice(0, 3);
  const totalGeral = currentRows.reduce((sum, row) => sum + Number(row.total || 0), 0);

  return (
    <div className="ranking">
      <div className="ranking__hero">
        <div>
          <span className="ranking__eyebrow">Painel comercial</span>
          <h2 className="ranking__title">Rankings</h2>
          <p className="ranking__subtitle">
            Consulta por periodo com carregamento separado por categoria.
          </p>
        </div>
        <div className="ranking__period">
          <span>Periodo atual</span>
          <strong>
            {formData.start} ate {formData.end}
          </strong>
        </div>
      </div>

      <div className="ranking__sectionTabs" role="tablist" aria-label="Secoes da pagina">
        <button
          type="button"
          className={`ranking__sectionTab ${section === 'rankings' ? 'is-active' : ''}`}
          onClick={() => setSection('rankings')}
        >
          Rankings
        </button>
        <button
          type="button"
          className={`ranking__sectionTab ${section === 'metas' ? 'is-active' : ''}`}
          onClick={() => setSection('metas')}
        >
          Metas
        </button>
        <button
          type="button"
          className={`ranking__sectionTab ${section === 'fechamento' ? 'is-active' : ''}`}
          onClick={() => setSection('fechamento')}
        >
          Fechamento
        </button>
      </div>

      {section === 'fechamento' && <FechamentoMes apiBase={API_BASE} toast={toast} />}

      {section === 'rankings' ? (
        <>
          <form
            className="ranking__panel"
            onSubmit={(e) => {
              e.preventDefault();
              setAppliedFormData({ ...formData });
              setHasApplied(true);
            }}
          >
            <div className="ranking__filters">
              <div className="ranking__field">
                <label className="ranking__label">Data inicio</label>
                <input
                  className="ranking__input"
                  name="start"
                  type="date"
                  value={formData.start}
                  onChange={handleChange}
                />
              </div>

              <div className="ranking__field">
                <label className="ranking__label">Data fim</label>
                <input
                  className="ranking__input"
                  name="end"
                  type="date"
                  value={formData.end}
                  onChange={handleChange}
                />
              </div>

              <label className="ranking__check">
                <input
                  id="include_pending"
                  name="include_pending"
                  type="checkbox"
                  checked={formData.include_pending}
                  onChange={handleChange}
                />
                <span>Incluir pendentes</span>
              </label>

              {tab === 'vgc_geral' && (
                <label className="ranking__check">
                  <input
                    id="apply_factor"
                    name="apply_factor"
                    type="checkbox"
                    checked={formData.apply_factor}
                    onChange={handleChange}
                  />
                  <span>Dividir por 0,06</span>
                </label>
              )}

              <div className="ranking__filterActions">
                <button className="ranking__btn ranking__btn--secondary" type="button" onClick={setLastWeek}>
                  Ultima semana
                </button>
                <button className="ranking__btn ranking__btn--primary" type="submit" disabled={loading}>
                  {loading ? 'Carregando...' : 'Aplicar'}
                </button>
              </div>
            </div>
          </form>

          <div className="ranking__tabs" role="tablist" aria-label="Categorias de ranking">
            {RANKING_TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`ranking__tab ${tab === item.id ? 'is-active' : ''}`}
                onClick={() => setTab(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="ranking__viewToggle">
            <button
              type="button"
              className={`ranking__viewBtn ${viewMode === 'corretor' ? 'is-active' : ''}`}
              onClick={() => setViewMode('corretor')}
            >
              Corretor
            </button>
            <button
              type="button"
              className={`ranking__viewBtn ${viewMode === 'equipe' ? 'is-active' : ''}`}
              onClick={() => setViewMode('equipe')}
            >
              Equipe
            </button>
          </div>

          <div className="ranking__summary">
            <div className="ranking__summaryCard">
              <span>Categoria</span>
              <strong>{activeTab.label}</strong>
            </div>
            <div className="ranking__summaryCard">
              <span>Registros</span>
              <strong>{formatNumber(currentRows.length)}</strong>
            </div>
            <div className="ranking__summaryCard">
              <span>Total da lista</span>
              <strong>{activeTab.unit === 'currency' ? formatCurrency(totalGeral) : formatNumber(totalGeral)}</strong>
            </div>
          </div>

          <div className="ranking__contentGrid">
            <section className="ranking__panel ranking__panel--table">
              <div className="ranking__tableHead">
                <div>
                  <h3 className="ranking__h3">{activeTab.title}</h3>
                  <p className="ranking__hint">Apenas esta categoria e carregada ao abrir a aba.</p>
                </div>
                <div className="ranking__tableHeadActions">
                  {loading && <span className="ranking__loading">Atualizando</span>}
                  {podeOcultar && ocultos.length > 0 && (
                    <button
                      type="button"
                      className="ranking__btn ranking__btn--outline"
                      onClick={() => setShowOcultos((s) => !s)}
                    >
                      Ocultos ({ocultos.length})
                    </button>
                  )}
                  {viewMode === 'corretor' && (tab === 'vgc_geral' || tab === 'vgv_geral') && currentRows.length > 0 && (
                    <button
                      type="button"
                      className="ranking__btn ranking__btn--outline"
                      onClick={baixarPdfTodos}
                      disabled={loadingPdfTodos}
                    >
                      {loadingPdfTodos ? 'Gerando...' : 'Baixar Relatório'}
                    </button>
                  )}
                </div>
              </div>

              {podeOcultar && showOcultos && (
                <div className="ranking__ocultos">
                  {ocultos.length === 0 ? (
                    <span className="ranking__ocultosEmpty">Nenhum corretor oculto.</span>
                  ) : (
                    ocultos.map((o) => (
                      <span key={o.id_corretor} className="ranking__ocultoChip">
                        {o.nome || o.id_corretor}
                        <button
                          type="button"
                          className="ranking__iconBtn"
                          title="Voltar ao ranking"
                          onClick={() => mostrarCorretor(o.id_corretor)}
                        >
                          👁️
                        </button>
                      </span>
                    ))
                  )}
                </div>
              )}

              <div className="ranking__tableWrap">
                <table className="ranking__table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>{viewMode === 'equipe' ? 'Equipe' : 'Corretor'}</th>
                      <th>{activeTab.unit === 'currency' ? 'Valor' : 'Total'}</th>
                      {viewMode === 'corretor' && (tab === 'vgc_geral' || tab === 'vgv_geral') && <th></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {currentRows.length === 0 ? (
                      <tr>
                        <td colSpan={viewMode === 'corretor' && (tab === 'vgc_geral' || tab === 'vgv_geral') ? 4 : 3} className="ranking__empty">
                          Nenhum dado encontrado para o periodo informado.
                        </td>
                      </tr>
                    ) : (
                      currentRows.map((row) => (
                        <tr key={`${row.id_corretor || ''}-${row.corretor}-${row.posicao}`}>
                          <td className="ranking__pos">{row.posicao}</td>
                          <td className="ranking__name">{row.corretor}</td>
                          <td className="ranking__value">{renderTotal(row)}</td>
                          {viewMode === 'corretor' && (tab === 'vgc_geral' || tab === 'vgv_geral') && (
                            <td className="ranking__detBtn">
                              <div className="ranking__rowActions">
                                <button
                                  type="button"
                                  className="ranking__btn ranking__btn--ghost"
                                  onClick={() => abrirDetalheCorretor(row.corretor)}
                                >
                                  Ver
                                </button>
                                {podeOcultar && (
                                  <button
                                    type="button"
                                    className="ranking__iconBtn"
                                    title="Ocultar do ranking"
                                    onClick={() => ocultarCorretor(row)}
                                  >
                                    🙈
                                  </button>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <aside className="ranking__panel ranking__side">
              <h3 className="ranking__h3">Top 3</h3>
              <div className="ranking__podium">
                {topRows.length === 0 ? (
                  <div className="ranking__empty ranking__empty--compact">Sem dados.</div>
                ) : (
                  topRows.map((row) => (
                    <div className="ranking__podiumItem" key={`top-${row.posicao}-${row.corretor}`}>
                      <span>{row.posicao}</span>
                      <div>
                        <strong>{row.corretor}</strong>
                        <small>{renderTotal(row)}</small>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </aside>
          </div>
        </>
      ) : section === 'metas' ? (
        <form className="ranking__panel ranking__panel--metas" onSubmit={visualizarMetas}>
          <div className="ranking__tableHead">
            <div>
              <h3 className="ranking__h3">Metas dos Gerentes</h3>
              <p className="ranking__hint">Preencha as metas e visualize ou baixe o relatório em PDF.</p>
            </div>
            <span className="ranking__autosave">Salvo automaticamente</span>
          </div>

          <div className="ranking__filters ranking__filters--metas">
            <div className="ranking__field">
              <label className="ranking__label">Mês</label>
              <select
                className="ranking__input"
                name="mes_relatorio"
                value={metaForm.mes_relatorio}
                onChange={handleMetaHeaderChange}
              >
                {MESES.map((nome, i) => (
                  <option key={i + 1} value={i + 1}>{nome}</option>
                ))}
              </select>
            </div>

            <div className="ranking__field">
              <label className="ranking__label">Ano</label>
              <input
                className="ranking__input"
                type="number"
                name="ano_relatorio"
                value={metaForm.ano_relatorio}
                onChange={handleMetaHeaderChange}
              />
            </div>
          </div>

          <div className="ranking__tableWrap">
            <table className="ranking__table ranking__table--metas">
              <thead>
                <tr>
                  <th>Gerente</th>
                  <th>VGV</th>
                  <th>Captações</th>
                  <th>VGC</th>
                  <th>Visitas</th>
                </tr>
              </thead>
              <tbody>
                {GERENTES.map((gerente) => (
                  <tr key={gerente}>
                    <td className="ranking__name">{gerente}</td>
                    <td>
                      <input
                        className="ranking__input ranking__input--meta"
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="Ex: 8.500.000"
                        value={metaForm.metas_mensais[gerente]?.Meta_VGV_Mes ?? ''}
                        onChange={(e) => handleMetaGerenteChange(gerente, 'Meta_VGV_Mes', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="ranking__input ranking__input--meta"
                        type="number"
                        min="0"
                        step="1"
                        placeholder="Ex: 12"
                        value={metaForm.metas_mensais[gerente]?.Meta_Cap_Mes ?? ''}
                        onChange={(e) => handleMetaGerenteChange(gerente, 'Meta_Cap_Mes', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="ranking__input ranking__input--meta"
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="Ex: 50.000"
                        value={metaForm.metas_mensais[gerente]?.Meta_VGC_Mes ?? ''}
                        onChange={(e) => handleMetaGerenteChange(gerente, 'Meta_VGC_Mes', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="ranking__input ranking__input--meta"
                        type="number"
                        min="0"
                        step="1"
                        placeholder="Ex: 30"
                        value={metaForm.metas_mensais[gerente]?.Meta_Vis_Mes ?? ''}
                        onChange={(e) => handleMetaGerenteChange(gerente, 'Meta_Vis_Mes', e.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="ranking__footerActions">
            <button
              type="button"
              className="ranking__btn ranking__btn--secondary"
              disabled={loadingPdf}
              onClick={gerarPdfMetas}
            >
              {loadingPdf ? 'Gerando…' : 'Baixar PDF'}
            </button>
            <button className="ranking__btn ranking__btn--primary" type="submit" disabled={loadingPreview}>
              {loadingPreview ? 'Carregando…' : 'Visualizar Metas'}
            </button>
          </div>
        </form>
      ) : null}

      {showPreview && (
        <div className="ranking__modalOverlay" onClick={() => setShowPreview(false)}>
          <div className="ranking__modal ranking__modal--wide" onClick={(e) => e.stopPropagation()}>
            <div className="ranking__modalHeader">
              <div>
                <h3 className="ranking__h3">
                  Metas · {MESES[metaForm.mes_relatorio - 1]} {metaForm.ano_relatorio}
                </h3>
                {previewData && (
                  <p className="ranking__hint">
                    {previewData.length} gerentes · {previewData.filter(r => r.Status_VGV === 'BATEU').length} bateram VGV
                  </p>
                )}
              </div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <button
                  type="button"
                  className="ranking__btn ranking__btn--outline"
                  onClick={gerarPdfMetas}
                  disabled={loadingPdf}
                >
                  {loadingPdf ? 'Gerando…' : 'Baixar PDF'}
                </button>
                <button type="button" className="ranking__modalClose" onClick={() => setShowPreview(false)}>✕</button>
              </div>
            </div>

            {loadingPreview ? (
              <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>
                Carregando dados das planilhas…
              </div>
            ) : previewData ? (
              <>
                {previewData.every(r =>
                  !r.Meta_VGV_Mes && !r.Meta_Cap_Mes && !r.Meta_VGC_Mes && !r.Meta_Vis_Mes
                ) && (
                  <div style={{
                    margin: '16px 24px 0',
                    padding: '12px 16px',
                    borderRadius: 8,
                    background: '#fef9c3',
                    border: '1px solid #fde047',
                    color: '#854d0e',
                    fontSize: '0.85rem',
                  }}>
                    Nenhuma meta foi configurada ainda. Preencha os valores no formulário e clique em "Visualizar Metas" novamente.
                  </div>
                )}
                <div className="mp-grid">
                  {previewData.map((row) => (
                    <MetaCard
                      key={row.Gerente}
                      row={row}
                      ano={metaForm.ano_relatorio}
                      mes={metaForm.mes_relatorio}
                    />
                  ))}
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {(detalheCorretor || loadingDetalhe) && (
        <div className="ranking__modalOverlay" onClick={() => setDetalheCorretor(null)}>
          <div className="ranking__modal" onClick={(e) => e.stopPropagation()}>
            <div className="ranking__modalHeader">
              <div>
                <h3 className="ranking__h3">
                  {loadingDetalhe ? 'Carregando...' : detalheCorretor?.corretor?.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())}
                </h3>
                {detalheCorretor && (
                  <p className="ranking__hint">
                    {detalheCorretor.kind === 'vgc_geral' ? 'VGC' : 'VGV'}
                    {detalheCorretor.apply_factor ? ' ÷ 0,06' : ''}
                    {' · '}
                    {detalheCorretor.start} até {detalheCorretor.end}
                    {' · '}
                    {detalheCorretor.negociacoes?.length || 0} negociações
                  </p>
                )}
              </div>
              <button type="button" className="ranking__modalClose" onClick={() => setDetalheCorretor(null)}>✕</button>
            </div>

            {!loadingDetalhe && detalheCorretor && (
              <>
                <div className="ranking__tableWrap">
                  <table className="ranking__table">
                    <thead>
                      <tr>
                        <th>Contrato</th>
                        <th>Data</th>
                        <th>Papel</th>
                        <th>V. Negócio</th>
                        <th>V. Total 61</th>
                        <th>Comissão</th>
                        <th>Outros envolvidos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalheCorretor.negociacoes.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="ranking__empty">Nenhuma negociação encontrada.</td>
                        </tr>
                      ) : (
                        detalheCorretor.negociacoes.map((neg, i) => (
                          <tr key={`neg-${i}`}>
                            <td>{neg.id_contrato}</td>
                            <td>{neg.data_contrato}</td>
                            <td>
                              <span className={`ranking__papel ranking__papel--${neg.papel === 'VENDA + CAPTAÇÃO' ? 'duplo' : neg.papel === 'VENDA' ? 'venda' : 'captacao'}`}>
                                {neg.papel}
                              </span>
                            </td>
                            <td className="ranking__value">{formatCurrency(neg.valor_negocio)}</td>
                            <td className="ranking__value">{formatCurrency(neg.valor_total_61)}</td>
                            <td className="ranking__value ranking__value--destaque">{formatCurrency(neg.valor_corretor)}</td>
                            <td className="ranking__hint">{neg.outros_envolvidos.join(', ') || '—'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td colSpan={5} className="ranking__totalLabel">TOTAL</td>
                        <td className="ranking__value ranking__value--destaque">{formatCurrency(detalheCorretor.total)}</td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                <div className="ranking__detalheTotais">
                  <div className="ranking__detalheTotalItem">
                    <span>VGV Total (Valor Negócio)</span>
                    <strong>{formatCurrency(detalheCorretor.total_vgv)}</strong>
                  </div>
                  <div className="ranking__detalheTotalItem">
                    <span>VGC sem ÷0,06</span>
                    <strong>{formatCurrency(detalheCorretor.total_vgc_bruto)}</strong>
                  </div>
                  <div className="ranking__detalheTotalItem ranking__detalheTotalItem--destaque">
                    <span>VGC com ÷0,06</span>
                    <strong>{formatCurrency(detalheCorretor.total_vgc_fator)}</strong>
                  </div>
                </div>

                <div className="ranking__modalFooter">
                  <button
                    type="button"
                    className="ranking__btn ranking__btn--primary"
                    onClick={baixarPdfCorretor}
                    disabled={loadingPdfCorretor}
                  >
                    {loadingPdfCorretor ? 'Gerando PDF...' : 'Baixar PDF'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Ranking;
