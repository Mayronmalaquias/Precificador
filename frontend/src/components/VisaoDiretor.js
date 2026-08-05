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
  const [customOpen, setCustomOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [mediaFilter, setMediaFilter] = useState('todos');
  const [alertsOnly, setAlertsOnly] = useState(false);
  const initialRange = useMemo(() => rangeFor('mes'), []);
  const [dates, setDates] = useState(initialRange);
  const [draftDates, setDraftDates] = useState(initialRange);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const load = async () => {
      const cacheKey = `visao-diretor:${idCorretor}:${dates.start}:${dates.end}:${equipe}`;
      let cached = null;
      try { cached = JSON.parse(sessionStorage.getItem(cacheKey) || 'null'); } catch { cached = null; }
      if (cached && active) setData(cached);
      setLoading(!cached);
      setError('');
      try {
        const params = new URLSearchParams({ solicitante_id: idCorretor, start: dates.start, end: dates.end });
        if (equipe !== 'todas') params.set('team', equipe);
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
  }, [dates, equipe, idCorretor]);

  const equipes = data?.equipes_opcoes || [];
  const equipesVisiveis = data?.equipes || [];
  const vendas = data?.vendas_recentes || [];
  const midia = data?.midia?.perfis || [];
  const alertas = data?.pendencias || [];
  const kpiData = data?.kpis || {};
  const delta = (value) => value == null ? 'Sem comparativo' : `${value > 0 ? '+' : ''}${String(value).replace('.', ',')}%`;
  const kpis = [
    { label: 'Total de vendas', value: currency(kpiData.vendas?.valor || 0), delta: delta(kpiData.vendas?.variacao_pct), positive: (kpiData.vendas?.variacao_pct || 0) >= 0, icon: 'revenue', caption: `${kpiData.vendas?.quantidade || 0} contratos no período` },
    { label: 'Propostas de visitas', value: number(kpiData.propostas?.valor || 0), delta: delta(kpiData.propostas?.variacao_pct), positive: (kpiData.propostas?.variacao_pct || 0) >= 0, icon: 'proposal', caption: 'SIM, NÃO e TALVEZ' },
    { label: 'Visitas realizadas', value: number(kpiData.visitas?.valor || 0), delta: delta(kpiData.visitas?.variacao_pct), positive: (kpiData.visitas?.variacao_pct || 0) >= 0, icon: 'visit', caption: `${dateLabel(dates.start)} a ${dateLabel(dates.end)}` },
    { label: 'Leads captados', value: number(kpiData.leads?.valor || 0), delta: delta(kpiData.leads?.variacao_pct), positive: (kpiData.leads?.variacao_pct || 0) >= 0, icon: 'lead', caption: 'Base real de leads do sistema' },
  ];
  const totalPropostas = equipesVisiveis.reduce((acc, item) => acc + item.sim + item.nao + item.talvez, 0);
  const proposalDenominator = Math.max(totalPropostas, 1);
  const maxVisitas = Math.max(...equipesVisiveis.map((item) => item.visitas), 1);
  const midiaVisivel = mediaFilter === 'todos' ? midia : midia.filter((item) => item.perfil === mediaFilter);
  const alertasVisiveis = alertsOnly ? alertas.filter((item) => item.nivel === 'critical') : alertas;

  return <div className="ev-page">
    <div className="ev-shell">
      <section className="ev-executive-header">
        <div><div className="ev-eyebrow"><span /> Painel executivo</div><h1>Visão do Diretor</h1><p>Decisões mais rápidas com a performance comercial, mídia e governança de todas as equipes.</p></div>
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
        <label className="ev-select-wrap"><span>Equipe</span><select value={equipe} onChange={(e) => setEquipe(e.target.value)}><option value="todas">Todas as equipes</option>{equipes.map((item) => <option value={item.id} key={item.id}>{item.nome} · {item.gerente}</option>)}</select></label>
        {customOpen && <div className="ev-date-popover"><label>De<input type="date" value={draftDates.start} onChange={(event) => setDraftDates((current) => ({ ...current, start: event.target.value }))} /></label><label>Até<input type="date" value={draftDates.end} onChange={(event) => setDraftDates((current) => ({ ...current, end: event.target.value }))} /></label><button onClick={() => { setDates(draftDates); setCustomOpen(false); }}>Aplicar período</button></div>}
      </section>

      <section className="ev-kpis" aria-label="Resumo executivo">
        {kpis.map((item) => <article className="ev-kpi" key={item.label}><div className={`ev-kpi-icon ${item.icon}`}><Icon name={item.icon} /></div><div className="ev-kpi-top"><span>{item.label}</span><em className={item.positive ? 'up' : 'down'}>{item.delta}</em></div><strong>{item.value}</strong><small>{item.caption}<b> vs. período anterior</b></small></article>)}
      </section>

      <div className="ev-section-heading"><div><span>01 · PERFORMANCE</span><h2>Controle de equipes e gerentes</h2></div><p>Leitura comparativa do ritmo comercial e da prospecção ativa.</p></div>

      <section className="ev-grid ev-grid-performance">
        <article className="ev-card ev-visits">
          <CardTitle eyebrow="Execução comercial" title="Visitas por equipe" description="Visitas registradas no período selecionado" action={<span className="ev-legend"><i /> Realizado</span>} />
          <div className="ev-bar-chart">
            {equipesVisiveis.map((item) => <div className="ev-bar-row" key={item.id}><div><strong>{item.nome}</strong><span>{item.gerente}</span></div><div className="ev-bar-track"><b style={{ width: `${(item.visitas / maxVisitas) * 100}%` }} /></div><strong>{item.visitas}</strong></div>)}
            {!equipesVisiveis.length && <p className="ev-empty">Nenhuma equipe ou visita encontrada.</p>}
          </div>
          <div className="ev-card-footer"><span><b>{kpiData.visitas?.valor || 0}</b> visitas realizadas</span><span>Metas de visita não estão cadastradas na base atual.</span></div>
        </article>

        <article className="ev-card ev-funnel">
          <CardTitle eyebrow="Qualidade das visitas" title="Funil de visitas" description="Visitas classificadas pela proposta registrada: SIM, NÃO ou TALVEZ" />
          <div className="ev-donut-wrap"><div className="ev-donut" style={{ '--sim': `${(equipesVisiveis.reduce((a, i) => a + i.sim, 0) / proposalDenominator) * 360}deg`, '--talvez': `${((equipesVisiveis.reduce((a, i) => a + i.sim + i.talvez, 0)) / proposalDenominator) * 360}deg` }}><div><strong>{totalPropostas}</strong><span>visitas</span></div></div>
            <div className="ev-funnel-legend">{[['sim', 'Proposta SIM', equipesVisiveis.reduce((a, i) => a + i.sim, 0)], ['talvez', 'Proposta TALVEZ', equipesVisiveis.reduce((a, i) => a + i.talvez, 0)], ['nao', 'Proposta NÃO', equipesVisiveis.reduce((a, i) => a + i.nao, 0)]].map(([tone, label, value]) => <div key={tone}><i className={tone} /><span>{label}</span><strong>{value}</strong></div>)}</div>
          </div>
          <div className="ev-stacked">{equipesVisiveis.map((item) => { const total = item.sim + item.nao + item.talvez; return <div key={item.id}><span>{item.nome}</span><div><i className="sim" style={{ width: `${item.sim / total * 100}%` }} /><i className="talvez" style={{ width: `${item.talvez / total * 100}%` }} /><i className="nao" style={{ width: `${item.nao / total * 100}%` }} /></div></div>})}</div>
        </article>

        <article className="ev-card ev-prospect">
          <CardTitle eyebrow="Prospecção ativa" title="Busca & captação" description="Volume trabalhado pelas equipes no período" />
          <div className="ev-prospect-total"><div><span>Imóveis trabalhados</span><strong>{number(data?.captacao?.trabalhados || 0)}</strong><small>Atualizados no período</small></div><div><span>Imóveis captados</span><strong>{number(data?.captacao?.captados || 0)}</strong><small>Marcados como captados</small></div></div>
          <p className="ev-data-note">“Imóveis buscados” foi substituído por imóveis efetivamente atualizados, pois a base não registra eventos de busca.</p>
        </article>

        <article className="ev-card ev-journey">
          <CardTitle eyebrow="Jornada de captação" title="Movimentações de etapa" description="Imóveis que avançaram durante o período" />
          <div className="ev-journey-list">{(data?.captacao?.etapas || []).map((item, index) => <div key={item.etapa}><span className="ev-step">0{index + 1}</span><div><strong>{item.label}</strong><span>{item.total} imóveis avançaram</span></div><em>{item.total}</em></div>)}</div>
        </article>
      </section>

      <section className="ev-card ev-sales">
        <CardTitle eyebrow="Fechamentos" title="Vendas recentes" description="Últimos contratos realizados pelas equipes" action={<button type="button" className="ev-text-button ev-sales-link" onClick={() => navigate('/Vendas')}>Ver todas as vendas <Icon name="arrow" size={14} /></button>} />
        <div className="ev-table-wrap"><table><thead><tr><th>Imóvel</th><th>Equipe / gerente</th><th>Valor de fechamento</th><th>Data</th><th>Valor Total 61</th><th /></tr></thead><tbody>{vendas.map((item) => <tr key={item.id} onClick={() => setDetail(item)}><td><strong>{item.imovel}</strong><span>{item.codigo}</span></td><td><strong>{item.equipe}</strong><span>{item.gerente}</span></td><td><strong>{currency(item.valor)}</strong></td><td>{dateLabel(item.data)}</td><td><strong>{currency(item.valor_total_61 || 0)}</strong></td><td><Icon name="arrow" size={15} /></td></tr>)}</tbody></table>{!vendas.length && <p className="ev-empty">Nenhum contrato cadastrado.</p>}</div>
      </section>

      <div className="ev-section-heading"><div><span>02 · EFICIÊNCIA DE MÍDIA</span><h2>DFImóveis + C2S</h2></div><p>Cruzamento entre exposição, interesse e geração de oportunidade.</p></div>
      <section className="ev-grid ev-media-grid">
        <article className="ev-card ev-conversion">
          <CardTitle eyebrow="Conversão consolidada" title="Acessos → impressões → leads" description="Dados extraídos do relatório real do DFImóveis" action={<span className="ev-source"><i /> {data?.midia?.data_relatorio ? `XLSX de ${dateLabel(data.midia.data_relatorio)}` : 'Sem XLSX'}</span>} />
          <div className="ev-conversion-flow"><div><span>Acessos</span><strong>{data?.midia?.acessos == null ? '—' : number(data.midia.acessos)}</strong><small>Acessos aos anúncios</small></div><b><Icon name="arrow" size={13} /></b><div><span>Impressões</span><strong>{number(data?.midia?.impressoes || 0)}</strong><small>Exibições registradas</small></div><b>{data?.midia?.impressoes ? `${(100 * (data?.midia?.leads || 0) / data.midia.impressoes).toFixed(1).replace('.', ',')}%` : '—'} <Icon name="arrow" size={13} /></b><div className="highlight"><span>Interações de lead</span><strong>{number(data?.midia?.leads || 0)}</strong><small>E-mail, telefone, WhatsApp, visita e proposta</small></div></div>
          <p className="ev-data-note">{data?.midia?.mensagem}</p>
        </article>
        <article className="ev-card ev-profiles">
          <CardTitle eyebrow="Performance por perfil" title="Onde a mídia converte melhor" action={<label className="ev-inline-select"><Icon name="filter" size={14}/><select value={mediaFilter} onChange={(e) => setMediaFilter(e.target.value)}><option value="todos">Todos os bairros</option>{midia.map((item) => <option key={item.id}>{item.perfil}</option>)}</select></label>} />
          <div className="ev-profile-list">{midiaVisivel.map((item) => <button key={item.id} onClick={() => setDetail(item)}><div><strong>{item.bairro || item.perfil || 'Não identificado'}</strong><span>{item.detalhe}</span></div><div className="ev-profile-metrics"><span><b>{number(item.acessos)}</b> acessos</span><Icon name="arrow" size={12}/><span><b>{number(item.impressoes)}</b> impressões</span><Icon name="arrow" size={12}/><span><b>{item.leads}</b> interações</span></div></button>)}{!midiaVisivel.length && <p className="ev-empty">Nenhum relatório DFImóveis disponível.</p>}</div>
        </article>
      </section>

      <div className="ev-section-heading"><div><span>03 · REVISÃO GERENCIAL</span><h2>Flags de acompanhamento das visitas</h2></div><p>Confirmações gravadas quando o gerente interage com cada visita.</p></div>
      <section className="ev-card ev-review-card">
        <CardTitle eyebrow="Auditoria por equipe" title="O que cada gerente ainda não revisou" description="Quantidades pendentes no período, agrupadas pela equipe responsável." />
        <div className="ev-team-review-list">
          {(data?.revisao_visitas?.por_equipe || []).map((item) => {
            const pending = item.nao_viu_visita + item.nao_viu_nota + item.nao_viu_anexo + item.nao_adicionou_motivo;
            return <article key={item.equipe_id} className={pending ? 'has-pending' : 'complete'}>
              <div className="ev-team-review-name"><span>{item.equipe_id}</span><strong>{item.equipe}</strong><small>{item.gerente} · {item.total_visitas} visitas</small></div>
              <div className="ev-team-review-metrics">
                <div><span>Não viu visitas</span><strong>{item.nao_viu_visita}</strong><small>de {item.total_visitas}</small></div>
                <div><span>Não viu notas</span><strong>{item.nao_viu_nota}</strong><small>de {item.notas_aplicaveis}</small></div>
                <div><span>Não viu anexos</span><strong>{item.nao_viu_anexo}</strong><small>de {item.anexos_aplicaveis}</small></div>
                <div><span>Não adicionou motivo</span><strong>{item.nao_adicionou_motivo}</strong><small>de {item.motivos_aplicaveis} SIM/TALVEZ</small></div>
              </div>
              <span className={`ev-team-review-status ${pending ? 'pending' : 'done'}`}>{pending ? `${pending} pendências` : 'Tudo revisado'}</span>
            </article>;
          })}
          {!(data?.revisao_visitas?.por_equipe || []).length && <p className="ev-empty">Nenhuma visita encontrada para as equipes no período.</p>}
        </div>
      </section>

      <section className="ev-audit">
        <div className="ev-audit-head"><div><span className="ev-alert-icon"><Icon name="alert" /></span><div><small>04 · GOVERNANÇA</small><h2>Pendências que exigem atenção</h2><p>Sinais operacionais gerados pelas flags de visualização e atualização.</p></div></div><label><input type="checkbox" checked={alertsOnly} onChange={(e) => setAlertsOnly(e.target.checked)} /><span /> Somente críticos</label></div>
        <div className="ev-alert-list">{alertasVisiveis.map((item) => <button key={item.id} onClick={() => setDetail(item)}><i className={item.nivel} /><div><span>{item.tipo}</span><strong>{item.descricao}</strong><small>{item.responsavel}</small></div><div><span>Em atraso</span><strong>{item.atraso}</strong></div><Icon name="arrow" size={16}/></button>)}</div>
        <div className="ev-audit-footer"><span><b>{alertas.filter((i) => i.nivel === 'critical').length} críticos</b> · {alertas.length} pendências no total</span><button>Ver central de pendências <Icon name="arrow" size={14}/></button></div>
      </section>
    </div>
    <Modal item={detail} onClose={() => setDetail(null)} />
  </div>;
}

export default VisaoDiretor;
