import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BASE as API_BASE } from '../services/api';
import '../assets/css/ranking.css';
import { useToast } from '../context/ToastContext';

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

function Ranking() {
  const toast = useToast();

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
    limit: 30,
    include_pending: false,
  });

  const [metaForm, setMetaForm] = useState({
    ano_relatorio: new Date().getFullYear(),
    mes_relatorio: Math.max(1, new Date().getMonth()),
    metas_mensais: GERENTES.reduce((acc, gerente) => {
      acc[gerente] = { Meta_VGV_Mes: '', Meta_Cap_Mes: '' };
      return acc;
    }, {}),
  });

  const [section, setSection] = useState('rankings');
  const [tab, setTab] = useState('vgc_geral');
  const [dataByTab, setDataByTab] = useState({});
  const [loadedKeyByTab, setLoadedKeyByTab] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);

  const activeTab = RANKING_TABS.find((item) => item.id === tab) || RANKING_TABS[0];
  const currentRows = dataByTab[tab] || [];
  const currentLoadKey = `${formData.start}|${formData.end}|${formData.limit}|${formData.include_pending}`;

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

      if (formData.start) params.set('start', formData.start);
      if (formData.end) params.set('end', formData.end);

      const limitNum = Number(formData.limit);
      if (!Number.isNaN(limitNum) && limitNum > 0) {
        params.set('limit', String(limitNum));
      }

      params.set('include_pending', formData.include_pending ? 'true' : 'false');

      return `${API_BASE}/rankings/${kind}?${params.toString()}`;
    },
    [formData]
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

  const gerarPdfMetas = async (e) => {
    e.preventDefault();
    setLoadingPdf(true);

    try {
      const payload = {
        ano_relatorio: Number(metaForm.ano_relatorio),
        mes_relatorio: Number(metaForm.mes_relatorio),
        metas_mensais: {},
      };

      GERENTES.forEach((gerente) => {
        payload.metas_mensais[gerente.toUpperCase()] = {
          Meta_VGV_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_VGV_Mes || 0),
          Meta_Cap_Mes: Number(metaForm.metas_mensais[gerente]?.Meta_Cap_Mes || 0),
        };
      });

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
  };

  useEffect(() => {
    if (section !== 'rankings') return;
    fetchRanking(tab);
  }, [fetchRanking, section, tab]);

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
      </div>

      {section === 'rankings' ? (
        <>
          <form
            className="ranking__panel"
            onSubmit={(e) => {
              e.preventDefault();
              fetchRanking(tab, true);
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

              <div className="ranking__field ranking__field--small">
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
                {loading && <span className="ranking__loading">Atualizando</span>}
              </div>

              <div className="ranking__tableWrap">
                <table className="ranking__table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Corretor</th>
                      <th>{activeTab.unit === 'currency' ? 'Valor' : 'Total'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentRows.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="ranking__empty">
                          Nenhum dado encontrado para o periodo informado.
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
      ) : (
        <form className="ranking__panel ranking__panel--metas" onSubmit={gerarPdfMetas}>
          <div className="ranking__tableHead">
            <div>
              <h3 className="ranking__h3">Relatorio de Metas dos Gerentes</h3>
              <p className="ranking__hint">Preencha as metas mensais e gere o PDF consolidado.</p>
            </div>
          </div>

          <div className="ranking__filters ranking__filters--metas">
            <div className="ranking__field">
              <label className="ranking__label">Ano do relatorio</label>
              <input
                className="ranking__input"
                type="number"
                name="ano_relatorio"
                value={metaForm.ano_relatorio}
                onChange={handleMetaHeaderChange}
              />
            </div>

            <div className="ranking__field">
              <label className="ranking__label">Mes do relatorio</label>
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
                  <th>Meta VGV do mes</th>
                  <th>Meta de captacao do mes</th>
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

          <div className="ranking__footerActions">
            <button className="ranking__btn ranking__btn--primary" type="submit" disabled={loadingPdf}>
              {loadingPdf ? 'Gerando PDF...' : 'Gerar PDF de Metas'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default Ranking;
