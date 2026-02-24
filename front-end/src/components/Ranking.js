import React, { useEffect, useMemo, useState } from 'react';
import '../assets/css/ranking.css';

function Ranking() {
  const API_BASE = useMemo(() => {
    return '/api';
  }, []);

  const DEFAULT_START = '2026-01-01';

  const [formData, setFormData] = useState({
    start: DEFAULT_START,   // <- padrão: início de 2026
    end: '',
    limit: 50,
    include_pending: false
  });

  const [tab, setTab] = useState('vgc'); // vgv | vgc | captacao | visitas
  const [data, setData] = useState({
    vgv: [],
    vgc: [],
    captacao: [],
    visitas: [],
    meta: null
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, type, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const buildUrl = () => {
    const params = new URLSearchParams();

    // fallback: se estiver vazio por algum motivo, usa 2026-01-01
    const startValue = formData.start || DEFAULT_START;

    if (startValue) params.set('start', startValue);
    if (formData.end) params.set('end', formData.end);

    const limitNum = Number(formData.limit);
    if (!Number.isNaN(limitNum) && limitNum > 0) params.set('limit', String(limitNum));

    params.set('include_pending', formData.include_pending ? 'true' : 'false');

    return `${API_BASE}/rankings?${params.toString()}`;
  };

  const fetchRankings = async () => {
    setLoading(true);
    try {
      const response = await fetch(buildUrl(), {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      const json = await response.json();

      if (!response.ok) {
        alert(json?.message || json?.error || 'Erro ao buscar rankings');
        setLoading(false);
        return;
      }

      setData({
        vgv: Array.isArray(json.vgv) ? json.vgv : [],
        vgc: Array.isArray(json.vgc) ? json.vgc : [],
        captacao: Array.isArray(json.captacao) ? json.captacao : [],
        visitas: Array.isArray(json.visitas) ? json.visitas : [],
        meta: json.meta || null
      });
    } catch (err) {
      console.error('Erro na requisição:', err);
      alert('Erro de conexão com o servidor.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRankings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentRows = data[tab] || [];

  const titleByTab = {
    vgv: 'Ranking VGV',
    vgc: 'Ranking VGC',
    captacao: 'Ranking Captação',
    visitas: 'Ranking Visitas'
  };

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

  const renderTotal = (row) => {
    if (tab === 'captacao' || tab === 'visitas') {
      return formatNumber(row.total);
    }
    return formatCurrency(row.total);
  };

  return (
    <div className="ranking" style={{ maxWidth: 980 }}>
      <div className="ranking__header">
        <div>
          <h2 className="ranking__title">Rankings</h2>
          <p className="ranking__subtitle">Acompanhe desempenho por período e categoria.</p>
        </div>
      </div>

      <form
        className="ranking__card"
        onSubmit={(e) => {
          e.preventDefault();
          fetchRankings();
        }}
      >
        <div className="ranking__grid">
          <div className="ranking__field">
            <label className="ranking__label">Data Início</label>
            <input
              className="ranking__input"
              name="start"
              type="date"
              value={formData.start}
              onChange={handleChange}
            />
          </div>

          <div className="ranking__field">
            <label className="ranking__label">Data Fim</label>
            <input
              className="ranking__input"
              name="end"
              type="date"
              value={formData.end}
              onChange={handleChange}
            />
          </div>

          <div className="ranking__field">
            <label className="ranking__label">Limite</label>
            <input
              className="ranking__input"
              name="limit"
              type="number"
              min="1"
              max="500"
              value={formData.limit}
              onChange={handleChange}
            />
          </div>
        </div>

        <div className="ranking__row">
          <label className="ranking__check">
            <input
              id="include_pending"
              name="include_pending"
              type="checkbox"
              checked={formData.include_pending}
              onChange={handleChange}
            />
            <span>Incluir pendentes (quando aplicável)</span>
          </label>

          <button className="ranking__btn ranking__btn--primary" type="submit" disabled={loading}>
            {loading ? 'Carregando...' : 'Aplicar Filtros'}
          </button>
        </div>
      </form>

      <div className="ranking__tabs" role="tablist" aria-label="Abas de ranking">
        <button type="button" className={`ranking__tab ${tab === 'vgc' ? 'is-active' : ''}`} onClick={() => setTab('vgc')}>
          VGC
        </button>
        <button type="button" className={`ranking__tab ${tab === 'vgv' ? 'is-active' : ''}`} onClick={() => setTab('vgv')}>
          VGV
        </button>
        <button type="button" className={`ranking__tab ${tab === 'captacao' ? 'is-active' : ''}`} onClick={() => setTab('captacao')}>
          Captação
        </button>
        <button type="button" className={`ranking__tab ${tab === 'visitas' ? 'is-active' : ''}`} onClick={() => setTab('visitas')}>
          Visitas
        </button>
      </div>

      <div className="ranking__card ranking__card--table">
        <div className="ranking__tableHead">
          <h3 className="ranking__h3">{titleByTab[tab]}</h3>

          {data.meta && (
            <div className="ranking__meta">
              <span><strong>Período:</strong> {data.meta.start || '—'} até {data.meta.end || '—'}</span>
              <span className="ranking__dot">•</span>
              <span>
                <strong>Bases:</strong>{' '}
                Vendas: {data.meta?.base_counts?.vendas ?? 0} |{' '}
                Divisões: {data.meta?.base_counts?.divisoes ?? 0} |{' '}
                Captação: {data.meta?.base_counts?.captacao ?? 0} |{' '}
                Visitas: {data.meta?.base_counts?.visitas ?? 0}
              </span>
            </div>
          )}
        </div>

        <div className="ranking__tableWrap">
          <table className="ranking__table">
            <thead>
              <tr>
                <th>#</th>
                <th>Corretor</th>
                <th>{tab === 'captacao' || tab === 'visitas' ? 'Total' : 'Valor'}</th>
              </tr>
            </thead>
            <tbody>
              {currentRows.length === 0 ? (
                <tr>
                  <td colSpan={3} className="ranking__empty">
                    Nenhum dado encontrado para o período informado.
                  </td>
                </tr>
              ) : (
                currentRows.map((row) => (
                  <tr key={`${row.id_corretor || ''}-${row.corretor}-${row.posicao}`}>
                    <td className="ranking__pos">{row.posicao}</td>
                    <td className="ranking__name">{row.corretor}</td>
                    <td className="ranking__value">{renderTotal(row)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Ranking;