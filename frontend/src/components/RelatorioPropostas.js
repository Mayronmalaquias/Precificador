import React, { useCallback, useEffect, useState } from "react";
import { BASE } from "../services/api";
import { moedaInput, moedaNumero, moedaDeNumero } from "../services/moeda";
import "../assets/css/RelatorioAbas.css";

const moeda = (v) => (v == null || v === "" ? "—"
  : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }));
const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString("pt-BR") : "—");

const FORM_VAZIO = {
  cliente: "", valor: "", forma_pagamento: "", valor_permuta: "", descricao_permuta: "",
  situacao: "", data_proposta: "", data_fechamento: "", observacao: "",
  codigo_imovel: "", imovel_endereco: "", bairro: "", tipo: "",
  numero: "", bloco: "", complemento: "", quartos: "", vagas: "", area: "",
};

/** Aba de propostas do Relatório do Gerente.
 *
 * O gerente edita a proposta e registra ação aqui mesmo, sem trocar de tela — os dois
 * usam os endpoints da tela dona (`PUT /propostas/:id` e `POST /propostas/:id/acoes`),
 * então a regra de negócio continua num lugar só. O escopo (o que ele vê e se pode
 * editar) é decidido pelo servidor a partir do cadastro; `pode_editar` vem no detalhe.
 *
 * O link para `/PropostasEfetivas` continua no rodapé para o que não cabe aqui: trocar
 * o imóvel pela busca do Imoview, vincular visita e excluir.
 */
export default function RelatorioPropostas({ idSolicitante, equipe, inicio, fim, corretor }) {
  const [dados, setDados] = useState({ itens: [], resumo: {} });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState("");
  const [detalhe, setDetalhe] = useState(null);
  const [podeEditar, setPodeEditar] = useState(false);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);

  // Edição e ação moram no mesmo modal; `editando` alterna entre ler e editar.
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [maisImovel, setMaisImovel] = useState(false);
  const [acao, setAcao] = useState({ descricao: "", situacao: "" });
  const [salvandoAcao, setSalvandoAcao] = useState(false);
  const [aviso, setAviso] = useState("");

  const carregar = useCallback(async () => {
    if (!idSolicitante) return;
    setCarregando(true);
    setErro("");
    try {
      const params = new URLSearchParams({ solicitante_id: idSolicitante });
      // Equipe escolhida no dropdown do relatorio. Vale so p/ quem enxerga tudo — para
      // gerente o servidor ignora e mantem a equipe do cadastro.
      if (equipe) params.set("team", equipe);
      // Mesmo periodo do relatorio, pela data de lancamento da proposta.
      if (inicio) params.set("inicio", inicio);
      if (fim) params.set("fim", fim);
      if (corretor) params.set("corretor", corretor);
      if (busca.trim()) params.set("busca", busca.trim());
      if (situacao) params.set("situacao", situacao);
      const r = await fetch(`${BASE}/propostas?${params.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao carregar propostas");
      setDados(d);
    } catch (e) {
      setErro(e.message || "Erro ao carregar propostas");
    } finally {
      setCarregando(false);
    }
  }, [idSolicitante, busca, situacao, equipe, inicio, fim, corretor]);

  useEffect(() => { carregar(); }, [idSolicitante, situacao, equipe, inicio, fim, corretor]); // eslint-disable-line react-hooks/exhaustive-deps

  const buscarDetalhe = useCallback(async (id) => {
    const r = await fetch(`${BASE}/propostas/${id}?solicitante_id=${encodeURIComponent(idSolicitante)}`);
    const d = await r.json();
    if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao abrir proposta");
    return d;
  }, [idSolicitante]);

  const fechar = () => {
    setDetalhe(null);
    setEditando(false);
    setMaisImovel(false);
    setAcao({ descricao: "", situacao: "" });
    setAviso("");
  };

  const abrir = async (id) => {
    setCarregandoDetalhe(true);
    setDetalhe({ id });
    setEditando(false);
    setMaisImovel(false);
    setAcao({ descricao: "", situacao: "" });
    setAviso("");
    try {
      const d = await buscarDetalhe(id);
      setDetalhe(d.proposta || d);
      setPodeEditar(!!d.pode_editar);
    } catch (e) {
      setErro(e.message);
      setDetalhe(null);
    } finally {
      setCarregandoDetalhe(false);
    }
  };

  // Recarrega o detalhe aberto e a lista — o que muda aqui muda a linha da tabela
  // (situação, valor, "sem ação"), então as duas precisam refletir.
  const recarregarTudo = async (id) => {
    const d = await buscarDetalhe(id);
    setDetalhe(d.proposta || d);
    setPodeEditar(!!d.pode_editar);
    carregar();
  };

  const iniciarEdicao = () => {
    setForm({
      cliente: detalhe.cliente || "",
      valor: moedaDeNumero(detalhe.valor),
      forma_pagamento: detalhe.forma_pagamento || "",
      valor_permuta: moedaDeNumero(detalhe.valor_permuta),
      descricao_permuta: detalhe.descricao_permuta || "",
      situacao: detalhe.situacao || "",
      data_proposta: detalhe.data_proposta || "",
      data_fechamento: detalhe.data_fechamento || "",
      observacao: detalhe.observacao || "",
      codigo_imovel: detalhe.codigo_imovel || "",
      imovel_endereco: detalhe.imovel_endereco || "",
      bairro: detalhe.bairro || "",
      tipo: detalhe.tipo || "",
      numero: detalhe.numero || "",
      bloco: detalhe.bloco || "",
      complemento: detalhe.complemento || "",
      quartos: detalhe.quartos || "",
      vagas: detalhe.vagas || "",
      area: detalhe.area || "",
    });
    setAviso("");
    setEditando(true);
  };

  const set = (campo) => (e) => {
    const bruto = e.target.value;
    const valor = ["valor", "valor_permuta"].includes(campo) ? moedaInput(bruto) : bruto;
    setForm((f) => ({ ...f, [campo]: valor }));
  };

  const ehPermuta = form.forma_pagamento === "permuta";

  const salvar = async (e) => {
    e.preventDefault();
    if (salvando) return;
    // O back não revalida o valor no update; sem esta guarda, salvar com o campo
    // vazio gravaria NULL numa proposta que já tinha valor.
    if (!moedaNumero(form.valor) || Number(moedaNumero(form.valor)) <= 0) {
      setAviso("Informe o valor da proposta.");
      return;
    }
    setSalvando(true);
    setAviso("");
    try {
      const corpo = {
        ...form,
        valor: moedaNumero(form.valor),
        valor_permuta: ehPermuta ? moedaNumero(form.valor_permuta) : "",
      };
      const r = await fetch(
        `${BASE}/propostas/${detalhe.id}?solicitante_id=${encodeURIComponent(idSolicitante)}`,
        { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) },
      );
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao salvar proposta");
      await recarregarTudo(detalhe.id);
      setEditando(false);
    } catch (err) {
      setAviso(err.message || "Erro ao salvar proposta");
    } finally {
      setSalvando(false);
    }
  };

  const registrarAcao = async (e) => {
    e.preventDefault();
    if (salvandoAcao) return;
    if (!acao.descricao.trim()) {
      setAviso("Descreva a ação realizada.");
      return;
    }
    setSalvandoAcao(true);
    setAviso("");
    try {
      const r = await fetch(
        `${BASE}/propostas/${detalhe.id}/acoes?solicitante_id=${encodeURIComponent(idSolicitante)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ descricao: acao.descricao.trim(), situacao: acao.situacao }),
        },
      );
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao registrar ação");
      setAcao({ descricao: "", situacao: "" });
      await recarregarTudo(detalhe.id);
    } catch (err) {
      setAviso(err.message || "Erro ao registrar ação");
    } finally {
      setSalvandoAcao(false);
    }
  };

  const situacoes = dados.opcoes?.situacoes || [];
  const formasPagamento = dados.opcoes?.formas_pagamento || [];
  const itens = dados.itens || dados.propostas || [];

  return (
    <div className="raba">
      <div className="raba-barra">
        <input
          placeholder="Buscar por imóvel, bairro, cliente ou corretor"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && carregar()}
        />
        <select value={situacao} onChange={(e) => setSituacao(e.target.value)}>
          <option value="">Todas as situações</option>
          {situacoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <button type="button" className="raba-cta" onClick={carregar}>Buscar</button>
        <span className="raba-contador">{itens.length} proposta{itens.length === 1 ? "" : "s"}</span>
      </div>

      {erro && <p className="raba-estado raba-estado--erro">{erro}</p>}
      {carregando && <p className="raba-estado">Carregando propostas…</p>}
      {!carregando && !itens.length && !erro && (
        <p className="raba-estado">Nenhuma proposta encontrada com esse filtro.</p>
      )}

      {!!itens.length && (
        <div className="raba-tabela-wrap">
          <table className="raba-tabela">
            <thead>
              <tr>
                <th>Imóvel</th><th>Cliente</th><th>Corretor</th><th>Valor</th>
                <th>Pagamento</th><th>Situação</th><th>Sem ação</th><th />
              </tr>
            </thead>
            <tbody>
              {itens.map((p) => (
                <tr key={p.id}>
                  <td>
                    <strong>{p.imovel_endereco || p.codigo_imovel || "Sem endereço"}</strong>
                    <span>{[p.bairro, p.tipo].filter(Boolean).join(" · ")}</span>
                  </td>
                  <td>{p.cliente || "—"}</td>
                  <td>{p.corretor_nome || p.gerente_nome || "—"}</td>
                  <td>{moeda(p.valor)}</td>
                  <td>{p.forma_pagamento_label || p.forma_pagamento || "—"}</td>
                  <td><span className={`raba-selo s-${p.situacao}`}>{p.situacao_label || p.situacao}</span></td>
                  <td className={(p.dias_sem_acao || 0) >= 2 ? "raba-critico" : ""}>
                    {p.dias_sem_acao == null ? "—" : `${p.dias_sem_acao} d`}
                  </td>
                  <td><button type="button" className="raba-link" onClick={() => abrir(p.id)}>Abrir</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detalhe && (
        <div className="raba-modal-bg" onClick={fechar}>
          <div className="raba-modal" onClick={(e) => e.stopPropagation()}>
            <header>
              <div>
                <span className="raba-eyebrow">Proposta #{detalhe.id}</span>
                <h3>{detalhe.imovel_endereco || detalhe.codigo_imovel || "Proposta"}</h3>
              </div>
              <button type="button" onClick={fechar} aria-label="Fechar">✕</button>
            </header>

            {carregandoDetalhe && <p className="raba-estado">Carregando…</p>}
            {!carregandoDetalhe && (
              <>
                {aviso && <p className="raba-nota">{aviso}</p>}

                {!editando && (
                  <>
                    <div className="raba-dados">
                      {[
                        ["Cliente", detalhe.cliente],
                        ["Corretor", detalhe.corretor_nome],
                        ["Gerente", detalhe.gerente_nome],
                        ["Equipe", detalhe.team],
                        ["Valor", moeda(detalhe.valor)],
                        ["Valor da permuta", detalhe.valor_permuta ? moeda(detalhe.valor_permuta) : null],
                        ["Pagamento", detalhe.forma_pagamento_label || detalhe.forma_pagamento],
                        ["Situação", detalhe.situacao_label || detalhe.situacao],
                        ["Data da proposta", dataBR(detalhe.data_proposta)],
                        ["Lançada em", detalhe.created_at ? dataBR(detalhe.created_at) : null],
                        ["Fechamento", detalhe.data_fechamento ? dataBR(detalhe.data_fechamento) : null],
                        ["Dias em aberto", detalhe.dias_em_aberto],
                        ["Dias sem ação", detalhe.dias_sem_acao],
                      ].filter(([, v]) => v != null && v !== "").map(([rotulo, valor]) => (
                        <div key={rotulo}><span>{rotulo}</span><strong>{valor}</strong></div>
                      ))}
                    </div>

                    {detalhe.observacao && <p className="raba-obs">{detalhe.observacao}</p>}
                  </>
                )}

                {editando && (
                  <form className="raba-form" onSubmit={salvar}>
                    <label className="raba-form-largo">Cliente
                      <input value={form.cliente} onChange={set("cliente")} />
                    </label>
                    <label>Valor da proposta *
                      <input value={form.valor} onChange={set("valor")} inputMode="numeric"
                        placeholder="0,00" maxLength={18} required />
                    </label>
                    <label>Forma de pagamento
                      <select value={form.forma_pagamento} onChange={set("forma_pagamento")}>
                        <option value="">Não informado</option>
                        {formasPagamento.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                      </select>
                    </label>
                    {ehPermuta && (
                      <>
                        <label>Valor da permuta *
                          <input value={form.valor_permuta} onChange={set("valor_permuta")}
                            inputMode="numeric" placeholder="0,00" maxLength={18} required />
                        </label>
                        <label>Descrição da permuta
                          <input value={form.descricao_permuta} onChange={set("descricao_permuta")} />
                        </label>
                      </>
                    )}
                    <label>Situação
                      <select value={form.situacao} onChange={set("situacao")}>
                        {situacoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                      </select>
                    </label>
                    <label>Data da proposta
                      <input type="date" value={form.data_proposta} onChange={set("data_proposta")} />
                    </label>
                    <label>Data de fechamento
                      <input type="date" value={form.data_fechamento} onChange={set("data_fechamento")} />
                    </label>
                    <label className="raba-form-largo">Observação
                      <textarea rows={3} value={form.observacao} onChange={set("observacao")} />
                    </label>

                    <div className="raba-form-largo">
                      <button type="button" className="raba-link" onClick={() => setMaisImovel((v) => !v)}>
                        {maisImovel ? "− Ocultar dados do imóvel" : "+ Editar dados do imóvel"}
                      </button>
                    </div>

                    {maisImovel && (
                      <>
                        <label>Código Imoview
                          <input value={form.codigo_imovel} onChange={set("codigo_imovel")} />
                        </label>
                        <label>Bairro
                          <input value={form.bairro} onChange={set("bairro")} />
                        </label>
                        <label className="raba-form-largo">Endereço
                          <input value={form.imovel_endereco} onChange={set("imovel_endereco")} />
                        </label>
                        <label>Tipo<input value={form.tipo} onChange={set("tipo")} /></label>
                        <label>Número<input value={form.numero} onChange={set("numero")} /></label>
                        <label>Bloco<input value={form.bloco} onChange={set("bloco")} /></label>
                        <label>Complemento<input value={form.complemento} onChange={set("complemento")} /></label>
                        <label>Quartos<input value={form.quartos} onChange={set("quartos")} /></label>
                        <label>Vagas<input value={form.vagas} onChange={set("vagas")} /></label>
                        <label>Área<input value={form.area} onChange={set("area")} /></label>
                      </>
                    )}

                    <div className="raba-modal-rodape raba-form-largo">
                      <button type="button" className="raba-link" onClick={() => setEditando(false)}
                        disabled={salvando}>Cancelar</button>
                      <button type="submit" className="raba-cta" disabled={salvando}>
                        {salvando ? "Salvando…" : "Salvar alterações"}
                      </button>
                    </div>
                  </form>
                )}

                {!!(detalhe.acoes || []).length && (
                  <>
                    <h4 className="raba-subtitulo">Histórico</h4>
                    <ul className="raba-historico">
                      {detalhe.acoes.map((a) => (
                        <li key={a.id}>
                          <b>{dataBR(a.created_at)}</b> {a.descricao}
                          {a.situacao_label ? <em> → {a.situacao_label}</em> : null}
                          {a.autor_nome ? <span> · {a.autor_nome}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                {podeEditar && !editando && (
                  <>
                    <h4 className="raba-subtitulo">Registrar ação</h4>
                    <form className="raba-form" onSubmit={registrarAcao}>
                      <label className="raba-form-largo">O que foi feito *
                        <textarea
                          rows={2}
                          placeholder="Ex.: cliente pediu prazo até sexta para responder"
                          value={acao.descricao}
                          onChange={(e) => setAcao((a) => ({ ...a, descricao: e.target.value }))}
                        />
                      </label>
                      <label>Mudar situação
                        <select value={acao.situacao}
                          onChange={(e) => setAcao((a) => ({ ...a, situacao: e.target.value }))}>
                          <option value="">Manter como está</option>
                          {situacoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                      </label>
                      <div className="raba-modal-rodape raba-form-largo">
                        <button type="submit" className="raba-cta" disabled={salvandoAcao}>
                          {salvandoAcao ? "Registrando…" : "Registrar ação"}
                        </button>
                      </div>
                    </form>
                  </>
                )}

                {!editando && (
                  <div className="raba-modal-rodape">
                    {/* O que depende da busca do Imoview, do vínculo com visita ou de
                        excluir continua na tela dona do processo. */}
                    <a className="raba-link" href={`/PropostasEfetivas?id=${detalhe.id}`}>
                      Abrir em Propostas Efetivas
                    </a>
                    {podeEditar && (
                      <button type="button" className="raba-cta" onClick={iniciarEdicao}>
                        Editar proposta
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
