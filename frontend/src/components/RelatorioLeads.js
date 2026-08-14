import React, { useCallback, useEffect, useState } from "react";
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
export default function RelatorioLeads({ idSolicitante, equipe, inicio, fim, corretor }) {
  const toast = useToast();
  const [dados, setDados] = useState({ itens: [], total: 0, page: 1, paginas: 1 });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  // Leads sem acompanhamento: o mesmo recorte do aviso do topo.
  const [soNaoVistos, setSoNaoVistos] = useState(false);
  const [detalhe, setDetalhe] = useState(null);
  const [criando, setCriando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  // Acompanhamento do lead aberto: o que o gerente registra depois de olhar.
  const [acomp, setAcomp] = useState({
    contato_status: "", visita_agendada: "", motivo_sem_visita: "", proxima_acao: "",
  });
  const [salvandoAcomp, setSalvandoAcomp] = useState(false);

  const carregar = useCallback(async (pagina = 1, termo = busca) => {
    if (!idSolicitante) return;
    setCarregando(true);
    setErro("");
    try {
      const params = new URLSearchParams({
        solicitante_id: idSolicitante, page: pagina, per_page: 30,
      });
      // Idem propostas: recorte do dropdown, ignorado pelo servidor p/ quem nao e global.
      if (equipe) params.set("id_gerente", equipe);
      // O periodo e o mesmo do filtro do relatorio: sem ele a aba trazia a base inteira.
      if (inicio) params.set("inicio", inicio);
      if (fim) params.set("fim", fim);
      if (soNaoVistos) params.set("nao_vistos", "1");
      // Filtro de corretor do topo do relatorio.
      if (corretor) params.set("corretor", corretor);
      if (termo.trim()) params.set("busca", termo.trim());
      const r = await fetch(`${BASE}/leads/gestao?${params.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao carregar leads");
      setDados(d);
    } catch (e) {
      setErro(e.message || "Erro ao carregar leads");
    } finally {
      setCarregando(false);
    }
  }, [idSolicitante, busca, equipe, inicio, fim, soNaoVistos, corretor]);

  useEffect(() => { carregar(1, ""); }, [idSolicitante, equipe, inicio, fim, soNaoVistos, corretor]); // eslint-disable-line react-hooks/exhaustive-deps

  const abrir = async (id) => {
    setDetalhe({ id });
    try {
      const r = await fetch(`${BASE}/leads/gestao/${id}?solicitante_id=${encodeURIComponent(idSolicitante)}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao abrir lead");
      setDetalhe({ ...d.lead, _imovel: d.imovel, _pode_editar: d.pode_editar, _opcoes: d.opcoes });
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
      const r = await fetch(`${BASE}/leads/gestao/${detalhe.id}?solicitante_id=${encodeURIComponent(idSolicitante)}`, {
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

  return (
    <div className="raba">
      <div className="raba-barra">
        <input
          placeholder="Buscar por cliente, telefone, código do imóvel ou fonte"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && carregar(1)}
        />
        <button type="button" className="raba-cta" onClick={() => carregar(1)}>Buscar</button>
        <button
          type="button"
          className={`raba-filtro ${soNaoVistos ? "is-ativo" : ""}`}
          aria-pressed={soNaoVistos}
          onClick={() => setSoNaoVistos((v) => !v)}
        >
          Sem acompanhamento{dados.nao_vistos ? ` (${dados.nao_vistos})` : ""}
        </button>
        {dados.pode_lancar && (
          <button type="button" className="raba-cta raba-cta--novo" onClick={() => setCriando(true)}>
            + Lançar lead
          </button>
        )}
        <span className="raba-contador">
          {dados.total?.toLocaleString("pt-BR") || 0} lead{dados.total === 1 ? "" : "s"}
        </span>
      </div>

      {erro && <p className="raba-estado raba-estado--erro">{erro}</p>}
      {carregando && <p className="raba-estado">Carregando leads…</p>}
      {!carregando && !dados.itens.length && !erro && <p className="raba-estado">Nenhum lead encontrado.</p>}

      {!!dados.itens.length && (
        <>
          <div className="raba-tabela-wrap">
            <table className="raba-tabela">
              <thead>
                <tr><th>Data</th><th>Cliente</th><th>Telefone</th><th>Imóvel</th><th>Fonte</th><th>Atendimento</th><th>Acompanhamento</th><th /></tr>
              </thead>
              <tbody>
                {dados.itens.map((l) => (
                  <tr key={l.id}>
                    <td>{dataBR(l.data)}</td>
                    <td><strong>{l.cliente || "Sem nome"}</strong></td>
                    <td>{l.telefone || "—"}</td>
                    <td>{l.codigo_imovel || "—"}</td>
                    <td>{l.fonte || "—"}</td>
                    <td>{l.atendimento_nome || "—"}</td>
                    <td>
                      {l.contato_label && <span className="raba-selo">{l.contato_label}</span>}
                      {l.visita_agendada === true && <span className="raba-selo s-aceita">Visita sim</span>}
                      {l.visita_agendada === false && <span className="raba-selo s-recusada">Visita não</span>}
                      {!l.contato_label && l.visita_agendada == null && "—"}
                    </td>
                    <td><button type="button" className="raba-link" onClick={() => abrir(l.id)}>Abrir</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {dados.paginas > 1 && (
            <div className="raba-paginacao">
              <button type="button" disabled={dados.page <= 1} onClick={() => carregar(dados.page - 1)}>← Anterior</button>
              <span>Página <b>{dados.page}</b> de {dados.paginas}</span>
              <button type="button" disabled={dados.page >= dados.paginas} onClick={() => carregar(dados.page + 1)}>Próxima →</button>
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

            {detalhe._pode_editar && (
              <>
                <h4 className="raba-subtitulo">Acompanhamento</h4>
                <div className="raba-form">
                  <label>Contato
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
