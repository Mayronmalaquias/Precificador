import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BASE } from '../services/api';
import { moedaInput, moedaNumero, moedaDeNumero } from '../services/moeda';
import { porRotulo } from '../services/ordenar';
import { descricaoImovel, edificioDe } from '../services/imovelLabel';
import { useAuth } from '../context/AuthContext';
import { useEquipes } from '../context/EquipesContext';
import { useToast } from '../context/ToastContext';
import { GraficoBarras, GraficoLinha, GraficoPizza } from './GraficosGestao';
import '../assets/css/GestaoModulo.css';
import '../assets/css/PropostasEfetivas.css';
import '../assets/css/PropostasEfetivasPolish.css';

// Mesmo traço dos ícones da Visão do Diretor: stroke 1.8, viewBox 24.
function Icon({ name, size = 18 }) {
  const paths = {
    proposta: <><path d="M6 2h9l4 4v16H6z" /><path d="M14 2v5h5M9 12h7M9 16h7" /></>,
    dinheiro: <><path d="M4 19V5M4 19h16" /><path d="m7 15 4-4 3 2 5-7" /></>,
    relogio: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    alerta: <><path d="M12 3 2.8 20h18.4z" /><path d="M12 9v5M12 17.5v.1" /></>,
    filtro: <path d="M4 6h16M7 12h10M10 18h4" />,
  };
  return (
    <svg className="pe-icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
  );
}

const VAZIO = {
  codigo_imovel: '', imovel_endereco: '', bairro: '', tipo: '', numero: '',
  bloco: '', complemento: '', quartos: '', vagas: '', area: '',
  valor: '', forma_pagamento: '', valor_permuta: '', descricao_permuta: '',
  situacao: 'em_analise', cliente: '', observacao: '', data_proposta: '',
  id_corretor: '', id_visita: '', id_gerente: '', gerente_nome: '',
};

const moeda = (v) => (v == null ? '—' : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }));
// Aceita data pura ("2026-08-10", que vira meia-noite local para não recuar um dia) e
// datetime ISO com fuso ("...Z", de `created_at`), que o navegador converte sozinho.
const dataBR = (v) => {
  if (!v) return '—';
  const d = String(v).length > 10 ? new Date(v) : new Date(`${v}T00:00:00`);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('pt-BR');
};

const CORES_SITUACAO = {
  'Em analise': '#6d7ce0',
  'Em análise': '#6d7ce0',
  Contraproposta: '#c07a11',
  Aceita: '#1b8a5a',
  Vendido: '#0f6247',
  Recusada: '#b03040',
  Cancelada: '#aeb4c2',
};

// Máscara de moeda em services/moeda.js — compartilhada com o Lançar Imóvel.

export default function PropostasEfetivas() {
  const toast = useToast();
  const { idCorretor } = useAuth();
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [filtros, setFiltros] = useState({
    situacao: '', forma_pagamento: '', busca: '',
    // Recortes acrescentados em 25/08/2026. `team` e `id_gerente` só têm efeito para
    // perfil global — o servidor ignora para gerente e corretor, cujo escopo sai do
    // cadastro.
    team: '', bairro: '', tipo: '',
    valor_min: '', valor_max: '', sem_acao_min: '',
  });
  const [maisFiltros, setMaisFiltros] = useState(false);
  const [form, setForm] = useState(VAZIO);
  const [editandoId, setEditandoId] = useState(null);
  const [formAberto, setFormAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [detalhe, setDetalhe] = useState(null);
  const [novaAcao, setNovaAcao] = useState({ descricao: '', situacao: '' });
  const [buscaImovel, setBuscaImovel] = useState('');
  const [imoveis, setImoveis] = useState([]);
  const [buscandoImovel, setBuscandoImovel] = useState(false);
  const [corretores, setCorretores] = useState([]);
  // So chega preenchido p/ perfil global; gerente lanca sempre no proprio nome.
  const [gerentes, setGerentes] = useState([]);
  const [visitas, setVisitas] = useState([]);
  const [buscandoVisita, setBuscandoVisita] = useState(false);

  const { equipesOpcoes } = useEquipes();
  const podeEditar = !!dados?.escopo?.edita;
  // Só quem enxerga tudo escolhe equipe ou gerente. Para os demais o filtro nem aparece:
  // o servidor o ignoraria, e um controle que não faz nada é pior que controle ausente.
  const veTudo = !!dados?.escopo?.ve_tudo;
  const filtrosLigados = ['team', 'bairro', 'tipo', 'valor_min',
    'valor_max', 'sem_acao_min'].filter((k) => String(filtros[k] || '').trim()).length;

  // O gerente da proposta pode nao estar na lista (deixou de ser gerente, ou a proposta
  // e de outra equipe). Sem acrescenta-lo, o select abriria em branco e salvar
  // reatribuiria a proposta para quem esta editando, sem ninguem pedir.
  const gerentesOpcoes = useMemo(() => {
    if (!form.id_gerente || gerentes.some((g) => g.id === form.id_gerente)) return gerentes;
    return [...gerentes, {
      id: form.id_gerente,
      nome: form.gerente_nome || form.id_gerente,
      team: '',
    }];
  }, [gerentes, form.id_gerente, form.gerente_nome]);
  const opcoes = useMemo(
    () => dados?.opcoes || { situacoes: [], formas_pagamento: [], bairros: [], tipos: [] },
    [dados?.opcoes],
  );

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const qs = new URLSearchParams({ solicitante_id: idCorretor || '' });
      Object.entries(filtros).forEach(([k, v]) => { if (v && v !== 'false') qs.set(k, v); });
      const r = await fetch(`${BASE}/propostas?${qs.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao carregar propostas');
      setDados(d);
    } catch (e) {
      toast(e.message || 'Erro ao carregar propostas', 'error');
    } finally {
      setCarregando(false);
    }
  }, [idCorretor, filtros, toast]);

  useEffect(() => { carregar(); }, [carregar]);

  // Corretores em nome de quem dá pra lançar (o back já corta pelo escopo).
  useEffect(() => {
    if (!podeEditar) return;
    (async () => {
      try {
        const r = await fetch(`${BASE}/propostas/corretores?solicitante_id=${idCorretor}`);
        const d = await r.json();
        // Ordenado por nome: o gerente procura a pessoa, nao a ordem do cadastro.
        if (r.ok && d.ok) {
          setCorretores(porRotulo(d.itens || [], 'nome'));
          setGerentes(porRotulo(d.gerentes || [], 'nome'));
        }
      } catch { /* silencioso: o campo vira opcional */ }
    })();
  }, [podeEditar, idCorretor]);

  // Visitas candidatas: se já escolheu o corretor, só as dele.
  const puxarVisitas = useCallback(async () => {
    setBuscandoVisita(true);
    try {
      const qs = new URLSearchParams({ solicitante_id: idCorretor || '' });
      if (form.id_corretor) qs.set('corretor', form.id_corretor);
      if (form.codigo_imovel) qs.set('codigo', form.codigo_imovel);
      const r = await fetch(`${BASE}/propostas/visitas?${qs.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao buscar visitas');
      setVisitas(d.itens || []);
      if (!(d.itens || []).length) toast('Nenhuma visita encontrada para esse filtro.', 'error');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBuscandoVisita(false);
    }
  }, [idCorretor, form.id_corretor, form.codigo_imovel, toast]);

  // Busca no Imoview pelo endereço (a API não filtra por código — ver imoview_service).
  const buscarImovel = useCallback(async () => {
    if (buscaImovel.trim().length < 3) { toast('Digite ao menos 3 letras do endereço', 'error'); return; }
    setBuscandoImovel(true);
    try {
      const r = await fetch(`${BASE}/imoveis_busca?endereco=${encodeURIComponent(buscaImovel.trim())}`);
      const d = await r.json();
      setImoveis(d.lista || []);
      if (!(d.lista || []).length) toast('Nenhum imóvel encontrado no Imoview', 'error');
    } catch {
      toast('Erro ao buscar no Imoview', 'error');
    } finally {
      setBuscandoImovel(false);
    }
  }, [buscaImovel, toast]);

  const escolherImovel = (item) => {
    setForm((f) => ({
      ...f,
      codigo_imovel: String(item.codigo || ''),
      // A proposta nao tem coluna de edificio; sem juntar aqui, o nome do predio
      // (unico jeito de identificar imovel em Aguas Claras) se perderia no lancamento.
      imovel_endereco: [edificioDe(item), item.endereco || item.titulo || ''].filter(Boolean).join(' — '),
      bairro: item.bairro || '',
      // "S/N" e "n/a" são lixo do Imoview em prédio — não vale preencher com isso.
      numero: /^(s\/n|n\/a)$/i.test(String(item.numero || '').trim()) ? '' : (item.numero || ''),
      bloco: item.bloco || '',
      complemento: item.complemento || '',
      tipo: item.tipo || f.tipo,
      quartos: item.quartos || '',
      vagas: item.vagas || '',
      area: item.area || '',
    }));
    setImoveis([]);
    setBuscaImovel('');
  };

  const abrirNova = () => { setForm({ ...VAZIO }); setEditandoId(null); setVisitas([]); setFormAberto(true); };

  const abrirEdicao = (item) => {
    setForm({
      codigo_imovel: item.codigo_imovel || '', imovel_endereco: item.imovel_endereco || '',
      bairro: item.bairro || '', tipo: item.tipo || '', numero: item.numero || '',
      bloco: item.bloco || '', complemento: item.complemento || '',
      quartos: item.quartos || '', vagas: item.vagas || '', area: item.area || '',
      valor: moedaDeNumero(item.valor),
      forma_pagamento: item.forma_pagamento || '',
      valor_permuta: moedaDeNumero(item.valor_permuta),
      descricao_permuta: item.descricao_permuta || '', situacao: item.situacao || 'em_analise',
      cliente: item.cliente || '', observacao: item.observacao || '',
      data_proposta: item.data_proposta || '',
      id_corretor: item.id_corretor || '', id_visita: item.id_visita || '',
      id_gerente: item.id_gerente || '',
      gerente_nome: item.gerente_nome || '',
    });
    setEditandoId(item.id);
    setVisitas([]);
    setFormAberto(true);
  };

  const set = (campo) => (e) => {
    const valor = ['valor', 'valor_permuta'].includes(campo) ? moedaInput(e.target.value) : e.target.value;
    setForm((f) => ({ ...f, [campo]: valor }));
  };

  const salvar = async (e) => {
    e.preventDefault();
    if (salvando) return;
    setSalvando(true);
    try {
      const corpo = { ...form, valor: moedaNumero(form.valor), valor_permuta: moedaNumero(form.valor_permuta) };
      const url = editandoId
        ? `${BASE}/propostas/${editandoId}?solicitante_id=${idCorretor}`
        : `${BASE}/propostas?solicitante_id=${idCorretor}`;
      const r = await fetch(url, {
        method: editandoId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
      });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao salvar');
      toast(editandoId ? 'Proposta atualizada!' : 'Proposta lançada!', 'success');
      setFormAberto(false);
      setForm(VAZIO);
      setEditandoId(null);
      carregar();
    } catch (err) {
      toast(err.message || 'Erro ao salvar', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const abrirDetalhe = async (id) => {
    try {
      const r = await fetch(`${BASE}/propostas/${id}?solicitante_id=${idCorretor}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao abrir proposta');
      setDetalhe(d.proposta);
      setNovaAcao({ descricao: '', situacao: '' });
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const registrarAcao = async () => {
    if (!novaAcao.descricao.trim()) { toast('Descreva a ação', 'error'); return; }
    try {
      const r = await fetch(`${BASE}/propostas/${detalhe.id}/acoes?solicitante_id=${idCorretor}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(novaAcao),
      });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao registrar ação');
      toast('Ação registrada!', 'success');
      abrirDetalhe(detalhe.id);
      carregar();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const excluir = async (item) => {
    if (!window.confirm(`Excluir a proposta do imóvel ${item.codigo_imovel || item.imovel_endereco}?`)) return;
    try {
      const r = await fetch(`${BASE}/propostas/${item.id}?solicitante_id=${idCorretor}`, { method: 'DELETE' });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao excluir');
      toast('Proposta excluída.', 'success');
      carregar();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const itens = useMemo(() => dados?.itens || [], [dados?.itens]);
  const paradas = dados?.paradas || [];
  const resumo = useMemo(() => dados?.resumo || {}, [dados?.resumo]);
  const ehPermuta = form.forma_pagamento === 'permuta';
  const setF = (k) => (e) => setFiltros((p) => ({ ...p, [k]: e.target.value }));

  const cards = useMemo(() => ([
    { label: 'Propostas abertas', valor: resumo.abertas ?? 0, nota: `${resumo.total ?? 0} no total`, icone: 'proposta' },
    { label: 'Valor em aberto', valor: moeda(resumo.valor_aberto || 0), nota: 'Soma das propostas não fechadas', icone: 'dinheiro' },
    { label: `Sem ação há ${opcoes.dias_atencao || 7}+ dias`, valor: resumo.sem_acao_7 ?? 0, nota: 'Precisam de follow-up', tom: 'atencao', icone: 'relogio' },
    { label: `Sem ação há ${opcoes.dias_critico || 14}+ dias`, valor: resumo.sem_acao_14 ?? 0, nota: 'Estão paradas', tom: 'critico', icone: 'alerta' },
  ]), [resumo, opcoes]);

  // Distribuição por situação: barra única que resume o pipeline sem pedir outra chamada.
  const distribuicao = useMemo(() => {
    const contagem = {};
    itens.forEach((i) => { contagem[i.situacao] = (contagem[i.situacao] || 0) + 1; });
    const total = itens.length || 1;
    return (opcoes.situacoes || [])
      .map((s) => ({ ...s, qtd: contagem[s.value] || 0, pct: ((contagem[s.value] || 0) / total) * 100 }))
      .filter((s) => s.qtd > 0);
  }, [itens, opcoes.situacoes]);

  // Os graficos usam exatamente os itens devolvidos pela API. Assim, respeitam tanto
  // o escopo do usuario quanto situacao, pagamento, busca e "so as abertas".
  const graficos = useMemo(() => {
    const porSituacao = new Map();
    const porMes = new Map();
    const porResponsavel = new Map();

    itens.forEach((item) => {
      const situacao = item.situacao_label || item.situacao || 'Nao informada';
      porSituacao.set(situacao, (porSituacao.get(situacao) || 0) + 1);

      // created_at representa o lancamento no sistema; data_proposta pode ser retroativa.
      const mes = String(item.created_at || '').slice(0, 7);
      if (/^\d{4}-\d{2}$/.test(mes)) porMes.set(mes, (porMes.get(mes) || 0) + 1);

      const responsavel = item.corretor_nome || item.gerente_nome || 'Sem responsavel';
      porResponsavel.set(responsavel, (porResponsavel.get(responsavel) || 0) + 1);
    });

    const situacoes = Array.from(porSituacao, ([rotulo, total]) => ({ rotulo, total }))
      .sort((a, b) => b.total - a.total || a.rotulo.localeCompare(b.rotulo, 'pt-BR'));

    const mesesComDados = Array.from(porMes.keys()).sort();
    const evolucao = [];
    if (mesesComDados.length) {
      const [anoFinal, mesFinal] = mesesComDados[mesesComDados.length - 1].split('-').map(Number);
      // Doze meses continuos deixam lacunas explicitas como zero, em vez de ligar meses distantes.
      for (let delta = 11; delta >= 0; delta -= 1) {
        const data = new Date(anoFinal, mesFinal - 1 - delta, 1);
        const chave = `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, '0')}`;
        evolucao.push({
          data: chave,
          label: `${String(data.getMonth() + 1).padStart(2, '0')}/${String(data.getFullYear()).slice(-2)}`,
          total: porMes.get(chave) || 0,
        });
      }
    }

    const responsaveis = Array.from(porResponsavel, ([rotulo, total]) => ({ rotulo, total }))
      .sort((a, b) => b.total - a.total || a.rotulo.localeCompare(b.rotulo, 'pt-BR'))
      .slice(0, 8);

    return { situacoes, evolucao, responsaveis };
  }, [itens]);

  return (
    <div className="pe-page">
      <header className="pe-hero">
        <div>
          <span className="pe-eyebrow"><i /> Comercial · Propostas</span>
          <h1>Gestão de propostas</h1>
          <p>Propostas formais de compra por imóvel — situação, forma de pagamento e o que já foi feito em cada uma.</p>
        </div>
        <div className="pe-hero-lado">
          <span className="pe-hero-status">{carregando ? 'Atualizando…' : `${itens.length} proposta(s) no filtro atual`}</span>
          {podeEditar && <button type="button" className="pe-cta" onClick={abrirNova}>+ Lançar proposta</button>}
        </div>
      </header>

      {!podeEditar && !carregando && (
        <p className="pe-aviso">Seu perfil acompanha as propostas em modo leitura — quem altera é gerente, diretor ou administrativo.</p>
      )}

      <div className="pe-secao"><div><span>01 · PIPELINE</span><h2>Onde as propostas estão</h2></div><p>Volume aberto, dinheiro em jogo e o que já passou do prazo de follow-up.</p></div>

      <section className="pe-cards">
        {cards.map((c) => (
          <article key={c.label} className={`pe-card ${c.tom || ''}`}>
            <div className={`pe-card-icone ${c.tom || ''}`}><Icon name={c.icone} /></div>
            <span>{c.label}</span><strong>{c.valor}</strong><small>{c.nota}</small>
          </article>
        ))}
      </section>

      {distribuicao.length > 0 && (
        <section className="pe-distribuicao">
          <div className="pe-distribuicao-head"><strong>Distribuição por situação</strong><span>{itens.length} proposta(s)</span></div>
          <div className="pe-distribuicao-barra">
            {distribuicao.map((s) => <i key={s.value} className={`s-${s.value}`} style={{ width: `${s.pct}%` }} title={`${s.label}: ${s.qtd}`} />)}
          </div>
          <div className="pe-distribuicao-legenda">
            {distribuicao.map((s) => <span key={s.value}><i className={`s-${s.value}`} />{s.label}<b>{s.qtd}</b></span>)}
          </div>
        </section>
      )}

      {itens.length > 0 && (
        <>
          <div className="pe-secao"><div><span>02 · ANÁLISE</span><h2>Leitura da carteira</h2></div><p>Os gráficos acompanham o mesmo escopo e os mesmos filtros da lista de propostas.</p></div>
          <section className="pe-dashboard gm gm-dashboard" aria-label="Gráficos das propostas filtradas">
            <article className="gm-grafico gm-grafico--linha">
              <header>
                <div><h4>Evolução de propostas</h4><p>Lançamentos por mês nos últimos 12 meses</p></div>
                <strong className="gm-grafico-total">{itens.length}</strong>
              </header>
              <GraficoLinha pontos={graficos.evolucao} rotuloAria="Evolução mensal das propostas filtradas" unidade="proposta(s)" />
            </article>

            <article className="gm-grafico">
              <header><div><h4>Propostas por situação</h4><p>Participação de cada etapa no filtro atual</p></div></header>
              <GraficoPizza
                dados={graficos.situacoes}
                centroValor={itens.length}
                centroRotulo="propostas"
                cores={CORES_SITUACAO}
              />
            </article>

            <article className="gm-grafico">
              <header><div><h4>Volume por responsável</h4><p>Até 8 responsáveis com mais propostas no filtro</p></div></header>
              <GraficoBarras dados={graficos.responsaveis} sufixo="proposta(s)" />
            </article>
          </section>
        </>
      )}

      {paradas.length > 0 && (
        <>
          <div className="pe-secao"><div><span>03 · ACOMPANHAMENTO</span><h2>Paradas há mais tempo</h2></div><p>Ordenado pelo tempo sem ação do gerente. É por aqui que o acompanhamento começa.</p></div>
          <section className="pe-paradas">
            <div className="pe-parada-list">
              {paradas.slice(0, 8).map((item) => (
                <button type="button" key={item.id} className={`pe-parada ${item.alerta || ''}`} onClick={() => abrirDetalhe(item.id)}>
                  <div>
                    <strong>{item.codigo_imovel ? `#${item.codigo_imovel}` : 'Sem código'} · {item.bairro || 'Bairro não informado'}</strong>
                    <small>{item.corretor_nome || item.gerente_nome || '—'} · {item.situacao_label}</small>
                  </div>
                  <div className="pe-parada-num">
                    <b>{item.dias_sem_acao ?? '—'}</b><span>dias sem ação</span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        </>
      )}

      <div className="pe-secao"><div><span>04 · CARTEIRA</span><h2>Todas as propostas</h2></div><p>Clique em qualquer linha para ver o histórico de ações e registrar uma nova.</p></div>

      <section className="pe-filtros">
        <span className="pe-filtro-icone"><Icon name="filtro" size={15} /></span>
        <input placeholder="Buscar por código, endereço, bairro, cliente ou corretor" value={filtros.busca} onChange={setF('busca')} />
        <select value={filtros.situacao} onChange={setF('situacao')}>
          <option value="">Todas as situações</option>
          {opcoes.situacoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select value={filtros.forma_pagamento} onChange={setF('forma_pagamento')}>
          <option value="">Toda forma de pagamento</option>
          {opcoes.formas_pagamento.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
        {/* O checkbox "Só as abertas" saiu: virou a opção "Ativas" do dropdown acima,
            que é o mesmo recorte (não vendida nem cancelada). Com os dois, marcar o
            checkbox e escolher "Vendido" deixava a tela pedindo duas coisas
            contraditórias, e vencia quem aplicasse por último no servidor. */}
        <button type="button" className={`pe-mais-filtros ${maisFiltros || filtrosLigados ? 'is-ativo' : ''}`}
          aria-pressed={maisFiltros} onClick={() => setMaisFiltros((v) => !v)}>
          Filtros{filtrosLigados ? ` (${filtrosLigados})` : ''}
        </button>
      </section>

      {maisFiltros && (
        <section className="pe-filtros-extra">
          {veTudo && (
            <>
              {/* Um dropdown só: `id_gerente` da proposta guarda o id da EQUIPE, o mesmo
                  valor de `team`. Dois controles para o mesmo recorte só criariam a
                  dúvida de qual usar. */}
              <label>Equipe / gerente
                <select value={filtros.team} onChange={setF('team')}>
                  <option value="">Todas as equipes</option>
                  {equipesOpcoes.map((eq) => (
                    <option key={eq.value} value={eq.value}>{eq.label}</option>
                  ))}
                </select>
              </label>
            </>
          )}
          {/* Só o que existe nas propostas do escopo — as listas vêm do servidor já
              deduplicadas por caixa ("Apartamento" e "APARTAMENTO" viram uma opção só). */}
          <label>Bairro
            <select value={filtros.bairro} onChange={setF('bairro')}>
              <option value="">Todos os bairros</option>
              {(opcoes.bairros || []).map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
          <label>Tipo
            <select value={filtros.tipo} onChange={setF('tipo')}>
              <option value="">Todos os tipos</option>
              {(opcoes.tipos || []).map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label>Valor de
            <input type="number" value={filtros.valor_min} placeholder="0" onChange={setF('valor_min')} />
          </label>
          <label>Valor até
            <input type="number" value={filtros.valor_max} placeholder="sem teto" onChange={setF('valor_max')} />
          </label>
          <label>Parada há (dias)
            <input type="number" min="0" value={filtros.sem_acao_min} placeholder="ex.: 7"
              onChange={setF('sem_acao_min')} />
          </label>
          <button type="button" className="pe-limpar" onClick={() => setFiltros((p) => ({
            ...p, team: '', bairro: '', tipo: '',
            valor_min: '', valor_max: '', sem_acao_min: '',
          }))}>
            Limpar
          </button>
        </section>
      )}

      <section className="pe-tabela-wrap">
        <table className="pe-tabela">
          <thead>
            <tr>
              <th>Imóvel</th><th>Bairro / Tipo</th><th>Valor</th><th>Pagamento</th>
              <th>Situação</th><th>Em aberto</th><th>Sem ação</th><th>Corretor</th><th>Gerente</th><th />
            </tr>
          </thead>
          <tbody>
            {itens.map((item) => (
              <tr key={item.id} className={item.alerta ? `linha-${item.alerta}` : ''}>
                <td onClick={() => abrirDetalhe(item.id)}>
                  <strong>{item.codigo_imovel ? `#${item.codigo_imovel}` : '—'}</strong>
                  <span>{item.imovel_endereco || ''}{item.numero ? `, ${item.numero}` : ''}</span>
                </td>
                <td onClick={() => abrirDetalhe(item.id)}><strong>{item.bairro || '—'}</strong><span>{item.tipo || ''}</span></td>
                <td onClick={() => abrirDetalhe(item.id)}>
                  <strong>{moeda(item.valor)}</strong>
                  {item.valor_permuta ? <span>+ permuta {moeda(item.valor_permuta)}</span> : null}
                </td>
                <td onClick={() => abrirDetalhe(item.id)}>{item.forma_pagamento_label || '—'}</td>
                <td onClick={() => abrirDetalhe(item.id)}><span className={`pe-situacao s-${item.situacao}`}>{item.situacao_label}</span></td>
                <td onClick={() => abrirDetalhe(item.id)}>{item.dias_em_aberto == null ? '—' : `${item.dias_em_aberto} d`}</td>
                <td onClick={() => abrirDetalhe(item.id)} className={item.alerta || ''}>{item.fechada ? '—' : `${item.dias_sem_acao ?? 0} d`}</td>
                <td onClick={() => abrirDetalhe(item.id)}>{item.corretor_nome || '—'}{item.id_visita ? <span>visita vinculada</span> : null}</td>
                <td onClick={() => abrirDetalhe(item.id)}>{item.gerente_nome || '—'}</td>
                <td className="pe-acoes-col">
                  {podeEditar && <button type="button" onClick={() => abrirEdicao(item)}>Editar</button>}
                  {podeEditar && <button type="button" className="perigo" onClick={() => excluir(item)}>Excluir</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!itens.length && !carregando && <p className="pe-vazio">Nenhuma proposta encontrada.</p>}
        {carregando && <p className="pe-vazio">Carregando…</p>}
      </section>

      {formAberto && (
        <div className="pe-modal-bg" onClick={() => setFormAberto(false)}>
          <form className="pe-modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
            <header><h2>{editandoId ? 'Editar proposta' : 'Lançar proposta'}</h2><button type="button" onClick={() => setFormAberto(false)}>✕</button></header>

            <div className="pe-imovel-busca">
              <label>Imóvel (busca no Imoview pelo endereço)</label>
              <div>
                <input value={buscaImovel} onChange={(e) => setBuscaImovel(e.target.value)} placeholder="Ex.: SQN 210 bloco A" />
                <button type="button" onClick={buscarImovel} disabled={buscandoImovel}>{buscandoImovel ? 'Buscando…' : 'Buscar'}</button>
              </div>
              {imoveis.length > 0 && (
                <ul className="pe-imovel-lista">
                  {imoveis.map((i) => (
                    <li key={i.codigo}><button type="button" onClick={() => escolherImovel(i)}>
                      <strong>#{i.codigo} · {i.tipo || 'Imóvel'}</strong>
                      <span className="pe-imovel-end">
                        {descricaoImovel(i)}
                      </span>
                      <em>
                        {[i.quartos ? `${i.quartos} quartos` : '', i.vagas ? `${i.vagas} vagas` : '', i.area ? `${i.area} m²` : '', i.valor, i.finalidade].filter(Boolean).join(' · ')}
                      </em>
                    </button></li>
                  ))}
                </ul>
              )}
            </div>

            <div className="pe-imovel-busca">
              <label>Visita relacionada (opcional)</label>
              <div>
                <button type="button" onClick={puxarVisitas} disabled={buscandoVisita}>{buscandoVisita ? 'Buscando…' : 'Puxar visitas'}</button>
                {form.id_visita
                  ? <span className="pe-visita-escolhida">Visita <b>{form.id_visita}</b> vinculada <button type="button" onClick={() => setForm((f) => ({ ...f, id_visita: '' }))}>remover</button></span>
                  : <span className="pe-visita-dica">{form.id_corretor ? 'Traz as visitas do corretor escolhido' : 'Traz as visitas da sua equipe'}{form.codigo_imovel ? ` · filtrando pelo código ${form.codigo_imovel}` : ''}</span>}
              </div>
              {visitas.length > 0 && (
                <ul className="pe-imovel-lista">
                  {visitas.map((v) => (
                    <li key={v.id_visita}><button type="button" onClick={() => {
                      // Cliente vem da visita: quem assinou a ficha é quem faz a proposta.
                      setForm((f) => ({ ...f, id_visita: v.id_visita, cliente: v.cliente || f.cliente }));
                      setVisitas([]);
                      if (v.cliente) toast(`Cliente "${v.cliente}" preenchido pela visita.`, 'success');
                    }}>
                      <strong>{v.imovel}</strong>
                      <span className="pe-imovel-end">{dataBR(v.data_visita)} · {v.corretor}{v.cliente ? ` · cliente: ${v.cliente}` : ''}</span>
                      {v.proposta_visita ? <em>proposta na visita: {v.proposta_visita}</em> : null}
                    </button></li>
                  ))}
                </ul>
              )}
            </div>

            <div className="pe-grid">
              {/* Só aparece para diretor/administrador — o servidor devolve a lista vazia
                  para gerente, que lança sempre no próprio nome. */}
              {!!gerentes.length && (
                <label className="span2">Gerente responsável pela proposta
                  <select value={form.id_gerente} onChange={set('id_gerente')}>
                    <option value="">Eu mesmo</option>
                    {gerentesOpcoes.map((g) => (
                      <option key={g.id} value={g.id}>{g.nome}{g.team ? ` · ${g.team}` : ''}</option>
                    ))}
                  </select>
                  <small className="pe-hint">
                    Define de quem é a proposta nos relatórios. Escolher o corretor abaixo
                    sobrescreve a equipe pela dele.
                  </small>
                </label>
              )}
              <label className="span2">Lançar no nome de (corretor)
                <select value={form.id_corretor} onChange={(e) => { setForm((f) => ({ ...f, id_corretor: e.target.value, id_visita: '' })); setVisitas([]); }}>
                  <option value="">Sem corretor definido</option>
                  {corretores.map((c) => <option key={c.id} value={c.id}>{c.nome}{c.team ? ` · ${c.team}` : ''}</option>)}
                </select>
              </label>
              <label>Código do imóvel<input value={form.codigo_imovel} onChange={set('codigo_imovel')} placeholder="Ex.: 12343" /></label>
              <label className="span2">Endereço<input value={form.imovel_endereco} onChange={set('imovel_endereco')} /></label>
              <label>Número<input value={form.numero} onChange={set('numero')} /></label>
              <label>Bloco<input value={form.bloco} onChange={set('bloco')} /></label>
              <label>Apto / complemento<input value={form.complemento} onChange={set('complemento')} placeholder="Apto 506" /></label>
              <label>Bairro<input value={form.bairro} onChange={set('bairro')} /></label>
              <label>Tipo<input value={form.tipo} onChange={set('tipo')} placeholder="Apartamento, casa…" /></label>
              <label>Quartos<input value={form.quartos} onChange={set('quartos')} inputMode="numeric" /></label>
              <label>Vagas<input value={form.vagas} onChange={set('vagas')} inputMode="numeric" /></label>
              <label>Área (m²)<input value={form.area} onChange={set('area')} /></label>
              {/* maxLength = 14 dígitos já formatados ("999.999.999.999,99"), o teto de Numeric(14,2). */}
              <label>Valor da proposta *<input value={form.valor} onChange={set('valor')} inputMode="numeric" placeholder="0,00" maxLength={18} required /></label>
              <label>Forma de pagamento
                <select value={form.forma_pagamento} onChange={set('forma_pagamento')}>
                  <option value="">Selecione…</option>
                  {opcoes.formas_pagamento.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                </select>
              </label>
              <label>Situação
                <select value={form.situacao} onChange={set('situacao')}>
                  {opcoes.situacoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </label>
              {ehPermuta && <label>Valor da permuta (2ª proposta) *<input value={form.valor_permuta} onChange={set('valor_permuta')} inputMode="numeric" placeholder="0,00" maxLength={18} required /></label>}
              {ehPermuta && <label className="span2">O que entra na permuta<input value={form.descricao_permuta} onChange={set('descricao_permuta')} placeholder="Ex.: apartamento menor na Asa Sul" /></label>}
              <label>Cliente<input value={form.cliente} onChange={set('cliente')} /></label>
              <label>Data da proposta<input type="date" value={form.data_proposta} onChange={set('data_proposta')} /></label>
              <label className="span3">Observação<textarea rows={3} value={form.observacao} onChange={set('observacao')} /></label>
            </div>

            <footer>
              <button type="button" onClick={() => setFormAberto(false)}>Cancelar</button>
              <button type="submit" className="pe-cta" disabled={salvando}>{salvando ? 'Salvando…' : 'Salvar proposta'}</button>
            </footer>
          </form>
        </div>
      )}

      {detalhe && (
        <div className="pe-modal-bg" onClick={() => setDetalhe(null)}>
          <div className="pe-modal" onClick={(e) => e.stopPropagation()}>
            <header className="pe-modal-head-detalhe">
              <div>
                <span className="pe-eyebrow"><i /> Proposta efetiva</span>
                <h2>{detalhe.codigo_imovel ? `Imóvel #${detalhe.codigo_imovel}` : 'Proposta'} · {detalhe.bairro || '—'}</h2>
                <small>{detalhe.imovel_endereco || 'Endereço não informado'}{detalhe.numero ? `, ${detalhe.numero}` : ''}</small>
              </div>
              <div className="pe-modal-head-acoes">
                <span className={`pe-situacao s-${detalhe.situacao}`}>{detalhe.situacao_label}</span>
                <button type="button" onClick={() => setDetalhe(null)}>✕</button>
              </div>
            </header>

            <div className="pe-detalhe-topo">
              <div className="pe-detalhe-valor">
                <span>Valor da proposta</span>
                <strong>{moeda(detalhe.valor)}</strong>
                {detalhe.valor_permuta
                  ? <small>+ permuta {moeda(detalhe.valor_permuta)} · total {moeda((detalhe.valor || 0) + detalhe.valor_permuta)}</small>
                  : <small>{detalhe.forma_pagamento_label || 'Forma de pagamento não informada'}</small>}
              </div>
              <div className="pe-detalhe-chips">
                <span className="pe-chip"><b>{detalhe.dias_em_aberto ?? '—'}</b> dias em aberto</span>
                <span className={`pe-chip ${detalhe.fechada ? '' : detalhe.alerta || ''}`}>
                  <b>{detalhe.fechada ? '—' : detalhe.dias_sem_acao ?? 0}</b> dias sem ação
                </span>
                {detalhe.valor_permuta ? <span className="pe-chip"><b>Permuta</b> 2ª proposta</span> : null}
              </div>
            </div>

            {!detalhe.fechada && detalhe.alerta && (
              <p className={`pe-faixa-alerta ${detalhe.alerta}`}>
                <Icon name="alerta" size={14} />
                {detalhe.alerta === 'critico'
                  ? `Parada há ${detalhe.dias_sem_acao} dias — precisa de uma ação do gerente.`
                  : `Sem ação há ${detalhe.dias_sem_acao} dias.`}
              </p>
            )}

            <div className="pe-detalhe-grid">
              <div><span>Proposta em</span><strong>{dataBR(detalhe.data_proposta)}</strong></div>
              {/* A data digitada quase sempre difere da de lançamento (vem retroativa), e é
                  pela de lançamento que o painel do diretor recorta o período. Mostrar as duas
                  evita o gestor comparar números que saem de datas diferentes. */}
              <div><span>Lançada em</span><strong>{dataBR(detalhe.created_at)}</strong></div>
              <div><span>Fechamento</span><strong>{dataBR(detalhe.data_fechamento)}</strong></div>
              <div><span>Corretor</span><strong>{detalhe.corretor_nome || '—'}</strong></div>
              <div><span>Gerente</span><strong>{detalhe.gerente_nome || '—'}</strong></div>
              <div><span>Cliente</span><strong>{detalhe.cliente || '—'}</strong></div>
              <div><span>Equipe</span><strong>{detalhe.team || '—'}</strong></div>
            </div>

            {detalhe.visita && (
              <div className="pe-visita-card">
                <span className="pe-visita-tag"><Icon name="relogio" size={13} /> Visita relacionada</span>
                <strong>{detalhe.visita.imovel}</strong>
                <small>
                  {dataBR(detalhe.visita.data_visita)} · {detalhe.visita.corretor}
                  {detalhe.visita.proposta_visita ? <em>proposta na visita: {detalhe.visita.proposta_visita}</em> : null}
                </small>
              </div>
            )}
            {detalhe.descricao_permuta && <p className="pe-nota"><b>Permuta:</b> {detalhe.descricao_permuta}</p>}
            {detalhe.observacao && <p className="pe-nota"><b>Observação:</b> {detalhe.observacao}</p>}

            <h3><Icon name="relogio" size={15} /> Ações <em>{(detalhe.acoes || []).length}</em></h3>
            <ul className="pe-timeline">
              {(detalhe.acoes || []).map((a) => (
                <li key={a.id}>
                  <div><strong>{a.descricao}</strong>{a.situacao_label ? <em>{a.situacao_label}</em> : null}</div>
                  <small>{a.autor_nome || '—'} · {a.created_at ? new Date(a.created_at).toLocaleString('pt-BR') : '—'}</small>
                </li>
              ))}
              {!(detalhe.acoes || []).length && <li className="pe-vazio">Nenhuma ação registrada.</li>}
            </ul>

            {podeEditar && (
              <div className="pe-nova-acao">
                <label>Registrar ação</label>
                <div>
                  <input placeholder="O que foi feito? Ex.: cliente pediu prazo até sexta" value={novaAcao.descricao} onChange={(e) => setNovaAcao((p) => ({ ...p, descricao: e.target.value }))} />
                  <select value={novaAcao.situacao} onChange={(e) => setNovaAcao((p) => ({ ...p, situacao: e.target.value }))}>
                    <option value="">Manter situação</option>
                    {opcoes.situacoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                  <button type="button" className="pe-cta" onClick={registrarAcao}>Registrar</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
