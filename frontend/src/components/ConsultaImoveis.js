import React, { useCallback, useEffect, useState } from 'react';
import { BASE } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { GraficoLinhaDupla, GraficoPizza, GraficoBarras } from './GraficosGestao';
// `GestaoModulo.css` traz as classes `gm-*` dos graficos. O bundle do CRA e unico, entao
// elas ja estariam la por causa de outra tela — mas depender disso quebraria a hora que
// aquela tela saisse do ar.
import '../assets/css/GestaoModulo.css';
import '../assets/css/ConsultaImoveis.css';

const moeda = (v) => (v == null || v === '' ? '—'
  : typeof v === 'number'
    ? v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
    : String(v));
const numero = (v) => (v == null || v === '' ? '—' : Number(v).toLocaleString('pt-BR'));
const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString('pt-BR') : '—');
// Duas casas: a media vem com a precisao do banco (`481.83333...`) e imprimir cru
// enchia o card de digitos que nao dizem nada.
const area = (v) => (v == null || v === '' ? '—'
  : `${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`);

// Situações que o cache guarda (ver sync_areas_imoview.SITUACOES).
const SITUACOES = [
  { value: 'disponivel', label: 'Disponíveis' },
  { value: 'vendido', label: 'Vendidos' },
  { value: 'saiu', label: 'Saíram do estoque' },
  { value: 'desativado', label: 'Desativados' },
  { value: 'moderacao', label: 'Em moderação' },
  { value: 'todos', label: 'Todos' },
];

// Rascunho dos filtros. Vazio = campo não enviado; o servidor ignora chave em branco.
const FILTROS_VAZIOS = {
  bairro: '', tipo: '',
  // Venda por padrao: a tela e do estoque COMERCIAL. Com "todas", o card de imoveis
  // somava 999 de venda + 53 de aluguel e dizia 1.052 — numero que a operacao nao
  // reconhece como estoque. Fica visivel no dropdown, nao escondido no servidor.
  finalidade: 'Venda', foco: '',
  valor_min: '', valor_max: '', area_min: '', area_max: '',
  quartos_min: '', vagas_min: '',
  mudou_de: '', mudou_ate: '', captado_de: '', captado_ate: '',
  // `visita_de`/`visita_ate` só valem com `visitas=com` — "nunca visitado" não tem
  // janela. `limparFiltros` zera tudo por `FILTROS_VAZIOS`, então basta estar aqui.
  visitas: '', visita_de: '', visita_ate: '', propostas: '',
  leads: '', lead_de: '', lead_ate: '',
};

const FOCOS = [
  { value: 'nao_foco', label: 'Não foco' },
  { value: 'pp', label: 'Foco PP' },
  { value: 'ac', label: 'Foco AC' },
  { value: 'pp_ac', label: 'Foco PP + AC' },
];
const focoParaValor = (f) => (f?.foco_pp && f?.foco_ac ? 'pp_ac' : f?.foco_pp ? 'pp' : f?.foco_ac ? 'ac' : 'nao_foco');

// Cor do selo de situação. O rótulo vem do Imoview em texto livre, então casa por trecho.
const classeSituacao = (s) => {
  const t = String(s || '').toLowerCase();
  if (t.includes('vend')) return 's-vendido';
  if (t.includes('lanc') || t.includes('lanç')) return 's-novo';
  return 's-disponivel';
};
const classeFoco = (label) => `f-${String(label || '').replace(/[^a-z]/gi, '').toLowerCase()}`;

/** Linha rótulo → valor dos blocos de dados. */
function Dado({ label, children }) {
  return <div className="ci-dado"><span>{label}</span><strong>{children ?? '—'}</strong></div>;
}

export default function ConsultaImoveis() {
  const toast = useToast();
  const { idCorretor } = useAuth();

  const [busca, setBusca] = useState('');
  const [termoAtivo, setTermoAtivo] = useState('');
  const [situacao, setSituacao] = useState('disponivel');
  const [lista, setLista] = useState({ itens: [], total: 0, page: 1, paginas: 1 });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const [codigoAberto, setCodigoAberto] = useState(null);
  const [detalhe, setDetalhe] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);
  const [erroDetalhe, setErroDetalhe] = useState('');
  const [focoEditado, setFocoEditado] = useState('');
  const [salvandoFoco, setSalvandoFoco] = useState(false);
  const [doc, setDoc] = useState({ matricula: '', inscricao_iptu: '' });
  const [salvandoDoc, setSalvandoDoc] = useState(false);
  // "Lancei eu": filtra pelos imoveis cuja CAPTACAO o proprio usuario lancou
  // (`fato_captacao.criado_por`). E a pergunta do estagiario: o que eu ja subi?
  const [apenasMeus, setApenasMeus] = useState(false);
  const [baixandoPdf, setBaixandoPdf] = useState(false);

  // `filtros` é o RASCUNHO (o que está nos campos); `filtrosAtivos` é o que foi
  // efetivamente buscado. Sem a separação, cada tecla digitada numa faixa de valor
  // dispararia uma consulta — foi o que já incomodou na tela de leads.
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [filtrosAtivos, setFiltrosAtivos] = useState(FILTROS_VAZIOS);
  const [painelFiltros, setPainelFiltros] = useState(false);
  const [opcoes, setOpcoes] = useState({ bairros: [], tipos: [], finalidades: [] });
  const [resumo, setResumo] = useState(null);
  const [aplicados, setAplicados] = useState(null);

  const carregar = useCallback(async (termo, page = 1, filtroSituacao = situacao,
                                      meus = apenasMeus, extras = filtrosAtivos) => {
    setCarregando(true);
    setErro('');
    try {
      const qs = new URLSearchParams({
        solicitante_id: idCorretor || '', page: String(page), situacao: filtroSituacao,
      });
      if (termo) qs.set('busca', termo);
      if (meus) qs.set('meus', '1');
      Object.entries(extras || {}).forEach(([chave, valor]) => {
        if (String(valor || '').trim()) qs.set(chave, String(valor).trim());
      });
      const r = await fetch(`${BASE}/imoveis/consulta?${qs.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao buscar imóveis');
      setLista({ itens: d.itens || [], total: d.total || 0, page: d.page || 1, paginas: d.paginas || 1 });
      setResumo(d.resumo || null);
      setAplicados(d.filtros_aplicados || null);
    } catch (e) {
      setErro(e.message || 'Erro ao buscar imóveis');
      setLista({ itens: [], total: 0, page: 1, paginas: 1 });
      setResumo(null);
      setAplicados(null);
    } finally {
      setCarregando(false);
    }
  }, [idCorretor, situacao, apenasMeus, filtrosAtivos]);

  useEffect(() => { carregar('', 1); }, [carregar]);

  // Bairros e tipos saem do catálogo, não de lista fixa: bairro novo aparece sozinho
  // quando a operação capta lá pela primeira vez.
  useEffect(() => {
    if (!idCorretor) return;
    (async () => {
      try {
        const r = await fetch(`${BASE}/imoveis/consulta/opcoes?solicitante_id=${idCorretor}`);
        const d = await r.json();
        if (r.ok && d.ok !== false) setOpcoes(d);
      } catch { /* dropdown vazio não impede a busca por texto */ }
    })();
  }, [idCorretor]);

  // Gráficos: mesmo recorte da listagem, endpoint separado. Ficam num `useEffect`
  // próprio para a tabela aparecer sem esperar as agregações, que são mais caras.
  const [graficos, setGraficos] = useState(null);
  const [carregandoGraficos, setCarregandoGraficos] = useState(false);
  const [painelGraficos, setPainelGraficos] = useState(true);

  const carregarGraficos = useCallback(async (termo, filtroSituacao, meus, extras) => {
    if (!idCorretor) return;
    setCarregandoGraficos(true);
    try {
      const qs = new URLSearchParams({
        solicitante_id: idCorretor, situacao: filtroSituacao,
      });
      if (termo) qs.set('busca', termo);
      if (meus) qs.set('meus', '1');
      Object.entries(extras || {}).forEach(([chave, valor]) => {
        if (String(valor || '').trim()) qs.set(chave, String(valor).trim());
      });
      const r = await fetch(`${BASE}/imoveis/consulta/graficos?${qs.toString()}`);
      const d = await r.json();
      setGraficos(r.ok && d.ok !== false ? d : null);
    } catch {
      setGraficos(null);
    } finally {
      setCarregandoGraficos(false);
    }
  }, [idCorretor]);

  useEffect(() => {
    if (painelGraficos) carregarGraficos(termoAtivo, situacao, apenasMeus, filtrosAtivos);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [painelGraficos, termoAtivo, situacao, apenasMeus, filtrosAtivos, carregarGraficos]);

  const aplicarFiltros = () => {
    setFiltrosAtivos(filtros);
    carregar(termoAtivo, 1, situacao, apenasMeus, filtros);
  };

  const limparFiltros = () => {
    setFiltros(FILTROS_VAZIOS);
    setFiltrosAtivos(FILTROS_VAZIOS);
    carregar(termoAtivo, 1, situacao, apenasMeus, FILTROS_VAZIOS);
  };

  const filtrosLigados = Object.values(filtrosAtivos).filter((v) => String(v || '').trim()).length;

  const baixarPdfImovel = async (codigo) => {
    if (baixandoPdf || !codigo) return;
    setBaixandoPdf(true);
    try {
      const r = await fetch(`${BASE}/imoveis/pdf/download?imovel_id=${encodeURIComponent(codigo)}`);
      if (!r.ok) throw new Error('Não consegui gerar o relatório deste imóvel.');
      const blob = await r.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = `imovel-${codigo}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
    } catch (err) {
      toast(err.message || 'Não consegui gerar o relatório.', 'error');
    } finally {
      setBaixandoPdf(false);
    }
  };

  const buscar = (e) => {
    e?.preventDefault();
    setTermoAtivo(busca.trim());
    carregar(busca.trim(), 1);
  };

  const abrir = useCallback(async (codigo) => {
    setCodigoAberto(codigo);
    setDetalhe(null);
    setErroDetalhe('');
    setCarregandoDetalhe(true);
    try {
      const r = await fetch(`${BASE}/imoveis/consulta/${encodeURIComponent(codigo)}?solicitante_id=${idCorretor}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao carregar o imóvel');
      setDetalhe(d);
      setFocoEditado(focoParaValor(d.interno?.foco));
      setDoc({
        matricula: d.interno?.documentacao?.matricula || '',
        inscricao_iptu: d.interno?.documentacao?.inscricao_iptu || '',
      });
    } catch (e) {
      setErroDetalhe(e.message || 'Erro ao carregar o imóvel');
    } finally {
      setCarregandoDetalhe(false);
    }
  }, [idCorretor]);

  const salvarFoco = async () => {
    if (!detalhe) return;
    setSalvandoFoco(true);
    try {
      const r = await fetch(`${BASE}/imoveis/consulta/${encodeURIComponent(detalhe.codigo)}?solicitante_id=${idCorretor}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ foco: focoEditado }),
      });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao salvar');
      toast(`Foco atualizado para ${d.foco.label}.`, 'success');
      setDetalhe((prev) => ({ ...prev, interno: { ...prev.interno, foco: { ...prev.interno.foco, ...d.foco, origem: 'manual' } } }));
      carregar(termoAtivo, lista.page);   // o rótulo da lista acompanha
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSalvandoFoco(false);
    }
  };

  const salvarDoc = async () => {
    if (!detalhe) return;
    setSalvandoDoc(true);
    try {
      const r = await fetch(`${BASE}/imoveis/consulta/${encodeURIComponent(detalhe.codigo)}?solicitante_id=${idCorretor}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(doc),
      });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao salvar');
      // O Trello e best-effort: a gravacao na base ja aconteceu. Avisa quando o cartao
      // nao pode ser atualizado em vez de deixar o usuario achar que sincronizou.
      if (d.trello?.ok && d.trello?.matricula_preservada) {
        toast('Salvo. No Trello, a matrícula foi mantida como "Cessão de Direitos".', 'success');
      } else if (d.trello?.ok) {
        toast('Matrícula e inscrição atualizadas — cartão do Trello também.', 'success');
      } else if (d.trello) {
        toast(`Salvo na base. Trello não atualizado: ${d.trello.motivo || 'erro'}.`, 'error');
      } else {
        toast('Matrícula e inscrição atualizadas.', 'success');
      }
      setDetalhe((prev) => ({
        ...prev,
        interno: { ...prev.interno, documentacao: { ...prev.interno.documentacao, ...doc } },
      }));
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSalvandoDoc(false);
    }
  };

  const imoview = detalhe?.imoview;
  const interno = detalhe?.interno;
  const focoMudou = interno && focoEditado !== focoParaValor(interno.foco);
  const docMudou = interno && (
    doc.matricula !== (interno.documentacao?.matricula || '')
    || doc.inscricao_iptu !== (interno.documentacao?.inscricao_iptu || '')
  );

  return (
    <div className="ci-page">
      <header className="ci-hero">
        <div>
          <span className="ci-eyebrow"><i /> Módulo · Imóveis</span>
          <h1>Gestão de imóveis</h1>
          <p>
            Estoque, saídas e foco num lugar só. Recorte por situação, período, bairro,
            faixa de valor ou metragem — e veja o VGV e o preço médio do recorte inteiro,
            não só da página.
          </p>
        </div>
      </header>

      <form className="ci-busca" onSubmit={buscar}>
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Código do imóvel, endereço, bairro ou tipo — Enter para buscar"
          aria-label="Buscar imóvel"
        />
        <button type="submit" className="ci-cta">Buscar</button>
        {termoAtivo && (
          <button type="button" className="ci-limpar" onClick={() => { setBusca(''); setTermoAtivo(''); carregar('', 1); }}>
            Limpar
          </button>
        )}
        <div className="ci-chips">
          {SITUACOES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={situacao === s.value ? 'is-ativo' : ''}
              onClick={() => { setSituacao(s.value); carregar(termoAtivo, 1, s.value, apenasMeus); }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Alternador separado dos chips de situacao de proposito: as duas coisas se
            combinam ("meus lancamentos, entre os vendidos"), nao se excluem. */}
        <button
          type="button"
          className={`ci-meus ${apenasMeus ? 'is-ativo' : ''}`}
          aria-pressed={apenasMeus}
          title="Imóveis cuja captação foi lançada por você"
          onClick={() => { const v = !apenasMeus; setApenasMeus(v); carregar(termoAtivo, 1, situacao, v); }}
        >
          Lançado por mim
        </button>
        <button
          type="button"
          className={`ci-meus ${painelFiltros || filtrosLigados ? 'is-ativo' : ''}`}
          aria-pressed={painelFiltros}
          onClick={() => setPainelFiltros((v) => !v)}
        >
          Filtros{filtrosLigados ? ` (${filtrosLigados})` : ''}
        </button>
        <button
          type="button"
          className={`ci-meus ${painelGraficos ? 'is-ativo' : ''}`}
          aria-pressed={painelGraficos}
          onClick={() => setPainelGraficos((v) => !v)}
        >
          Gráficos
        </button>
        <span className="ci-contador">
          {carregando ? 'Buscando…' : `${numero(lista.total)} imóve${lista.total === 1 ? 'l' : 'is'}`}
          {termoAtivo ? ` para “${termoAtivo}”` : ''}
          {apenasMeus ? ' que você lançou' : ''}
        </span>
      </form>

      {painelFiltros && (
        <section className="ci-filtros">
          <div className="ci-filtros-grid">
            <label>Bairro
              <select value={filtros.bairro}
                onChange={(e) => setFiltros((f) => ({ ...f, bairro: e.target.value }))}>
                <option value="">Todos os bairros</option>
                {(opcoes.bairros || []).map((b2) => <option key={b2} value={b2}>{b2}</option>)}
              </select>
            </label>
            <label>Tipo
              <select value={filtros.tipo}
                onChange={(e) => setFiltros((f) => ({ ...f, tipo: e.target.value }))}>
                <option value="">Todos os tipos</option>
                {(opcoes.tipos || []).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label>Finalidade
              <select value={filtros.finalidade}
                onChange={(e) => setFiltros((f) => ({ ...f, finalidade: e.target.value }))}>
                <option value="">Todas</option>
                {(opcoes.finalidades || []).map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </label>
            <label>Foco
              <select value={filtros.foco}
                onChange={(e) => setFiltros((f) => ({ ...f, foco: e.target.value }))}>
                <option value="">Qualquer</option>
                <option value="qualquer">Só os de foco</option>
                <option value="pp">Foco PP</option>
                <option value="ac">Foco AC</option>
                <option value="pp_ac">Foco PP + AC</option>
                <option value="nao_foco">Não foco</option>
              </select>
            </label>

            <label>Valor de
              <input type="number" value={filtros.valor_min} placeholder="0"
                onChange={(e) => setFiltros((f) => ({ ...f, valor_min: e.target.value }))} />
            </label>
            <label>Valor até
              <input type="number" value={filtros.valor_max} placeholder="sem teto"
                onChange={(e) => setFiltros((f) => ({ ...f, valor_max: e.target.value }))} />
            </label>
            <label>Área de (m²)
              <input type="number" value={filtros.area_min}
                onChange={(e) => setFiltros((f) => ({ ...f, area_min: e.target.value }))} />
            </label>
            <label>Área até (m²)
              <input type="number" value={filtros.area_max}
                onChange={(e) => setFiltros((f) => ({ ...f, area_max: e.target.value }))} />
            </label>

            <label>Quartos (mín.)
              <input type="number" min="0" value={filtros.quartos_min}
                onChange={(e) => setFiltros((f) => ({ ...f, quartos_min: e.target.value }))} />
            </label>
            <label>Vagas (mín.)
              <input type="number" min="0" value={filtros.vagas_min}
                onChange={(e) => setFiltros((f) => ({ ...f, vagas_min: e.target.value }))} />
            </label>

            <label>Mudou de situação — de
              <input type="date" value={filtros.mudou_de}
                onChange={(e) => setFiltros((f) => ({ ...f, mudou_de: e.target.value }))} />
            </label>
            <label>até
              <input type="date" value={filtros.mudou_ate}
                onChange={(e) => setFiltros((f) => ({ ...f, mudou_ate: e.target.value }))} />
            </label>

            {/* Visitas: 406 dos 12.450 imóveis já receberam alguém (3%) — é por ser
                pouco que interessa isolar. As datas ficam desabilitadas fora de
                "Com visita", para não sugerir um recorte que o servidor ignora. */}
            {/* "Tem lead" e "tem lead EM ANDAMENTO" são perguntas diferentes: 1.651
                imóveis do catálogo tiveram todos os leads arquivados. Por "qualquer"
                eles pareceriam procurados, quando ninguém está mais atrás deles. */}
            <label>Leads
              <select value={filtros.leads}
                onChange={(e) => setFiltros((f) => ({ ...f, leads: e.target.value }))}>
                <option value="">Todos</option>
                <option value="qualquer">Com lead (qualquer)</option>
                <option value="ativos">Com lead em andamento</option>
                <option value="arquivados">Só leads arquivados</option>
                <option value="sem">Sem nenhum lead</option>
              </select>
            </label>
            <label>Lead — de
              <input type="date" value={filtros.lead_de}
                disabled={!filtros.leads || filtros.leads === 'sem'}
                title={filtros.leads && filtros.leads !== 'sem' ? '' : 'Não se aplica a "Sem nenhum lead"'}
                onChange={(e) => setFiltros((f) => ({ ...f, lead_de: e.target.value }))} />
            </label>
            <label>até
              <input type="date" value={filtros.lead_ate}
                disabled={!filtros.leads || filtros.leads === 'sem'}
                onChange={(e) => setFiltros((f) => ({ ...f, lead_ate: e.target.value }))} />
            </label>

            {/* Propostas: 22 dos 12.450 imóveis já receberam alguma (15 abertas, 7
                fechadas). "Aberta" usa a mesma constante da Visão do Diretor — vendido e
                cancelado encerram, aceita continua aberta. */}
            <label>Propostas
              <select value={filtros.propostas}
                onChange={(e) => setFiltros((f) => ({ ...f, propostas: e.target.value }))}>
                <option value="">Todos</option>
                <option value="qualquer">Com proposta (qualquer)</option>
                <option value="abertas">Com proposta em aberto</option>
                <option value="fechadas">Com proposta fechada</option>
                <option value="sem">Sem nenhuma proposta</option>
              </select>
            </label>
            <label>Visitas
              <select value={filtros.visitas}
                onChange={(e) => setFiltros((f) => ({ ...f, visitas: e.target.value }))}>
                <option value="">Todos</option>
                <option value="com">Com visita</option>
                <option value="sem">Nunca visitado</option>
              </select>
            </label>
            <label>Visitado — de
              <input type="date" value={filtros.visita_de} disabled={filtros.visitas !== 'com'}
                title={filtros.visitas === 'com' ? '' : 'Só vale com "Com visita" selecionado'}
                onChange={(e) => setFiltros((f) => ({ ...f, visita_de: e.target.value }))} />
            </label>
            <label>até
              <input type="date" value={filtros.visita_ate} disabled={filtros.visitas !== 'com'}
                onChange={(e) => setFiltros((f) => ({ ...f, visita_ate: e.target.value }))} />
            </label>

            <label>Captado — de
              <input type="date" value={filtros.captado_de}
                onChange={(e) => setFiltros((f) => ({ ...f, captado_de: e.target.value }))} />
            </label>
            <label>até
              <input type="date" value={filtros.captado_ate}
                onChange={(e) => setFiltros((f) => ({ ...f, captado_ate: e.target.value }))} />
            </label>
          </div>

          <p className="ci-filtros-dica">
            <strong>Vendidos no período:</strong> escolha a situação <em>Vendidos</em> nos
            chips acima e preencha <em>Mudou de situação</em>. A data é o
            <code> datahoraultimasituacao </code> do Imoview — não existe “data da venda” na
            API deles. Se o imóvel mudar de situação outra vez, essa data é sobrescrita.
          </p>

          <div className="ci-filtros-acoes">
            <button type="button" className="ci-limpar" onClick={limparFiltros}>
              Limpar filtros
            </button>
            <button type="button" className="ci-cta" onClick={aplicarFiltros}>
              Aplicar filtros
            </button>
          </div>
        </section>
      )}

      {/* O que o servidor de fato aplicou. Sem isto, filtro herdado de estado anterior
          some da vista: o dropdown mostra "Todos os bairros" e o recorte continua ativo. */}
      {aplicados && !carregando && (
        <p className="ci-aplicados">
          <b>Recorte:</b>{' '}
          {Object.entries(aplicados)
            .filter(([k, v]) => v !== null && v !== false && v !== '')
            .map(([k, v]) => `${k}=${v}`)
            .join(' · ')}
        </p>
      )}

      {resumo && !carregando && (
        <section className="ci-resumo">
          <div><span>Imóveis</span><strong>{numero(resumo.total)}</strong></div>
          <div>
            <span>VGV do recorte</span>
            <strong>{moeda(resumo.vgv)}</strong>
            <small>{numero(resumo.com_valor)} com valor</small>
          </div>
          <div>
            <span>Ticket médio</span>
            <strong>{moeda(resumo.ticket_medio)}</strong>
          </div>
          <div>
            <span>Área média</span>
            <strong>{area(resumo.area_media)}</strong>
          </div>
          {/* Publicados = com ao menos um portal ATIVO agora. Portal retirado não conta:
              o imóvel já esteve no ar e não está mais, que é a diferença que importa. */}
          <div className={resumo.portais?.sem_portal ? 'is-alerta' : ''}>
            <span>Nos portais</span>
            <strong>{numero(resumo.portais?.publicados)}</strong>
            <small>
              {numero(resumo.portais?.sem_portal)} fora
              {resumo.portais?.sem_dado
                ? ` · ${numero(resumo.portais.sem_dado)} sem dado`
                : ''}
            </small>
          </div>
          {(resumo.portais?.por_destaque || []).map((d) => (
            <div key={d.nivel}>
              <span>{d.rotulo}</span>
              <strong>{numero(d.total)}</strong>
              <small>
                {resumo.portais.publicados
                  ? `${Math.round((d.total / resumo.portais.publicados) * 100)}% dos publicados`
                  : ''}
              </small>
            </div>
          ))}
          <div>
            <span>Site próprio</span>
            <strong>{numero(resumo.portais?.no_site_proprio)}</strong>
          </div>
          <div>
            <span>Preço por m²</span>
            <strong>{moeda(resumo.valor_m2_medio)}</strong>
            <small>{numero(resumo.com_area_e_valor)} com área</small>
          </div>
        </section>
      )}

      {painelGraficos && (
        <section className="ci-graficos">
          {carregandoGraficos && <p className="ci-estado">Montando gráficos…</p>}
          {!carregandoGraficos && !graficos && (
            <p className="ci-estado">Não consegui montar os gráficos deste recorte.</p>
          )}
          {!carregandoGraficos && graficos && (
            <>
              <article className="gm-grafico ci-grafico--largo">
                <header>
                  <div>
                    <h4>Entradas e saídas por mês</h4>
                    <p>
                      Entrada é a data de cadastro no Imoview; saída é a mudança para
                      vendido, desativado ou em reforma. Não responde aos filtros de
                      recorte — é o fluxo do catálogo inteiro.
                    </p>
                  </div>
                </header>
                <GraficoLinhaDupla
                  pontos={graficos.fluxo_mensal}
                  series={[
                    { campo: 'entradas', rotulo: 'Entradas', cor: '#1b6340' },
                    { campo: 'saidas', rotulo: 'Saídas', cor: '#c4005a' },
                  ]}
                  rotuloAria="Entradas e saídas de imóveis por mês"
                />
              </article>

              <article className="gm-grafico">
                <header><div><h4>Situação</h4><p>Onde o estoque está</p></div></header>
                <GraficoPizza dados={graficos.por_situacao} centroRotulo="imóveis" />
              </article>

              <article className="gm-grafico">
                <header><div><h4>Foco</h4><p>PP, AC ou fora do foco</p></div></header>
                <GraficoPizza dados={graficos.por_foco} centroRotulo="imóveis" />
              </article>

              <article className="gm-grafico">
                <header><div><h4>Tipo</h4><p>Composição do estoque</p></div></header>
                <GraficoPizza dados={graficos.por_tipo} centroRotulo="imóveis" />
              </article>

              <article className="gm-grafico">
                <header><div><h4>Faixa de valor</h4><p>Distribuição de preço</p></div></header>
                <GraficoBarras dados={graficos.por_faixa_valor} sufixo="imóvel(is)" />
              </article>

              <article className="gm-grafico">
                <header><div><h4>Bairro</h4><p>Os 10 maiores do recorte</p></div></header>
                <GraficoBarras dados={graficos.por_bairro} sufixo="imóvel(is)" />
              </article>

              <article className="gm-grafico">
                <header><div><h4>Finalidade</h4><p>Venda ou aluguel</p></div></header>
                <GraficoBarras dados={graficos.por_finalidade} sufixo="imóvel(is)" />
              </article>
            </>
          )}
        </section>
      )}

      {erro && <p className="ci-estado ci-estado--erro">{erro}</p>}
      {!erro && carregando && <p className="ci-estado">Carregando imóveis…</p>}
      {!erro && !carregando && !lista.itens.length && (
        <p className="ci-estado">
          {apenasMeus
            ? 'Você ainda não lançou nenhuma captação com esse filtro. O “Lancei eu” usa quem registrou a captação no Lançar Imóvel.'
            : `Nenhum imóvel encontrado${termoAtivo ? ` para “${termoAtivo}”` : ''}. Tente outro código ou parte do endereço.`}
        </p>
      )}

      <section className="ci-grid">
        {lista.itens.map((item) => (
          <button type="button" key={item.codigo} className="ci-card" onClick={() => abrir(item.codigo)}>
            <div className="ci-card-topo">
              <strong>#{item.codigo}</strong>
              <span className={`ci-foco ${classeFoco(item.foco_label)}`}>{item.foco_label}</span>
            </div>
            <div className="ci-card-situacao">
              <span className={`ci-sit ${classeSituacao(item.situacao)}`}>{item.situacao || 'Sem situação'}</span>
            </div>
            <p className="ci-card-endereco">{item.endereco || item.bairro || 'Endereço ainda não sincronizado'}</p>
            <p className="ci-card-bairro">{[item.bairro, item.tipo].filter(Boolean).join(' · ')}</p>
            <div className="ci-card-specs">
              <span>{item.quartos ? `${item.quartos} qtos` : '—'}</span>
              <span>{item.vagas ? `${item.vagas} vagas` : '—'}</span>
              <span>{area(item.area)}</span>
            </div>
            <div className="ci-card-rodape">
              <b>{moeda(item.valor)}</b>
              {item.tem_captacao && <em title="Tem captação registrada na inteligência">captação</em>}
            </div>
          </button>
        ))}
      </section>

      {lista.paginas > 1 && (
        <div className="ci-paginacao">
          <button type="button" disabled={lista.page <= 1} onClick={() => carregar(termoAtivo, lista.page - 1)}>← Anterior</button>
          <span>Página <b>{lista.page}</b> de {lista.paginas}</span>
          <button type="button" disabled={lista.page >= lista.paginas} onClick={() => carregar(termoAtivo, lista.page + 1)}>Próxima →</button>
        </div>
      )}

      {codigoAberto && (
        <div className="ci-modal-bg" onClick={() => setCodigoAberto(null)}>
          <div className="ci-modal" onClick={(e) => e.stopPropagation()}>
            <header className="ci-modal-topo">
              <div className="ci-modal-titulo">
                <span className="ci-eyebrow"><i /> Imóvel #{codigoAberto}</span>
                <h2>{imoview?.endereco || (carregandoDetalhe ? 'Carregando…' : `Imóvel ${codigoAberto}`)}</h2>
                <small>{[imoview?.bairro || interno?.captacao?.bairro, imoview?.tipo].filter(Boolean).join(' · ')}</small>
                {detalhe && (
                  <div className="ci-modal-chips">
                    {imoview?.situacao && (
                      <span className={`ci-sit ${classeSituacao(imoview.situacao)}`}>{imoview.situacao}</span>
                    )}
                    {interno?.foco?.label && (
                      <span className={`ci-foco ${classeFoco(interno.foco.label)}`}>{interno.foco.label}</span>
                    )}
                    {imoview?.valores?.Valor && <span className="ci-modal-valor">{imoview.valores.Valor}</span>}
                  </div>
                )}
              </div>
              <div className="ci-modal-acoes">
                {/* Relatorio de visitas do imovel: quem visitou, quando e o que respondeu.
                    Vai por `fetch` como blob porque a API exige X-API-KEY, injetado no
                    `fetch` global — um `<a href>` nao passa pelo interceptor e leva 401. */}
                <button type="button" className="ci-cta" disabled={baixandoPdf}
                  onClick={() => baixarPdfImovel(codigoAberto)}>
                  {baixandoPdf ? 'Gerando…' : 'PDF de visitas'}
                </button>
                <button type="button" className="ci-fechar" onClick={() => setCodigoAberto(null)} aria-label="Fechar">✕</button>
              </div>
            </header>

            {carregandoDetalhe && <p className="ci-estado">Carregando dados do imóvel…</p>}
            {erroDetalhe && <p className="ci-estado ci-estado--erro">{erroDetalhe}</p>}

            {detalhe && (
              <div className="ci-blocos">
                <section className="ci-bloco ci-bloco--crm">
                  <h3>Dados do imóvel <em>Imoview · só leitura</em></h3>
                  {!imoview && (
                    <p className="ci-nota">
                      Este imóvel ainda não foi sincronizado com o catálogo do Imoview — a varredura roda uma vez por dia.
                      Enquanto isso, os dados abaixo vêm do lançamento (bloco verde).
                    </p>
                  )}
                  {imoview && !imoview.ao_vivo && (
                    <p className="ci-nota">Imóvel fora do catálogo ativo — mostrando a última captura{imoview?.capturado_em ? ` de ${dataBR(imoview.capturado_em)}` : ''}.</p>
                  )}
                  {imoview && (
                    <>
                      <div className="ci-dados">
                        <Dado label="Código">{imoview.codigo}</Dado>
                        <Dado label="Tipo">{imoview.tipo}</Dado>
                        <Dado label="Destinação">{imoview.destinacao}</Dado>
                        <Dado label="Finalidade">{imoview.finalidade}</Dado>
                        <Dado label="Situação">{imoview.situacao}</Dado>
                        <Dado label="Destaque no portal">{imoview.destaque}</Dado>
                        <Dado label="Edifício">{imoview.edificio}</Dado>
                        <Dado label="Endereço">{[imoview.endereco, imoview.numero !== 'S/N' ? imoview.numero : null].filter(Boolean).join(', ')}</Dado>
                        <Dado label="Bloco / apto">{[imoview.bloco, imoview.complemento].filter(Boolean).join(' · ') || '—'}</Dado>
                        <Dado label="Bairro">{[imoview.bairro, imoview.cidade, imoview.estado].filter(Boolean).join(' · ')}</Dado>
                      </div>

                      {!!Object.keys(imoview.caracteristicas || {}).length && (
                        <>
                          <h4 className="ci-subtitulo">Características</h4>
                          <div className="ci-dados">
                            {Object.entries(imoview.caracteristicas).map(([k, v]) => <Dado key={k} label={k}>{v}</Dado>)}
                          </div>
                        </>
                      )}

                      {!!Object.keys(imoview.valores || {}).length && (
                        <>
                          <h4 className="ci-subtitulo">Valores</h4>
                          <div className="ci-dados">
                            {Object.entries(imoview.valores).map(([k, v]) => <Dado key={k} label={k}>{v}</Dado>)}
                          </div>
                        </>
                      )}

                      {!!Object.keys(imoview.gestao || {}).length && (
                        <>
                          <h4 className="ci-subtitulo">Gestão do anúncio</h4>
                          <div className="ci-dados">
                            {Object.entries(imoview.gestao).map(([k, v]) => <Dado key={k} label={k}>{v}</Dado>)}
                          </div>
                        </>
                      )}

                      {!!imoview.extras?.length && (
                        <>
                          <h4 className="ci-subtitulo">Diferenciais</h4>
                          <div className="ci-extras">{imoview.extras.map((e) => <span key={e}>{e}</span>)}</div>
                        </>
                      )}

                      <div className="ci-links">
                        {imoview.urlvideo && <a href={imoview.urlvideo} target="_blank" rel="noreferrer">▶ Vídeo</a>}
                        {imoview.urlpublica && <a href={imoview.urlpublica} target="_blank" rel="noreferrer">🌐 Anúncio</a>}
                        {imoview.latitude && imoview.longitude && (
                          <a href={`https://www.google.com/maps?q=${imoview.latitude},${imoview.longitude}`} target="_blank" rel="noreferrer">📍 Mapa</a>
                        )}
                      </div>

                      {imoview.descricao && imoview.descricao !== '//' && (
                        <p className="ci-descricao">{imoview.descricao}</p>
                      )}
                    </>
                  )}
                  <p className="ci-nota ci-nota--fraca">Para alterar qualquer campo acima, edite no Imoview.</p>
                </section>

                <section className="ci-bloco ci-bloco--interno">
                  <h3>Dados internos <em>banco · editável</em></h3>

                  <div className="ci-foco-editor">
                    <label>Foco</label>
                    <select value={focoEditado} onChange={(e) => setFocoEditado(e.target.value)}>
                      {FOCOS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                    </select>
                    <button type="button" className="ci-cta" disabled={!focoMudou || salvandoFoco} onClick={salvarFoco}>
                      {salvandoFoco ? 'Salvando…' : 'Salvar foco'}
                    </button>
                    {interno?.foco?.origem && <span className="ci-tag">registrado: {interno.foco.origem}</span>}
                  </div>

                  {/* Matrícula e inscrição não vêm do CRM: são digitadas no lançamento
                      (iam só p/ o Sheets e o Trello) e ficam editáveis aqui. */}
                  <div className="ci-doc-editor">
                    <label>
                      <span>Matrícula</span>
                      <input
                        value={doc.matricula}
                        onChange={(e) => setDoc((d) => ({ ...d, matricula: e.target.value }))}
                        placeholder="Nº da matrícula no cartório"
                        disabled={interno?.documentacao?.editavel === false}
                      />
                    </label>
                    <label>
                      <span>Inscrição IPTU</span>
                      <input
                        value={doc.inscricao_iptu}
                        onChange={(e) => setDoc((d) => ({ ...d, inscricao_iptu: e.target.value }))}
                        placeholder="Inscrição do imóvel"
                        disabled={interno?.documentacao?.editavel === false}
                      />
                    </label>
                    <button type="button" className="ci-cta" disabled={!docMudou || salvandoDoc} onClick={salvarDoc}>
                      {salvandoDoc ? 'Salvando…' : 'Salvar'}
                    </button>
                  </div>
                  {interno?.documentacao?.trello_url && (
                    <p className="ci-nota ci-nota--fraca">
                      Cartão no Trello:{' '}
                      <a href={interno.documentacao.trello_url} target="_blank" rel="noreferrer">
                        {interno.documentacao.trello_url}
                      </a>
                    </p>
                  )}
                  {interno?.documentacao?.editavel === false && (
                    <p className="ci-nota">Imóvel fora do catálogo — matrícula e inscrição só podem ser gravadas depois que a varredura do Imoview trouxer o imóvel.</p>
                  )}

                  <div className="ci-dados">
                    <Dado label="Captadores">{interno?.captacao?.captadores?.map((c) => c.nome).join(', ')}</Dado>
                    <Dado label="Entrada da captação">{dataBR(interno?.captacao?.data_entrada)}</Dado>
                    <Dado label="Valor na captação">{moeda(interno?.captacao?.valor)}</Dado>
                    <Dado label="Comissão">{interno?.captacao?.comissao_pct ? `${interno.captacao.comissao_pct}%` : '—'}</Dado>
                    <Dado label="No estoque de">{dataBR(interno?.estoque?.data_estoque)}</Dado>
                    <Dado label="Exclusivo">{interno?.estoque?.exclusivo}</Dado>
                    <Dado label="Publicação">{interno?.estoque?.publicacao_na_internet}</Dado>
                    <Dado label="Saiu do estoque">{interno?.saida ? `${dataBR(interno.saida.data_saida)} — ${interno.saida.motivo || 'sem motivo'}` : '—'}</Dado>
                  </div>
                </section>

                <section className="ci-bloco">
                  <h3>Desempenho <em>mídia, visitas e propostas</em></h3>
                  <div className="ci-dados">
                    <Dado label="Acessos (DFImóveis)">{numero(interno?.midia?.acessos)}</Dado>
                    <Dado label="Impressões">{numero(interno?.midia?.impressoes)}</Dado>
                    <Dado label="Interações">{numero(interno?.midia?.leads)}</Dado>
                    <Dado label="Relatório de">{dataBR(interno?.midia?.data_relatorio)}</Dado>
                    <Dado label="Visitas">{numero(interno?.visitas?.total)}</Dado>
                    <Dado label="Última visita">{dataBR(interno?.visitas?.ultima)}</Dado>
                    <Dado label="Propostas efetivas">
                      {interno?.propostas_resumo?.total
                        ? `${interno.propostas_resumo.total} (${interno.propostas_resumo.abertas} em aberto)`
                        : '—'}
                    </Dado>
                    <Dado label="Maior proposta">{moeda(interno?.propostas_resumo?.maior_valor)}</Dado>
                    {/* Leads vêm do espelho do C2S pelo código que o cliente citou.
                        Arquivados aparecem à parte: 18 leads com 13 arquivados não é a
                        mesma procura que 18 em andamento. */}
                    <Dado label="Leads recebidos">
                      {interno?.leads?.total
                        ? `${interno.leads.total} (${interno.leads.arquivados} arquivados)`
                        : '—'}
                    </Dado>
                    <Dado label="1º / último lead">
                      {interno?.leads?.total
                        ? `${dataBR(interno.leads.primeiro)} — ${dataBR(interno.leads.ultimo)}`
                        : '—'}
                    </Dado>
                    <Dado label="Venda">{interno?.venda ? `${dataBR(interno.venda.data)} — ${moeda(interno.venda.valor)}` : '—'}</Dado>
                  </div>

                  {(interno?.leads?.por_origem || []).length > 0 && (
                    <>
                      <h4 className="ci-sub">Leads por origem</h4>
                      <div className="ci-origens">
                        {interno.leads.por_origem.map((o) => (
                          <div key={o.origem}>
                            <span>{o.origem}</span>
                            <strong>{o.total}</strong>
                            <small>
                              {Math.round((o.total / interno.leads.total) * 100)}%
                            </small>
                          </div>
                        ))}
                      </div>
                    </>
                  )}


                  {!!interno?.visitas?.itens?.length && (
                    <table className="ci-tabela">
                      <thead><tr><th>Visita</th><th>Data</th><th>Proposta</th></tr></thead>
                      <tbody>
                        {interno.visitas.itens.slice(0, 8).map((v) => (
                          <tr key={v.id_visita}><td>{v.id_visita}</td><td>{dataBR(v.data)}</td><td>{v.proposta || '—'}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {!!interno?.propostas?.length && (
                    <table className="ci-tabela">
                      <thead><tr><th>Proposta</th><th>Valor</th><th>Situação</th><th>Data</th></tr></thead>
                      <tbody>
                        {interno.propostas.map((p) => (
                          <tr key={p.id}><td>{p.corretor || '—'}</td><td>{moeda(p.valor)}</td><td>{p.situacao}</td><td>{dataBR(p.data_proposta)}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </section>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
