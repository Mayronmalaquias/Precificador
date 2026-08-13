import React, { useCallback, useEffect, useState } from "react";
import { BASE } from "../services/api";
import { useToast } from "../context/ToastContext";
import "../assets/css/RelatorioAbas.css";

const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString("pt-BR") : "—");

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
export default function RelatorioLeads({ idSolicitante, equipe }) {
  const toast = useToast();
  const [dados, setDados] = useState({ itens: [], total: 0, page: 1, paginas: 1 });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  const [detalhe, setDetalhe] = useState(null);
  const [criando, setCriando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);

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
  }, [idSolicitante, busca, equipe]);

  useEffect(() => { carregar(1, ""); }, [idSolicitante, equipe]); // eslint-disable-line react-hooks/exhaustive-deps

  const abrir = async (id) => {
    setDetalhe({ id });
    try {
      const r = await fetch(`${BASE}/leads/gestao/${id}?solicitante_id=${encodeURIComponent(idSolicitante)}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao abrir lead");
      setDetalhe(d.lead);
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
                <tr><th>Data</th><th>Cliente</th><th>Telefone</th><th>Imóvel</th><th>Fonte</th><th>Atendimento</th><th /></tr>
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
