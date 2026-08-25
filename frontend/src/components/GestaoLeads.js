import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useEquipes } from "../context/EquipesContext";
import RelatorioLeads from "./RelatorioLeads";
import { GraficoLinha, GraficoPizza, GraficoBarras } from "./GraficosGestao";
import "../assets/css/GestaoModulo.css";

/** Gestão de Leads — módulo especializado.
 *
 * A listagem, os filtros e as ações já existem em `RelatorioLeads`, que é usado como aba
 * do Relatório do Gerente. Aqui ele é reaproveitado por baixo de um cabeçalho com período
 * próprio, métricas e gráficos — em vez de duplicar 400 linhas de tabela e modal que já
 * funcionam (e que carregam as correções de paginação, cache e ordem de resposta).
 *
 * As métricas e os gráficos saem de `/leads/gestao/resumo` (banco, instantâneo), **não**
 * da leitura ao vivo do C2S: contar é consulta indexada e não pode custar os minutos que
 * a varredura custa. O preço é que a situação aqui é a da última importação — está dito
 * na tela, porque a listagem abaixo mostra a de agora e as duas vão divergir.
 */

const hoje = () => new Date();
const iso = (d) => d.toISOString().slice(0, 10);
const primeiroDiaDoMes = () => { const d = hoje(); d.setDate(1); return iso(d); };

// Canal de contato tem significado fixo — cor fixa também, para o olho não reaprender a
// legenda a cada período.
const CORES_CONTATO = {
  "Sem acompanhamento": "#b9b4c2",
  "Contato WhatsApp": "#1b6340",
  "Contato telefone": "#2f6f9f",
  "Contato e-mail": "#6a4b9c",
  "Sem contato": "#a3444a",
};

export default function GestaoLeads() {
  const { idCorretor, permissao } = useAuth();
  const { equipesOpcoes, getNomeEquipe } = useEquipes();

  const [periodo, setPeriodo] = useState({ inicio: primeiroDiaDoMes(), fim: iso(hoje()) });
  const [equipe, setEquipe] = useState("");
  const [resumo, setResumo] = useState(null);
  const [carregandoResumo, setCarregandoResumo] = useState(true);
  const [erroResumo, setErroResumo] = useState("");

  const veTudo = ["diretor", "administrador", "administrativo", "inteligencia"].includes(
    String(permissao || "").toLowerCase(),
  );

  const carregarResumo = useCallback(async () => {
    if (!idCorretor) return;
    setCarregandoResumo(true);
    setErroResumo("");
    try {
      const p = new URLSearchParams({ solicitante_id: idCorretor });
      if (equipe) p.set("id_gerente", equipe);
      if (periodo.inicio) p.set("inicio", periodo.inicio);
      if (periodo.fim) p.set("fim", periodo.fim);
      const r = await fetch(`${BASE}/leads/gestao/resumo?${p.toString()}`);
      const d = await r.json();
      if (!r.ok || d.ok === false) throw new Error(d.error || "Erro ao carregar o resumo.");
      setResumo(d);
    } catch (err) {
      setResumo(null);
      setErroResumo(err.message || "Erro ao carregar o resumo.");
    } finally {
      setCarregandoResumo(false);
    }
  }, [idCorretor, equipe, periodo.inicio, periodo.fim]);

  useEffect(() => { carregarResumo(); }, [carregarResumo]);

  const cards = useMemo(() => {
    const total = resumo?.total;
    const semAcomp = resumo?.sem_acompanhamento;
    const comAcomp = resumo?.com_acompanhamento;
    const pct = total ? Math.round(((comAcomp || 0) / total) * 1000) / 10 : null;
    return [
      { rotulo: "Leads no período", valor: total },
      { rotulo: "Com acompanhamento", valor: comAcomp },
      { rotulo: "Sem acompanhamento", valor: semAcomp, alerta: true },
      { rotulo: "% acompanhados", valor: pct == null ? null : `${pct}%` },
      { rotulo: "Visitas agendadas", valor: resumo?.visita_agendada },
      { rotulo: "Arquivados", valor: resumo?.arquivados },
      { rotulo: "Negócios fechados", valor: resumo?.negocios_fechados },
    ];
  }, [resumo]);

  // Ritmo diário — o total sozinho esconde isso quando o período muda de tamanho.
  // Divide por `dias_com_entrada`, não pelo número de pontos: acima de 62 dias o
  // servidor agrupa a série por semana ou mês, e aí ponto deixa de ser dia.
  const mediaDiaria = useMemo(() => {
    const dias = resumo?.dias_com_entrada || 0;
    if (!dias) return null;
    return Math.round((resumo.total / dias) * 10) / 10;
  }, [resumo]);

  const rotuloSerie = { dia: "dia", semana: "semana", mes: "mês" }[resumo?.granularidade] || "dia";

  // Funil NOSSO (o que fizemos com o lead), diferente de `por_funil`, que e a etapa
  // que o corretor marca dentro do C2S.
  const funilAcompanhamento = useMemo(() => {
    if (!resumo) return [];
    return [
      { rotulo: "Chegaram", total: resumo.total },
      { rotulo: "Acompanhados", total: resumo.com_acompanhamento },
      { rotulo: "Visita agendada", total: resumo.visita_agendada },
    ];
  }, [resumo]);

  return (
    <div className="gm">
      <header className="gm-topo">
        <div>
          <span className="gm-eyebrow">Módulo</span>
          <h1>Gestão de Leads</h1>
          <p>
            Leads espelhados do Contact2Sale — situação, etapa do funil e motivo do
            arquivamento acompanham as mudanças, não ficam congelados na entrada.
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
              {equipesOpcoes.map((eq) => (
                <option key={eq.value} value={eq.value}>{eq.label}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="gm-cards">
        {cards.map((c) => (
          <div key={c.rotulo} className={`gm-card ${c.alerta && c.valor ? "is-alerta" : ""}`}>
            <span>{c.rotulo}</span>
            <strong>{carregandoResumo ? "…" : (c.valor ?? "—")}</strong>
          </div>
        ))}
      </div>

      {erroResumo && <p className="gm-nota">{erroResumo}</p>}

      {resumo && !carregandoResumo && (
        <div className="gm-dashboard-leads">
          <article className="gm-grafico gm-grafico--largo">
            <header>
              <div>
                <h4>Leads por {rotuloSerie}</h4>
                <p>
                  {resumo.dias_com_entrada} dia(s) com entrada
                  {mediaDiaria != null ? ` · média de ${mediaDiaria} por dia` : ""}
                  {resumo.granularidade !== "dia"
                    ? ` · agrupado por ${rotuloSerie} para caber no gráfico`
                    : ""}
                </p>
              </div>
              <span className="gm-grafico-total">{resumo.total}</span>
            </header>
            <GraficoLinha pontos={resumo.por_dia} unidade="lead(s)"
              rotuloAria={`Quantidade de leads recebidos por ${rotuloSerie}`} />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Origem do lead</h4><p>Portal ou canal de entrada</p></div></header>
            <GraficoPizza dados={resumo.por_fonte} centroRotulo="leads" />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Acompanhamento</h4><p>Como o lead foi abordado</p></div></header>
            <GraficoPizza dados={resumo.por_contato} cores={CORES_CONTATO} centroRotulo="leads" />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Por corretor</h4><p>Quem recebeu no período</p></div></header>
            <GraficoBarras dados={resumo.por_corretor} sufixo="lead(s)" />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Por equipe</h4><p>Distribuição entre as equipes</p></div></header>
            <GraficoBarras dados={resumo.por_equipe} sufixo="lead(s)"
              resolverRotulo={(id) => getNomeEquipe?.(id) || id} />
          </article>

          <article className="gm-grafico">
            <header>
              <div>
                <h4>Do lead à visita</h4>
                <p>Quanto sobra em cada passo</p>
              </div>
            </header>
            <GraficoBarras dados={funilAcompanhamento} sufixo="lead(s)" />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Situação no C2S</h4><p>Onde o lead está agora</p></div></header>
            <GraficoPizza dados={resumo.por_situacao} centroRotulo="leads" />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Etapa do funil</h4><p>Andamento do atendimento</p></div></header>
            <GraficoBarras dados={resumo.por_funil} sufixo="lead(s)" />
          </article>

          <article className="gm-grafico">
            <header><div><h4>Canal de entrada</h4><p>Por onde o cliente chegou</p></div></header>
            <GraficoPizza dados={resumo.por_canal} centroRotulo="leads" />
          </article>

          {resumo.motivos_arquivamento?.length > 0 && (
            <article className="gm-grafico">
              <header>
                <div>
                  <h4>Motivo do arquivamento</h4>
                  <p>Por que o lead foi encerrado</p>
                </div>
                <span className="gm-grafico-total">{resumo.arquivados}</span>
              </header>
              <GraficoBarras dados={resumo.motivos_arquivamento} sufixo="lead(s)" />
            </article>
          )}

          {resumo.motivos_sem_visita?.length > 0 && (
            <article className="gm-grafico">
              <header>
                <div>
                  <h4>Por que não agendou</h4>
                  <p>Motivos registrados pelo corretor</p>
                </div>
              </header>
              <GraficoBarras dados={resumo.motivos_sem_visita} sufixo="lead(s)" />
            </article>
          )}
        </div>
      )}

      <p className="gm-nota">
        Cards, gráficos e listagem saem todos do espelho local do Contact2Sale, atualizado
        de hora em hora — por isso mostram o mesmo total.
        {resumo?.sincronizado_em
          ? ` Última sincronização: ${new Date(resumo.sincronizado_em).toLocaleString("pt-BR")}.`
          : ""}
        {" "}Lead que muda de situação ou é arquivado depois de entrar aparece atualizado na
        passada seguinte. Os filtros continuam sendo aplicados no botão Buscar, para não
        recarregar a cada mexida num select.
      </p>

      <section className="gm-conteudo">
        <RelatorioLeads
          idSolicitante={idCorretor}
          equipe={equipe}
          inicio={periodo.inicio}
          fim={periodo.fim}
          corretor=""
          podeLancar={Boolean(resumo?.escopo?.pode_lancar)}
        />
      </section>
    </div>
  );
}
