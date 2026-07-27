import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
import { useToast } from "../context/ToastContext";
import { BarrasSemanas, CORES, LineChart } from "./CaptacaoEvolucao";
import "../assets/css/captacaoEvolucao.css";

const DIMENSOES = [
  ["total", "Total"],
  ["equipe", "Equipe"],
  ["corretor", "Corretor"],
  ["proposta", "Proposta"],
  ["quartos", "Quartos"],
  ["cliente", "Cliente"],
  ["imovel", "Imóvel"],
  ["tipo_captacao", "Tipo de captação"],
];

const MES_NOME = [
  "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

export default function VisitasEvolucao({ idGerente, dataInicial = "", dataFinal = "", todasEquipes = false }) {
  const toast = useToast();
  const [dimensao, setDimensao] = useState(() => todasEquipes ? "equipe" : "corretor");
  const [filtros, setFiltros] = useState({
    equipe: "",
    corretor: "",
    proposta: "",
    quartos: "",
    cliente: "",
    imovel: "",
    tipo_captacao: "",
    com_parceiro: "",
    start: dataInicial,
    end: dataFinal,
  });
  const [opcoes, setOpcoes] = useState({
    equipes: [], corretores: [], clientes: [], propostas: [], quartos: [], tipos_captacao: [],
  });
  const [dados, setDados] = useState({ datas: [], series: [], resumo: {} });
  const [ocultas, setOcultas] = useState(() => new Set());
  const [loading, setLoading] = useState(false);
  const [mesBar, setMesBar] = useState("");

  useEffect(() => {
    setFiltros((atual) => ({ ...atual, start: dataInicial || "", end: dataFinal || "" }));
  }, [dataInicial, dataFinal]);

  useEffect(() => {
    if (!idGerente && !todasEquipes) return;
    let ativo = true;
    const params = new URLSearchParams();
    if (idGerente) params.set("id_gerente", idGerente);
    if (todasEquipes) params.set("solicitante_permissao", "diretor");
    fetch(`${BASE}/gerente-dashboard/visitas/evolucao/opcoes?${params.toString()}`)
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (ativo && ok && d.ok) {
          setOpcoes({
            equipes: d.equipes || [],
            corretores: d.corretores || [],
            clientes: d.clientes || [],
            propostas: d.propostas || [],
            quartos: d.quartos || [],
            tipos_captacao: d.tipos_captacao || [],
          });
        }
      })
      .catch(() => {});
    return () => { ativo = false; };
  }, [idGerente, todasEquipes]);

  useEffect(() => {
    setDimensao(todasEquipes ? "equipe" : "corretor");
    setFiltros((atual) => ({ ...atual, equipe: "", corretor: "" }));
  }, [todasEquipes]);

  const buscar = useCallback(async () => {
    if (!idGerente && !todasEquipes) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ dimensao });
      if (idGerente) params.set("id_gerente", idGerente);
      if (todasEquipes) params.set("solicitante_permissao", "diretor");
      Object.entries(filtros).forEach(([chave, valor]) => {
        if (valor !== undefined && valor !== null && String(valor).trim()) {
          params.set(chave, valor);
        }
      });
      const resposta = await fetch(`${BASE}/gerente-dashboard/visitas/evolucao?${params.toString()}`);
      const json = await resposta.json();
      if (!resposta.ok || json.ok === false) throw new Error(json.error || "Erro ao carregar evolucao");
      setDados({ datas: json.datas || [], series: json.series || [], resumo: json.resumo || {} });
      setOcultas(new Set());
    } catch (erro) {
      toast(erro.message || "Erro ao carregar evolução de visitas", "error");
    } finally {
      setLoading(false);
    }
  }, [dimensao, filtros, idGerente, todasEquipes, toast]);

  useEffect(() => {
    buscar();
    // Os demais filtros sao aplicados pelo botao para evitar uma requisicao por tecla.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idGerente, dimensao]);

  const corPorNome = useMemo(() => {
    const mapa = {};
    dados.series.forEach((serie, indice) => { mapa[serie.nome] = CORES[indice % CORES.length]; });
    return mapa;
  }, [dados.series]);

  const seriesVisiveis = useMemo(
    () => dados.series
      .filter((serie) => !ocultas.has(serie.nome))
      .map((serie) => ({ ...serie, cor: corPorNome[serie.nome] })),
    [dados.series, ocultas, corPorNome]
  );

  const totalPorData = useMemo(() => {
    const totais = {};
    dados.datas.forEach((data, indice) => {
      totais[data] = dados.series.reduce((soma, serie) => soma + (serie.pontos[indice] || 0), 0);
    });
    return totais;
  }, [dados]);

  const mesesDisponiveis = useMemo(
    () => Array.from(new Set(dados.datas.map((data) => data.slice(0, 7)))).sort(),
    [dados.datas]
  );

  useEffect(() => {
    if (mesesDisponiveis.length && !mesesDisponiveis.includes(mesBar)) {
      setMesBar(mesesDisponiveis[mesesDisponiveis.length - 1]);
    }
  }, [mesBar, mesesDisponiveis]);

  const setFiltro = (chave) => (e) => setFiltros((atual) => ({ ...atual, [chave]: e.target.value }));
  const setEquipe = (e) => {
    const equipe = e.target.value;
    setFiltros((atual) => ({ ...atual, equipe, corretor: "" }));
    setDimensao(equipe ? "corretor" : "equipe");
  };
  const corretoresDisponiveis = useMemo(
    () => filtros.equipe
      ? opcoes.corretores.filter((corretor) => corretor.equipe === filtros.equipe)
      : opcoes.corretores,
    [filtros.equipe, opcoes.corretores]
  );
  const toggleSerie = (nome) => setOcultas((atual) => {
    const proximo = new Set(atual);
    proximo.has(nome) ? proximo.delete(nome) : proximo.add(nome);
    return proximo;
  });
  const resumo = dados.resumo || {};

  return (
    <div className="ce-wrap ve-wrap">
      <div className="ve-resumo">
        <div><span>Visitas</span><strong>{resumo.total_visitas || 0}</strong></div>
        <div><span>Clientes únicos</span><strong>{resumo.clientes_unicos || 0}</strong></div>
        <div><span>Com proposta</span><strong>{resumo.visitas_com_proposta || 0}</strong></div>
        <div><span>Imóveis visitados</span><strong>{resumo.imoveis_unicos || 0}</strong></div>
      </div>

      <div className="ce-controls">
        <div className="ce-dims">
          <span className="ce-dims-label">Agrupar linhas por:</span>
          {DIMENSOES.filter(([id]) => todasEquipes || id !== "equipe").map(([id, label]) => (
            <button key={id} className={`ce-dim ${dimensao === id ? "is-active" : ""}`} onClick={() => setDimensao(id)}>
              {label}
            </button>
          ))}
        </div>

        <div className="ce-filtros">
          {todasEquipes && (
            <select className="ce-input" value={filtros.equipe} onChange={setEquipe}>
              <option value="">Equipe (todas)</option>
              {opcoes.equipes.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          )}
          <select className="ce-input" value={filtros.corretor} onChange={setFiltro("corretor")}>
            <option value="">Corretor (todos)</option>
            {corretoresDisponiveis.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="ce-input" value={filtros.proposta} onChange={setFiltro("proposta")}>
            <option value="">Proposta (todas)</option>
            {opcoes.propostas.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="ce-input" value={filtros.quartos} onChange={setFiltro("quartos")}>
            <option value="">Quartos (todos)</option>
            {opcoes.quartos.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="ce-input" value={filtros.cliente} onChange={setFiltro("cliente")}>
            <option value="">Cliente (todos)</option>
            {opcoes.clientes.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <input className="ce-input" placeholder="Código ou endereço do imóvel" value={filtros.imovel} onChange={setFiltro("imovel")} />
          <select className="ce-input" value={filtros.tipo_captacao} onChange={setFiltro("tipo_captacao")}>
            <option value="">Tipo de captação (todos)</option>
            {opcoes.tipos_captacao.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="ce-input" value={filtros.com_parceiro} onChange={setFiltro("com_parceiro")}>
            <option value="">Parceiro (todos)</option>
            <option value="sim">Com parceiro</option>
            <option value="nao">Sem parceiro</option>
          </select>
          <input className="ce-input" type="date" value={filtros.start} onChange={setFiltro("start")} />
          <input className="ce-input" type="date" value={filtros.end} onChange={setFiltro("end")} />
          <button className="ce-btn" onClick={buscar} disabled={loading}>{loading ? "..." : "Aplicar"}</button>
        </div>
      </div>

      {!dados.datas.length ? (
        <div className="ce-empty">{loading ? "Carregando..." : "Sem visitas para os filtros selecionados."}</div>
      ) : (
        <>
          <LineChart datas={dados.datas} series={seriesVisiveis} cores={CORES} />
          <div className="ce-legend">
            {dados.series.map((serie) => (
              <button key={serie.nome} className={`ce-leg ${ocultas.has(serie.nome) ? "is-off" : ""}`} onClick={() => toggleSerie(serie.nome)}>
                <span className="ce-dot" style={{ background: corPorNome[serie.nome] }} />
                {serie.nome}
              </button>
            ))}
          </div>

          {mesBar && (
            <div className="ce-barswrap">
              <div className="ce-barshead">
                <strong>Visitas por dia (mês em semanas)</strong>
                <select className="ce-input" value={mesBar} onChange={(e) => setMesBar(e.target.value)}>
                  {mesesDisponiveis.map((mes) => {
                    const [ano, numero] = mes.split("-");
                    return <option key={mes} value={mes}>{MES_NOME[Number(numero)]}/{ano}</option>;
                  })}
                </select>
              </div>
              <BarrasSemanas mes={mesBar} totalPorData={totalPorData} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
