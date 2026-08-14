import React, { useCallback, useEffect, useState } from "react";
import { BASE } from "../services/api";
import "../assets/css/RelatorioAbas.css";

const moeda = (v) => (v == null || v === "" ? "—"
  : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }));
const dataBR = (v) => (v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString("pt-BR") : "—");

/** Aba de propostas do Relatório do Gerente.
 *
 * Só leitura: lançar e editar continua em `/PropostasEfetivas`, que é a tela dona do
 * processo. Aqui o gerente encontra a proposta a partir do relatório sem trocar de tela,
 * e o botão "Abrir" leva para lá quando ele precisa agir.
 *
 * O escopo (quais propostas ele vê) é decidido pelo servidor a partir do cadastro.
 */
export default function RelatorioPropostas({ idSolicitante, equipe, inicio, fim, corretor }) {
  const [dados, setDados] = useState({ itens: [], resumo: {} });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState("");
  const [detalhe, setDetalhe] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);

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

  const abrir = async (id) => {
    setCarregandoDetalhe(true);
    setDetalhe({ id });
    try {
      const r = await fetch(`${BASE}/propostas/${id}?solicitante_id=${encodeURIComponent(idSolicitante)}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao abrir proposta");
      setDetalhe(d.proposta || d);
    } catch (e) {
      setErro(e.message);
      setDetalhe(null);
    } finally {
      setCarregandoDetalhe(false);
    }
  };

  const situacoes = dados.opcoes?.situacoes || [];
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
        <div className="raba-modal-bg" onClick={() => setDetalhe(null)}>
          <div className="raba-modal" onClick={(e) => e.stopPropagation()}>
            <header>
              <div>
                <span className="raba-eyebrow">Proposta #{detalhe.id}</span>
                <h3>{detalhe.imovel_endereco || detalhe.codigo_imovel || "Proposta"}</h3>
              </div>
              <button type="button" onClick={() => setDetalhe(null)} aria-label="Fechar">✕</button>
            </header>

            {carregandoDetalhe && <p className="raba-estado">Carregando…</p>}
            {!carregandoDetalhe && (
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
                    ["Fechamento", detalhe.data_fechamento ? dataBR(detalhe.data_fechamento) : null],
                    ["Dias em aberto", detalhe.dias_em_aberto],
                    ["Dias sem ação", detalhe.dias_sem_acao],
                  ].filter(([, v]) => v != null && v !== "").map(([rotulo, valor]) => (
                    <div key={rotulo}><span>{rotulo}</span><strong>{valor}</strong></div>
                  ))}
                </div>

                {detalhe.observacao && <p className="raba-obs">{detalhe.observacao}</p>}

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

                <div className="raba-modal-rodape">
                  {/* Editar continua na tela dona do processo — evita duas telas
                      gravando a mesma proposta com regras diferentes. */}
                  <a className="raba-cta" href={`/PropostasEfetivas?id=${detalhe.id}`}>Abrir em Propostas Efetivas</a>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
