import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
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
 * O checkout de revisão marca as três flags de uma vez (`viu_anexo`, `viu_notas`,
 * `add_motivo`). Elas são monotônicas: uma vez `true`, permanecem.
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

  const revisar = async (v) => {
    if (revisando) return;
    setRevisando(v.id_visita);
    try {
      const r = await fetch(`${BASE}/visitas/vistas?solicitante_id=${encodeURIComponent(idCorretor)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // `id_gerente` da tabela de flags é o id da EQUIPE — é assim que o painel casa.
        body: JSON.stringify({
          id_gerente: v.equipe, id_visita: v.id_visita,
          viu_anexo: true, viu_notas: true, add_motivo: true,
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui marcar");
      toast("Visita marcada como revisada.", "success");
      setVisitas((lista) => lista.map((x) => (
        x.id_visita === v.id_visita ? { ...x, revisao_pendente: false, pendencias: [] } : x
      )));
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setRevisando(null);
    }
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
    });
  };

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
        </section>
      )}

      {erro && <p className="gm-estado gm-estado--erro">{erro}</p>}
      {carregando && <p className="gm-estado">Carregando visitas…</p>}
      {!carregando && !erro && !filtradas.length && (
        <p className="gm-estado">Nenhuma visita com esse filtro.</p>
      )}

      {!!filtradas.length && (
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
                    <button type="button" className="gm-btn"
                      onClick={() => baixarPdf(v)} disabled={baixando === v.id_visita}>
                      {baixando === v.id_visita ? "Gerando…" : "PDF"}
                    </button>
                    {v.revisao_pendente && (
                      <button type="button" className="gm-btn gm-btn--primario"
                        onClick={() => revisar(v)} disabled={revisando === v.id_visita}>
                        {revisando === v.id_visita ? "Marcando…" : "Revisar"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
              <label className="gm-largo">Endereço externo
                <input value={form.enderecoExterno || ""}
                  placeholder="Só para imóvel fora do CRM"
                  onChange={(e) => setForm((f) => ({ ...f, enderecoExterno: e.target.value }))} />
              </label>
            </div>

            {!!(editando.pendencias || []).length && (
              <p className="gm-nota gm-nota--modal">
                Falta revisar: <strong>{editando.pendencias.join(", ")}</strong>. Preencher o
                motivo aqui resolve essa parte; anexo e notas você marca com o botão
                Revisar na lista.
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
