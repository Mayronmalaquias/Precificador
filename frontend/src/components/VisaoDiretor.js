import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import '../assets/css/VisaoDiretor.css';
import '../assets/css/VisaoDiretorPolish.css';

const currency = (value) => value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
const number = (value) => value.toLocaleString('pt-BR');
const iso = (date) => date.toISOString().slice(0, 10);
const dateLabel = (value) => value ? new Date(`${value}T12:00:00`).toLocaleDateString('pt-BR') : '—';

// Métricas do card de execução comercial, na ordem do funil.
const METRICAS = [['leads', 'Leads'], ['clientes', 'Clientes'], ['visitas', 'Visitas']];

// Imóveis parados por página no bloco de governança.
const PARADOS_POR_PAGINA = 8;

// Dimensões do card de performance de mídia.
const DIMENSOES_MIDIA = [['bairro', 'Bairro'], ['quartos', 'Quartos'], ['metragem', 'Metragem'], ['valor', 'Valor']];

function rangeFor(period) {
  const end = new Date();
  const start = new Date(end);
  if (period === 'semana') start.setDate(end.getDate() - 6);
  else if (period === 'trimestre') start.setMonth(end.getMonth() - 2, 1);
  else start.setDate(1);
  return { start: iso(start), end: iso(end) };
}

function Icon({ name, size = 18 }) {
  const paths = {
    revenue: <><path d="M4 19V5M4 19h16"/><path d="m7 15 4-4 3 2 5-7"/></>,
    proposal: <><path d="M6 2h9l4 4v16H6z"/><path d="M14 2v5h5M9 12h7M9 16h7"/></>,
    visit: <><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V21h13V10.5M9 21v-6h6v6"/></>,
    lead: <><circle cx="12" cy="8" r="4"/><path d="M4.5 21c.7-4.1 3.2-6 7.5-6s6.8 1.9 7.5 6"/></>,
    arrow: <path d="m9 18 6-6-6-6"/>,
    alert: <><path d="M12 3 2.8 20h18.4z"/><path d="M12 9v5M12 17.5v.1"/></>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></>,
    filter: <path d="M4 6h16M7 12h10M10 18h4"/>,
  };
  return <svg className="ev-icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function CardTitle({ eyebrow, title, description, action }) {
  return <div className="ev-card-title"><div><span>{eyebrow}</span><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>;
}

function Modal({ item, onClose }) {
  if (!item) return null;
  return <div className="ev-modal-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="ev-modal" role="dialog" aria-modal="true" aria-labelledby="ev-modal-title" onMouseDown={(e) => e.stopPropagation()}>
      <div className="ev-modal-head"><div><span>Detalhamento operacional</span><h2 id="ev-modal-title">{item.tipo || item.imovel || item.perfil}</h2></div><button onClick={onClose} aria-label="Fechar"><Icon name="close" /></button></div>
      <div className="ev-modal-body">
        {Object.entries(item).filter(([key]) => !['id', 'tone', 'nivel'].includes(key)).map(([key, value]) => <div key={key}><span>{key.replace(/_/g, ' ')}</span><strong>{typeof value === 'number' ? number(value) : value}</strong></div>)}
      </div>
      <div className="ev-modal-note"><Icon name="alert" /><p>Este modal está pronto para receber histórico, responsável, comentários e ações do endpoint de detalhe.</p></div>
    </section>
  </div>;
}

function VisaoDiretor() {
  const navigate = useNavigate();
  const { idCorretor } = useAuth();
  const [periodo, setPeriodo] = useState('mes');
  const [equipe, setEquipe] = useState('todas');
  const [corretor, setCorretor] = useState('todos');
  const [customOpen, setCustomOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [dimMidia, setDimMidia] = useState('bairro');
  const [faixaParados, setFaixaParados] = useState('');
  const [etapaParados, setEtapaParados] = useState('');
  const [buscaParados, setBuscaParados] = useState('');
  const [paginaParados, setPaginaParados] = useState(1);
  const initialRange = useMemo(() => rangeFor('mes'), []);
  const [dates, setDates] = useState(initialRange);
  const [draftDates, setDraftDates] = useState(initialRange);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const load = async () => {
      const cacheKey = `visao-diretor:${idCorretor}:${dates.start}:${dates.end}:${equipe}:${corretor}`;
      let cached = null;
      try { cached = JSON.parse(sessionStorage.getItem(cacheKey) || 'null'); } catch { cached = null; }
      if (cached && active) setData(cached);
      setLoading(!cached);
      setError('');
      try {
        const params = new URLSearchParams({ solicitante_id: idCorretor, start: dates.start, end: dates.end });
        if (equipe !== 'todas') params.set('team', equipe);
        // Gerente não escolhe equipe (o back trava), então o corretor vai sozinho.
        if (corretor !== 'todos') params.set('corretor', corretor);
        const response = await api.get(`/diretor-dashboard/executivo?${params.toString()}`);
        if (active) {
          setData(response);
          try { sessionStorage.setItem(cacheKey, JSON.stringify(response)); } catch { /* armazenamento indisponível */ }
        }
      } catch (err) {
        if (active) setError(err.message || 'Não foi possível carregar a visão executiva.');
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => { active = false; };
  }, [dates, equipe, corretor, idCorretor]);

  const equipes = data?.equipes_opcoes || [];
  // Gerente: o back tranca o escopo na equipe dele e devolve escopo='equipe'.
  const escopoEquipe = data?.escopo === 'equipe';
  const equipeFixa = escopoEquipe ? (equipes[0]?.nome || data?.filtros?.equipe || '—') : '';
  // Com uma equipe escolhida o back devolve uma linha por corretor no lugar das equipes.
  const porCorretor = data?.dimensao === 'corretor';
  const corretores = data?.corretores_opcoes || [];
  const unidade = porCorretor ? 'corretor' : 'equipe';
  const equipesVisiveis = data?.equipes || [];
  const vendas = data?.vendas_recentes || [];
  const perfisMidia = data?.midia?.perfis_por_dimensao?.[dimMidia] || data?.midia?.perfis || [];
  const parados = data?.imoveis_parados || {};
  const paradosVisiveis = useMemo(() => {
    const alvo = buscaParados.trim().toLowerCase();
    return (parados.itens || []).filter((i) => (
      (!faixaParados || i.faixa === faixaParados)
      && (!etapaParados || i.etapa_label === etapaParados)
      && (!alvo || `${i.endereco} ${i.bairro || ''} ${i.responsavel}`.toLowerCase().includes(alvo))
    ));
  }, [parados.itens, faixaParados, etapaParados, buscaParados]);
  const totalPaginas = Math.max(Math.ceil(paradosVisiveis.length / PARADOS_POR_PAGINA), 1);
  // Trocar de filtro tem que voltar pra página 1, senão o usuário cai numa página vazia.
  useEffect(() => { setPaginaParados(1); }, [faixaParados, etapaParados, buscaParados]);
  const paradosPagina = paradosVisiveis.slice((paginaParados - 1) * PARADOS_POR_PAGINA, paginaParados * PARADOS_POR_PAGINA);
  // Período que alcança hoje (este mês / esta semana / trimestre): a última foto é o
  // estado atual, não um fechamento passado — o rótulo muda junto.
  const periodoAtual = dates.end >= iso(new Date());
  const rotuloFim = periodoAtual ? 'Atual' : 'No fim';
  const estoque = data?.estoque_semanal || {};
  const kpiData = data?.kpis || {};
  const delta = (value) => value == null ? 'Sem comparativo' : `${value > 0 ? '+' : ''}${String(value).replace('.', ',')}%`;
  // Funil (leads → clientes → visitas → propostas → vendas) + os números de valor.
  const kpi = (chave) => kpiData[chave] || {};
  // Sempre 2 casas: 3,3% e 3,25% são coisas diferentes quando o VGV é milionário.
  const pct = (v) => (v == null ? '—' : `${Number(v).toFixed(2).replace('.', ',')}%`);
  const kpis = [
    { label: 'Leads C2S', value: number(kpi('leads').valor || 0), delta: delta(kpi('leads').variacao_pct), positive: (kpi('leads').variacao_pct || 0) >= 0, icon: 'lead', caption: 'Leads do Contact2Sale no período' },
    { label: 'Clientes', value: number(kpi('clientes').valor || 0), delta: delta(kpi('clientes').variacao_pct), positive: (kpi('clientes').variacao_pct || 0) >= 0, icon: 'lead', caption: 'Clientes distintos atendidos em visitas' },
    { label: 'Visitas', value: number(kpi('visitas').valor || 0), delta: delta(kpi('visitas').variacao_pct), positive: (kpi('visitas').variacao_pct || 0) >= 0, icon: 'visit', caption: `${dateLabel(dates.start)} a ${dateLabel(dates.end)}` },
    { label: 'Propostas', value: number(kpi('propostas').valor || 0), delta: delta(kpi('propostas').variacao_pct), positive: (kpi('propostas').variacao_pct || 0) >= 0, icon: 'proposal', caption: 'Propostas efetivas lançadas no período' },
    { label: 'Vendas (quantidade)', value: number(kpi('vendas_quantidade').valor || 0), delta: delta(kpi('vendas_quantidade').variacao_pct), positive: (kpi('vendas_quantidade').variacao_pct || 0) >= 0, icon: 'proposal', caption: 'Contratos fechados no período' },
    { label: 'VGV', value: currency(kpi('vgv').valor || 0), delta: delta(kpi('vgv').variacao_pct), positive: (kpi('vgv').variacao_pct || 0) >= 0, icon: 'revenue', caption: 'Valor geral de vendas' },
    { label: 'VGC', value: currency(kpi('vgc').valor || 0), delta: delta(kpi('vgc').variacao_pct), positive: (kpi('vgc').variacao_pct || 0) >= 0, icon: 'revenue', caption: 'Comissão que fica com a 61' },
    { label: '% VGC / VGV', value: pct(kpi('vgc_sobre_vgv').valor), delta: delta(kpi('vgc_sobre_vgv').variacao_pct), positive: (kpi('vgc_sobre_vgv').variacao_pct || 0) >= 0, icon: 'revenue', caption: 'Quanto da venda virou comissão' },
  ];
  const totalPropostas = equipesVisiveis.reduce((acc, item) => acc + item.sim + item.nao + item.talvez, 0);
  const maxClassificadas = Math.max(...equipesVisiveis.map((i) => i.sim + i.nao + i.talvez), 1);
  const proposalDenominator = Math.max(totalPropostas, 1);
  // Cada métrica tem escala própria: a barra cheia é sempre o líder daquela métrica.
  const maxPorMetrica = useMemo(() => ({
    visitas: Math.max(...equipesVisiveis.map((i) => i.visitas || 0), 1),
    clientes: Math.max(...equipesVisiveis.map((i) => i.clientes || 0), 1),
    leads: Math.max(...equipesVisiveis.map((i) => i.leads || 0), 1),
  }), [equipesVisiveis]);
  const totalClientes = equipesVisiveis.reduce((acc, i) => acc + (i.clientes || 0), 0);
  const totalLeads = equipesVisiveis.reduce((acc, i) => acc + (i.leads || 0), 0);

  return <div className="ev-page">
    <div className="ev-shell">
      <section className="ev-executive-header">
        <div><div className="ev-eyebrow"><span /> Painel executivo</div><h1>{escopoEquipe ? 'Visão da Equipe' : 'Visão do Diretor'}</h1><p>{escopoEquipe ? `Performance comercial, mídia e governança da equipe ${equipeFixa}.` : 'Decisões mais rápidas com a performance comercial, mídia e governança de todas as equipes.'}</p></div>
        <div className="ev-updated"><span className="ev-live" /> {loading ? 'Atualizando dados…' : `Dados consultados em ${new Date(data?.atualizado_em || Date.now()).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`}</div>
      </section>

      {error && <div className="ev-data-state ev-data-state--error">{error}</div>}
      {!error && loading && !data && <div className="ev-data-state">Carregando dados reais do sistema…</div>}

      <section className="ev-filterbar" aria-label="Filtros globais">
        <div className="ev-periods">
          {[['semana', 'Esta semana'], ['mes', 'Este mês'], ['trimestre', 'Trimestre']].map(([value, label]) => <button key={value} className={periodo === value ? 'active' : ''} onClick={() => { setPeriodo(value); setDates(rangeFor(value)); setCustomOpen(false); }}>{label}</button>)}
          <button className={periodo === 'custom' ? 'active' : ''} onClick={() => { setPeriodo('custom'); setCustomOpen(!customOpen); }}><Icon name="calendar" size={15} /> Personalizado</button>
        </div>
        <div className="ev-filter-divider" />
        {escopoEquipe
          ? <label className="ev-select-wrap"><span>Equipe</span><strong className="ev-fixed-filter">{equipeFixa}</strong></label>
          : <label className="ev-select-wrap"><span>Equipe</span><select value={equipe} onChange={(e) => { setEquipe(e.target.value); setCorretor('todos'); }}><option value="todas">Todas as equipes</option>{equipes.map((item) => <option value={item.id} key={item.id}>{item.nome} · {item.gerente}</option>)}</select></label>}
        <label className="ev-select-wrap"><span>Corretor</span><select value={corretor} onChange={(e) => setCorretor(e.target.value)} disabled={!escopoEquipe && equipe === 'todas'} title={!escopoEquipe && equipe === 'todas' ? 'Escolha uma equipe para filtrar por corretor' : undefined}><option value="todos">{!escopoEquipe && equipe === 'todas' ? 'Escolha uma equipe' : 'Todos os corretores'}</option>{corretores.map((item) => <option value={item.id} key={item.id}>{item.nome}</option>)}</select></label>
        {customOpen && <div className="ev-date-popover"><label>De<input type="date" value={draftDates.start} onChange={(event) => setDraftDates((current) => ({ ...current, start: event.target.value }))} /></label><label>Até<input type="date" value={draftDates.end} onChange={(event) => setDraftDates((current) => ({ ...current, end: event.target.value }))} /></label><button onClick={() => { setDates(draftDates); setCustomOpen(false); }}>Aplicar período</button></div>}
      </section>

      <section className="ev-kpis" aria-label="Resumo executivo">
        {kpis.map((item) => <article className="ev-kpi" key={item.label}><div className={`ev-kpi-icon ${item.icon}`}><Icon name={item.icon} /></div><div className="ev-kpi-top"><span>{item.label}</span><em className={item.positive ? 'up' : 'down'}>{item.delta}</em></div><strong>{item.value}</strong><small>{item.caption}<b> vs. período anterior</b></small></article>)}
      </section>

      <div className="ev-section-heading"><div><span>01 · PERFORMANCE</span><h2>{porCorretor ? 'Controle de corretores da equipe' : 'Controle de equipes e gerentes'}</h2></div><p>Leitura comparativa do ritmo comercial e da prospecção ativa.</p></div>

      <section className="ev-grid ev-grid-performance">
        <article className="ev-card ev-visits">
          <CardTitle
            eyebrow="Execução comercial"
            title={`Visitas, clientes e leads por ${unidade}`}
            description={`Cada barra cheia é ${porCorretor ? 'o corretor' : 'a equipe'} com o maior número da métrica`}
            action={<span className="ev-legend ev-legend-metricas">{METRICAS.map(([chave, rotulo]) => <em key={chave}><i className={`m-${chave}`} /> {rotulo}</em>)}</span>}
          />
          <div className="ev-bar-chart">
            {equipesVisiveis.map((item) => (
              <div className="ev-bar-group" key={item.id}>
                <div className="ev-bar-ident"><strong>{item.nome}</strong><span>{item.gerente}</span></div>
                <div className="ev-bar-metricas">
                  {METRICAS.map(([chave, rotulo]) => (
                    <div className="ev-bar-linha" key={chave}>
                      <span>{rotulo}</span>
                      <div className="ev-bar-track"><b className={`m-${chave}`} style={{ width: `${((item[chave] || 0) / maxPorMetrica[chave]) * 100}%` }} /></div>
                      <strong>{number(item[chave] || 0)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {!equipesVisiveis.length && <p className="ev-empty">{porCorretor ? 'Nenhum corretor com visita no período.' : 'Nenhuma equipe ou visita encontrada.'}</p>}
          </div>
          <div className="ev-card-footer"><span><b>{kpiData.visitas?.valor || 0}</b> visitas · <b>{number(totalClientes)}</b> clientes · <b>{number(totalLeads)}</b> leads</span><span>Leads sem equipe (recepção) não entram nas barras.</span></div>
        </article>

        <article className="ev-card ev-funnel">
          <CardTitle eyebrow="Qualidade das visitas" title="Visitas" description="Visitas classificadas pela proposta registrada: SIM, NÃO ou TALVEZ" />
          <div className="ev-donut-wrap"><div className="ev-donut" style={{ '--sim': `${(equipesVisiveis.reduce((a, i) => a + i.sim, 0) / proposalDenominator) * 360}deg`, '--talvez': `${((equipesVisiveis.reduce((a, i) => a + i.sim + i.talvez, 0)) / proposalDenominator) * 360}deg` }}><div><strong>{totalPropostas}</strong><span>visitas</span></div></div>
            <div className="ev-funnel-legend">{[['sim', 'Proposta SIM', equipesVisiveis.reduce((a, i) => a + i.sim, 0)], ['talvez', 'Proposta TALVEZ', equipesVisiveis.reduce((a, i) => a + i.talvez, 0)], ['nao', 'Proposta NÃO', equipesVisiveis.reduce((a, i) => a + i.nao, 0)]].map(([tone, label, value]) => <div key={tone}><i className={tone} /><span>{label}</span><strong>{value}</strong></div>)}</div>
          </div>
          {/* Quantitativa: a largura é o volume de visitas, não a proporção interna —
              a barra cheia é quem tem mais visitas classificadas no período. */}
          <div className="ev-stacked ev-stacked-qtd">{equipesVisiveis.filter((item) => item.sim + item.nao + item.talvez > 0).map((item) => { const total = item.sim + item.nao + item.talvez; return <div key={item.id}><span>{item.nome}</span><div style={{ width: `${(total / maxClassificadas) * 100}%` }}><i className="sim" style={{ width: `${item.sim / total * 100}%` }} /><i className="talvez" style={{ width: `${item.talvez / total * 100}%` }} /><i className="nao" style={{ width: `${item.nao / total * 100}%` }} /></div><b>{number(total)}</b></div>})}</div>
        </article>

        <article className="ev-card ev-prospect">
          <CardTitle eyebrow="Estoque" title="Captações, saídas e estoque" description="Movimento de imóveis, direto da situação no Imoview" />
          <div className="ev-prospect-total">
            <div><span>Captações</span><strong>{number(estoque.entradas || 0)}</strong><small>Registradas no período</small></div>
            <div><span>Saídas</span><strong>{number(estoque.saidas || 0)}</strong><small>Deixaram de estar disponíveis</small></div>
            <div className={`ev-saldo ${(estoque.saldo || 0) >= 0 ? 'positivo' : 'negativo'}`}>
              <span>Saldo</span><strong>{(estoque.saldo || 0) > 0 ? '+' : ''}{number(estoque.saldo || 0)}</strong><small>Captações − saídas</small>
            </div>
            {/* Estoque é saldo, não acumulado: mostra o agora, independente do período. */}
            <div><span>Total de estoque</span><strong>{number(estoque.estoque || 0)}</strong><small>Disponíveis hoje</small></div>
          </div>
          <p className="ev-data-note">
            Estoque = imóveis <b>vago/disponível</b> no catálogo (varredura de {dateLabel(estoque.data_estoque)}).
            Saída = mudou de disponível para vendido, desativado ou em reforma — <b>em moderação não conta</b>, o imóvel continua sendo nosso.
            {String(estoque.saidas_fonte || '').includes('planilha') && ' Parte das saídas deste período ainda vem da planilha semanal: o log de situação começou depois.'}
            {(equipe !== 'todas' || corretor !== 'todos') && ' Com filtro, entra só imóvel com captação registrada — é a única ligação entre imóvel e equipe.'}
          </p>
        </article>

        <article className="ev-card ev-journey">
          <CardTitle
            eyebrow="Jornada de captação"
            title="Etapas no período"
            description={`Entraram no período · estiveram na etapa em algum dia · ${periodoAtual ? `como está atualmente (${dateLabel(data?.captacao?.data_fim)})` : `como fechou em ${dateLabel(data?.captacao?.data_fim)}`}`}
            action={<span className="ev-legend ev-legend-metricas"><em><i className="m-entraram" /> Entraram</em><em><i className="m-periodo" /> No período</em><em><i className="m-fim" /> {rotuloFim}</em></span>}
          />
          <div className="ev-journey-list">{(data?.captacao?.etapas || []).map((item, index) => (
            <div key={item.etapa}>
              <span className="ev-step">0{index + 1}</span>
              <div>
                <strong>{item.label}</strong>
                <span>{number(item.ja_estavam ?? 0)} já estavam + {number(item.entraram ?? 0)} que entraram · {periodoAtual ? 'está com' : 'fechou com'} {number(item.no_fim ?? 0)}</span>
              </div>
              <div className="ev-journey-nums">
                <em className="entraram" title="Entraram na etapa no período">{number(item.entraram ?? item.total ?? 0)}</em>
                <em className="periodo" title="Estiveram na etapa em algum dia do período">{number(item.no_periodo ?? item.total ?? 0)}</em>
                <em className="fim" title={periodoAtual ? 'Estão na etapa agora' : 'Estavam na etapa no último dia do período'}>{number(item.no_fim ?? 0)}</em>
              </div>
            </div>
          ))}</div>
        </article>
      </section>

      <section className="ev-card ev-sales">
        <CardTitle eyebrow="Fechamentos" title="Vendas recentes" description="Últimos contratos realizados pelas equipes" action={<button type="button" className="ev-text-button ev-sales-link" onClick={() => navigate('/Vendas')}>Ver todas as vendas <Icon name="arrow" size={14} /></button>} />
        <div className="ev-table-wrap"><table><thead><tr><th>Endereço</th><th>Equipe</th><th>Corretor</th><th>Valor</th><th>Data</th><th>Valor Total 61</th><th>% compra</th><th>Metragem²</th><th>Valor m²</th><th /></tr></thead><tbody>{vendas.map((item) => <tr key={item.id} onClick={() => setDetail(item)}>
          <td><strong>{item.endereco || item.imovel}</strong><span>{item.codigo ? `Cód. ${item.codigo}` : 'Sem código'}</span></td>
          <td>{item.equipe}</td>
          <td>{item.corretor || '—'}</td>
          <td><strong>{currency(item.valor)}</strong></td>
          <td>{dateLabel(item.data)}</td>
          <td><strong>{currency(item.valor_total_61 || 0)}</strong></td>
          <td>{item.percentual_compra == null ? '—' : `${item.percentual_compra.toFixed(2).replace('.', ',')}%`}</td>
          <td>{item.area == null ? '—' : `${number(item.area)} m²`}</td>
          <td>{item.valor_m2 == null ? '—' : currency(item.valor_m2)}</td>
          <td><Icon name="arrow" size={15} /></td>
        </tr>)}</tbody></table>{!vendas.length && <p className="ev-empty">Nenhum contrato cadastrado.</p>}</div>
      </section>

      <div className="ev-section-heading"><div><span>02 · EFICIÊNCIA DE MÍDIA</span><h2>DFImóveis + C2S</h2></div><p>Cruzamento entre exposição, interesse e geração de oportunidade.</p></div>
      <section className="ev-grid ev-media-grid">
        <article className="ev-card ev-conversion">
          <CardTitle eyebrow="Conversão consolidada" title="Acessos → impressões → leads" description="Dados extraídos do relatório real do DFImóveis" action={<span className="ev-source"><i /> {data?.midia?.data_relatorio ? `XLSX de ${dateLabel(data.midia.data_relatorio)}` : 'Sem XLSX'}</span>} />
          <div className="ev-conversion-flow"><div><span>Acessos</span><strong>{data?.midia?.acessos == null ? '—' : number(data.midia.acessos)}</strong><small>Acessos aos anúncios</small></div><b><Icon name="arrow" size={13} /></b><div><span>Impressões</span><strong>{number(data?.midia?.impressoes || 0)}</strong><small>Exibições registradas</small></div><b>{data?.midia?.impressoes ? `${(100 * (data?.midia?.leads || 0) / data.midia.impressoes).toFixed(1).replace('.', ',')}%` : '—'} <Icon name="arrow" size={13} /></b><div className="highlight"><span>Interações de lead</span><strong>{number(data?.midia?.leads || 0)}</strong><small>E-mail, telefone, WhatsApp, visita e proposta</small></div></div>
          <p className="ev-data-note">{data?.midia?.mensagem}</p>
        </article>
        <article className="ev-card ev-profiles">
          <CardTitle
            eyebrow="Performance por perfil"
            title="Onde a mídia converte melhor"
            description="Conversão = interações ÷ acessos"
            action={<div className="ev-dim-tabs">{DIMENSOES_MIDIA.map(([chave, rotulo]) => (
              <button key={chave} type="button" className={dimMidia === chave ? 'is-ativa' : ''} onClick={() => setDimMidia(chave)}>{rotulo}</button>
            ))}</div>}
          />
          <div className="ev-profile-list">
            {perfisMidia.map((item) => (
              <button key={item.id} onClick={() => setDetail(item)}>
                <div><strong>{item.perfil || 'Não identificado'}</strong><span>{item.detalhe}</span></div>
                <div className="ev-profile-metrics">
                  <span><b>{number(item.acessos)}</b> acessos</span><Icon name="arrow" size={12}/>
                  <span><b>{number(item.impressoes)}</b> impressões</span><Icon name="arrow" size={12}/>
                  <span><b>{item.leads}</b> interações</span>
                </div>
                <em className={item.conversao >= 2 ? 'up' : ''}>{item.conversao == null ? '—' : `${item.conversao.toFixed(2).replace('.', ',')}%`}</em>
              </button>
            ))}
            {!perfisMidia.length && <p className="ev-empty">Sem dados nesse perfil — quartos, metragem e valor dependem do cruzamento com o catálogo do Imoview.</p>}
          </div>
        </article>
      </section>

      <div className="ev-section-heading"><div><span>03 · REVISÃO GERENCIAL</span><h2>Flags de acompanhamento das visitas</h2></div><p>Confirmações gravadas quando o gerente interage com cada visita.</p></div>
      <section className="ev-card ev-review-card">
        <CardTitle eyebrow="Auditoria por equipe" title="O que cada gerente ainda não revisou" description={`Pendências no período por equipe · proposta conta como parada após ${data?.revisao_visitas?.dias_followup || 1} dia sem ação.`} />
        <div className="ev-team-review-list">
          {(data?.revisao_visitas?.por_equipe || []).map((item) => {
            const pending = item.nao_viu_visita + item.nao_viu_nota + item.nao_viu_anexo + item.nao_adicionou_motivo + (item.propostas_sem_acao || 0);
            return <article key={item.equipe_id} className={pending ? 'has-pending' : 'complete'}>
              <div className="ev-team-review-name"><span>{item.equipe_id}</span><strong>{item.equipe}</strong><small>{item.gerente} · {item.total_visitas} visitas</small></div>
              <div className="ev-team-review-metrics">
                <div><span>Não viu visitas</span><strong>{item.nao_viu_visita}</strong><small>de {item.total_visitas}</small></div>
                <div><span>Não viu notas</span><strong>{item.nao_viu_nota}</strong><small>de {item.notas_aplicaveis}</small></div>
                <div><span>Não viu anexos</span><strong>{item.nao_viu_anexo}</strong><small>de {item.anexos_aplicaveis}</small></div>
                <div><span>Não adicionou motivo</span><strong>{item.nao_adicionou_motivo}</strong><small>de {item.motivos_aplicaveis} SIM/TALVEZ</small></div>
                <div className={item.propostas_sem_acao ? 'ev-review-proposta' : ''}>
                  <span>Propostas sem ação</span>
                  <strong>{item.propostas_sem_acao || 0}</strong>
                  <small>de {item.propostas_abertas || 0} em aberto</small>
                </div>
              </div>
              <span className={`ev-team-review-status ${pending ? 'pending' : 'done'}`}>{pending ? `${pending} pendências` : 'Tudo revisado'}</span>
            </article>;
          })}
          {!(data?.revisao_visitas?.por_equipe || []).length && <p className="ev-empty">Nenhuma visita encontrada para as equipes no período.</p>}
        </div>
      </section>

      <section className="ev-audit">
        <div className="ev-audit-head"><div><span className="ev-alert-icon"><Icon name="alert" /></span><div><small>04 · GOVERNANÇA</small><h2>Imóveis parados na jornada</h2><p>Tempo na etapa atual. Captação, encerradas e captadas ficam de fora.</p></div></div></div>

        <div className="ev-contratos-atraso">
          {/* Cards de faixa são o filtro: clicar seleciona, clicar de novo limpa. */}
          <div className="ev-parados-resumo">
            {[
              ['7_14', 'faixa-leve', 'Parados 7 a 14 dias', parados.faixa_7_14, 'Atenção inicial'],
              ['14_30', 'faixa-media', 'Parados 14 a 30 dias', parados.faixa_14_30, 'Precisam de ação'],
              ['30_mais', 'faixa-alta', 'Parados 30+ dias', parados.faixa_30_mais, 'Travados'],
              ['', '', 'Total parados', parados.total, 'Jornada de captação'],
            ].map(([chave, classe, rotulo, valor, nota]) => (
              <button type="button" key={rotulo}
                className={`${classe} ${faixaParados === chave ? 'is-ativa' : ''}`}
                onClick={() => setFaixaParados(faixaParados === chave ? '' : chave)}>
                <span>{rotulo}</span><strong>{number(valor || 0)}</strong><small>{nota}</small>
              </button>
            ))}
          </div>

          <div className="ev-parados-filtros">
            <label>
              Etapa
              <select value={etapaParados} onChange={(e) => setEtapaParados(e.target.value)}>
                <option value="">Todas as etapas</option>
                {Object.entries(parados.por_etapa || {}).map(([etapa, qtd]) => <option key={etapa} value={etapa}>{etapa} ({qtd})</option>)}
              </select>
            </label>
            <input placeholder="Buscar endereço, bairro ou responsável" value={buscaParados} onChange={(e) => setBuscaParados(e.target.value)} />
            <span>{number(paradosVisiveis.length)} de {number((parados.itens || []).length)} imóveis</span>
          </div>

          <div className="ev-contratos-lista">
            {paradosPagina.map((item) => (
              <button type="button" key={item.id} className={`${item.nivel} ev-parado-item`}
                title="Abrir o card na Jornada de Captação"
                onClick={() => navigate(`/JornadaCaptacao?id=${item.id}`)}>
                <i />
                <div>
                  <strong>{item.endereco}</strong>
                  <small><em className={`ev-etapa-chip ${item.nivel}`}>{item.etapa_label}</em>{item.responsavel}{item.bairro ? ` · ${item.bairro}` : ''}</small>
                </div>
                <div className="ev-contratos-num"><b>{number(item.dias)}</b><span>dias parado</span></div>
                <Icon name="arrow" size={15} />
              </button>
            ))}
            {!paradosVisiveis.length && <p className="ev-empty">Nenhum imóvel parado com esse filtro.</p>}
          </div>

          {totalPaginas > 1 && (
            <div className="ev-paginacao">
              <button type="button" onClick={() => setPaginaParados((p) => Math.max(p - 1, 1))} disabled={paginaParados <= 1}>← Anterior</button>
              <span>
                Página <b>{paginaParados}</b> de {totalPaginas}
                {' · '}{number((paginaParados - 1) * PARADOS_POR_PAGINA + 1)}–{number(Math.min(paginaParados * PARADOS_POR_PAGINA, paradosVisiveis.length))} de {number(paradosVisiveis.length)}
              </span>
              <button type="button" onClick={() => setPaginaParados((p) => Math.min(p + 1, totalPaginas))} disabled={paginaParados >= totalPaginas}>Próxima →</button>
            </div>
          )}
        </div>
      </section>
    </div>
    <Modal item={detail} onClose={() => setDetail(null)} />
  </div>;
}

export default VisaoDiretor;
