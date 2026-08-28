import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BASE } from "../services/api";
import { GraficoMultiLinha, GraficoBarras } from "./GraficosGestao";
import Avaliacoes from "./Avaliacoes";
import { useAuth } from "../context/AuthContext";
import { useEquipes } from "../context/EquipesContext";
import { useToast } from "../context/ToastContext";
import { porRotulo } from "../services/ordenar";
import "../assets/css/GestaoModulo.css";

/** Gestão de Visitas — módulo especializado.
 *
 * Uma observação de escopo que vale registrar: `visitas` guarda visita REALIZADA. Não há
 * campo de agendamento futuro, então a faixa semanal aqui é distribuição do que já
 * aconteceu, não agenda. Transformar em calendário de marcação exige coluna nova.
 *
 * As flags de revisão acompanham a ação real: abrir anexo, abrir notas e salvar motivo.
 */

const iso = (d) => d.toISOString().slice(0, 10);
const hoje = () => new Date();
const diasAtras = (n) => { const d = hoje(); d.setDate(d.getDate() - n); return iso(d); };
const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString("pt-BR") : "—");

const RESPOSTAS = [
  { id: "", rotulo: "Todas as respostas" },
  { id: "sim", rotulo: "SIM" },
  { id: "talvez", rotulo: "TALVEZ" },
  { id: "nao", rotulo: "NÃO" },
];

const norm = (v) => String(v || "").trim().toLowerCase();

const CORES_RESPOSTA = { sim: "#17804a", talvez: "#d28a13", nao: "#64748b", vazio: "#d8d4df" };
const rotuloResposta = (id) => ({ sim: "SIM", talvez: "TALVEZ", nao: "NÃO", vazio: "Sem resposta" }[id] || id);

function LinhaVisitas({ pontos }) {
  const largura = 640;
  const altura = 180;
  const margem = { topo: 14, direita: 12, baixo: 28, esquerda: 34 };
  const w = largura - margem.esquerda - margem.direita;
  const h = altura - margem.topo - margem.baixo;
  const maior = Math.max(1, ...pontos.map((p) => p.total));
  const x = (i) => margem.esquerda + (pontos.length === 1 ? w / 2 : (i / (pontos.length - 1)) * w);
  const y = (n) => margem.topo + h - (n / maior) * h;
  const caminho = pontos.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.total)}`).join(" ");
  const marcadores = pontos.length <= 10 ? pontos.map((_, i) => i) : [0, Math.floor((pontos.length - 1) / 2), pontos.length - 1];

  return (
    <svg className="gm-linha-svg" viewBox={`0 0 ${largura} ${altura}`} role="img"
      aria-label="Evolução da quantidade de visitas realizadas por dia">
      {[0, .5, 1].map((f) => (
        <g key={f}>
          <line x1={margem.esquerda} x2={largura - margem.direita}
            y1={margem.topo + h * f} y2={margem.topo + h * f} className="gm-grid-line" />
          <text x={margem.esquerda - 8} y={margem.topo + h * f + 4} textAnchor="end">
            {Math.round(maior * (1 - f))}
          </text>
        </g>
      ))}
      <path d={caminho} className="gm-linha-path" />
      {pontos.map((p, i) => (
        <circle key={p.dia} cx={x(i)} cy={y(p.total)} r="3.5" className="gm-linha-ponto">
          <title>{`${dataBR(p.dia)}: ${p.total} visita(s)`}</title>
        </circle>
      ))}
      {marcadores.map((i) => (
        <text key={pontos[i].dia} x={x(i)} y={altura - 7} textAnchor="middle">
          {dataBR(pontos[i].dia).slice(0, 5)}
        </text>
      ))}
    </svg>
  );
}

export default function GestaoVisitas() {
  const toast = useToast();
  const { idCorretor, permissao } = useAuth();
  const { equipesOpcoes, getNomeEquipe } = useEquipes();

  const [periodo, setPeriodo] = useState({ inicio: diasAtras(30), fim: iso(hoje()) });
  const [equipe, setEquipe] = useState("");
  const [resposta, setResposta] = useState("");
  const [soPendentes, setSoPendentes] = useState(false);
  const [busca, setBusca] = useState("");

  const [visitas, setVisitas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [revisando, setRevisando] = useState(null);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({});
  const [salvando, setSalvando] = useState(false);
  const [baixando, setBaixando] = useState(null);
  const [aba, setAba] = useState("visitas");
  // Evolução vem do servidor, não da agregação local: ela precisa de série por
  // corretor ao longo do tempo, e a lista carregada é achatada por visita.
  const [evolucao, setEvolucao] = useState(null);
  const [carregandoEvolucao, setCarregandoEvolucao] = useState(false);
  const [granularidade, setGranularidade] = useState("dia");
  const [dimensao, setDimensao] = useState("corretor");
  const [corretores, setCorretores] = useState([]);
  const [pdfCorretor, setPdfCorretor] = useState("");
  const visitaUrlAberta = useRef(false);

  const veTudo = ["diretor", "administrador", "administrativo", "inteligencia"].includes(
    norm(permissao),
  );

  const carregar = useCallback(async () => {
    if (!idCorretor) return;
    setCarregando(true);
    setErro("");
    try {
      const p = new URLSearchParams({ solicitante_id: idCorretor });
      if (equipe) p.set("id_gerente", equipe);
      if (periodo.inicio) p.set("inicio", periodo.inicio);
      if (periodo.fim) p.set("fim", periodo.fim);
      const r = await fetch(`${BASE}/gestao/visitas?${p.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao carregar visitas");
      setVisitas(d.itens || []);
    } catch (e) {
      setErro(e.message || "Erro ao carregar visitas");
      setVisitas([]);
    } finally {
      setCarregando(false);
    }
  }, [idCorretor, equipe, periodo.inicio, periodo.fim]);

  useEffect(() => { carregar(); }, [carregar]);

  const filtradas = useMemo(() => {
    const alvo = norm(busca);
    return visitas.filter((v) => {
      if (resposta && norm(v.proposta) !== resposta) return false;
      if (soPendentes && !v.revisao_pendente) return false;
      if (alvo) {
        const texto = [v.imovel, v.cliente, v.corretor, v.bairro].join(" ").toLowerCase();
        if (!texto.includes(alvo)) return false;
      }
      return true;
    });
  }, [visitas, resposta, soPendentes, busca]);

  const resumo = useMemo(() => {
    const conta = (r) => visitas.filter((v) => norm(v.proposta) === r).length;
    const sim = conta("sim");
    const total = visitas.length;
    return {
      total,
      sim,
      talvez: conta("talvez"),
      pendentes: visitas.filter((v) => v.revisao_pendente).length,
      pctSim: total ? `${Math.round((sim / total) * 1000) / 10}%` : "—",
    };
  }, [visitas]);

  /** Indicadores das visitas realizadas que estão visíveis com os filtros locais. */
  const indicadores = useMemo(() => {
    const mapa = new Map();
    const respostas = { sim: 0, talvez: 0, nao: 0, vazio: 0 };
    const corretores = new Map();
    filtradas.forEach((v) => {
      const d = String(v.data_visita || "").slice(0, 10);
      if (d) mapa.set(d, (mapa.get(d) || 0) + 1);
      const r = norm(v.proposta);
      respostas[Object.prototype.hasOwnProperty.call(respostas, r) ? r : "vazio"] += 1;
      const nome = v.corretor || "Sem corretor";
      corretores.set(nome, (corretores.get(nome) || 0) + 1);
    });
    const porDia = [...mapa.entries()].sort((a, b) => a[0].localeCompare(b[0]))
      .slice(-30).map(([dia, total]) => ({ dia, total }));
    const porResposta = Object.entries(respostas).map(([id, total]) => ({ id, total }));
    const porCorretor = [...corretores.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 8).map(([nome, total]) => ({ nome, total }));
    return { porDia, porResposta, porCorretor };
  }, [filtradas]);

  const pizzaResposta = useMemo(() => {
    const total = indicadores.porResposta.reduce((s, item) => s + item.total, 0);
    if (!total) return "conic-gradient(#e7e4eb 0 100%)";
    let inicio = 0;
    return `conic-gradient(${indicadores.porResposta.filter((item) => item.total).map((item) => {
      const fim = inicio + (item.total / total) * 100;
      const trecho = `${CORES_RESPOSTA[item.id]} ${inicio}% ${fim}%`;
      inicio = fim;
      return trecho;
    }).join(", ")})`;
  }, [indicadores.porResposta]);

  const marcarParteVista = async (v, pendencia, flag) => {
    if (revisando) return;
    setRevisando(`${v.id_visita}:${pendencia}`);
    try {
      const r = await fetch(`${BASE}/visitas/vistas?solicitante_id=${encodeURIComponent(idCorretor)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // `id_gerente` da tabela de flags é o id da EQUIPE — é assim que o painel casa.
        body: JSON.stringify({
          id_gerente: v.equipe, id_visita: v.id_visita,
          [flag]: true,
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui marcar");
      setVisitas((lista) => lista.map((x) => (
        x.id_visita === v.id_visita ? (() => {
          const pendencias = (x.pendencias || []).filter((p) => p !== pendencia);
          return { ...x, revisao_pendente: Boolean(pendencias.length), pendencias };
        })() : x
      )));
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setRevisando(null);
    }
  };

  const abrirNotas = (v) => {
    abrirEdicao(v);
    marcarParteVista(v, "notas", "viu_notas");
  };

  const abrirEdicao = (v) => {
    setEditando(v);
    setForm({
      dataVisita: String(v.data_visita || "").slice(0, 10),
      proposta: v.proposta || "",
      motivoSim: v.motivo_sim || "",
      motivoTalvez: v.motivo_talvez || "",
      enderecoExterno: v.endereco_externo || "",
      linkImagem: v.link_imagem || "",
      linkAudio: v.link_audio || "",
      anexoFichaVisita: v.anexo_ficha_visita || "",
      situacaoImovel: v.situacao_imovel || "",
      avaliacoes: v.avaliacoes || [],
    });
  };

  useEffect(() => {
    if (visitaUrlAberta.current || !visitas.length) return;
    const id = new URLSearchParams(window.location.search).get("visita");
    if (!id) return;
    const visita = visitas.find((v) => String(v.id_visita) === id);
    if (visita) {
      visitaUrlAberta.current = true;
      abrirEdicao(visita);
    }
  }, [visitas]); // abre uma unica vez o registro indicado pelo painel de tarefas

  const fecharEdicao = () => { setEditando(null); setForm({}); };

  const salvar = async (e) => {
    e.preventDefault();
    if (salvando || !editando) return;
    const resp = norm(form.proposta);
    // O campo cobrado depende da resposta — mesma regra que o servidor usa para decidir
    // se a visita tem pendência de motivo.
    if (resp === "sim" && !String(form.motivoSim).trim()) {
      toast("Resposta SIM exige o motivo.", "error"); return;
    }
    if (resp === "talvez" && !String(form.motivoTalvez).trim()) {
      toast("Resposta TALVEZ exige o motivo.", "error"); return;
    }
    setSalvando(true);
    try {
      const r = await fetch(`${BASE}/visitas/${encodeURIComponent(editando.id_visita)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui salvar");
      const motivo = resp === "sim" ? form.motivoSim : resp === "talvez" ? form.motivoTalvez : "";
      if (String(motivo || "").trim()) {
        await marcarParteVista(editando, "motivo", "add_motivo");
      }
      toast("Visita atualizada.", "success");
      fecharEdicao();
      carregar();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setSalvando(false);
    }
  };

  /** Baixa o PDF via fetch, não por link direto.
   *
   * A API exige `X-API-KEY`, injetado pelo interceptor global de `fetch`. Um `<a href>`
   * comum não passa por ele e receberia 401.
   */
  /** Imoveis e clientes do periodo, agregados a partir das MESMAS visitas filtradas.
   *
   *  Sem endpoint novo de proposito: as duas abas respondem por construcao aos mesmos
   *  filtros da aba de visitas. Um endpoint proprio precisaria repetir periodo, equipe,
   *  resposta e busca — e a primeira divergencia entre as duas implementacoes apareceria
   *  como "a lista mostra 12 imoveis e o resumo diz 15".
   */
  const agrupar = useCallback((chaveId, chaveNome) => {
    const mapa = new Map();
    filtradas.forEach((v) => {
      const id = v[chaveId];
      if (!id) return;
      if (!mapa.has(id)) {
        mapa.set(id, {
          id,
          nome: v[chaveNome] || id,
          visitas: 0,
          // Set porque a mesma visita repete cliente/imovel: contar linhas daria
          // "3 clientes" para o mesmo cliente que voltou tres vezes.
          outros: new Set(),
          corretores: new Set(),
          respostas: { Sim: 0, Talvez: 0, Nao: 0 },
          notas: [],
          ultima: null,
          pendentes: 0,
        });
      }
      const item = mapa.get(id);
      item.visitas += 1;
      const outro = chaveId === "id_imovel" ? v.cliente : v.imovel;
      if (outro) item.outros.add(outro);
      if (v.corretor) item.corretores.add(v.corretor);
      const r = norm(v.proposta);
      if (r === "sim") item.respostas.Sim += 1;
      else if (r === "talvez") item.respostas.Talvez += 1;
      else if (r === "nao" || r === "não") item.respostas.Nao += 1;
      (v.avaliacoes || []).forEach((av) => {
        const n = Number(av.notaGeral);
        if (!Number.isNaN(n) && av.notaGeral != null) item.notas.push(n);
      });
      if (v.revisao_pendente) item.pendentes += 1;
      if (!item.ultima || (v.data_visita || "") > item.ultima) item.ultima = v.data_visita;
    });
    return [...mapa.values()]
      .map((item) => ({
        ...item,
        outros: item.outros.size,
        corretores: [...item.corretores].join(", "),
        nota: item.notas.length
          ? (item.notas.reduce((x, y) => x + y, 0) / item.notas.length).toFixed(1)
          : null,
      }))
      .sort((x, y) => y.visitas - x.visitas || String(x.nome).localeCompare(String(y.nome)));
  }, [filtradas]);

  // Só busca quando a aba está aberta: é uma consulta a mais, e a tela abre em Visitas.
  useEffect(() => {
    if (aba !== "evolucao" || !idCorretor) return;
    let vivo = true;
    setCarregandoEvolucao(true);
    (async () => {
      try {
        const p = new URLSearchParams({
          start: periodo.inicio, end: periodo.fim,
          granularidade, dimensao,
        });
        if (equipe) p.set("id_gerente", equipe);
        const r = await fetch(`${BASE}/gerente-dashboard/visitas/evolucao?${p.toString()}`);
        const d = await r.json();
        if (vivo) setEvolucao(r.ok && d.ok !== false ? d : null);
      } catch {
        if (vivo) setEvolucao(null);
      } finally {
        if (vivo) setCarregandoEvolucao(false);
      }
    })();
    return () => { vivo = false; };
  }, [aba, idCorretor, periodo.inicio, periodo.fim, equipe, granularidade, dimensao]);

  // Lista de corretores para o PDF individual: a visita traz o NOME, e o endpoint do
  // PDF quer o id.
  useEffect(() => {
    if (!idCorretor) return;
    (async () => {
      try {
        const r = await fetch(`${BASE}/propostas/corretores?solicitante_id=${encodeURIComponent(idCorretor)}`);
        const d = await r.json();
        if (r.ok && d.ok !== false) setCorretores(d.itens || []);
      } catch { /* sem lista, só o PDF individual fica indisponível */ }
    })();
  }, [idCorretor]);

  /** Ranking por pessoa ou equipe, das MESMAS visitas filtradas.
   *
   *  `agrupar` acima nao serve: la a chave e um id de registro (imovel, cliente) e o que
   *  interessa e quantos DISTINTOS passaram por ele. Aqui a chave e quem fez a visita, e
   *  o que interessa e o resultado — quanto virou interesse do cliente.
   */
  const ranquear = useCallback((chave, rotular) => {
    const mapa = new Map();
    filtradas.forEach((v) => {
      const id = v[chave];
      if (!id) return;
      if (!mapa.has(id)) {
        mapa.set(id, {
          id, nome: rotular ? rotular(id) : id,
          visitas: 0, clientes: new Set(), imoveis: new Set(),
          sim: 0, talvez: 0, nao: 0, notas: [], pendentes: 0,
        });
      }
      const item = mapa.get(id);
      item.visitas += 1;
      if (v.id_cliente) item.clientes.add(v.id_cliente);
      if (v.id_imovel) item.imoveis.add(v.id_imovel);
      const r = norm(v.proposta);
      if (r === "sim") item.sim += 1;
      else if (r === "talvez") item.talvez += 1;
      else if (r === "nao" || r === "não") item.nao += 1;
      (v.avaliacoes || []).forEach((av) => {
        const n = Number(av.notaGeral);
        if (av.notaGeral != null && !Number.isNaN(n)) item.notas.push(n);
      });
      if (v.revisao_pendente) item.pendentes += 1;
    });
    return [...mapa.values()]
      .map((item) => ({
        ...item,
        clientes: item.clientes.size,
        imoveis: item.imoveis.size,
        // Interesse = SIM ou TALVEZ. Sobre as visitas COM resposta, nao sobre todas:
        // visita sem resposta registrada nao e recusa, e dado que falta.
        respondidas: item.sim + item.talvez + item.nao,
        taxa: (item.sim + item.talvez + item.nao)
          ? Math.round(((item.sim + item.talvez) / (item.sim + item.talvez + item.nao)) * 1000) / 10
          : null,
        nota: item.notas.length
          ? (item.notas.reduce((x, y) => x + y, 0) / item.notas.length).toFixed(1)
          : null,
      }))
      .sort((x, y) => y.visitas - x.visitas || String(x.nome).localeCompare(String(y.nome)));
  }, [filtradas]);

  const rankCorretor = useMemo(() => ranquear("corretor"), [ranquear]);
  const rankEquipe = useMemo(
    () => ranquear("equipe", (id) => getNomeEquipe(id) || id),
    [ranquear, getNomeEquipe],
  );

  const imoveis = useMemo(() => agrupar("id_imovel", "imovel"), [agrupar]);
  const clientes = useMemo(() => agrupar("id_cliente", "cliente"), [agrupar]);

  /* Distribuicao de clientes por numero de visitas.
   *
   * A aba Clientes ja mostra o ranking — quem visitou mais. O que ela nao responde e a
   * forma da cauda: se a operacao vive de cliente que vem uma vez so ou de cliente que
   * volta. Sao decisoes diferentes (captar mais x cuidar melhor de quem ja esta na mao).
   *
   * Faixas em vez de valor exato porque a cauda e longa e esparsa: um cliente com 11
   * visitas e outro com 9 viram duas barras de altura 1 que nao dizem nada. `6+` junta.
   *
   * Reusa `clientes`, que ja e o agrupamento por id_cliente do periodo filtrado — contar
   * de novo a partir de `filtradas` daria os mesmos numeros com risco de divergir depois. */
  const porVisitasCliente = useMemo(() => {
    const faixas = [
      { rotulo: "1 visita", teste: (n) => n === 1 },
      { rotulo: "2 visitas", teste: (n) => n === 2 },
      { rotulo: "3 visitas", teste: (n) => n === 3 },
      { rotulo: "4 a 5 visitas", teste: (n) => n >= 4 && n <= 5 },
      { rotulo: "6 ou mais", teste: (n) => n >= 6 },
    ];
    const dados = faixas.map(({ rotulo, teste }) => ({
      rotulo,
      total: clientes.filter((c) => teste(c.visitas)).length,
    }));
    const voltaram = clientes.filter((c) => c.visitas > 1).length;
    return {
      // Faixa vazia vira barra de altura zero e so ocupa espaco.
      dados: dados.filter((d) => d.total),
      voltaram,
      pctVoltaram: clientes.length ? Math.round((voltaram / clientes.length) * 100) : 0,
      media: clientes.length
        ? (clientes.reduce((s, c) => s + c.visitas, 0) / clientes.length).toFixed(1)
        : "0,0",
    };
  }, [clientes]);

  /** PDF por fetch, nao por link: a API exige X-API-KEY, injetado no `fetch` global. */
  const baixarPdfDe = async (rotulo, url, chave, nome) => {
    if (baixando) return;
    setBaixando(chave);
    try {
      const r = await fetch(`${BASE}${url}`);
      if (!r.ok) throw new Error(`Nao consegui gerar o PDF do ${rotulo}.`);
      const blob = await r.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `${rotulo}-${nome}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
    } catch (e) {
      toast(e.message || "Nao consegui gerar o PDF", "error");
    } finally {
      setBaixando(null);
    }
  };

  const baixarPdf = async (v) => {
    if (baixando) return;
    setBaixando(v.id_visita);
    try {
      const r = await fetch(`${BASE}/visitas/pdf/download?visita_id=${encodeURIComponent(v.id_visita)}`);
      if (!r.ok) throw new Error("Não consegui gerar o PDF");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `visita-${v.id_visita}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBaixando(null);
    }
  };

  return (
    <div className="gm">
      <header className="gm-topo">
        <div>
          <span className="gm-eyebrow">Módulo</span>
          <h1>Gestão de Visitas</h1>
          <p>
            Visitas realizadas, resposta do cliente e o que ainda falta o gerente revisar.
          </p>
        </div>
      </header>

      <div className="gm-barra">
        <label>De
          <input type="date" value={periodo.inicio}
            onChange={(e) => setPeriodo((p) => ({ ...p, inicio: e.target.value }))} />
        </label>
        <label>Até
          <input type="date" value={periodo.fim}
            onChange={(e) => setPeriodo((p) => ({ ...p, fim: e.target.value }))} />
        </label>
        {veTudo && (
          <label>Equipe
            <select value={equipe} onChange={(e) => setEquipe(e.target.value)}>
              <option value="">Todas as equipes</option>
              {porRotulo(equipesOpcoes).map((eq) => (
                <option key={eq.value} value={eq.value}>{eq.label}</option>
              ))}
            </select>
          </label>
        )}
        <label>Resposta
          <select value={resposta} onChange={(e) => setResposta(e.target.value)}>
            {RESPOSTAS.map((r) => <option key={r.id || "t"} value={r.id}>{r.rotulo}</option>)}
          </select>
        </label>
        <label className="gm-busca">Buscar
          <input placeholder="Imóvel, cliente ou corretor" value={busca}
            onChange={(e) => setBusca(e.target.value)} />
        </label>
        <button
          type="button"
          className={`gm-toggle ${soPendentes ? "is-ativo" : ""}`}
          aria-pressed={soPendentes}
          onClick={() => setSoPendentes((v) => !v)}
        >
          Só a revisar{resumo.pendentes ? ` (${resumo.pendentes})` : ""}
        </button>
      </div>

      <div className="gm-cards">
        <div className="gm-card"><span>Visitas</span><strong>{carregando ? "…" : resumo.total}</strong></div>
        <div className="gm-card"><span>Com SIM</span><strong>{carregando ? "…" : resumo.sim}</strong></div>
        <div className="gm-card"><span>Com TALVEZ</span><strong>{carregando ? "…" : resumo.talvez}</strong></div>
        <div className="gm-card"><span>% SIM</span><strong>{carregando ? "…" : resumo.pctSim}</strong></div>
        <div className={`gm-card ${resumo.pendentes ? "is-alerta" : ""}`}>
          <span>A revisar</span><strong>{carregando ? "…" : resumo.pendentes}</strong>
        </div>
      </div>

      {!carregando && !!filtradas.length && (
        <section className="gm-dashboard" aria-label="Indicadores das visitas filtradas">
          <article className="gm-grafico gm-grafico--linha">
            <header>
              <div><h4>Evolução das visitas</h4><p>Visitas realizadas por dia</p></div>
              <span className="gm-grafico-total">{filtradas.length}</span>
            </header>
            <LinhaVisitas pontos={indicadores.porDia} />
          </article>
          <article className="gm-grafico">
            <header><div><h4>Respostas do cliente</h4><p>Distribuição no período</p></div></header>
            <div className="gm-pizza-wrap">
              <div className="gm-pizza" style={{ background: pizzaResposta }} aria-hidden="true">
                <span><strong>{filtradas.length}</strong><small>visitas</small></span>
              </div>
              <div className="gm-legenda">
                {indicadores.porResposta.map((item) => (
                  <div key={item.id}>
                    <i style={{ background: CORES_RESPOSTA[item.id] }} />
                    <span>{rotuloResposta(item.id)}</span><strong>{item.total}</strong>
                    <small>{Math.round((item.total / filtradas.length) * 100)}%</small>
                  </div>
                ))}
              </div>
            </div>
          </article>
          <article className="gm-grafico gm-grafico--ranking">
            <header><div><h4>Visitas por corretor</h4><p>Até 8 maiores volumes no filtro</p></div></header>
            <div className="gm-ranking">
              {indicadores.porCorretor.map((item) => {
                const maior = indicadores.porCorretor[0]?.total || 1;
                return (
                  <div key={item.nome} className="gm-ranking-item" title={`${item.nome}: ${item.total} visita(s)`}>
                    <span>{item.nome}</span><div><i style={{ width: `${(item.total / maior) * 100}%` }} /></div>
                    <strong>{item.total}</strong>
                  </div>
                );
              })}
            </div>
          </article>
          <article className="gm-grafico gm-grafico--ranking">
            <header>
              <div>
                <h4>Visitas por cliente</h4>
                <p>{porVisitasCliente.voltaram} de {clientes.length} voltaram
                  ({porVisitasCliente.pctVoltaram}%) — média de {porVisitasCliente.media} por cliente</p>
              </div>
              <span className="gm-grafico-total">{clientes.length}</span>
            </header>
            <GraficoBarras dados={porVisitasCliente.dados} sufixo="cliente(s)" />
          </article>
        </section>
      )}

      {/* PDFs consolidados do período, herdados do Relatório do Gerente. Diferentes dos
          PDFs das abas, que são de um registro só: aqui é o fechamento do período —
          corretor no mês, gerente com a equipe toda, comparativo entre equipes. */}
      <div className="gm-pdfs-barra">
        <span className="gm-pdfs-rotulo">Relatórios do período</span>
        <select value={pdfCorretor} onChange={(e) => setPdfCorretor(e.target.value)}
          aria-label="Corretor do relatório individual">
          <option value="">Escolha o corretor…</option>
          {corretores.map((co) => (
            <option key={co.id} value={co.id}>{co.nome}</option>
          ))}
        </select>
        <button type="button" className="gm-btn" disabled={!pdfCorretor || baixando === "pdf-corretor"}
          onClick={() => baixarPdfDe(
            "corretor",
            `/gerente-dashboard/corretor/pdf/download?id_corretor=${encodeURIComponent(pdfCorretor)}`
            + `&start=${periodo.inicio}&end=${periodo.fim}`,
            "pdf-corretor", pdfCorretor,
          )}>
          {baixando === "pdf-corretor" ? "Gerando…" : "PDF do corretor"}
        </button>
        <button type="button" className="gm-btn" disabled={!equipe || baixando === "pdf-gerente"}
          title={equipe ? "" : "Escolha uma equipe no filtro acima"}
          onClick={() => baixarPdfDe(
            "gerente",
            `/gerente-dashboard/gerente/pdf/download?id_gerente=${encodeURIComponent(equipe)}`
            + `&start=${periodo.inicio}&end=${periodo.fim}`,
            "pdf-gerente", equipe,
          )}>
          {baixando === "pdf-gerente" ? "Gerando…" : "PDF do gerente"}
        </button>
        <button type="button" className="gm-btn" disabled={baixando === "pdf-equipes"}
          onClick={() => baixarPdfDe(
            "equipes",
            `/gerente-dashboard/equipes/pdf/download?start=${periodo.inicio}&end=${periodo.fim}`,
            "pdf-equipes", "periodo",
          )}>
          {baixando === "pdf-equipes" ? "Gerando…" : "PDF por equipe"}
        </button>
      </div>

      <div className="gm-abas" role="tablist" aria-label="Visoes da gestao de visitas">
        {[
          ["visitas", `Visitas (${filtradas.length})`],
          ["imoveis", `Imoveis visitados (${imoveis.length})`],
          ["clientes", `Clientes que visitaram (${clientes.length})`],
          ["ranking", `Ranking (${rankCorretor.length})`],
          ["evolucao", "Evolução"],
        ].map(([id, rotulo]) => (
          <button key={id} type="button" role="tab" aria-selected={aba === id}
            className={aba === id ? "is-ativa" : ""} onClick={() => setAba(id)}>
            {rotulo}
          </button>
        ))}
      </div>

      {erro && <p className="gm-estado gm-estado--erro">{erro}</p>}
      {carregando && <p className="gm-estado">Carregando visitas…</p>}
      {!carregando && !erro && !filtradas.length && (
        <p className="gm-estado">Nenhuma visita com esse filtro.</p>
      )}

      {aba === "visitas" && !!filtradas.length && (
        <div className="gm-tabela-wrap">
          <table className="gm-tabela">
            <thead>
              <tr>
                <th>Data</th><th>Imóvel</th><th>Cliente</th><th>Corretor</th>
                <th>Resposta</th><th>Revisão</th><th />
              </tr>
            </thead>
            <tbody>
              {filtradas.map((v) => (
                <tr key={v.id_visita}>
                  <td>{dataBR(v.data_visita)}</td>
                  <td>
                    <strong>{v.imovel || "—"}</strong>
                    <span>{v.bairro || ""}</span>
                  </td>
                  <td>{v.cliente || "—"}</td>
                  <td>
                    {v.corretor || "—"}
                    <span>{v.equipe ? getNomeEquipe(v.equipe) : ""}</span>
                  </td>
                  <td>
                    <span className={`gm-selo r-${norm(v.proposta) || "vazio"}`}>
                      {v.proposta || "—"}
                    </span>
                  </td>
                  <td>
                    {v.revisao_pendente
                      ? <span className="gm-selo r-pendente">
                          {(v.pendencias || []).join(", ") || "pendente"}
                        </span>
                      : <span className="gm-selo r-ok">revisada</span>}
                  </td>
                  <td className="gm-acoes-col">
                    <button type="button" className="gm-btn" onClick={() => abrirEdicao(v)}>
                      Editar
                    </button>
                    {(v.pendencias || []).includes("motivo")
                      && ["sim", "talvez"].includes(norm(v.proposta)) && (
                      <button type="button" className="gm-btn gm-btn--primario"
                        onClick={() => abrirEdicao(v)}>
                        Adicionar motivo
                      </button>
                    )}
                    {v.link_imagem && (
                      <a className="gm-btn" href={v.link_imagem} target="_blank" rel="noreferrer"
                        onClick={() => marcarParteVista(v, "anexo", "viu_anexo")}>
                        Abrir anexo
                      </a>
                    )}
                    <button type="button" className="gm-btn" onClick={() => abrirNotas(v)}>
                      Abrir notas
                    </button>
                    <button type="button" className="gm-btn"
                      onClick={() => baixarPdf(v)} disabled={baixando === v.id_visita}>
                      {baixando === v.id_visita ? "Gerando…" : "PDF"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Imoveis e clientes: mesma estrutura, colunas espelhadas. O que muda e o que a
          linha AGREGA — no imovel, quantos clientes distintos passaram; no cliente,
          quantos imoveis distintos viu. */}
      {(aba === "imoveis" || aba === "clientes") && (() => {
        const ehImovel = aba === "imoveis";
        const linhas = ehImovel ? imoveis : clientes;
        if (!linhas.length) {
          return <p className="gm-estado">Nenhum registro com esse filtro.</p>;
        }
        return (
          <div className="gm-tabela-wrap">
            <table className="gm-tabela">
              <thead>
                <tr>
                  <th>{ehImovel ? "Imóvel" : "Cliente"}</th>
                  <th>Visitas</th>
                  <th>{ehImovel ? "Clientes" : "Imóveis"}</th>
                  <th>Corretor(es)</th>
                  <th>Respostas</th>
                  <th>Nota</th>
                  <th>Última</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {linhas.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {item.nome}
                      {item.pendentes > 0 && (
                        <span className="gm-selo" title="Visitas com revisão pendente">
                          {item.pendentes} a revisar
                        </span>
                      )}
                    </td>
                    <td>{item.visitas}</td>
                    <td>{item.outros}</td>
                    <td className="gm-col-larga">{item.corretores || "—"}</td>
                    <td className="gm-respostas">
                      {item.respostas.Sim > 0 && <b className="r-sim">{item.respostas.Sim} sim</b>}
                      {item.respostas.Talvez > 0 && <b className="r-talvez">{item.respostas.Talvez} talvez</b>}
                      {item.respostas.Nao > 0 && <b className="r-nao">{item.respostas.Nao} não</b>}
                      {!item.respostas.Sim && !item.respostas.Talvez && !item.respostas.Nao && "—"}
                    </td>
                    <td>{item.nota ?? "—"}</td>
                    <td>{dataBR(item.ultima)}</td>
                    <td>
                      <button
                        type="button"
                        className="gm-btn"
                        disabled={baixando === item.id}
                        onClick={() => baixarPdfDe(
                          ehImovel ? "imovel" : "cliente",
                          ehImovel
                            ? `/imoveis/pdf/download?imovel_id=${encodeURIComponent(item.id)}`
                            : `/clientes/pdf/download?id_cliente=${encodeURIComponent(item.id)}`,
                          item.id,
                          item.id,
                        )}
                      >
                        {baixando === item.id ? "Gerando…" : "PDF"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })()}

      {aba === "ranking" && (
        !rankCorretor.length ? (
          <p className="gm-estado">Nenhuma visita com esse filtro.</p>
        ) : (
          <>
            {/* Pódio dos três primeiros. O resto vem na tabela abaixo — o pódio é para
                reconhecer, a tabela é para comparar. */}
            <div className="gm-podio">
              {rankCorretor.slice(0, 3).map((item, i) => (
                <article key={item.id} className={`gm-podio-item p-${i + 1}`}>
                  <span className="gm-podio-pos">{i + 1}º</span>
                  <strong className="gm-podio-nome">{item.nome}</strong>
                  <span className="gm-podio-visitas">{item.visitas}</span>
                  <small>visita{item.visitas === 1 ? "" : "s"}</small>
                  <div className="gm-podio-extra">
                    <span>{item.clientes} cliente(s)</span>
                    <span>{item.taxa == null ? "—" : `${item.taxa}% interesse`}</span>
                  </div>
                </article>
              ))}
            </div>

            <div className="gm-tabela-wrap">
              <table className="gm-tabela gm-tabela--rank">
                <thead>
                  <tr>
                    <th>#</th><th>Corretor</th><th>Visitas</th><th>Clientes</th>
                    <th>Imóveis</th><th>Sim</th><th>Talvez</th><th>Não</th>
                    <th>Interesse</th><th>Nota</th><th>A revisar</th>
                  </tr>
                </thead>
                <tbody>
                  {rankCorretor.map((item, i) => (
                    <tr key={item.id}>
                      <td className="gm-rank-pos">{i + 1}</td>
                      <td>{item.nome}</td>
                      <td>
                        {/* Barra proporcional ao líder: a comparação que interessa é
                            relativa, e o número absoluto está do lado. */}
                        <div className="gm-rank-barra">
                          <span style={{
                            width: `${Math.max(4, (item.visitas / rankCorretor[0].visitas) * 100)}%`,
                          }} />
                          <b>{item.visitas}</b>
                        </div>
                      </td>
                      <td>{item.clientes}</td>
                      <td>{item.imoveis}</td>
                      <td className="r-sim">{item.sim || "—"}</td>
                      <td className="r-talvez">{item.talvez || "—"}</td>
                      <td className="r-nao">{item.nao || "—"}</td>
                      <td>
                        {item.taxa == null ? "—" : (
                          <span className={`gm-taxa ${item.taxa < 50 ? "is-baixa" : ""}`}>
                            {item.taxa}%
                          </span>
                        )}
                      </td>
                      <td>{item.nota ?? "—"}</td>
                      <td>
                        {item.pendentes
                          ? <span className="gm-selo">{item.pendentes}</span>
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Só faz sentido quando há mais de uma equipe no recorte — para o gerente
                seria uma tabela de uma linha só. */}
            {rankEquipe.length > 1 && (
              <div className="gm-tabela-wrap gm-rank-equipes">
                <h4 className="gm-rank-titulo">Por equipe</h4>
                <table className="gm-tabela gm-tabela--rank">
                  <thead>
                    <tr>
                      <th>#</th><th>Equipe</th><th>Visitas</th><th>Clientes</th>
                      <th>Imóveis</th><th>Interesse</th><th>Nota</th><th>A revisar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankEquipe.map((item, i) => (
                      <tr key={item.id}>
                        <td className="gm-rank-pos">{i + 1}</td>
                        <td>{item.nome}</td>
                        <td>
                          <div className="gm-rank-barra">
                            <span style={{
                              width: `${Math.max(4, (item.visitas / rankEquipe[0].visitas) * 100)}%`,
                            }} />
                            <b>{item.visitas}</b>
                          </div>
                        </td>
                        <td>{item.clientes}</td>
                        <td>{item.imoveis}</td>
                        <td>
                          {item.taxa == null ? "—" : (
                            <span className={`gm-taxa ${item.taxa < 50 ? "is-baixa" : ""}`}>
                              {item.taxa}%
                            </span>
                          )}
                        </td>
                        <td>{item.nota ?? "—"}</td>
                        <td>{item.pendentes || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )
      )}

      {aba === "evolucao" && (
        <article className="gm-grafico">
          <header>
            <div>
              <h4>Evolução das visitas</h4>
              <p>
                {evolucao?.resumo
                  ? `${evolucao.resumo.total_visitas} visitas · ${evolucao.resumo.clientes_unicos} clientes · ${evolucao.resumo.imoveis_unicos} imóveis`
                  : "Quem visitou, e quando, ao longo do período"}
              </p>
            </div>
            <div className="gm-grafico-controles">
              <select value={dimensao} onChange={(e) => setDimensao(e.target.value)}
                aria-label="Agrupar a evolução por">
                <option value="corretor">Por corretor</option>
                <option value="equipe">Por equipe</option>
              </select>
              <select value={granularidade} onChange={(e) => setGranularidade(e.target.value)}
                aria-label="Granularidade da evolução">
                <option value="dia">Por dia</option>
                <option value="semana">Por semana</option>
                <option value="mes">Por mês</option>
              </select>
            </div>
          </header>
          {carregandoEvolucao ? (
            <p className="gm-estado">Montando a evolução…</p>
          ) : !evolucao ? (
            <p className="gm-estado">Não consegui carregar a evolução deste recorte.</p>
          ) : (
            <GraficoMultiLinha
              datas={evolucao.datas || []}
              series={evolucao.series || []}
              rotuloAria="Evolução das visitas por período"
            />
          )}
        </article>
      )}

      {editando && (
        <div className="gm-modal-bg" onClick={fecharEdicao}>
          <form className="gm-modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
            <header>
              <div>
                <span className="gm-eyebrow">Visita {editando.id_visita}</span>
                <h3>{editando.imovel || "Editar visita"}</h3>
              </div>
              <button type="button" onClick={fecharEdicao} aria-label="Fechar">✕</button>
            </header>

            <p className="gm-modal-alvo">
              {editando.cliente || "Sem cliente"}
              <small>{editando.corretor}{editando.equipe ? ` · ${getNomeEquipe(editando.equipe)}` : ""}</small>
            </p>

            <div className="gm-modal-grid">
              <label>Data da visita
                <input type="date" value={form.dataVisita || ""}
                  onChange={(e) => setForm((f) => ({ ...f, dataVisita: e.target.value }))} />
              </label>
              <label>Resposta do cliente
                <select value={form.proposta || ""}
                  onChange={(e) => setForm((f) => ({ ...f, proposta: e.target.value }))}>
                  <option value="">Não respondido</option>
                  <option value="Sim">SIM</option>
                  <option value="Talvez">TALVEZ</option>
                  <option value="Nao">NÃO</option>
                </select>
              </label>

              {/* Só o motivo da resposta escolhida aparece: pedir os dois convida a
                  preencher o errado, e é o campo errado que deixa a pendência de pé. */}
              {norm(form.proposta) === "sim" && (
                <label className="gm-largo">Motivo do SIM *
                  <textarea rows={2} value={form.motivoSim || ""}
                    placeholder="O que fez o cliente querer avançar"
                    onChange={(e) => setForm((f) => ({ ...f, motivoSim: e.target.value }))} />
                </label>
              )}
              {norm(form.proposta) === "talvez" && (
                <label className="gm-largo">Motivo do TALVEZ *
                  <textarea rows={2} value={form.motivoTalvez || ""}
                    placeholder="O que ficou pendente para o cliente decidir"
                    onChange={(e) => setForm((f) => ({ ...f, motivoTalvez: e.target.value }))} />
                </label>
              )}

              <label className="gm-largo">Link da imagem
                <input value={form.linkImagem || ""} placeholder="https://drive.google.com/…"
                  onChange={(e) => setForm((f) => ({ ...f, linkImagem: e.target.value }))} />
              </label>
              <label className="gm-largo">Link do áudio
                <input value={form.linkAudio || ""} placeholder="https://drive.google.com/…"
                  onChange={(e) => setForm((f) => ({ ...f, linkAudio: e.target.value }))} />
              </label>
              <label className="gm-largo">Situação do imóvel
                <select value={form.situacaoImovel || ""}
                  onChange={(e) => setForm((f) => ({ ...f, situacaoImovel: e.target.value }))}>
                  <option value="">Manter como está</option>
                  <option value="CAPTACAO_61">Captação 61</option>
                  <option value="IMOVEL_NAO_CAPTADO">Imóvel não captado</option>
                </select>
              </label>
              <label className="gm-largo">Arquivo da ficha
                <input value={form.anexoFichaVisita || ""}
                  placeholder="Caminho ou link do arquivo"
                  onChange={(e) => setForm((f) => ({ ...f, anexoFichaVisita: e.target.value }))} />
              </label>
              <label className="gm-largo">Endereço externo
                <input value={form.enderecoExterno || ""}
                  placeholder="Só para imóvel fora do CRM"
                  onChange={(e) => setForm((f) => ({ ...f, enderecoExterno: e.target.value }))} />
              </label>
            </div>

            <h4 className="gm-subtitulo">Avaliação do imóvel</h4>
            <Avaliacoes
              avaliacoes={form.avaliacoes || []}
              onChange={(lista) => setForm((f) => ({ ...f, avaliacoes: lista }))}
            />

            {!!(editando.pendencias || []).length && (
              <p className="gm-nota gm-nota--modal">
                Falta revisar: <strong>{editando.pendencias.join(", ")}</strong>. Preencher o
                motivo aqui resolve essa parte; anexo e notas só contam quando forem
                abertos pelos respectivos botões.
              </p>
            )}

            <footer>
              <button type="button" className="gm-btn" onClick={() => baixarPdf(editando)}
                disabled={baixando === editando.id_visita}>
                {baixando === editando.id_visita ? "Gerando…" : "Baixar PDF"}
              </button>
              <span className="gm-espaco" />
              <button type="button" className="gm-btn" onClick={fecharEdicao} disabled={salvando}>
                Cancelar
              </button>
              <button type="submit" className="gm-btn gm-btn--primario" disabled={salvando}>
                {salvando ? "Salvando…" : "Salvar alterações"}
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
}
