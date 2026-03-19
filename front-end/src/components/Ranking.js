import React, { useEffect, useMemo, useState } from 'react';
import '../assets/css/ranking.css';

function Ranking() {
  const API_BASE = useMemo(() => {
    //return '/api';
    return 'http://localhost:5000';
  }, []);

  const GERENTES = useMemo(
    () => [
      'José Marques',
      'Marcelo Souza',
      'Luana Salvinski',
      'Thais Tannús',
      'Marcelo Pincinato',
      'Helio Junio',
      'Paolla Gardenia'
    ],
    []
  );

  const [formData, setFormData] = useState({
    start: '2026-01-01',
    end: '2026-12-31',
    limit: 50,
    include_pending: false
  });

  const [metaForm, setMetaForm] = useState({
    ano_relatorio: 2026,
    mes_relatorio: 2,
    metas_mensais: {
      'José Marques': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' },
      'Marcelo Souza': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' },
      'Luana Salvinski': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' },
      'Thais Tannús': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' },
      'Marcelo Pincinato': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' },
      'Helio Junio': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' },
      'Paolla Gardenia': { Meta_VGV_Mes: '', Meta_Cap_Mes: '' }
    }
  });

  const [tab, setTab] = useState('vgc_geral');
  const [data, setData] = useState({
    vgv_geral: [],
    vgc_geral: [],
    captacao: [],
    visitas: [],
    meta: null
  });

  const [loading, setLoading] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);

  const handleChange = (e) => {
    const { name, type, value, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleMetaHeaderChange = (e) => {
    const { name, value } = e.target;
    setMetaForm((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleMetaGerenteChange = (gerente, campo, valor) => {
    setMetaForm((prev) => ({
      ...prev,
      metas_mensais: {
        ...prev.metas_mensais,
        [gerente]: {
          ...prev.metas_mensais[gerente],
          [campo]: valor
        }
      }
    }));
  };

  const buildUrl = () => {
    const params = new URLSearchParams();

    if (formData.start) params.set('start', formData.start);
    if (formData.end) params.set('end', formData.end);

    const limitNum = Number(formData.limit);
    if (!Number.isNaN(limitNum) && limitNum > 0) {
      params.set('limit', String(limitNum));
    }

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
        vgv_geral: Array.isArray(json.vgv) ? json.vgv : [],
        vgc_geral: Array.isArray(json.vgc) ? json.vgc : [],
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

  const gerarPdfMetas = async (e) => {
    e.preventDefault();
    setLoadingPdf(true);

    try {
      const payload = {
        ano_relatorio: Number(metaForm.ano_relatorio),
        mes_relatorio: Number(metaForm.mes_relatorio),
        metas_mensais: {}
      };

      GERENTES.forEach((gerente) => {
        payload.metas_mensais[gerente.toUpperCase()] = {
          Meta_VGV_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_VGV_Mes || 0),
          Meta_Cap_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_Cap_Mes || 0)
        };
      });

      const response = await fetch(`${API_BASE}/relatorio/metas-gerentes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        let erroTexto = 'Erro ao gerar PDF';
        try {
          const erroJson = await response.json();
          erroTexto = erroJson?.message || erroJson?.error || erroTexto;
        } catch {
          // ignora parse se não vier json
        }
        alert(erroTexto);
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
      alert('Erro de conexão ao gerar o PDF.');
    } finally {
      setLoadingPdf(false);
    }
  };

  useEffect(() => {
    fetchRankings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentRows = data[tab] || [];

  const titleByTab = {
    vgv_geral: 'Ranking VGV',
    vgc_geral: 'Ranking VGC',
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
    <div className="ranking" style={{ maxWidth: 1100 }}>
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
        <button
          type="button"
          className={`ranking__tab ${tab === 'vgc_geral' ? 'is-active' : ''}`}
          onClick={() => setTab('vgc_geral')}
        >
          VGC
        </button>
        <button
          type="button"
          className={`ranking__tab ${tab === 'vgv_geral' ? 'is-active' : ''}`}
          onClick={() => setTab('vgv_geral')}
        >
          VGV
        </button>
        <button
          type="button"
          className={`ranking__tab ${tab === 'captacao' ? 'is-active' : ''}`}
          onClick={() => setTab('captacao')}
        >
          Captação
        </button>
        <button
          type="button"
          className={`ranking__tab ${tab === 'visitas' ? 'is-active' : ''}`}
          onClick={() => setTab('visitas')}
        >
          Visitas
        </button>
      </div>

      <div className="ranking__card ranking__card--table">
        <div className="ranking__tableHead">
          <h3 className="ranking__h3">{titleByTab[tab]}</h3>

          {data.meta && (
            <div className="ranking__meta">
              <span>
                <strong>Período:</strong> {data.meta.start || '—'} até {data.meta.end || '—'}
              </span>
              <span className="ranking__dot">•</span>
              <span>
                <strong>Bases:</strong>{' '}
                Vendas: {data.meta?.base_counts?.vendas ?? 0} | Divisões:{' '}
                {data.meta?.base_counts?.divisoes ?? 0} | Captação:{' '}
                {data.meta?.base_counts?.captacao ?? 0} | Visitas:{' '}
                {data.meta?.base_counts?.visitas ?? 0}
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

      <form className="ranking__card" onSubmit={gerarPdfMetas} style={{ marginTop: 24 }}>
        <div className="ranking__header" style={{ marginBottom: 16 }}>
          <div>
            <h3 className="ranking__h3">Relatório de Metas dos Gerentes</h3>
            <p className="ranking__subtitle">
              Preencha as metas mensais e gere o PDF consolidado.
            </p>
          </div>
        </div>

        <div className="ranking__grid" style={{ marginBottom: 20 }}>
          <div className="ranking__field">
            <label className="ranking__label">Ano do Relatório</label>
            <input
              className="ranking__input"
              type="number"
              name="ano_relatorio"
              value={metaForm.ano_relatorio}
              onChange={handleMetaHeaderChange}
            />
          </div>

          <div className="ranking__field">
            <label className="ranking__label">Mês do Relatório</label>
            <input
              className="ranking__input"
              type="number"
              min="1"
              max="12"
              name="mes_relatorio"
              value={metaForm.mes_relatorio}
              onChange={handleMetaHeaderChange}
            />
          </div>
        </div>

        <div className="ranking__tableWrap">
          <table className="ranking__table">
            <thead>
              <tr>
                <th>Gerente</th>
                <th>Meta VGV do Mês</th>
                <th>Meta de Captação do Mês</th>
              </tr>
            </thead>
            <tbody>
              {GERENTES.map((gerente) => (
                <tr key={gerente}>
                  <td className="ranking__name">{gerente}</td>
                  <td>
                    <input
                      className="ranking__input"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="Ex: 8500000"
                      value={metaForm.metas_mensais[gerente]?.Meta_VGV_Mes ?? ''}
                      onChange={(e) =>
                        handleMetaGerenteChange(gerente, 'Meta_VGV_Mes', e.target.value)
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="ranking__input"
                      type="number"
                      min="0"
                      step="1"
                      placeholder="Ex: 12"
                      value={metaForm.metas_mensais[gerente]?.Meta_Cap_Mes ?? ''}
                      onChange={(e) =>
                        handleMetaGerenteChange(gerente, 'Meta_Cap_Mes', e.target.value)
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="ranking__row" style={{ marginTop: 20 }}>
          <button
            className="ranking__btn ranking__btn--primary"
            type="submit"
            disabled={loadingPdf}
          >
            {loadingPdf ? 'Gerando PDF...' : 'Gerar PDF de Metas'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Ranking;