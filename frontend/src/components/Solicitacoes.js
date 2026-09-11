import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BASE } from '../services/api';
import '../assets/css/Solicitacoes.css';

const TIPOS = ['Ônus', 'Parecer Jurídico', 'Troca de Titularidade', 'Celer'];
const EQUIPES = ['AGEF', 'AGUIA', 'LOTUS', 'PRIME', 'SENNA', 'NOVA UNIÃO', 'Controle de Qualidade', 'LIDER'];
const FINALIDADES = { Real: ['Venda', 'Pós-venda'], 'Cópia': ['Captação (Apenas para o CQC)', 'Assertiva', 'Pós-Venda', 'Imóvel Seguro'] };
const STATUS = { aguardando_trello: 'Aguardando Trello', criacao_incerta: 'Integração a conferir', em_atendimento: 'Em atendimento', pronto: 'Pronto para envio', envio_incerto: 'Envio a conferir', enviado_pendente_trello: 'E-mail enviado · atualizando Trello', enviado: 'Enviado' };
const OFICIOS = ['Asa Sul, Lago Sul, Sudoeste, Cruzeiro, Octogonal e Setor Gráfico Sul', 'Parte norte do Plano Piloto, áreas adjacentes, Paranoá e Jardim', 'Taguatinga, Águas Claras, Samambaia, Recanto das Emas e SHVP (exceto trecho 01)', 'Guará, Núcleo Bandeirante, Candangolândia, Riacho Fundo, Setor de Indústria, SMPW e SHVP trecho 01', 'Gama e Santa Maria', 'Ceilândia', 'Sobradinho', 'Planaltina/DF', 'Brazlândia'];
// Espelha a regra do back (solicitacao_service.validar): Captação só existe para o CQC.
const CAPTACAO_CQC = FINALIDADES['Cópia'][0];
function equipesDisponiveis(form) {
  if (form.tipo === 'Celer') return EQUIPES.filter(e => e !== 'Controle de Qualidade');
  if (form.finalidade === CAPTACAO_CQC) return ['Controle de Qualidade'];
  return EQUIPES;
}
const initial = { tipo: 'Ônus', tipo_onus: 'Real' };
const data = value => value ? new Date(value).toLocaleString('pt-BR') : '—';
function tempo(inicio, fim) {
  if (!inicio) return '—';
  const minutos = Math.max(0, Math.floor(((fim ? new Date(fim) : Date.now()) - new Date(inicio)) / 60000));
  if (minutos < 60) return `${minutos} min`;
  if (minutos < 1440) return `${Math.floor(minutos / 60)} h ${minutos % 60} min`;
  return `${Math.floor(minutos / 1440)} d ${Math.floor((minutos % 1440) / 60)} h`;
}
async function api(path, options) {
  const r = await fetch(`${BASE}/solicitacoes${path}`, options);
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || d.message || 'Não foi possível carregar as solicitações.');
  return d;
}

export default function Solicitacoes() {
  const [lista, setLista] = useState({ itens: [], resumo: {}, total: 0 });
  const [filtro, setFiltro] = useState({ tipo: '', status: '', busca: '', pagina: 1 });
  const [form, setForm] = useState(initial);
  const [arquivos, setArquivos] = useState([]);
  const [aberto, setAberto] = useState(false);
  const [detalhe, setDetalhe] = useState(null);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [emailCadastro, setEmailCadastro] = useState('');
  const [salvandoEmail, setSalvandoEmail] = useState(false);
  const [erroEmail, setErroEmail] = useState('');
  const [carregando, setCarregando] = useState(true);
  const chave = useRef(null);
  const erroRef = useRef(null);
  const seq = useRef(0);
  const detalheSeq = useRef(0);
  const carregar = useCallback(async () => {
    const id = ++seq.current;
    setCarregando(true);
    try {
      const r = await api(`?${new URLSearchParams(filtro)}`);
      if (id === seq.current) { setLista(r); setErro(''); }
    } catch (e) { if (id === seq.current) setErro(e.message); }
    finally { if (id === seq.current) setCarregando(false); }
  }, [filtro]);
  const invalidar = useCallback(() => { seq.current++; detalheSeq.current++; }, []);
  // O banner fica no topo e o botao de enviar no fim do formulario: sem isto, a
  // recusa do back acontece fora da area visivel e a tela parece nao reagir.
  useEffect(() => { if (erro) erroRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, [erro]);
  useEffect(() => {
    setLista({ itens: [], resumo: {}, total: 0 });
    carregar();
    const timer = setInterval(carregar, 60000);
    return () => { clearInterval(timer); invalidar(); };
  }, [carregar, invalidar]);
  function campo(nome, label, options, extra) {
    return <label key={nome}>{label} *{options ? <select required value={form[nome] || ''} onChange={e => setForm({ ...form, [nome]: e.target.value, ...(extra ? extra(e.target.value) : {}) })}><option value="">Selecione</option>{options.map(o => <option key={o} value={o}>{o}</option>)}</select> : <input required maxLength={1000} value={form[nome] || ''} onChange={e => setForm({ ...form, [nome]: e.target.value })} />}</label>;
  }
  async function salvarEmail(e) {
    e.preventDefault();
    if (salvandoEmail) return;
    setSalvandoEmail(true); setErroEmail('');
    seq.current++; // Descarta consultas iniciadas antes da atualização do cadastro.
    try {
      const r = await api('/meu-email', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: emailCadastro.trim() }) });
      seq.current++;
      setLista(atual => ({ ...atual, ...r }));
      setAviso('E-mail salvo no seu cadastro. Agora você pode registrar sua solicitação.');
      setAberto(true);
    } catch (error) { setErroEmail(error.message); }
    finally { setSalvandoEmail(false); }
  }
  async function salvar(e) {
    e.preventDefault();
    if (enviando || lista.precisa_email !== false) return;
    setEnviando(true); setErro(''); setAviso('');
    if (!chave.current) chave.current = crypto.randomUUID();
    const fd = new FormData();
    Object.entries(form).forEach(([k,v]) => fd.append(k,v));
    fd.append('chave_cliente', chave.current);
    arquivos.forEach(a => fd.append('anexos', a));
    try {
      const item = await api('', { method: 'POST', body: fd });
      setAberto(false); setForm(initial); setArquivos([]); chave.current = null;
      setAviso(`${item.protocolo} registrada. A integração é processada a cada 15 minutos.`);
      await carregar();
    } catch (error) { setErro(error.message); }
    finally { setEnviando(false); }
  }
  async function abrir(id) {
    const n = ++detalheSeq.current;
    setDetalhe(null);
    try { const d = await api(`/${id}`); if (n === detalheSeq.current) setDetalhe(d); }
    catch (e) { setErro(e.message); }
  }
  async function baixar(a) {
    try {
      const r = await fetch(`${BASE}/solicitacoes/${detalhe.id}/anexos/${a.id}`);
      if (!r.ok) throw new Error('Não foi possível baixar o anexo.');
      const url = URL.createObjectURL(await r.blob());
      const link = document.createElement('a'); link.href = url; link.download = a.nome; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) { setErro(e.message); }
  }
  const totalResumo = Object.values(lista.resumo).reduce((a,b) => a+b, 0);
  return <main className="sol-page">
    <div className="sol-heading"><div><small>61 IMÓVEIS · SOLICITAÇÕES</small><h1>{lista.gestor ? 'Acompanhar solicitações' : 'Minhas solicitações'}</h1><p>Do pedido ao envio do resultado, acompanhe cada etapa.</p></div><button disabled={lista.precisa_email !== false || salvandoEmail} onClick={() => { setAberto(!aberto); setErro(''); }}> {aberto ? 'Fechar formulário' : '+ Nova solicitação'}</button></div>
    <p className="sol-note">Integração e envio de resultados a cada 15 minutos. O e-mail é obtido do cadastro: <strong>{lista.email || 'não cadastrado'}</strong>.</p>
    {erro && <div className="sol-error" role="alert" ref={erroRef}>{erro}</div>}{aviso && <div className="sol-success" role="status">{aviso}</div>}
    {lista.precisa_email === true && <form onSubmit={salvarEmail} className="sol-panel" aria-label="Cadastrar e-mail"><h2>Cadastre seu e-mail</h2><p>Informe o endereço em que deseja receber os resultados das solicitações. Ele será salvo no seu cadastro.</p><div className="sol-grid"><label>Seu e-mail *<input type="email" autoComplete="email" required maxLength={255} value={emailCadastro} disabled={salvandoEmail} onChange={e => setEmailCadastro(e.target.value)} placeholder="nome@exemplo.com" /></label></div>{erroEmail && <p className="sol-error" role="alert">{erroEmail}</p>}<button type="submit" disabled={salvandoEmail}>{salvandoEmail ? 'Salvando…' : 'Salvar e-mail'}</button></form>}
    {aberto && lista.precisa_email === false && <form onSubmit={salvar} className="sol-panel"><h2>Nova solicitação</h2><fieldset disabled={enviando}><div className="sol-grid">
      <label>Tipo de solicitação *<select value={form.tipo} onChange={e => { setForm({ tipo: e.target.value, tipo_onus: 'Real' }); setArquivos([]); }}><option>Ônus</option><option>Parecer Jurídico</option><option>Troca de Titularidade</option><option>Celer</option></select></label>
      {form.tipo === 'Ônus' && <><label>Tipo de ônus *<select value={form.tipo_onus} onChange={e => setForm({ ...form, tipo_onus: e.target.value, finalidade: '' })}><option>Real</option><option>Cópia</option></select></label>{campo('finalidade', 'Finalidade', FINALIDADES[form.tipo_onus], v => ({ equipe: v === CAPTACAO_CQC ? 'Controle de Qualidade' : '' }))}</>}
      {form.tipo !== 'Celer' && campo('endereco', 'Endereço')}
      {['Ônus','Celer'].includes(form.tipo) && campo('equipe', 'Equipe', equipesDisponiveis(form))}
      {form.tipo === 'Ônus' && <>{campo('oficio', 'Ofício', ['1','2','3','4','5','6','7','8','9'])}{campo('matricula', 'Matrícula')}{form.tipo_onus === 'Cópia' && campo('corretor', 'Corretor')}<p className="sol-note">{form.oficio ? `${form.oficio}º Ofício — ${OFICIOS[Number(form.oficio)-1]}` : 'Selecione o ofício para consultar sua abrangência.'}</p></>}
      {['Celer','Parecer Jurídico'].includes(form.tipo) && campo('codigo_imovel', 'Código do imóvel')}
      {form.tipo === 'Parecer Jurídico' && campo('possui_onus', 'Possui ônus?', ['Sim','Não'])}
      {['Celer','Troca de Titularidade'].includes(form.tipo) && <label>{form.tipo === 'Celer' ? 'Foto *' : 'Ônus real atualizado e ficha cadastral (dois arquivos) *'}<input key={form.tipo} type="file" multiple required accept={form.tipo === 'Celer' ? 'image/png,image/jpeg' : 'application/pdf,image/png,image/jpeg'} onChange={e => setArquivos(Array.from(e.target.files))} /><small>Até 5 arquivos; 10 MB por arquivo e 20 MB no total. PDF, PNG ou JPEG.</small></label>}
    </div><button type="submit">{enviando ? 'Registrando…' : 'Registrar solicitação'}</button></fieldset></form>}
    <div className="sol-stats">{[['Total', totalResumo], ['Em atendimento', (lista.resumo.aguardando_trello || 0)+(lista.resumo.em_atendimento || 0)], ['Prontas', lista.resumo.pronto || 0], ['E-mails enviados', (lista.resumo.enviado || 0)+(lista.resumo.enviado_pendente_trello || 0)], ['A conferir', (lista.resumo.envio_incerto || 0)+(lista.resumo.criacao_incerta || 0)]].map(([label,n]) => <div key={label}><span>{label}</span><strong>{n}</strong></div>)}</div>
    <div className="sol-filters"><label>Buscar protocolo ou imóvel<input value={filtro.busca} onChange={e => setFiltro({ ...filtro, busca: e.target.value, pagina: 1 })} placeholder="Endereço, matrícula, código…" /></label><label>Tipo<select value={filtro.tipo} onChange={e => setFiltro({ ...filtro, tipo: e.target.value, pagina: 1 })}><option value="">Todos</option>{TIPOS.map(t => <option key={t}>{t}</option>)}</select></label><label>Status<select value={filtro.status} onChange={e => setFiltro({ ...filtro, status: e.target.value, pagina: 1 })}><option value="">Todos</option>{Object.entries(STATUS).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label><button onClick={carregar} disabled={carregando}>Atualizar</button></div>
    <p className="sol-note">Indicadores consideram a busca e o tipo selecionados, antes do filtro de status.</p>
    <div className="sol-table"><table><thead><tr><th>Protocolo / imóvel</th><th>Solicitação</th><th>Etapa</th><th>Solicitada em</th><th>E-mail enviado em</th><th>Tempo</th><th /></tr></thead><tbody>{lista.itens.map(i => <tr key={i.id}><td><strong>{i.protocolo}</strong><br />{i.dados.endereco || i.dados.codigo_imovel}<small>{i.dados.equipe}</small></td><td>{i.tipo}{i.tipo === 'Ônus' ? ` ${i.dados.tipo_onus}` : ''}</td><td><span className={`sol-badge ${i.enviado_em ? 'done' : ''}`}>{STATUS[i.status] || i.status}</span><small>{i.lista_nome}</small>{i.erro && <small className="sol-danger">{i.erro}</small>}</td><td>{data(i.criado_em)}</td><td>{data(i.enviado_em)}{i.enviado_em && <small>Há {tempo(i.enviado_em)}</small>}</td><td>{tempo(i.criado_em, i.enviado_em)}<small>{i.enviado_em ? 'até o envio' : 'desde o pedido'}</small></td><td><button onClick={() => abrir(i.id)}>Detalhes</button></td></tr>)}</tbody></table>{!lista.itens.length && <p>{carregando ? 'Carregando…' : 'Nenhuma solicitação encontrada.'}</p>}</div>
    <div className="sol-pagination"><button disabled={filtro.pagina <= 1} onClick={() => setFiltro({ ...filtro, pagina: filtro.pagina-1 })}>Anterior</button><span>Página {filtro.pagina} · {lista.total} solicitações</span><button disabled={filtro.pagina*30 >= lista.total} onClick={() => setFiltro({ ...filtro, pagina: filtro.pagina+1 })}>Próxima</button></div>
    {detalhe && <section className="sol-panel" aria-label="Detalhes da solicitação"><div className="sol-heading"><h2>{detalhe.protocolo} · {STATUS[detalhe.status]}</h2><button onClick={() => { detalheSeq.current++; setDetalhe(null); }}>Fechar detalhes</button></div><p>Destinatário: {detalhe.email}</p><div className="sol-grid">{Object.entries(detalhe.dados).filter(([,v]) => v).map(([k,v]) => <div key={k}><small>{k.replaceAll('_',' ')}</small><p>{v}</p></div>)}</div><p>Registrada: {data(detalhe.criado_em)} · Integrada: {data(detalhe.integrado_em)}</p><p>Conclusão identificada: {data(detalhe.concluido_em)} · E-mail enviado: {data(detalhe.enviado_em)}</p><p>Última consulta ao Trello: {data(detalhe.sincronizado_em)}</p>{detalhe.trello_url && <a href={detalhe.trello_url} target="_blank" rel="noreferrer">Abrir cartão no Trello</a>}<h3>Anexos da solicitação</h3>{detalhe.anexos.map(a => <button key={a.id} onClick={() => baixar(a)}>{a.nome}</button>)}{!detalhe.anexos.length && <p>Sem anexos de entrada.</p>}{detalhe.resultado && <><h3>Resultado</h3><pre>{detalhe.resultado.descricao}</pre>{(detalhe.resultado.anexos || []).filter(a => a.url?.startsWith('https://')).map((a,i) => <p key={i}><a href={a.url} target="_blank" rel="noreferrer">{a.nome || 'Baixar resultado'}</a></p>)}</>}<h3>Histórico</h3><ol>{detalhe.historico.map((h,i) => <li key={i}><strong>{data(h.data)}</strong> — {h.descricao}</li>)}</ol><p className="sol-note">“Enviado” indica que o servidor de e-mail aceitou a mensagem. A conclusão é datada quando o sistema identifica o cartão pronto.</p></section>}
  </main>;
}
