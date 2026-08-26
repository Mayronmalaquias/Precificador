import React, { useMemo } from "react";

/** Gráficos SVG dos módulos de gestão.
 *
 * Feito à mão em vez de puxar uma biblioteca: o projeto não tem nenhuma lib de gráfico,
 * e as três formas usadas aqui (linha, rosca, barras) cabem em ~150 linhas. O CSS já
 * existia em `GestaoModulo.css`, escrito para a Gestão de Visitas.
 *
 * Todos recebem os dados já agregados pelo servidor — nenhum deles conta nada.
 */

// Paleta de fatias. Ordem fixa: a mesma categoria mantém a cor entre recarregamentos,
// senão comparar dois períodos vira adivinhação de legenda.
export const PALETA = [
  "#c4005a", "#2f6f9f", "#1b6340", "#c07a11", "#6a4b9c",
  "#0f8a8a", "#a3444a", "#4c5563", "#7a8b2e", "#b2568f",
];

export const corDaFatia = (i) => PALETA[i % PALETA.length];

const num = (v) => Number(v) || 0;

/** Linha temporal. `pontos`: [{ data, label, total }] já ordenados. */
export function GraficoLinha({ pontos = [], rotuloAria = "Evolução por dia", unidade = "" }) {
  const largura = 640;
  const altura = 200;
  const margem = { topo: 14, direita: 12, baixo: 28, esquerda: 38 };
  const w = largura - margem.esquerda - margem.direita;
  const h = altura - margem.topo - margem.baixo;

  if (!pontos.length) return <p className="gm-vazio">Sem dados no período.</p>;

  const maior = Math.max(1, ...pontos.map((p) => num(p.total)));
  const x = (i) => margem.esquerda + (pontos.length === 1 ? w / 2 : (i / (pontos.length - 1)) * w);
  const y = (n) => margem.topo + h - (num(n) / maior) * h;
  const caminho = pontos.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.total)}`).join(" ");
  // Área sob a curva: só enfeite, mas ajuda a ler volume quando a série é longa.
  const area = `${caminho} L${x(pontos.length - 1)},${margem.topo + h} L${x(0)},${margem.topo + h} Z`;

  // Rótulos do eixo X: com muitos pontos eles se sobrepõem e viram borrão. Três âncoras
  // (começo, meio, fim) dizem o período sem poluir.
  const marcadores = pontos.length <= 10
    ? pontos.map((_, i) => i)
    : [0, Math.floor((pontos.length - 1) / 2), pontos.length - 1];

  return (
    <svg className="gm-linha-svg" viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label={rotuloAria}>
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={margem.esquerda} x2={largura - margem.direita}
            y1={margem.topo + h * f} y2={margem.topo + h * f} className="gm-grid-line" />
          <text x={margem.esquerda - 8} y={margem.topo + h * f + 4} textAnchor="end">
            {Math.round(maior * (1 - f))}
          </text>
        </g>
      ))}
      <path d={area} className="gm-linha-area" />
      <path d={caminho} className="gm-linha-path" />
      {pontos.map((p, i) => (
        <circle key={p.data || i} cx={x(i)} cy={y(p.total)} r="3.5" className="gm-linha-ponto">
          <title>{`${p.label}: ${p.total}${unidade ? ` ${unidade}` : ""}`}</title>
        </circle>
      ))}
      {marcadores.map((i) => (
        <text key={`m${i}`} x={x(i)} y={altura - 7} textAnchor="middle">{pontos[i].label}</text>
      ))}
    </svg>
  );
}

/** Linha com duas series sobrepostas. `pontos`: [{ label, ...campos }].
 *
 * Separado de `GraficoLinha` porque a pergunta e outra: uma serie mostra evolucao, duas
 * mostram SALDO — entrou mais do que saiu? O eixo Y e compartilhado de proposito; com um
 * eixo por serie o cruzamento das linhas viraria enfeite, sem significar nada.
 */
export function GraficoLinhaDupla({ pontos = [], series = [], rotuloAria = "Comparativo" }) {
  const largura = 640;
  const altura = 210;
  const margem = { topo: 14, direita: 12, baixo: 34, esquerda: 38 };
  const w = largura - margem.esquerda - margem.direita;
  const h = altura - margem.topo - margem.baixo;

  if (!pontos.length || !series.length) return <p className="gm-vazio">Sem dados no período.</p>;

  const maior = Math.max(1, ...pontos.flatMap((p) => series.map((s) => num(p[s.campo]))));
  const x = (i) => margem.esquerda + (pontos.length === 1 ? w / 2 : (i / (pontos.length - 1)) * w);
  const y = (v) => margem.topo + h - (num(v) / maior) * h;

  const marcadores = pontos.length <= 12
    ? pontos.map((_, i) => i)
    : [0, Math.floor((pontos.length - 1) / 2), pontos.length - 1];

  return (
    <>
      <svg className="gm-linha-svg" viewBox={`0 0 ${largura} ${altura}`} role="img" aria-label={rotuloAria}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={margem.esquerda} x2={largura - margem.direita}
              y1={margem.topo + h * f} y2={margem.topo + h * f} className="gm-grid-line" />
            <text x={margem.esquerda - 8} y={margem.topo + h * f + 4} textAnchor="end">
              {Math.round(maior * (1 - f))}
            </text>
          </g>
        ))}
        {series.map((s) => (
          <path key={s.campo} fill="none" stroke={s.cor} strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round"
            d={pontos.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p[s.campo])}`).join(" ")} />
        ))}
        {series.map((s) => pontos.map((p, i) => (
          <circle key={`${s.campo}-${i}`} cx={x(i)} cy={y(p[s.campo])} r="3"
            fill="#fff" stroke={s.cor} strokeWidth="2">
            <title>{`${p.label} · ${s.rotulo}: ${p[s.campo]}`}</title>
          </circle>
        )))}
        {marcadores.map((i) => (
          <text key={`m${i}`} x={x(i)} y={altura - 7} textAnchor="middle">{pontos[i].label}</text>
        ))}
      </svg>
      <div className="gm-legenda-inline">
        {series.map((s) => (
          <span key={s.campo}><i style={{ background: s.cor }} />{s.rotulo}</span>
        ))}
      </div>
    </>
  );
}

/** N series sobre o mesmo eixo. `datas`: rotulos do X; `series`: [{ nome, pontos[] }].
 *
 * Separado de `GraficoLinhaDupla` porque a pergunta e outra: duas series comparam saldo
 * (entrou x saiu), N series comparam PARTICIPANTES entre si. Por isso legenda com nome e
 * cor da paleta rotativa, em vez de cor com significado fixo.
 *
 * Series zeradas saem: um corretor que nao visitou no periodo vira uma reta no zero, e
 * dez retas no zero escondem quem de fato trabalhou.
 */
export function GraficoMultiLinha({ datas = [], series = [], rotuloAria = "Evolução" }) {
  const largura = 720;
  const altura = 240;
  const margem = { topo: 14, direita: 12, baixo: 34, esquerda: 38 };
  const w = largura - margem.esquerda - margem.direita;
  const h = altura - margem.topo - margem.baixo;

  const vivas = series.filter((s) => (s.pontos || []).some((p) => num(p) > 0));
  if (!datas.length || !vivas.length) return <p className="gm-vazio">Sem dados no período.</p>;

  const maior = Math.max(1, ...vivas.flatMap((s) => (s.pontos || []).map(num)));
  const x = (i) => margem.esquerda + (datas.length === 1 ? w / 2 : (i / (datas.length - 1)) * w);
  const y = (v) => margem.topo + h - (num(v) / maior) * h;

  const marcadores = datas.length <= 12
    ? datas.map((_, i) => i)
    : [0, Math.floor((datas.length - 1) / 2), datas.length - 1];

  // `dd/mm` a partir do ISO: o eixo nao tem largura para o ano.
  const curto = (iso) => String(iso || "").slice(5).split("-").reverse().join("/");

  return (
    <>
      <svg className="gm-linha-svg gm-linha-svg--alta" viewBox={`0 0 ${largura} ${altura}`}
        role="img" aria-label={rotuloAria}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={margem.esquerda} x2={largura - margem.direita}
              y1={margem.topo + h * f} y2={margem.topo + h * f} className="gm-grid-line" />
            <text x={margem.esquerda - 8} y={margem.topo + h * f + 4} textAnchor="end">
              {Math.round(maior * (1 - f))}
            </text>
          </g>
        ))}
        {vivas.map((s, i) => (
          <path key={s.nome} fill="none" stroke={corDaFatia(i)} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round"
            d={(s.pontos || []).map((p, j) => `${j ? "L" : "M"}${x(j)},${y(p)}`).join(" ")}>
            <title>{s.nome}</title>
          </path>
        ))}
        {marcadores.map((i) => (
          <text key={`m${i}`} x={x(i)} y={altura - 7} textAnchor="middle">{curto(datas[i])}</text>
        ))}
      </svg>
      <div className="gm-legenda-inline">
        {vivas.map((s, i) => (
          <span key={s.nome}>
            <i style={{ background: corDaFatia(i) }} />
            {s.nome} <b>{(s.pontos || []).reduce((a, p) => a + num(p), 0)}</b>
          </span>
        ))}
      </div>
    </>
  );
}

/** Rosca com legenda. `dados`: [{ rotulo, total }].
 *
 * `conic-gradient` em vez de arcos SVG: o furo do meio é um `::after` do CSS que já
 * existia, e um anel com 8 fatias sai em uma propriedade em vez de 8 paths com
 * trigonometria.
 */
export function GraficoPizza({ dados = [], centroValor, centroRotulo, cores }) {
  const total = dados.reduce((s, d) => s + num(d.total), 0);

  const fundo = useMemo(() => {
    if (!total) return "conic-gradient(#e7e4eb 0 100%)";
    let inicio = 0;
    const trechos = dados.filter((d) => num(d.total)).map((d, i) => {
      const fim = inicio + (num(d.total) / total) * 100;
      const trecho = `${(cores && cores[d.rotulo]) || corDaFatia(i)} ${inicio}% ${fim}%`;
      inicio = fim;
      return trecho;
    });
    return `conic-gradient(${trechos.join(", ")})`;
  }, [dados, total, cores]);

  if (!total) return <p className="gm-vazio">Sem dados no período.</p>;

  return (
    <div className="gm-pizza-wrap">
      <div className="gm-pizza" style={{ background: fundo }} aria-hidden="true">
        <span>
          <strong>{centroValor ?? total}</strong>
          <small>{centroRotulo || "total"}</small>
        </span>
      </div>
      <div className="gm-legenda">
        {dados.filter((d) => num(d.total)).map((d, i) => (
          <div key={d.rotulo} title={`${d.rotulo}: ${d.total}`}>
            <i style={{ background: (cores && cores[d.rotulo]) || corDaFatia(i) }} />
            <span className="gm-legenda-nome">{d.rotulo}</span>
            <strong>{d.total}</strong>
            <small>{Math.round((num(d.total) / total) * 100)}%</small>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Barras horizontais ordenadas. `dados`: [{ rotulo, total }].
 *
 * O denominador é o maior item, não o total: aqui a pergunta é "quem lidera e por
 * quanto", e contra o total todas as barras ficariam curtas quando há muitas categorias.
 */
export function GraficoBarras({ dados = [], sufixo = "", resolverRotulo }) {
  if (!dados.length) return <p className="gm-vazio">Sem dados no período.</p>;
  const maior = Math.max(1, ...dados.map((d) => num(d.total)));
  const total = dados.reduce((s, d) => s + num(d.total), 0);

  return (
    <div className="gm-ranking">
      {dados.map((d, i) => {
        const nome = resolverRotulo ? resolverRotulo(d.rotulo) : d.rotulo;
        const pct = total ? Math.round((num(d.total) / total) * 100) : 0;
        return (
          <div className="gm-ranking-item" key={d.rotulo}
            title={`${nome}: ${d.total}${sufixo ? ` ${sufixo}` : ""} (${pct}% do total)`}>
            <span>{nome}</span>
            <div>
              <span style={{
                display: "block", height: "100%",
                width: `${Math.max(3, (num(d.total) / maior) * 100)}%`,
                background: corDaFatia(i), borderRadius: 99,
              }} />
            </div>
            <strong>{d.total}</strong>
          </div>
        );
      })}
    </div>
  );
}
