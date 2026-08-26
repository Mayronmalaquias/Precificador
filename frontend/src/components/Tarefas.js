import React, { useCallback, useEffect, useRef, useState } from "react";
import { BASE } from "../services/api";
import Avaliacoes from "./Avaliacoes";
import { useAuth } from "../context/AuthContext";
import { useEquipes } from "../context/EquipesContext";
import { useToast } from "../context/ToastContext";
import "../assets/css/Tarefas.css";

/** Painel de Tarefas — hub das pendências dos quatro módulos.
 *
 * Concluir aqui chama o MESMO endpoint que o módulo de origem usa, então não existe
 * sincronização a fazer: a tarefa some porque a condição que a criava deixou de ser
 * verdadeira. Por isso o botão de ação de cada tipo é diferente — ele é um atalho para o
 * fluxo do módulo, não uma "conclusão de tarefa".
 */

const TIPOS = [
  { id: "", rotulo: "Tudo" },
  { id: "proposta", rotulo: "Propostas" },
  { id: "visita", rotulo: "Visitas" },
  { id: "lead", rotulo: "Leads" },
];

const NIVEIS = [
  { id: "", rotulo: "Todas" },
  { id: "critica", rotulo: "Críticas" },
  { id: "atencao", rotulo: "Atenção" },
];

const CONTATOS = [
  ["whatsapp", "WhatsApp"],
  ["telefone", "Telefone"],
  ["email", "E-mail"],
  ["sem_contato", "Não consegui contato"],
];

/** Onde mora cada tipo de tarefa.
 *
 * O hub não tem endpoint próprio de leitura nem de escrita: abrir e salvar chamam o
 * mesmo endpoint que o módulo chama. É o que garante que corrigir aqui e corrigir lá
 * dão no mesmo — e que a tarefa some sozinha quando o estado de origem muda.
 *
 * `id` sai da tarefa; `campos` descreve o formulário; `montar` traduz o que o GET
 * devolveu para o formulário e `enviar` faz o caminho de volta.
 */
const FICHAS = {
  proposta: {
    rotulo: "Proposta",
    id: (t) => t.acao.id,
    url: (id) => `/propostas/${id}`,
    metodo: "PUT",
    extrair: (d) => d.proposta || d.item || d,
    // Registrar ação é o que RESOLVE a pendência da proposta, e grava noutro endpoint
    // que a edição (`POST .../acoes` contra `PUT` no id). Fica dentro da ficha porque o
    // painel passou a ter um botão só: o gerente abre, olha o histórico e age ali.
    acao: { url: (id) => `/propostas/${id}/acoes`, metodo: "POST" },
    leitura: [
      { rotulo: "Situação", valor: (r) => r.situacao_label },
      { rotulo: "Corretor", valor: (r) => r.corretor_nome },
      { rotulo: "Gerente", valor: (r) => r.gerente_nome },
      { rotulo: "Equipe", valor: (r) => r.team },
      { rotulo: "Forma de pagamento", valor: (r) => r.forma_pagamento_label },
      { rotulo: "Dias em aberto", valor: (r) => r.dias_em_aberto },
      { rotulo: "Dias sem ação", valor: (r) => r.dias_sem_acao },
      { rotulo: "Ações registradas", valor: (r) => r.total_acoes },
      { rotulo: "Última ação", valor: (r) => dataHora(r.ultima_acao_em) },
      { rotulo: "Lançada em", valor: (r) => dataHora(r.created_at) },
    ],
    // Todos os campos que `proposta_service.atualizar` aceita — os mesmos da tela de
    // Gestão de Propostas. Um subconjunto aqui obrigaria a trocar de tela no meio do
    // acompanhamento justamente para corrigir o campo que faltou.
    campos: [
      { nome: "cliente", rotulo: "Cliente", largo: true },
      { nome: "codigo_imovel", rotulo: "Código do imóvel" },
      { nome: "imovel_endereco", rotulo: "Endereço", largo: true },
      { nome: "bairro", rotulo: "Bairro" },
      { nome: "tipo", rotulo: "Tipo" },
      { nome: "numero", rotulo: "Número" },
      { nome: "bloco", rotulo: "Bloco" },
      { nome: "complemento", rotulo: "Complemento" },
      { nome: "quartos", rotulo: "Quartos" },
      { nome: "vagas", rotulo: "Vagas" },
      { nome: "area", rotulo: "Área (m²)" },
      { nome: "valor", rotulo: "Valor (R$)", tipo: "number" },
      {
        nome: "forma_pagamento", rotulo: "Forma de pagamento", tipo: "select",
        opcoes: [
          ["", "Não informada"], ["permuta", "Permuta"], ["consorcio", "Consórcio"],
          ["financiamento", "Financiamento"], ["recurso_proprio", "Recurso próprio"],
          ["outros", "Outros"],
        ],
      },
      { nome: "valor_permuta", rotulo: "Valor da permuta (R$)", tipo: "number" },
      { nome: "descricao_permuta", rotulo: "Descrição da permuta", largo: true },
      { nome: "data_proposta", rotulo: "Data da proposta", tipo: "date" },
      { nome: "data_fechamento", rotulo: "Data de fechamento", tipo: "date" },
      {
        nome: "situacao", rotulo: "Situação", tipo: "select",
        opcoes: [
          ["em_analise", "Em análise"], ["contraproposta", "Contraproposta"],
          ["aceita", "Aceita"], ["vendido", "Vendido"],
          ["recusada", "Recusada"], ["cancelada", "Cancelada"],
        ],
      },
      // Corretor e gerente saem do cadastro, carregados junto com a ficha.
      { nome: "id_corretor", rotulo: "Corretor", tipo: "select", lista: "corretores" },
      { nome: "id_gerente", rotulo: "Gerente", tipo: "select", lista: "gerentes" },
      { nome: "observacao", rotulo: "Observação", tipo: "textarea", largo: true },
    ],
  },
  visita: {
    rotulo: "Visita",
    id: (t) => t.acao.id,
    url: (id) => `/visitas/${id}`,
    metodo: "PUT",
    extrair: (d) => d.visita || d,
    leitura: [
      { rotulo: "Cliente", valor: (r) => r.cliente },
      { rotulo: "Corretor", valor: (r) => r.corretor },
      { rotulo: "Equipe", valor: (r) => r.equipe },
      { rotulo: "Imóvel", valor: (r) => r.imovel },
      { rotulo: "Tem anexo", valor: (r) => (r.tem_anexo ? "Sim" : "Não") },
      { rotulo: "Tem notas", valor: (r) => (r.tem_nota ? "Sim" : "Não") },
      { rotulo: "Motivo preenchido", valor: (r) => (r.motivo_ok ? "Sim" : "Não") },
      // Só o que falta revisar; lista vazia some pelo filtro do render.
      { rotulo: "Pendências", valor: (r) => (r.pendencias || []).join(", ") },
      { rotulo: "Revisada em", valor: (r) => dataHora(r.visto_em) },
    ],
    // Nomes do PUT de visita são camelCase; o GET devolve snake_case. `de`/`para` fazem
    // a tradução em vez de espalhar o nome dos dois lados pelo componente.
    campos: [
      { nome: "dataVisita", de: "data_visita", rotulo: "Data da visita", tipo: "date" },
      {
        nome: "proposta", rotulo: "Resposta do cliente", tipo: "select",
        opcoes: [["", "Sem resposta"], ["Sim", "SIM"], ["Talvez", "TALVEZ"], ["Nao", "NÃO"]],
      },
      {
        nome: "situacaoImovel", de: "situacao_imovel", rotulo: "Situação do imóvel",
        tipo: "select",
        // Duas opções, não quatro: a escrita aceita CAPTACAO_61 / _PROPRIA / _PARCEIRO,
        // mas as três gravam o mesmo `tipo_captacao`. Oferecer as três daria a impressão
        // de uma distinção que o banco não guarda — e ela sumiria no próximo reload.
        opcoes: [
          ["", "Manter como está"],
          ["CAPTACAO_61", "Captação 61"],
          ["IMOVEL_NAO_CAPTADO", "Imóvel não captado"],
        ],
      },
      { nome: "motivoSim", de: "motivo_sim", rotulo: "Motivo do SIM", tipo: "textarea", largo: true },
      { nome: "motivoTalvez", de: "motivo_talvez", rotulo: "Motivo do TALVEZ", tipo: "textarea", largo: true },
      { nome: "enderecoExterno", de: "endereco_externo", rotulo: "Endereço externo", largo: true },
      { nome: "linkImagem", de: "link_imagem", rotulo: "Link da imagem (anexo)", largo: true },
      { nome: "linkAudio", de: "link_audio", rotulo: "Link do áudio", largo: true },
      { nome: "anexoFichaVisita", de: "anexo_ficha_visita", rotulo: "Arquivo da ficha", largo: true },
    ],
  },
  lead: {
    rotulo: "Lead",
    id: (t) => t.acao.id,
    url: (id) => `/leads/c2s/${id}`,
    metodo: "PATCH",
    extrair: (d) => d.lead || d,
    // Acompanhamento grava em OUTRO endpoint que os dados do lead: `PUT` contra `PATCH`
    // no mesmo id. São coisas diferentes — um é o que o lead É, o outro é o que fizemos
    // com ele — mas abrir a ficha e não poder registrar contato obrigava a fechá-la e
    // usar o botão "Registrar contato" para a mesma tarefa.
    acompanhamento: { url: (id) => `/leads/c2s/${id}`, metodo: "PUT" },
    // Campos que o servidor manda e não cabem em input: só leitura.
    leitura: [
      { rotulo: "Situação", valor: (r) => r.situacao },
      { rotulo: "Etapa do funil", valor: (r) => r.funil },
      { rotulo: "Canal", valor: (r) => r.contato },
      { rotulo: "E-mail", valor: (r) => r.email },
      { rotulo: "Equipe", valor: (r) => r.equipe },
      { rotulo: "Arquivado", valor: (r) => (r.arquivado ? "Sim" : null) },
      { rotulo: "Motivo do arquivamento", valor: (r) => r.motivo_arquivamento },
      { rotulo: "Negócio fechado", valor: (r) => (r.negocio_fechado ? "Sim" : null) },
    ],
    campos: [
      { nome: "cliente", rotulo: "Cliente", largo: true },
      { nome: "telefone", rotulo: "Telefone" },
      { nome: "codigo_imovel", rotulo: "Código do imóvel" },
      { nome: "fonte", rotulo: "Fonte" },
      // Repasse de dono: só vale dentro da própria equipe, o servidor recusa o resto.
      { nome: "atendimento", rotulo: "Repassar para", tipo: "select", lista: "corretores" },
      { nome: "observacao", rotulo: "Observação", tipo: "textarea", largo: true },
    ],
  },
};

// A resposta do cliente na visita muda o motivo que o servidor cobra — só faz sentido
// mostrar o campo da resposta escolhida.
const MOTIVO_DA_RESPOSTA = { sim: "motivoSim", talvez: "motivoTalvez" };

/** PDFs do painel: visita, cliente e imóvel. */
/** ISO -> dd/mm/aaaa hh:mm. Valor ausente vira null para a linha sumir da ficha. */
function dataHora(valor) {
  if (!valor) return null;
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString("pt-BR");
}

/** Link do Drive -> URL que o `<iframe>` consegue exibir.
 *
 * `/view` devolve a página do Drive com cabeçalho e menus; `/preview` devolve só o
 * visualizador, e funciona tanto para imagem quanto para PDF — o anexo da visita é ora
 * um, ora outro. Link que não é do Drive volta como está.
 */
function urlDeIframe(link) {
  const texto = String(link || "").trim();
  if (!texto) return "";
  const id = texto.match(/\/d\/([\w-]{10,})/)?.[1]
    || texto.match(/[?&]id=([\w-]{10,})/)?.[1];
  return id ? `https://drive.google.com/file/d/${id}/preview` : texto;
}

const PDFS = [
  { chave: "visita", rotulo: "PDF da visita",
    url: (v) => `/visitas/pdf/download?visita_id=${encodeURIComponent(v.id_visita)}`,
    tem: (v) => Boolean(v.id_visita) },
  { chave: "cliente", rotulo: "PDF do cliente",
    url: (v) => `/clientes/pdf/download?id_cliente=${encodeURIComponent(v.id_cliente)}`,
    tem: (v) => Boolean(v.id_cliente) },
  { chave: "imovel", rotulo: "PDF do imóvel",
    url: (v) => `/imoveis/pdf/download?imovel_id=${encodeURIComponent(v.id_imovel)}`,
    tem: (v) => Boolean(v.id_imovel) },
];

export default function Tarefas() {
  const toast = useToast();
  const { idCorretor } = useAuth();
  const { getNomeEquipe } = useEquipes();

  const [dados, setDados] = useState({ itens: [], resumo: {}, escopo: {}, filtros: {} });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [tipo, setTipo] = useState("");
  const [nivel, setNivel] = useState("");
  const [responsavel, setResponsavel] = useState("");
  const [gerente, setGerente] = useState("");

  // Tarefa aberta no modal de resolução.

  // Ficha = ver/editar o registro de origem sem sair do painel. Separada de `alvo`
  // (que é concluir a tarefa) porque são coisas diferentes: uma corrige o dado, a
  // outra registra o que foi feito.
  const [ficha, setFicha] = useState(null);
  const [formFicha, setFormFicha] = useState({});
  const [carregandoFicha, setCarregandoFicha] = useState(false);
  const [salvandoFicha, setSalvandoFicha] = useState(false);
  const [baixandoPdf, setBaixandoPdf] = useState("");
  const [acompFicha, setAcompFicha] = useState({
    contato_status: "", visita_agendada: "", motivo_sem_visita: "", proxima_acao: "",
  });
  const [salvandoAcomp, setSalvandoAcomp] = useState(false);
  const [acaoFicha, setAcaoFicha] = useState({ descricao: "", situacao: "" });
  const [salvandoAcao, setSalvandoAcao] = useState(false);
  // Corretores e gerentes do cadastro, para os campos de pessoa da ficha. Uma chamada
  // por sessão: a lista muda com contratação, não com tarefa.
  const [pessoas, setPessoas] = useState({ corretores: [], gerentes: [] });

  const pedidoRef = useRef(0);

  const carregar = useCallback(async () => {
    if (!idCorretor) return;
    const meu = ++pedidoRef.current;
    setCarregando(true);
    setErro("");
    try {
      const p = new URLSearchParams({ solicitante_id: idCorretor });
      if (tipo) p.set("tipos", tipo);
      if (nivel) p.set("nivel", nivel);
      if (responsavel.trim()) p.set("responsavel", responsavel.trim());
      if (gerente) p.set("gerente_id", gerente);
      const r = await fetch(`${BASE}/tarefas?${p.toString()}`);
      const d = await r.json();
      if (meu !== pedidoRef.current) return;
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao carregar tarefas");
      setDados(d);
    } catch (e) {
      if (meu === pedidoRef.current) setErro(e.message || "Erro ao carregar tarefas");
    } finally {
      if (meu === pedidoRef.current) setCarregando(false);
    }
  }, [idCorretor, tipo, nivel, responsavel, gerente]);

  useEffect(() => { carregar(); }, [idCorretor, tipo, nivel, gerente]); // eslint-disable-line react-hooks/exhaustive-deps



  const fecharFicha = () => { setFicha(null); setFormFicha({}); };

  /** Abre o registro de origem lendo do endpoint do módulo. */
  const abrirFicha = async (t) => {
    const spec = FICHAS[t.tipo];
    const id = spec?.id(t);
    if (!spec || !id) {
      toast("Essa tarefa não tem registro para abrir.", "error");
      return;
    }
    setFicha({ tarefa: t, spec, id, registro: null });
    setFormFicha({});
    setCarregandoFicha(true);
    try {
      const r = await fetch(
        `${BASE}${spec.url(id)}?solicitante_id=${encodeURIComponent(idCorretor)}`,
      );
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui abrir o registro.");
      const registro = spec.extrair(d) || {};
      const inicial = {};
      spec.campos.forEach((c) => {
        const bruto = registro[c.de || c.nome];
        inicial[c.nome] = bruto == null ? "" : String(bruto);
      });
      // Avaliações não são campo plano: entram como lista, do jeito que o PUT de visita
      // espera de volta.
      if (t.tipo === "visita") inicial.avaliacoes = registro.avaliacoes || [];
      setFicha((f) => (f && f.id === id ? { ...f, registro } : f));
      setFormFicha(inicial);

      // As notas ficam visíveis assim que a ficha abre, então a evidência de "viu notas"
      // é a abertura. Só marca quando há nota para ver — senão a pendência baixaria numa
      // visita sem nota nenhuma.
      if (t.tipo === "visita" && registro.tem_nota) {
        marcarParteVista(t, registro, "notas", "viu_notas");
      }

      setAcaoFicha({ descricao: "", situacao: "" });
      const ac = registro.acompanhamento || {};
      setAcompFicha({
        contato_status: ac.contato_status || "",
        // Tri-estado: "" (ninguém respondeu), "sim", "nao".
        visita_agendada: ac.visita_agendada == null ? "" : (ac.visita_agendada ? "sim" : "nao"),
        motivo_sem_visita: ac.motivo_sem_visita || "",
        proxima_acao: ac.proxima_acao || "",
      });
    } catch (err) {
      toast(err.message || "Não consegui abrir o registro.", "error");
      setFicha(null);
    } finally {
      setCarregandoFicha(false);
    }
  };

  /** Registra a acao da proposta — e o que RESOLVE a pendencia dela.
   *
   *  Endpoint proprio (`POST .../acoes`), separado do `PUT` que edita os campos: corrigir
   *  um endereco nao e acompanhamento, e so a acao carimba `ultima_acao_em`.
   */
  const salvarAcaoFicha = async () => {
    if (salvandoAcao || !ficha?.spec?.acao) return;
    if (!acaoFicha.descricao.trim()) {
      toast("Descreva a ação realizada.", "error");
      return;
    }
    setSalvandoAcao(true);
    try {
      const { url, metodo } = ficha.spec.acao;
      const r = await fetch(`${BASE}${url(ficha.id)}?solicitante_id=${encodeURIComponent(idCorretor)}`, {
        method: metodo,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          descricao: acaoFicha.descricao.trim(),
          situacao: acaoFicha.situacao || "",
          solicitante_id: idCorretor,
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui registrar.");
      toast("Ação registrada.", "success");
      fecharFicha();
      carregar();
    } catch (err) {
      toast(err.message || "Não consegui registrar.", "error");
    } finally {
      setSalvandoAcao(false);
    }
  };

  /** Grava o acompanhamento sem fechar a ficha.
   *
   *  Separado de `salvarFicha` porque é outro endpoint e outra regra: se fosse um botão
   *  só, corrigir o telefone passaria a exigir também escolher um contato.
   */
  const salvarAcompFicha = async () => {
    if (salvandoAcomp || !ficha?.spec?.acompanhamento) return;
    if (!acompFicha.contato_status) {
      toast("Escolha como foi o contato.", "error");
      return;
    }
    if (acompFicha.visita_agendada === "nao" && !acompFicha.motivo_sem_visita.trim()) {
      toast("Sem visita agendada: informe o motivo.", "error");
      return;
    }
    setSalvandoAcomp(true);
    try {
      const { url, metodo } = ficha.spec.acompanhamento;
      const r = await fetch(`${BASE}${url(ficha.id)}?solicitante_id=${encodeURIComponent(idCorretor)}`, {
        method: metodo,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contato_status: acompFicha.contato_status,
          visita_agendada: acompFicha.visita_agendada === ""
            ? null : acompFicha.visita_agendada === "sim",
          motivo_sem_visita: acompFicha.motivo_sem_visita || "",
          proxima_acao: acompFicha.proxima_acao || "",
          solicitante_id: idCorretor,
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui gravar.");
      toast("Acompanhamento registrado.", "success");
      fecharFicha();
      carregar();
    } catch (err) {
      toast(err.message || "Não consegui gravar.", "error");
    } finally {
      setSalvandoAcomp(false);
    }
  };

  /** Cada evidencia de revisao baixa apenas pela acao real correspondente. */
  // Cada (visita, pendencia) e marcada uma vez por sessao. O `onLoad` do iframe dispara
  // a marcacao, que faz `setState`, que re-renderiza — sem esta trava, um `onLoad` que
  // refire viraria uma sequencia de POSTs contra a API.
  const jaMarcado = useRef(new Set());

  const marcarParteVista = async (tarefa, registro, pendencia, flag) => {
    if (!tarefa?.equipe || !registro?.id_visita) return;
    const chave = `${registro.id_visita}:${pendencia}`;
    if (jaMarcado.current.has(chave)) return;
    jaMarcado.current.add(chave);
    const restantes = (tarefa.acao?.pendentes || []).filter((p) => p !== pendencia);

    // Atualizacao otimista: o gerente ve a pendencia baixar no mesmo clique; a leitura
    // do servidor logo abaixo reconcilia contadores e remove a tarefa se era a ultima.
    setFicha((atual) => atual ? {
      ...atual,
      tarefa: {
        ...atual.tarefa,
        motivo: restantes.length ? `Falta revisar: ${restantes.join(", ")}` : "Revisada",
        acao: { ...atual.tarefa.acao, pendentes: restantes },
      },
    } : atual);
    setDados((atual) => ({
      ...atual,
      itens: (atual.itens || []).flatMap((item) => {
        if (item.chave !== tarefa.chave) return [item];
        if (!restantes.length) return [];
        return [{
          ...item,
          motivo: `Falta revisar: ${restantes.join(", ")}`,
          acao: { ...item.acao, pendentes: restantes },
        }];
      }),
    }));

    try {
      const r = await fetch(`${BASE}/visitas/vistas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id_gerente: tarefa.equipe,
          id_visita: registro.id_visita,
          [flag]: true,
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui registrar a revisão.");
      await carregar();
    } catch (err) {
      toast(err.message || "Não consegui registrar a revisão.", "error");
      carregar();
    }
  };

  useEffect(() => {
    if (!idCorretor) return;
    (async () => {
      try {
        const r = await fetch(`${BASE}/propostas/corretores?solicitante_id=${encodeURIComponent(idCorretor)}`);
        const d = await r.json();
        if (r.ok && d.ok !== false) {
          setPessoas({ corretores: d.itens || [], gerentes: d.gerentes || [] });
        }
      } catch { /* select fica só com "manter" — a ficha continua salvando o resto */ }
    })();
  }, [idCorretor]);

  /** PDF por fetch, não por link: a API exige X-API-KEY, injetado no `fetch` global.
   *  Um `<a href>` comum não passa pelo interceptor e receberia 401. */
  const baixarPdf = async (spec, registro) => {
    if (baixandoPdf) return;
    setBaixandoPdf(spec.chave);
    try {
      const r = await fetch(`${BASE}${spec.url(registro)}`);
      if (!r.ok) throw new Error(`Não consegui gerar o ${spec.rotulo.toLowerCase()}.`);
      const blob = await r.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `${spec.chave}-${registro.id_visita || ""}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
    } catch (err) {
      toast(err.message || "Não consegui gerar o PDF.", "error");
    } finally {
      setBaixandoPdf("");
    }
  };

  /** Salva no endpoint do módulo — o mesmo que a tela dele usa. */
  const salvarFicha = async (e) => {
    e.preventDefault();
    if (salvandoFicha || !ficha?.registro) return;
    const { spec, id, tarefa } = ficha;

    // Mesma regra do servidor: a resposta escolhida define o motivo cobrado.
    if (tarefa.tipo === "visita") {
      const campoMotivo = MOTIVO_DA_RESPOSTA[String(formFicha.proposta || "").trim().toLowerCase()];
      if (campoMotivo && !String(formFicha[campoMotivo] || "").trim()) {
        toast("Essa resposta exige o motivo.", "error");
        return;
      }
    }

    setSalvandoFicha(true);
    try {
      // Campo de pessoa em branco significa "manter", não "limpar" — enviar `""` faria
      // o servidor tentar resolver um corretor vazio e devolver erro.
      const corpo = { ...formFicha };
      spec.campos.filter((c) => c.lista).forEach((c) => {
        if (!String(corpo[c.nome] || "").trim()) delete corpo[c.nome];
      });

      const r = await fetch(`${BASE}${spec.url(id)}?solicitante_id=${encodeURIComponent(idCorretor)}`, {
        method: spec.metodo,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...corpo, solicitante_id: idCorretor }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui salvar.");
      if (ficha.tarefa.tipo === "visita") {
        const resposta = String(formFicha.proposta || "").trim().toLowerCase();
        const motivo = resposta === "sim" ? formFicha.motivoSim
          : resposta === "talvez" ? formFicha.motivoTalvez : "";
        if (String(motivo || "").trim()) {
          await marcarParteVista(ficha.tarefa, ficha.registro, "motivo", "add_motivo");
        }
      }
      toast("Registro atualizado.", "success");
      fecharFicha();
      // Recarrega: corrigir o dado pode ter resolvido a pendência (preencher o motivo
      // da visita, por exemplo) e a tarefa deve sumir sozinha.
      carregar();
    } catch (err) {
      toast(err.message || "Não consegui salvar.", "error");
    } finally {
      setSalvandoFicha(false);
    }
  };

  /** Resolve chamando o endpoint do MÓDULO DE ORIGEM — nunca um endpoint do hub. */

  const resumo = dados.resumo || {};
  const porTipo = resumo.por_tipo || {};
  const podeResolver = dados.escopo?.resolve !== false;

  return (
    <div className="tf">
      <header className="tf-topo">
        <div>
          <h1>Minhas tarefas</h1>
          <p>Tudo que precisa de ação, dos quatro módulos, em uma lista só.</p>
        </div>
        <button type="button" className="tf-btn" onClick={carregar} disabled={carregando}>
          {carregando ? "Atualizando…" : "Atualizar"}
        </button>
      </header>

      <div className="tf-cards">
        <div className="tf-card"><span>Abertas</span><strong>{resumo.total ?? "—"}</strong></div>
        <div className="tf-card is-critica"><span>Críticas</span><strong>{resumo.criticas ?? "—"}</strong></div>
        <div className="tf-card"><span>Atenção</span><strong>{resumo.atencao ?? "—"}</strong></div>
        <div className="tf-card">
          <span>Régua</span>
          <strong className="tf-regua">
            {dados.reguas ? `${dados.reguas.atencao}d / ${dados.reguas.critico}d` : "—"}
          </strong>
          <small>proposta parada</small>
        </div>
      </div>

      <div className="tf-filtros">
        <div className="tf-chips">
          {TIPOS.map((t) => (
            <button
              key={t.id || "tudo"}
              type="button"
              className={`tf-chip ${tipo === t.id ? "is-ativo" : ""} ${t.id ? `t-${t.id}` : ""}`}
              aria-pressed={tipo === t.id}
              onClick={() => setTipo(t.id)}
            >
              {t.rotulo}
              {t.id
                ? <b>{porTipo[t.id] ?? 0}</b>
                : <b>{resumo.total ?? 0}</b>}
            </button>
          ))}
        </div>
        <div className="tf-filtros-linha">
          {dados.filtros?.pode_filtrar_gerente && (
            <select
              className="tf-filtro-gerente"
              value={gerente}
              onChange={(e) => setGerente(e.target.value)}
              aria-label="Filtrar tarefas por gerente"
            >
              <option value="">Todos os gerentes</option>
              {(dados.filtros.gerentes || []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nome}{item.team ? ` · ${getNomeEquipe(item.team)}` : ""}
                </option>
              ))}
            </select>
          )}
          <select value={nivel} onChange={(e) => setNivel(e.target.value)}>
            {NIVEIS.map((n) => <option key={n.id || "todas"} value={n.id}>{n.rotulo}</option>)}
          </select>
          <input
            placeholder="Responsável"
            value={responsavel}
            onChange={(e) => setResponsavel(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && carregar()}
          />
          <button type="button" className="tf-btn" onClick={carregar}>Filtrar</button>
        </div>
      </div>

      {erro && <p className="tf-estado tf-estado--erro">{erro}</p>}
      {carregando && <p className="tf-estado">Carregando tarefas…</p>}
      {!carregando && !erro && !dados.itens.length && (
        <p className="tf-estado tf-estado--ok">
          Nenhuma pendência com esse filtro. Nada a fazer agora.
        </p>
      )}

      {/* O teto de exibição é por tipo, não do total — sem este aviso a lista parecia
          completa e o chip parecia errado. */}
      {resumo.exibidas != null && resumo.exibidas < resumo.total && (
        <p className="tf-nota">
          Mostrando {resumo.exibidas} de {resumo.total} pendências — no máximo 100 por
          tipo, as mais atrasadas primeiro. Resolva ou use os filtros para chegar no
          resto.
        </p>
      )}

      <div className="tf-lista">
        {dados.itens.map((t) => (
          <article key={t.chave} className={`tf-item n-${t.nivel} t-${t.tipo}`}>
            <div className="tf-item-tags">
              <span className={`tf-nivel n-${t.nivel}`}>
                {t.nivel === "critica" ? "Crítica" : t.nivel === "atencao" ? "Atenção" : "Normal"}
              </span>
              <span className={`tf-tipo t-${t.tipo}`}>{t.tipo}</span>
              <span className="tf-dias">{t.motivo}</span>
            </div>
            <h3>{t.titulo}</h3>
            <p className="tf-detalhe">{t.detalhe || "—"}</p>
            <p className="tf-resp">
              {t.responsavel}{t.equipe ? ` · ${t.equipe}` : ""}
            </p>
            {/* Um botao so. Antes o card tinha "Registrar acao"/"Registrar contato" ao
                lado de "Ver / editar", cada um abrindo uma modal diferente para o mesmo
                registro — e resolver exigia escolher qual antes de ver o que havia. */}
            <div className="tf-acoes">
              <button type="button" className="tf-btn tf-btn--primario"
                onClick={() => abrirFicha(t)}>
                Ver / editar
              </button>
              <a className="tf-link" href={t.link}>Abrir no módulo →</a>
            </div>
          </article>
        ))}
      </div>


      {ficha && (
        <div className="tf-modal-bg" onClick={fecharFicha}>
          <form className="tf-modal tf-modal--largo" onClick={(e) => e.stopPropagation()}
            onSubmit={salvarFicha}>
            <header>
              <div>
                <span className="tf-eyebrow">{ficha.spec.rotulo}</span>
                <h3>{ficha.tarefa.titulo}</h3>
              </div>
              <button type="button" onClick={fecharFicha} aria-label="Fechar">✕</button>
            </header>

            {carregandoFicha ? (
              <p className="tf-estado">Carregando registro…</p>
            ) : !ficha.registro ? (
              <p className="tf-estado tf-estado--erro">Registro indisponível.</p>
            ) : (
              <>
                <p className="tf-modal-alvo">
                  {ficha.tarefa.responsavel}
                  {ficha.tarefa.equipe ? ` · ${ficha.tarefa.equipe}` : ""}
                  <br /><small>{ficha.tarefa.motivo}</small>
                </p>

                {/* O que o servidor manda e não cabe em campo editável: situação, etapa
                    do funil, arquivamento. Linha sem valor some, em vez de virar um
                    rótulo vazio. */}
                {ficha.spec.leitura?.length > 0 && (
                  <dl className="tf-ficha-leitura">
                    {ficha.spec.leitura
                      .map((l) => [l, l.valor(ficha.registro)])
                      .filter(([, v]) => v !== null && v !== undefined && v !== "")
                      .map(([l, v]) => (
                        <div key={l.rotulo}>
                          <dt>{l.rotulo}</dt>
                          <dd>{v}</dd>
                        </div>
                      ))}
                  </dl>
                )}

                <div className="tf-ficha-grid">
                  {ficha.spec.campos.map((c) => {
                    // Motivo só aparece para a resposta que o exige — mostrar os dois
                    // convida a preencher o errado, que é o que deixa a pendência de pé.
                    if (ficha.tarefa.tipo === "visita" && (c.nome === "motivoSim" || c.nome === "motivoTalvez")) {
                      const esperado = MOTIVO_DA_RESPOSTA[String(formFicha.proposta || "").trim().toLowerCase()];
                      if (c.nome !== esperado) return null;
                    }
                    const valor = formFicha[c.nome] ?? "";
                    const mudar = (v) => setFormFicha((f) => ({ ...f, [c.nome]: v }));
                    return (
                      <label key={c.nome} className={c.largo ? "tf-ficha-largo" : ""}>
                        {c.rotulo}
                        {c.lista ? (
                          <select value={valor} onChange={(e) => mudar(e.target.value)}>
                            <option value="">Manter como está</option>
                            {(pessoas[c.lista] || []).map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.nome} {p.team ? `· ${p.team}` : ""}
                              </option>
                            ))}
                          </select>
                        ) : c.tipo === "select" ? (
                          <select value={valor} onChange={(e) => mudar(e.target.value)}>
                            {c.opcoes.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                          </select>
                        ) : c.tipo === "textarea" ? (
                          <textarea rows={3} value={valor} onChange={(e) => mudar(e.target.value)} />
                        ) : (
                          <input type={c.tipo || "text"} value={valor}
                            onChange={(e) => mudar(e.target.value)} />
                        )}
                      </label>
                    );
                  })}
                </div>

                {ficha.tarefa.tipo === "visita" && (
                  <>
                    {formFicha.linkImagem ? (
                      <div className="tf-anexo">
                        {/* O anexo aparece aqui dentro. `onLoad` marca "viu anexo": a
                            evidência é o arquivo ter sido exibido, não um clique — e o
                            objetivo da tela é resolver sem sair dela.

                            `onLoad` também dispara quando o Drive devolve página de
                            erro (arquivo não compartilhado). É o único sinal que um
                            iframe de outro domínio expõe; por isso o link para abrir
                            fora continua ao lado, para o caso de não renderizar. */}
                        <iframe
                          title="Anexo da visita"
                          src={urlDeIframe(formFicha.linkImagem)}
                          onLoad={() => marcarParteVista(
                            ficha.tarefa, ficha.registro, "anexo", "viu_anexo",
                          )}
                          allow="autoplay"
                        />
                        <a href={formFicha.linkImagem} target="_blank" rel="noreferrer"
                          className="tf-link">
                          Não carregou? Abrir no Drive →
                        </a>
                      </div>
                    ) : (
                      <p className="tf-nota">
                        Esta visita não tem imagem anexada. Cole o link no campo abaixo
                        para resolver essa parte da pendência.
                      </p>
                    )}

                    {/* Sem `<details>`: as notas ficam à vista. Antes era preciso abrir
                        para marcar "viu notas"; agora elas já estão na tela quando a
                        ficha abre, e a flag é marcada em `abrirFicha`. É evidência mais
                        fraca que o clique — em troca, revisar deixou de exigir um passo
                        que só existia para produzir o clique. */}
                    <h4 className="tf-subtitulo">Notas e avaliações</h4>
                    <Avaliacoes
                      avaliacoes={formFicha.avaliacoes || []}
                      onChange={(lista) => setFormFicha((f) => ({ ...f, avaliacoes: lista }))}
                    />

                    <div className="tf-pdfs">
                      {PDFS.map((spec) => (
                        <button
                          key={spec.chave}
                          type="button"
                          className="tf-btn"
                          disabled={!spec.tem(ficha.registro) || Boolean(baixandoPdf)}
                          title={spec.tem(ficha.registro)
                            ? spec.rotulo
                            : "Esta visita não tem esse dado registrado"}
                          onClick={() => baixarPdf(spec, ficha.registro)}
                        >
                          {baixandoPdf === spec.chave ? "Gerando…" : spec.rotulo}
                        </button>
                      ))}
                    </div>
                  </>
                )}

                {ficha.spec.acao && podeResolver && (
                  <>
                    <h4 className="tf-subtitulo">Registrar ação</h4>
                    <div className="tf-ficha-grid">
                      <label className="tf-ficha-largo">O que foi feito *
                        <textarea rows={3} value={acaoFicha.descricao}
                          placeholder="Ex.: cliente pediu prazo até sexta"
                          onChange={(e) => setAcaoFicha((a2) => ({ ...a2, descricao: e.target.value }))} />
                      </label>
                      <label>Mudar situação
                        <select value={acaoFicha.situacao}
                          onChange={(e) => setAcaoFicha((a2) => ({ ...a2, situacao: e.target.value }))}>
                          <option value="">Manter como está</option>
                          <option value="em_analise">Em análise</option>
                          <option value="contraproposta">Contraproposta</option>
                          <option value="aceita">Aceita</option>
                          <option value="vendido">Vendido</option>
                          <option value="recusada">Recusada</option>
                          <option value="cancelada">Cancelada</option>
                        </select>
                      </label>
                    </div>
                    <div className="tf-pdfs">
                      <button type="button" className="tf-btn tf-btn--primario"
                        disabled={salvandoAcao} onClick={salvarAcaoFicha}>
                        {salvandoAcao ? "Registrando…" : "Registrar ação"}
                      </button>
                    </div>
                  </>
                )}

                {ficha.spec.acompanhamento && podeResolver && (
                  <>
                    <h4 className="tf-subtitulo">Acompanhamento</h4>
                    <div className="tf-ficha-grid">
                      <label>Como foi o contato *
                        <select value={acompFicha.contato_status}
                          onChange={(e) => setAcompFicha((a2) => ({ ...a2, contato_status: e.target.value }))}>
                          <option value="">Selecione…</option>
                          {CONTATOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                        </select>
                      </label>
                      <label>Agendou visita?
                        <select value={acompFicha.visita_agendada}
                          onChange={(e) => setAcompFicha((a2) => ({ ...a2, visita_agendada: e.target.value }))}>
                          <option value="">Não respondido</option>
                          <option value="sim">Sim</option>
                          <option value="nao">Não</option>
                        </select>
                      </label>
                      {/* Motivo e próxima ação só existem quando NÃO houve agendamento —
                          mesma regra que o servidor aplica. */}
                      {acompFicha.visita_agendada === "nao" && (
                        <>
                          <label className="tf-ficha-largo">Motivo de não agendar *
                            <input value={acompFicha.motivo_sem_visita}
                              onChange={(e) => setAcompFicha((a2) => ({ ...a2, motivo_sem_visita: e.target.value }))} />
                          </label>
                          <label className="tf-ficha-largo">Próxima ação
                            <input value={acompFicha.proxima_acao}
                              onChange={(e) => setAcompFicha((a2) => ({ ...a2, proxima_acao: e.target.value }))} />
                          </label>
                        </>
                      )}
                    </div>
                    <div className="tf-pdfs">
                      <button type="button" className="tf-btn" disabled={salvandoAcomp}
                        onClick={salvarAcompFicha}>
                        {salvandoAcomp ? "Gravando…" : "Registrar acompanhamento"}
                      </button>
                    </div>
                  </>
                )}

                {ficha.tarefa.tipo === "lead" && (
                  <p className="tf-nota">
                    A correção vale na base interna. O Contact2Sale continua com o valor
                    antigo — a importação diária não reescreve o que já existe aqui.
                  </p>
                )}

                <footer>
                  <button type="button" className="tf-link" onClick={fecharFicha}
                    disabled={salvandoFicha}>
                    Cancelar
                  </button>
                  {/* Assistente ve tudo e nao grava nada — a regra ja existia no card,
                      e sumiu junto com o botao antigo. O servidor tambem recusa, mas
                      botao que sempre falha e pior que botao ausente. */}
                  {podeResolver && (
                    <button type="submit" className="tf-btn tf-btn--primario" disabled={salvandoFicha}>
                      {salvandoFicha ? "Salvando…" : "Salvar alterações"}
                    </button>
                  )}
                </footer>
              </>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
