import React, { useCallback, useEffect, useState } from 'react';
import { BASE } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import '../assets/css/ConsultaImoveis.css';

const moeda = (v) => (v == null || v === '' ? '—'
  : typeof v === 'number'
    ? v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
    : String(v));
const numero = (v) => (v == null || v === '' ? '—' : Number(v).toLocaleString('pt-BR'));
const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString('pt-BR') : '—');
const area = (v) => (v == null || v === '' ? '—' : `${String(v).replace('.', ',')} m²`);

// Situações que o cache guarda (ver sync_areas_imoview.SITUACOES).
const SITUACOES = [
  { value: 'disponivel', label: 'Disponíveis' },
  { value: 'vendido', label: 'Vendidos' },
  { value: 'todos', label: 'Todos' },
];

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

  const carregar = useCallback(async (termo, page = 1, filtroSituacao = situacao, meus = apenasMeus) => {
    setCarregando(true);
    setErro('');
    try {
      const qs = new URLSearchParams({
        solicitante_id: idCorretor || '', page: String(page), situacao: filtroSituacao,
      });
      if (termo) qs.set('busca', termo);
      if (meus) qs.set('meus', '1');
      const r = await fetch(`${BASE}/imoveis/consulta?${qs.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || 'Erro ao buscar imóveis');
      setLista({ itens: d.itens || [], total: d.total || 0, page: d.page || 1, paginas: d.paginas || 1 });
    } catch (e) {
      setErro(e.message || 'Erro ao buscar imóveis');
      setLista({ itens: [], total: 0, page: 1, paginas: 1 });
    } finally {
      setCarregando(false);
    }
  }, [idCorretor, situacao, apenasMeus]);

  useEffect(() => { carregar('', 1); }, [carregar]);

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
      toast('Matrícula e inscrição atualizadas.', 'success');
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
          <span className="ci-eyebrow"><i /> Consulta · Imóveis</span>
          <h1>Consulta de imóveis</h1>
          <p>Busque por código ou endereço e veja, numa tela só, o que o CRM tem e o que a inteligência registrou.</p>
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
          Lancei eu
        </button>
        <span className="ci-contador">
          {carregando ? 'Buscando…' : `${numero(lista.total)} imóve${lista.total === 1 ? 'l' : 'is'}`}
          {termoAtivo ? ` para “${termoAtivo}”` : ''}
          {apenasMeus ? ' que você lançou' : ''}
        </span>
      </form>

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
              <button type="button" className="ci-fechar" onClick={() => setCodigoAberto(null)} aria-label="Fechar">✕</button>
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
                    <Dado label="Propostas efetivas">{numero(interno?.propostas?.length)}</Dado>
                    <Dado label="Venda">{interno?.venda ? `${dataBR(interno.venda.data)} — ${moeda(interno.venda.valor)}` : '—'}</Dado>
                  </div>

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
