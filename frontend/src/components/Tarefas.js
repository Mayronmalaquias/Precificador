import React, { useCallback, useEffect, useRef, useState } from "react";
import { BASE } from "../services/api";
import { useAuth } from "../context/AuthContext";
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
  { id: "cliente", rotulo: "Clientes" },
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
    campos: [
      { nome: "cliente", rotulo: "Cliente" },
      { nome: "codigo_imovel", rotulo: "Código do imóvel" },
      { nome: "imovel_endereco", rotulo: "Endereço", largo: true },
      { nome: "valor", rotulo: "Valor (R$)", tipo: "number" },
      { nome: "data_proposta", rotulo: "Data da proposta", tipo: "date" },
      {
        nome: "situacao", rotulo: "Situação", tipo: "select",
        opcoes: [
          ["em_analise", "Em análise"], ["contraproposta", "Contraproposta"],
          ["aceita", "Aceita"], ["vendido", "Vendido"],
          ["recusada", "Recusada"], ["cancelada", "Cancelada"],
        ],
      },
      { nome: "observacao", rotulo: "Observação", tipo: "textarea", largo: true },
    ],
  },
  visita: {
    rotulo: "Visita",
    id: (t) => t.acao.id,
    url: (id) => `/visitas/${id}`,
    metodo: "PUT",
    extrair: (d) => d.visita || d,
    // Nomes do PUT de visita são camelCase; o GET devolve snake_case. `de`/`para` fazem
    // a tradução em vez de espalhar o nome dos dois lados pelo componente.
    campos: [
      { nome: "dataVisita", de: "data_visita", rotulo: "Data da visita", tipo: "date" },
      {
        nome: "proposta", rotulo: "Resposta do cliente", tipo: "select",
        opcoes: [["", "Sem resposta"], ["Sim", "SIM"], ["Talvez", "TALVEZ"], ["Nao", "NÃO"]],
      },
      { nome: "motivoSim", de: "motivo_sim", rotulo: "Motivo do SIM", largo: true },
      { nome: "motivoTalvez", de: "motivo_talvez", rotulo: "Motivo do TALVEZ", largo: true },
      { nome: "linkImagem", de: "link_imagem", rotulo: "Link da imagem (anexo)", largo: true },
      { nome: "linkAudio", de: "link_audio", rotulo: "Link do áudio", largo: true },
      { nome: "enderecoExterno", de: "endereco_externo", rotulo: "Endereço externo", largo: true },
    ],
  },
  lead: {
    rotulo: "Lead",
    id: (t) => t.acao.id,
    url: (id) => `/leads/gestao/${id}`,
    metodo: "PATCH",
    extrair: (d) => d.lead || d,
    campos: [
      { nome: "cliente", rotulo: "Cliente", largo: true },
      { nome: "telefone", rotulo: "Telefone" },
      { nome: "codigo_imovel", rotulo: "Código do imóvel" },
      { nome: "fonte", rotulo: "Fonte" },
      { nome: "observacao", rotulo: "Observação", tipo: "textarea", largo: true },
    ],
  },
  cliente: {
    rotulo: "Cliente",
    id: (t) => t.acao.id_cliente,
    url: (id) => `/clientes/${id}`,
    metodo: "PUT",
    extrair: (d) => d.cliente || d,
    campos: [
      { nome: "nome", rotulo: "Nome", largo: true },
      { nome: "telefone", rotulo: "Telefone" },
      { nome: "email", rotulo: "E-mail", tipo: "email" },
    ],
  },
};

// A resposta do cliente na visita muda o motivo que o servidor cobra — só faz sentido
// mostrar o campo da resposta escolhida.
const MOTIVO_DA_RESPOSTA = { sim: "motivoSim", talvez: "motivoTalvez" };

export default function Tarefas() {
  const toast = useToast();
  const { idCorretor } = useAuth();

  const [dados, setDados] = useState({ itens: [], resumo: {}, escopo: {} });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [tipo, setTipo] = useState("");
  const [nivel, setNivel] = useState("");
  const [responsavel, setResponsavel] = useState("");

  // Tarefa aberta no modal de resolução.
  const [alvo, setAlvo] = useState(null);
  const [form, setForm] = useState({});
  const [salvando, setSalvando] = useState(false);

  // Ficha = ver/editar o registro de origem sem sair do painel. Separada de `alvo`
  // (que é concluir a tarefa) porque são coisas diferentes: uma corrige o dado, a
  // outra registra o que foi feito.
  const [ficha, setFicha] = useState(null);
  const [formFicha, setFormFicha] = useState({});
  const [carregandoFicha, setCarregandoFicha] = useState(false);
  const [salvandoFicha, setSalvandoFicha] = useState(false);

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
  }, [idCorretor, tipo, nivel, responsavel]);

  useEffect(() => { carregar(); }, [idCorretor, tipo, nivel]); // eslint-disable-line react-hooks/exhaustive-deps

  const abrir = (t) => {
    setAlvo(t);
    setForm(
      t.acao.tipo === "acao_proposta" ? { descricao: "", situacao: "" }
        : t.acao.tipo === "contato_lead" ? { contato_status: "", visita_agendada: "", motivo_sem_visita: "", proxima_acao: "" }
          : {},
    );
  };

  const fechar = () => { setAlvo(null); setForm({}); };

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
      setFicha((f) => (f && f.id === id ? { ...f, registro } : f));
      setFormFicha(inicial);
    } catch (err) {
      toast(err.message || "Não consegui abrir o registro.", "error");
      setFicha(null);
    } finally {
      setCarregandoFicha(false);
    }
  };

  /** Salva no endpoint do módulo — o mesmo que a tela dele usa. */
  const salvarFicha = async (e) => {
    e.preventDefault();
    if (salvandoFicha || !ficha?.registro) return;
    const { spec, id, tarefa } = ficha;

    // Mesma regra do servidor: a resposta escolhida define o motivo cobrado.
    if (tarefa.tipo === "visita") {
      const campoMotivo = MOTIVO_DA_RESPOSTA[String(formFicha.proposta || "").toLowerCase()];
      if (campoMotivo && !String(formFicha[campoMotivo] || "").trim()) {
        toast("Essa resposta exige o motivo.", "error");
        return;
      }
    }

    setSalvandoFicha(true);
    try {
      const r = await fetch(`${BASE}${spec.url(id)}?solicitante_id=${encodeURIComponent(idCorretor)}`, {
        method: spec.metodo,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...formFicha, solicitante_id: idCorretor }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui salvar.");
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
  const resolver = async (e) => {
    e.preventDefault();
    if (salvando || !alvo) return;
    const q = `solicitante_id=${encodeURIComponent(idCorretor)}`;
    let url;
    let corpo;

    if (alvo.acao.tipo === "acao_proposta") {
      if (!form.descricao?.trim()) { toast("Descreva a ação realizada.", "error"); return; }
      url = `${BASE}/propostas/${alvo.acao.id}/acoes?${q}`;
      corpo = { descricao: form.descricao.trim(), situacao: form.situacao || "" };
    } else if (alvo.acao.tipo === "revisar_visita") {
      url = `${BASE}/visitas/vistas?${q}`;
      // As três flags são monotônicas: marcar todas resolve a pendência de uma vez.
      // `id_gerente` na tabela de flags é o id da EQUIPE, não do usuário — é assim que
      // `_visit_reviews` casa a linha (`id_gerente == usuarios.team`).
      corpo = {
        id_gerente: alvo.equipe, id_visita: alvo.acao.id,
        viu_anexo: true, viu_notas: true, add_motivo: true,
      };
    } else if (alvo.acao.tipo === "contato_lead") {
      if (!form.contato_status) { toast("Escolha como foi o contato.", "error"); return; }
      if (form.visita_agendada === "nao" && !form.motivo_sem_visita?.trim()) {
        toast("Informe o motivo de não agendar a visita.", "error"); return;
      }
      url = `${BASE}/leads/gestao/${alvo.acao.id}?${q}`;
      corpo = {
        contato_status: form.contato_status,
        visita_agendada: form.visita_agendada === "" ? null : form.visita_agendada === "sim",
        motivo_sem_visita: form.motivo_sem_visita || "",
        proxima_acao: form.proxima_acao || "",
      };
    } else {
      // Lançar proposta é fluxo completo: leva para o módulo com o cliente preenchido.
      window.location.href = alvo.link;
      return;
    }

    setSalvando(true);
    try {
      const r = await fetch(url, {
        method: alvo.acao.tipo === "contato_lead" ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.ok === false) throw new Error(d.error || "Não consegui concluir");
      toast("Tarefa concluída.", "success");
      fechar();
      carregar();
    } catch (err) {
      toast(err.message || "Não consegui concluir", "error");
    } finally {
      setSalvando(false);
    }
  };

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
            <div className="tf-acoes">
              {podeResolver && (
                <button type="button" className="tf-btn tf-btn--primario" onClick={() => abrir(t)}>
                  {t.acao.rotulo}
                </button>
              )}
              <button type="button" className="tf-btn" onClick={() => abrirFicha(t)}>
                Ver / editar
              </button>
              <a className="tf-link" href={t.link}>Abrir no módulo →</a>
            </div>
          </article>
        ))}
      </div>

      {alvo && (
        <div className="tf-modal-bg" onClick={fechar}>
          <form className="tf-modal" onClick={(e) => e.stopPropagation()} onSubmit={resolver}>
            <header>
              <div>
                <span className="tf-eyebrow">{alvo.tipo}</span>
                <h3>{alvo.acao.rotulo}</h3>
              </div>
              <button type="button" onClick={fechar} aria-label="Fechar">✕</button>
            </header>

            <p className="tf-modal-alvo">{alvo.titulo}<br /><small>{alvo.detalhe}</small></p>

            {alvo.acao.tipo === "acao_proposta" && (
              <>
                <label>O que foi feito *
                  <textarea
                    rows={3}
                    placeholder="Ex.: cliente pediu prazo até sexta"
                    value={form.descricao || ""}
                    onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
                  />
                </label>
                <label>Mudar situação
                  <select value={form.situacao || ""}
                    onChange={(e) => setForm((f) => ({ ...f, situacao: e.target.value }))}>
                    <option value="">Manter como está</option>
                    <option value="em_analise">Em análise</option>
                    <option value="contraproposta">Contraproposta</option>
                    <option value="aceita">Aceita</option>
                    <option value="vendido">Vendido</option>
                    <option value="recusada">Recusada</option>
                    <option value="cancelada">Cancelada</option>
                  </select>
                </label>
              </>
            )}

            {alvo.acao.tipo === "revisar_visita" && (
              <p className="tf-nota">
                Marca anexo, notas e motivo como revisados de uma vez. Se ainda falta
                <strong> preencher</strong> o motivo da visita, abra no módulo — aqui só
                registra que você revisou.
              </p>
            )}

            {alvo.acao.tipo === "contato_lead" && (
              <>
                <label>Como foi o contato *
                  <select value={form.contato_status || ""}
                    onChange={(e) => setForm((f) => ({ ...f, contato_status: e.target.value }))}>
                    <option value="">Selecione…</option>
                    {CONTATOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                  </select>
                </label>
                <label>Agendou visita?
                  <select value={form.visita_agendada || ""}
                    onChange={(e) => setForm((f) => ({ ...f, visita_agendada: e.target.value }))}>
                    <option value="">Não respondido</option>
                    <option value="sim">Sim</option>
                    <option value="nao">Não</option>
                  </select>
                </label>
                {form.visita_agendada === "nao" && (
                  <label>Motivo de não agendar *
                    <input value={form.motivo_sem_visita || ""}
                      onChange={(e) => setForm((f) => ({ ...f, motivo_sem_visita: e.target.value }))} />
                  </label>
                )}
                <label>Próxima ação
                  <input value={form.proxima_acao || ""}
                    onChange={(e) => setForm((f) => ({ ...f, proxima_acao: e.target.value }))} />
                </label>
              </>
            )}

            {alvo.acao.tipo === "nova_proposta" && (
              <p className="tf-nota">
                Lançar proposta é um fluxo completo. Você vai para Propostas Efetivas com o
                cliente já preenchido.
              </p>
            )}

            <footer>
              <button type="button" className="tf-link" onClick={fechar} disabled={salvando}>
                Cancelar
              </button>
              <button type="submit" className="tf-btn tf-btn--primario" disabled={salvando}>
                {salvando ? "Concluindo…" : "Concluir tarefa"}
              </button>
            </footer>
          </form>
        </div>
      )}

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

                <div className="tf-ficha-grid">
                  {ficha.spec.campos.map((c) => {
                    // Motivo só aparece para a resposta que o exige — mostrar os dois
                    // convida a preencher o errado, que é o que deixa a pendência de pé.
                    if (ficha.tarefa.tipo === "visita" && (c.nome === "motivoSim" || c.nome === "motivoTalvez")) {
                      const esperado = MOTIVO_DA_RESPOSTA[String(formFicha.proposta || "").toLowerCase()];
                      if (c.nome !== esperado) return null;
                    }
                    const valor = formFicha[c.nome] ?? "";
                    const mudar = (v) => setFormFicha((f) => ({ ...f, [c.nome]: v }));
                    return (
                      <label key={c.nome} className={c.largo ? "tf-ficha-largo" : ""}>
                        {c.rotulo}
                        {c.tipo === "select" ? (
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
                  <button type="submit" className="tf-btn tf-btn--primario" disabled={salvandoFicha}>
                    {salvandoFicha ? "Salvando…" : "Salvar alterações"}
                  </button>
                </footer>
              </>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
