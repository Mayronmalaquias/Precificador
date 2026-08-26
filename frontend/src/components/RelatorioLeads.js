import React, { useCallback, useEffect, useRef, useState } from "react";
import { BASE } from "../services/api";
import { useToast } from "../context/ToastContext";
import "../assets/css/RelatorioAbas.css";

const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString("pt-BR") : "—");
const moeda = (v) => (v == null ? "—"
  : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }));
const area = (v) => (v == null ? "—" : `${Number(v).toLocaleString("pt-BR")} m²`);

// Canais aceitos pela API do C2S (`channel_abbrev`).
const CANAIS = [
  ["telefone", "Telefone"],
  ["whatsapp", "WhatsApp"],
  ["internet", "Internet"],
  ["showroom", "Showroom"],
];
const NEGOCIACOES = ["Comprar", "Alugar", "Lançamento"];

const FILTROS_VAZIOS = {
  situacao: "", fonte: "", canal: "", funil: "", motivo: "",
  arquivado: "", fechado: "", por: "criacao",
  // Do IMÓVEL citado, não do lead: casam com o catálogo pelo código.
  bairro: "", tipo: "", quartos: "",
};

const FORM_VAZIO = {
  nome: "", telefone: "", email: "", codigo_imovel: "", descricao: "",
  negociacao: "Comprar", canal: "telefone", cidade: "", bairro: "",
  mensagem: "", observacao: "",
};

/** Aba de leads do Relatório do Gerente: consultar e lançar no Contact2Sale.
 *
 * O escopo vem do servidor — gerente vê a equipe, corretor vê só os dele, diretoria vê
 * tudo. `pode_lancar` também: quem não é gestão não recebe o botão.
 */
export default function RelatorioLeads({ idSolicitante, equipe, inicio, fim, corretor,
  podeLancar = false }) {
  const toast = useToast();
  const [dados, setDados] = useState({ itens: [], total: 0, page: 1, paginas: 1 });
  // Comeca em `false`: a aba nao busca ao abrir, entao nascer "carregando" mostrava
  // "Buscando…" e "Carregando leads…" sem nenhuma requisicao em curso — e escondia
  // o convite para clicar em Buscar, que so aparece quando nao esta carregando.
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  // Leads sem acompanhamento: o mesmo recorte do aviso do topo.
  const [soNaoVistos, setSoNaoVistos] = useState(false);
  // Filtros sobre os campos que vem do C2S. A API deles so honra janela de data e
  // paginacao, entao o servidor aplica estes por cima do que a API devolveu.
  // `filtros` e o RASCUNHO (o que esta nos selects); `filtrosAtivos` e o que foi
  // efetivamente buscado. Sem essa separacao, cada clique num select disparava uma
  // varredura de minutos no periodo inteiro.
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [filtrosAtivos, setFiltrosAtivos] = useState(FILTROS_VAZIOS);
  const [buscaAtiva, setBuscaAtiva] = useState("");
  const [maisFiltros, setMaisFiltros] = useState(false);
  const [detalhe, setDetalhe] = useState(null);
  const [criando, setCriando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  // Acompanhamento do lead aberto: o que o gerente registra depois de olhar.
  const [acomp, setAcomp] = useState({
    contato_status: "", visita_agendada: "", motivo_sem_visita: "", proxima_acao: "",
  });
  const [salvandoAcomp, setSalvandoAcomp] = useState(false);
  // Correcao dos dados do lead. `null` = bloco fechado; abrir copia o que esta na tela.
  const [edicao, setEdicao] = useState(null);
  const [salvandoEdicao, setSalvandoEdicao] = useState(false);
  // Corretores para o repasse de dono. O servidor recusa repasse para fora da equipe,
  // entao a lista aqui e conveniencia, nao controle de acesso.
  const [corretoresDoRepasse, setCorretoresDoRepasse] = useState([]);
  // Qual seta esta buscando: so ela mostra "Carregando", as duas ficam travadas.
  const [paginando, setPaginando] = useState(null);

  // A API do C2S responde em ~5s e nao filtra por equipe/portal/motivo, entao consulta
  // filtrada varre o periodo e leva minutos. Tres decisoes decorrem disso:
  //
  //  1. filtro e RASCUNHO: mexer nos selects nao dispara nada. So o botao Buscar
  //     promove o rascunho a `filtrosAtivos`, que e o que a requisicao usa. Antes cada
  //     clique num select disparava uma varredura;
  //  2. resultado fica em cache por combinacao exata de parametros — repetir uma busca
  //     ja feita nao volta ao servidor;
  //  3. resposta fora de ordem e descartada (`pedidoRef`): com requisicoes de minutos,
  //     a antiga chegava depois da nova e sobrescrevia a tabela.
  const abortRef = useRef(null);
  const pedidoRef = useRef(0);
  const cacheRef = useRef(new Map());

  const montarParams = useCallback((pagina, termo, ativos) => {
    const params = new URLSearchParams({
      solicitante_id: idSolicitante, page: pagina, per_page: 50,
    });
    // Idem propostas: recorte do dropdown, ignorado pelo servidor p/ quem nao e global.
    if (equipe) params.set("equipe", equipe);
    // O periodo e o mesmo do filtro do relatorio: sem ele a aba trazia a base inteira.
    if (inicio) params.set("inicio", inicio);
    if (fim) params.set("fim", fim);
    if (soNaoVistos) params.set("sem_acompanhamento", "1");
    // Filtro de corretor do topo do relatorio.
    if (corretor) params.set("corretor", corretor);
    if ((termo || "").trim()) params.set("busca", termo.trim());
    // Só o que está preenchido vai na URL — filtro vazio não vira parâmetro.
    Object.entries(ativos).forEach(([k, v]) => { if (v) params.set(k, v); });
    return params;
  }, [idSolicitante, equipe, inicio, fim, soNaoVistos, corretor]);

  const carregar = useCallback(async (pagina = 1, termo = buscaAtiva, ativos = filtrosAtivos) => {
    if (!idSolicitante) return;
    const params = montarParams(pagina, termo, ativos);
    const chave = params.toString();

    // Cache por combinação exata: voltar a uma busca já feita é instantâneo.
    const guardado = cacheRef.current.get(chave);
    if (guardado) {
      setDados(guardado);
      setErro("");
      setCarregando(false);
      return;
    }

    const meu = ++pedidoRef.current;
    if (abortRef.current) abortRef.current.abort();
    const controle = new AbortController();
    abortRef.current = controle;

    setCarregando(true);
    setErro("");
    try {
      const r = await fetch(`${BASE}/leads/c2s?${chave}`, { signal: controle.signal });
      const d = await r.json();
      if (meu !== pedidoRef.current) return;   // chegou tarde: ja ha pedido mais novo
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao carregar leads");
      cacheRef.current.set(chave, d);
      setDados(d);
    } catch (e) {
      if (e.name === "AbortError") return;
      if (meu === pedidoRef.current) setErro(e.message || "Erro ao carregar leads");
    } finally {
      if (meu === pedidoRef.current) setCarregando(false);
    }
  }, [idSolicitante, buscaAtiva, filtrosAtivos, montarParams]);

  // NADA e buscado sozinho — nem ao abrir a aba. Uma consulta filtrada varre o periodo
  // e leva minutos, entao ela so acontece quando o usuario pede. Trocar de aba ou de
  // periodo nao pode disparar isso sem querer.
  const [jaBuscou, setJaBuscou] = useState(false);

  // Catálogo fixo dos filtros. É uma chamada local (não consulta o Contact2Sale), então
  // pode rodar ao abrir — é o que permite escolher o motivo antes da primeira busca.
  const [catalogo, setCatalogo] = useState({
    motivos: [], situacoes: [], funis: [], bairros: [], tipos: [], quartos: [],
  });
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const r = await fetch(`${BASE}/leads/c2s/opcoes`);
        const d = await r.json();
        if (vivo && r.ok && d.ok) {
          // Guarda a resposta inteira em vez de escolher chave por chave: era assim
          // antes, e por isso `bairros`, `tipos` e `quartos` chegavam do servidor e eram
          // descartados aqui — os dropdowns ficavam só com "Todos". `ok` fora porque não
          // é lista de opção.
          const { ok, ...listas } = d;
          setCatalogo(listas);
        }
      } catch { /* dropdown cai no que a busca trouxer */ }
    })();
    return () => { vivo = false; };
  }, []);

  useEffect(() => {
    if (!idSolicitante) return;
    (async () => {
      try {
        const r = await fetch(`${BASE}/propostas/corretores?solicitante_id=${encodeURIComponent(idSolicitante)}`);
        const d = await r.json();
        if (r.ok && d.ok !== false) setCorretoresDoRepasse(d.itens || []);
      } catch { /* sem lista o repasse fica indisponível; o resto da edição continua */ }
    })();
  }, [idSolicitante]);

  // Opções = catálogo fixo + o que a janela consultada trouxer de novo (motivo com
  // texto livre do corretor, portal novo). `dados.opcoes` só existe depois de buscar.
  const opcoesDe = (campo) => {
    const daBusca = dados.opcoes?.[campo] || [];
    const fixas = catalogo[campo] || [];
    return fixas.length ? [...new Set([...fixas, ...daBusca])] : daBusca;
  };

  // Chave do que esta na tela agora; comparada com a ultima efetivamente buscada para
  // saber se ha algo a aplicar (inclui periodo e equipe, nao so os selects).
  const chaveAtual = montarParams(1, busca, filtros).toString();
  const [chaveAplicada, setChaveAplicada] = useState("");
  const pendente = jaBuscou && chaveAtual !== chaveAplicada;

  // Busca sozinha ao abrir. Antes nao buscava: a leitura era ao vivo do C2S e uma
  // consulta custava minutos, entao a tela nascia vazia esperando o clique. Agora a
  // listagem vem do espelho local (sincronizado de hora em hora) e a primeira carga e
  // uma consulta indexada — deixar a tela vazia so escondia o conteudo.
  //
  // Os FILTROS continuam sendo rascunho, aplicados no botao: nao por custo, mas porque
  // disparar a cada mexida num select era o comportamento reclamado antes.
  useEffect(() => {
    if (jaBuscou || !idSolicitante || !inicio || !fim) return;
    aplicarFiltros();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSolicitante, inicio, fim]);

  // Aplicar = promover o rascunho. Os valores vao por parametro porque `setState` e
  // assincrono: ler `filtrosAtivos` aqui pegaria o valor anterior.
  const aplicarFiltros = () => {
    setFiltrosAtivos(filtros);
    setBuscaAtiva(busca);
    setChaveAplicada(chaveAtual);
    setJaBuscou(true);
    carregar(1, busca, filtros);
  };

  /** Abre o detalhe. Duas rotas, e a escolha importa.
   *
   * `id_interno` só existe para o lead que também está em `leads_legado`. A importação
   * legada só aceita lead da recepção ou de fonte Faixa/Indicação, então lead de portal
   * (Grupo Zap, DF imóveis, ImovelWeb) nunca teve linha lá — 26% do espelho. Antes esses
   * apareciam com um "—" no lugar do botão e não abriam de jeito nenhum.
   *
   * Sem `id_interno`, abre pelo id do C2S: o espelho tem o lead inteiro. O que falta é
   * onde gravar acompanhamento, e aí `pode_editar` vem falso.
   */
  const abrir = async (lead) => {
    const idInterno = lead?.id_interno;
    const url = idInterno
      ? `${BASE}/leads/gestao/${idInterno}`
      : `${BASE}/leads/c2s/${encodeURIComponent(lead?.id_c2s)}`;
    setDetalhe({ id: idInterno || null });
    try {
      const r = await fetch(`${url}?solicitante_id=${encodeURIComponent(idSolicitante)}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao abrir lead");
      setDetalhe({ ...d.lead, _imovel: d.imovel, _pode_editar: d.pode_editar,
                   _pode_corrigir: d.pode_corrigir_dados,
                   _sem_registro: d.sem_registro_interno, _opcoes: d.opcoes });
      setEdicao(null);
      const a = d.lead?.acompanhamento || {};
      setAcomp({
        contato_status: a.contato_status || "",
        // Tri-estado: "" (ninguém respondeu), "sim", "nao".
        visita_agendada: a.visita_agendada == null ? "" : (a.visita_agendada ? "sim" : "nao"),
        motivo_sem_visita: a.motivo_sem_visita || "",
        proxima_acao: a.proxima_acao || "",
      });
    } catch (e) {
      toast(e.message, "error");
      setDetalhe(null);
    }
  };

  const set = (campo) => (e) => setForm((f) => ({ ...f, [campo]: e.target.value }));

  const abrirEdicao = () => setEdicao({
    // `atendimento` nasce vazio de proposito: em branco significa "manter o dono", e
    // preenchê-lo com o valor atual faria todo salvamento tentar um repasse.
    atendimento: "",
    cliente: detalhe.cliente || "",
    telefone: detalhe.telefone || "",
    codigo_imovel: detalhe.codigo_imovel || "",
    fonte: detalhe.fonte || "",
    observacao: detalhe.observacao || "",
  });

  /** PATCH corrige o dado do lead; o PUT ao lado grava o acompanhamento. Sao coisas
   *  diferentes — um e o que o lead E, o outro e o que fizemos com ele. */
  const salvarEdicao = async () => {
    if (salvandoEdicao || !edicao) return;
    if (!String(edicao.cliente).trim()) {
      toast("Nome do cliente nao pode ficar vazio.", "error");
      return;
    }
    setSalvandoEdicao(true);
    try {
      const r = await fetch(`${BASE}/leads/gestao/${detalhe.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        // `atendimento` em branco significa "manter", não "limpar" — enviar `""` faria
        // o servidor tentar resolver um corretor vazio.
        body: JSON.stringify({
          ...edicao,
          ...(edicao.atendimento ? {} : { atendimento: undefined }),
          solicitante_id: idSolicitante,
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || !d.ok) throw new Error(d.error || "Erro ao salvar o lead.");
      // Atualiza so o modal. Recarregar a lista custaria uma varredura do C2S de
      // minutos, e a listagem vem de la — nao da base que acabou de mudar.
      setDetalhe((p) => ({ ...p, ...edicao }));
      setEdicao(null);
      toast(d.alterados?.length ? "Lead atualizado." : "Nada mudou.", "success");
    } catch (err) {
      toast(err.message || "Erro ao salvar o lead.", "error");
    } finally {
      setSalvandoEdicao(false);
    }
  };

  const lancar = async (e) => {
    e.preventDefault();
    // A API do C2S responde 423 sem telefone e sem e-mail; barrar aqui evita a viagem.
    if (!form.telefone.trim() && !form.email.trim()) {
      toast("Informe telefone ou e-mail — o Contact2Sale recusa lead sem os dois.", "error");
      return;
    }
    setSalvando(true);
    try {
      const r = await fetch(`${BASE}/leads/gestao?solicitante_id=${encodeURIComponent(idSolicitante)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao lançar lead");
      toast(
        `Lead criado no Contact2Sale${d.recebido_por ? ` · recebido por ${d.recebido_por}` : ""}.`,
        "success",
      );
      setCriando(false);
      setForm(FORM_VAZIO);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setSalvando(false);
    }
  };


  const salvarAcomp = async () => {
    if (!detalhe) return;
    // Mesma regra do servidor, checada aqui só para não gastar a viagem.
    if (acomp.visita_agendada === "nao" && !acomp.motivo_sem_visita.trim()) {
      toast("Sem visita agendada: informe o motivo.", "error");
      return;
    }
    setSalvandoAcomp(true);
    try {
      const corpo = {
        contato_status: acomp.contato_status,
        visita_agendada: acomp.visita_agendada === "" ? "" : acomp.visita_agendada === "sim",
        motivo_sem_visita: acomp.motivo_sem_visita,
        proxima_acao: acomp.proxima_acao,
      };
      // Acompanhamento grava pelo id do C2S: `detalhe.id` (o de `leads_legado`) só
      // existe para 74% dos leads, e é justamente essa dependência que impedia lead de
      // portal de receber acompanhamento.
      const r = await fetch(`${BASE}/leads/c2s/${encodeURIComponent(detalhe.id_c2s)}?solicitante_id=${encodeURIComponent(idSolicitante)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao salvar");
      toast("Acompanhamento salvo.", "success");
      setDetalhe((p) => ({ ...p, acompanhamento: d.acompanhamento }));
      carregar(dados.page);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setSalvandoAcomp(false);
    }
  };

  const irPara = async (pagina, direcao) => {
    // A API leva alguns segundos; sem sinal na propria seta o clique parece nao ter
    // funcionado e o gerente clica de novo, empilhando requisicao.
    setPaginando(direcao);
    try {
      await carregar(pagina);
    } finally {
      setPaginando(null);
    }
  };

  const setFiltro = (campo) => (e) =>
    setFiltros((f) => ({ ...f, [campo]: e.target.value }));
  // "por" tem valor padrao, entao nao conta como filtro ativo.
  const ativos = Object.entries(filtros)
    .filter(([k, v]) => v && !(k === "por" && v === "criacao")).length;
  const limparFiltros = () => setFiltros(FILTROS_VAZIOS);
  // Com filtro local o total pode ser desconhecido, entao a navegacao usa `tem_mais`
  // em vez de um numero de paginas que seria chute.
  const paginas = dados.total == null
    ? null
    : Math.max(Math.ceil(dados.total / (dados.per_page || 50)), 1);

  return (
    <div className="raba">
      <div className="raba-barra">
        <input
          placeholder="Buscar por cliente, telefone, código do imóvel ou fonte"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && aplicarFiltros()}
        />
        <button
          type="button"
          className={`raba-cta ${pendente ? "raba-cta--pendente" : ""}`}
          onClick={aplicarFiltros}
          disabled={carregando}
        >
          {carregando ? "Buscando…" : pendente ? "Buscar (filtros alterados)" : "Buscar"}
        </button>
        <button
          type="button"
          className={`raba-filtro ${soNaoVistos ? "is-ativo" : ""}`}
          aria-pressed={soNaoVistos}
          onClick={() => setSoNaoVistos((v) => !v)}
        >
          Sem acompanhamento
        </button>
        {(dados.pode_lancar || podeLancar) && (
          <button type="button" className="raba-cta raba-cta--novo" onClick={() => setCriando(true)}>
            + Lançar lead
          </button>
        )}
        <button
          type="button"
          className={`raba-filtro ${maisFiltros ? "is-ativo" : ""}`}
          aria-pressed={maisFiltros}
          onClick={() => setMaisFiltros((v) => !v)}
        >
          Filtros{ativos ? ` (${ativos})` : ""}
        </button>
        <span className="raba-contador">
          {dados.total == null
            ? `${dados.itens?.length || 0}+ leads`
            : `${dados.total.toLocaleString("pt-BR")} lead${dados.total === 1 ? "" : "s"}`}
        </span>
      </div>

      {maisFiltros && (
        <div className="raba-filtros">
          {/* Motivo, situação e funil vêm do catálogo fixo da C2S (carregado ao abrir,
              sem consultar a API deles). Portal e canal não têm catálogo, então só
              aparecem depois da primeira busca, com o que existir no período. */}
          <label>Situacao
            <select value={filtros.situacao} onChange={setFiltro("situacao")}>
              <option value="">Todas</option>
              {opcoesDe("situacoes").map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Etapa do funil
            <select value={filtros.funil} onChange={setFiltro("funil")}>
              <option value="">Todas</option>
              {opcoesDe("funis").map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Portal
            <select value={filtros.fonte} onChange={setFiltro("fonte")}>
              <option value="">Todos</option>
              {(dados.opcoes?.fontes || []).map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Canal
            <select value={filtros.canal} onChange={setFiltro("canal")}>
              <option value="">Todos</option>
              {(dados.opcoes?.canais || []).map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>

          {/* Bairro, tipo e quartos são do IMÓVEL que o cliente citou, não do lead. As
              opções saem do catálogo restrito ao que os leads de fato pedem — oferecer os
              109 bairros do catálogo incluiria dezenas que devolvem lista vazia.
              Lead sem código, ou com código fora do catálogo, sai do resultado quando
              qualquer um destes está ligado. */}
          <label>Bairro do imóvel
            <select value={filtros.bairro} onChange={setFiltro("bairro")}>
              <option value="">Todos</option>
              {opcoesDe("bairros").map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Tipo do imóvel
            <select value={filtros.tipo} onChange={setFiltro("tipo")}>
              <option value="">Todos</option>
              {opcoesDe("tipos").map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Quartos
            <select value={filtros.quartos} onChange={setFiltro("quartos")}>
              <option value="">Qualquer</option>
              {opcoesDe("quartos").map((v) => (
                <option key={v} value={v}>{v} quarto{Number(v) === 1 ? "" : "s"}</option>
              ))}
            </select>
          </label>
          <label>Arquivado
            <select value={filtros.arquivado} onChange={setFiltro("arquivado")}>
              <option value="">Tanto faz</option>
              <option value="sim">So arquivados</option>
              <option value="nao">So ativos</option>
            </select>
          </label>
          <label>Motivo do arquivamento
            <select value={filtros.motivo} onChange={setFiltro("motivo")}>
              <option value="">Todos</option>
              {opcoesDe("motivos").map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>Negocio fechado
            <select value={filtros.fechado} onChange={setFiltro("fechado")}>
              <option value="">Tanto faz</option>
              <option value="sim">So fechados</option>
              <option value="nao">So em aberto</option>
            </select>
          </label>
          <label>Periodo por
            {/* O C2S so filtra por data de criacao ou de atualizacao. "Atualizacao"
                acha o lead que mudou de situacao no periodo, mesmo sendo antigo. */}
            <select value={filtros.por} onChange={setFiltro("por")}>
              <option value="criacao">Data de criacao</option>
              <option value="atualizacao">Data de atualizacao</option>
            </select>
          </label>
          {!!ativos && (
            <button type="button" className="raba-link" onClick={limparFiltros}>Limpar filtros</button>
          )}
        </div>
      )}

      {dados.total_exato === false && (
        <p className="raba-nota">
          O período é grande demais para varrer inteiro ({dados.total_c2s?.toLocaleString("pt-BR")}{" "}
          leads) e a leitura parou no limite de segurança, então o total está incompleto.
          Estreite o período.
        </p>
      )}

      {erro && <p className="raba-estado raba-estado--erro">{erro}</p>}
      {carregando && (
        <p className="raba-estado">
          {ativos
            /* A API do C2S nao filtra por equipe, portal nem motivo: o servidor varre o
               periodo para contar certo. So a primeira consulta paga isso — o resultado
               fica 15 min em cache. */
            ? "Aplicando o filtro no período inteiro… a primeira consulta pode levar alguns minutos; as seguintes são imediatas."
            : "Carregando leads…"}
        </p>
      )}
      {!carregando && !jaBuscou && !erro && (
        <p className="raba-estado">
          Escolha o período e os filtros e clique em <b>Buscar</b>. A consulta lê os leads
          direto do Contact2Sale, por isso não roda sozinha ao abrir a aba.
        </p>
      )}
      {!carregando && jaBuscou && !dados.itens.length && !erro && (
        <p className="raba-estado">Nenhum lead encontrado com esse filtro.</p>
      )}

      {!!dados.itens.length && (
        <>
          <div className="raba-tabela-wrap">
            <table className="raba-tabela">
              <thead>
                <tr><th>Data</th><th>Cliente</th><th>Telefone</th><th>Imóvel</th><th>Portal</th><th>Atendimento</th><th>Situação</th><th>Motivo</th><th /></tr>
              </thead>
              <tbody>
                {dados.itens.map((l) => (
                  <tr key={l.id_c2s}>
                    <td>{dataBR(l.criado_em)}</td>
                    <td>
                      <strong>{l.cliente || "Sem nome"}</strong>
                      <span>{l.equipe || ""}</span>
                    </td>
                    <td>{l.telefone || "—"}</td>
                    <td>{l.codigo_imovel || "—"}</td>
                    <td>{l.fonte || "—"}</td>
                    <td>{l.corretor || "—"}</td>
                    <td>
                      {/* Situação vem do C2S na hora — é o motivo desta aba ter deixado
                          de ler a base interna, que guarda o status do dia da importação. */}
                      {l.situacao
                        ? <span className={`raba-selo ${l.arquivado ? "s-recusada" : ""}`}>{l.situacao}</span>
                        : "—"}
                      {l.negocio_fechado && <span className="raba-selo s-aceita">Fechado</span>}
                      {!l.acompanhamento_em && <span className="raba-selo">Sem acomp.</span>}
                    </td>
                    <td>{l.motivo_arquivamento || "—"}</td>
                    <td>
                      <button type="button" className="raba-link" onClick={() => abrir(l)}>
                        Abrir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(dados.tem_mais || dados.page > 1) && (
            <div className="raba-paginacao">
              <button
                type="button"
                disabled={dados.page <= 1 || !!paginando}
                onClick={() => irPara(dados.page - 1, "anterior")}
              >
                {paginando === "anterior" ? <><span className="ds-spinner" /> Carregando…</> : "← Anterior"}
              </button>
              <span>Página <b>{dados.page}</b>{paginas ? ` de ${paginas}` : ""}</span>
              <button
                type="button"
                disabled={!dados.tem_mais || !!paginando}
                onClick={() => irPara(dados.page + 1, "proxima")}
              >
                {paginando === "proxima" ? <><span className="ds-spinner" /> Carregando…</> : "Próxima →"}
              </button>
            </div>
          )}
        </>
      )}

      {detalhe && (
        <div className="raba-modal-bg" onClick={() => setDetalhe(null)}>
          <div className="raba-modal" onClick={(e) => e.stopPropagation()}>
            <header>
              <div>
                <span className="raba-eyebrow">Lead #{detalhe.id}</span>
                <h3>{detalhe.cliente || "Lead sem nome"}</h3>
              </div>
              <button type="button" onClick={() => setDetalhe(null)} aria-label="Fechar">✕</button>
            </header>
            <div className="raba-dados">
              {[
                ["Data", dataBR(detalhe.data)],
                ["Telefone", detalhe.telefone],
                ["Código do imóvel", detalhe.codigo_imovel],
                ["Fonte", detalhe.fonte],
                ["Canal", detalhe.contato],
                ["Relatório", detalhe.relatorio],
                ["Atendimento", detalhe.atendimento_nome],
                ["Equipe", detalhe.equipe],
              ].filter(([, v]) => v != null && v !== "").map(([rotulo, valor]) => (
                <div key={rotulo}><span>{rotulo}</span><strong>{valor}</strong></div>
              ))}
            </div>
            {detalhe.observacao && <p className="raba-obs">{detalhe.observacao}</p>}

            {/* Imóvel citado no lead. Endereço/valor/metragem vêm do catálogo; a data da
                captação só existe em `fato_captacao` — por isso as duas fontes. */}
            {detalhe._imovel && (
              <>
                <h4 className="raba-subtitulo">Imóvel do lead · {detalhe._imovel.codigo}</h4>
                <div className="raba-dados">
                  {[
                    ["Endereço", detalhe._imovel.endereco],
                    ["Bairro", detalhe._imovel.bairro],
                    ["Tipo", detalhe._imovel.tipo],
                    ["Valor", detalhe._imovel.valor != null ? moeda(detalhe._imovel.valor) : null],
                    ["Metragem", detalhe._imovel.area != null ? area(detalhe._imovel.area) : null],
                    ["Quartos", detalhe._imovel.quartos],
                    ["Vagas", detalhe._imovel.vagas],
                    ["Situação", detalhe._imovel.situacao],
                    ["Data da captação", detalhe._imovel.data_captacao ? dataBR(detalhe._imovel.data_captacao) : null],
                  ].filter(([, v]) => v != null && v !== "").map(([rotulo, valor]) => (
                    <div key={rotulo}><span>{rotulo}</span><strong>{valor}</strong></div>
                  ))}
                </div>
              </>
            )}
            {detalhe.codigo_imovel && !detalhe._imovel && (
              <p className="raba-nota">
                O imóvel <b>{detalhe.codigo_imovel}</b> não está no catálogo nem na base de
                captação — sem dados para mostrar.
              </p>
            )}

            {detalhe._sem_registro && (
              <p className="raba-nota">
                Lead vindo de portal, sem registro na base histórica — a importação antiga
                só aceita lead da recepção ou de fonte Faixa/Indicação. O acompanhamento
                funciona normalmente; só a correção dos dados do lead depende daquele
                registro.
              </p>
            )}

            {detalhe._pode_corrigir && (
              <>
                <h4 className="raba-subtitulo">
                  Dados do lead
                  {!edicao && (
                    <button type="button" className="raba-link" onClick={abrirEdicao}>
                      Corrigir
                    </button>
                  )}
                </h4>
                {edicao ? (
                  <>
                    <div className="raba-form">
                      <label className="raba-form-largo">Cliente
                        <input value={edicao.cliente}
                          onChange={(e) => setEdicao((v) => ({ ...v, cliente: e.target.value }))} />
                      </label>
                      <label>Telefone
                        <input value={edicao.telefone} placeholder="61999999999"
                          onChange={(e) => setEdicao((v) => ({ ...v, telefone: e.target.value }))} />
                      </label>
                      <label>Código do imóvel
                        <input value={edicao.codigo_imovel}
                          onChange={(e) => setEdicao((v) => ({ ...v, codigo_imovel: e.target.value }))} />
                      </label>
                      <label>Fonte
                        <input value={edicao.fonte}
                          onChange={(e) => setEdicao((v) => ({ ...v, fonte: e.target.value }))} />
                      </label>
                      <label>Repassar para
                        <select value={edicao.atendimento}
                          onChange={(e) => setEdicao((v) => ({ ...v, atendimento: e.target.value }))}>
                          <option value="">Manter o dono atual</option>
                          {(corretoresDoRepasse || []).map((p2) => (
                            <option key={p2.id} value={p2.id}>
                              {p2.nome}{p2.team ? ` · ${p2.team}` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="raba-form-largo">Observação
                        <input value={edicao.observacao}
                          onChange={(e) => setEdicao((v) => ({ ...v, observacao: e.target.value }))} />
                      </label>
                    </div>
                    <p className="raba-nota">
                      A correção vale na base interna. O Contact2Sale continua com o valor
                      antigo — a importação diária não reescreve o que já existe aqui.
                    </p>
                    <div className="raba-modal-rodape">
                      <button type="button" className="raba-filtro" onClick={() => setEdicao(null)}>
                        Cancelar
                      </button>
                      <button type="button" className="raba-cta" disabled={salvandoEdicao}
                        onClick={salvarEdicao}>
                        {salvandoEdicao ? "Salvando…" : "Salvar dados"}
                      </button>
                    </div>
                  </>
                ) : null}

                <h4 className="raba-subtitulo">Acompanhamento</h4>
                <div className="raba-form">
                  <label>Interação
                    <select
                      value={acomp.contato_status}
                      onChange={(e) => setAcomp((a) => ({ ...a, contato_status: e.target.value }))}
                    >
                      <option value="">Não informado</option>
                      {((detalhe._opcoes || {}).contatos || []).map((c) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>Visita agendada
                    <select
                      value={acomp.visita_agendada}
                      onChange={(e) => setAcomp((a) => ({ ...a, visita_agendada: e.target.value }))}
                    >
                      <option value="">Não informado</option>
                      <option value="sim">Sim</option>
                      <option value="nao">Não</option>
                    </select>
                  </label>

                  {/* Motivo e próxima ação só existem quando NÃO houve agendamento. */}
                  {acomp.visita_agendada === "nao" && (
                    <>
                      <label className="raba-form-largo">Motivo
                        <input
                          value={acomp.motivo_sem_visita}
                          onChange={(e) => setAcomp((a) => ({ ...a, motivo_sem_visita: e.target.value }))}
                          placeholder="Por que não agendou"
                        />
                      </label>
                      <label className="raba-form-largo">Próxima ação
                        <input
                          value={acomp.proxima_acao}
                          onChange={(e) => setAcomp((a) => ({ ...a, proxima_acao: e.target.value }))}
                          placeholder="O que fazer e quando"
                        />
                      </label>
                    </>
                  )}
                </div>
                <div className="raba-modal-rodape">
                  {detalhe.acompanhamento?.em && (
                    <span className="raba-contador">
                      Atualizado em {dataBR(detalhe.acompanhamento.em)}
                      {detalhe.acompanhamento.por ? ` por ${detalhe.acompanhamento.por}` : ""}
                    </span>
                  )}
                  <button type="button" className="raba-cta" disabled={salvandoAcomp} onClick={salvarAcomp}>
                    {salvandoAcomp ? "Salvando…" : "Salvar acompanhamento"}
                  </button>
                </div>
              </>
            )}

            {detalhe.telefone && (
              <div className="raba-modal-rodape">
                <a className="raba-cta" target="_blank" rel="noreferrer"
                  href={`https://wa.me/${String(detalhe.telefone).replace(/\D/g, "")}`}>
                  Chamar no WhatsApp
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {criando && (
        <div className="raba-modal-bg" onClick={() => !salvando && setCriando(false)}>
          <form className="raba-modal" onClick={(e) => e.stopPropagation()} onSubmit={lancar}>
            <header>
              <div>
                <span className="raba-eyebrow">Contact2Sale</span>
                <h3>Lançar lead</h3>
              </div>
              <button type="button" onClick={() => setCriando(false)} aria-label="Fechar">✕</button>
            </header>

            <p className="raba-nota">
              O lead é criado <b>direto no Contact2Sale</b> e segue a distribuição de lá.
              Ele aparece nesta lista depois da importação diária.
            </p>

            <div className="raba-form">
              <label>Nome<input value={form.nome} onChange={set("nome")} placeholder="Nome do cliente" /></label>
              <label>Telefone<input value={form.telefone} onChange={set("telefone")} placeholder="(61) 90000-0000" /></label>
              <label>E-mail<input type="email" value={form.email} onChange={set("email")} placeholder="cliente@email.com" /></label>
              <label>Código do imóvel<input value={form.codigo_imovel} onChange={set("codigo_imovel")} placeholder="Deixe vazio se não houver" /></label>
              <label>Negociação
                <select value={form.negociacao} onChange={set("negociacao")}>
                  {NEGOCIACOES.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </label>
              <label>Canal
                <select value={form.canal} onChange={set("canal")}>
                  {CANAIS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </label>
              <label>Cidade<input value={form.cidade} onChange={set("cidade")} /></label>
              <label>Bairro<input value={form.bairro} onChange={set("bairro")} /></label>
              <label className="raba-form-largo">Descrição do interesse
                <input value={form.descricao} onChange={set("descricao")} maxLength={250} placeholder="Apartamento 2 quartos na Asa Sul" />
              </label>
              <label className="raba-form-largo">Primeira mensagem
                <textarea value={form.mensagem} onChange={set("mensagem")} rows={3} placeholder="O que o cliente falou" />
              </label>
              <label className="raba-form-largo">Observação interna
                <textarea value={form.observacao} onChange={set("observacao")} rows={2} />
              </label>
            </div>

            <div className="raba-modal-rodape">
              <button type="button" className="raba-link" onClick={() => setCriando(false)} disabled={salvando}>Cancelar</button>
              <button type="submit" className="raba-cta" disabled={salvando}>
                {salvando ? "Enviando…" : "Criar no Contact2Sale"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
