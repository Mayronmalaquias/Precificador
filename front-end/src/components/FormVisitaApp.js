import React, { useCallback, useEffect, useMemo, useState } from "react";
import "../assets/css/AppVisita.css";

import { BASE } from "../services/api";

function parseBrDate(dateStr) {
  if (!dateStr) return null;
  const parts = String(dateStr).split("/");
  if (parts.length !== 3) return null;
  const [dd, mm, yyyy] = parts.map(Number);
  if (!dd || !mm || !yyyy) return null;
  return new Date(yyyy, mm - 1, dd);
}

export default function ApiForms() {
  const [corretorId, setCorretorId] = useState("");
  const [corTel, setCorTel] = useState("");
  const [corNome, setCorNome] = useState("");

  const [loadingPage, setLoadingPage] = useState(true);
  const [error, setError] = useState("");

  const [visitas, setVisitas] = useState([]);
  const [imoveis, setImoveis] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [visitaSelecionadaId, setVisitaSelecionadaId] = useState("");

  useEffect(() => {
    const userDataString = localStorage.getItem("userData");

    if (!userDataString) {
      setLoadingPage(false);
      setError("Usuário não encontrado no localStorage. Faça login novamente.");
      return;
    }

    try {
      const userData = JSON.parse(userDataString);

      const id =
        userData.idCorretor ||
        userData.id_corretor ||
        userData.codigoCorretor ||
        userData.codigo ||
        userData.id_usuarios ||
        "";

      setCorretorId(id);
      setCorTel(userData.telefone || "");
      setCorNome(userData.nome || "");
    } catch (err) {
      console.error(err);
      setError("Erro ao carregar os dados do corretor.");
      setLoadingPage(false);
    }
  }, []);

  const carregarTudo = useCallback(async () => {
    if (!corretorId) return;

    setLoadingPage(true);
    setError("");

    try {
      const query = `id_corretor=${encodeURIComponent(corretorId)}&q=&limit=200`;
      const [respVisitas, respImoveis, respClientes] = await Promise.all([
        fetch(`${BASE}/visitas_busca?${query}`, { method: "GET" }),
        fetch(`${BASE}/imoveis_busca_corretor?${query}`, { method: "GET" }),
        fetch(`${BASE}/clientes_busca?${query}`, { method: "GET" }),
      ]);

      const dataVisitas = await respVisitas.json().catch(() => ({}));
      const dataImoveis = await respImoveis.json().catch(() => ({}));
      const dataClientes = await respClientes.json().catch(() => ({}));

      if (!respVisitas.ok || !dataVisitas.ok) {
        throw new Error(dataVisitas.error || "Erro ao carregar visitas.");
      }

      if (!respImoveis.ok || !dataImoveis.ok) {
        throw new Error(dataImoveis.error || "Erro ao carregar imóveis.");
      }

      if (!respClientes.ok || !dataClientes.ok) {
        throw new Error(dataClientes.error || "Erro ao carregar clientes.");
      }

      setVisitas(Array.isArray(dataVisitas.lista) ? dataVisitas.lista : []);
      setImoveis(Array.isArray(dataImoveis.lista) ? dataImoveis.lista : []);
      setClientes(Array.isArray(dataClientes.lista) ? dataClientes.lista : []);
    } catch (err) {
      console.error(err);
      setError(err.message || "Erro ao carregar os dados da página.");
    } finally {
      setLoadingPage(false);
    }
  }, [corretorId]);

  useEffect(() => {
    carregarTudo();
  }, [carregarTudo]);

  useEffect(() => {
    if (!visitas.length) {
      setVisitaSelecionadaId("");
      return;
    }

    const existeSelecionada = visitas.some(
      (visita) => visita.id_visita === visitaSelecionadaId
    );

    if (!existeSelecionada) {
      setVisitaSelecionadaId(visitas[0].id_visita || "");
    }
  }, [visitas, visitaSelecionadaId]);

  const resumo = useMemo(() => {
    const totalVisitas = visitas.length;
    const totalImoveis = imoveis.length;
    const totalClientes = clientes.length;

    let ultimaVisita = "-";

    if (visitas.length > 0) {
      const ordenadas = [...visitas].sort((a, b) => {
        const da = parseBrDate(a.dataVisita);
        const db = parseBrDate(b.dataVisita);

        if (!da && !db) return 0;
        if (!da) return 1;
        if (!db) return -1;

        return db - da;
      });

      ultimaVisita = ordenadas[0]?.dataVisita || "-";
    }

    return {
      totalVisitas,
      totalImoveis,
      totalClientes,
      ultimaVisita,
    };
  }, [visitas, imoveis, clientes]);

  const visitaSelecionada = useMemo(() => {
    if (!visitas.length) return null;
    return (
      visitas.find((visita) => visita.id_visita === visitaSelecionadaId) ||
      visitas[0]
    );
  }, [visitas, visitaSelecionadaId]);

  const texto = (valor) => {
    const limpo = String(valor || "").trim();
    return limpo || "-";
  };

  const textoLista = (items, campo = "nome") => {
    if (!Array.isArray(items) || !items.length) return "-";
    return items.map((item) => item?.[campo]).filter(Boolean).join(", ") || "-";
  };

  return (
    <div className="relatorios-page">
      <div className="relatorios-header">
        <div>
          <h1 className="relatorios-title">Painel de Relatórios</h1>
          <p className="relatorios-subtitle">
            Visualize suas visitas, imóveis e clientes.
          </p>
        </div>

        <button
          type="button"
          className="relatorios-refresh"
          onClick={carregarTudo}
          disabled={loadingPage}
        >
          {loadingPage ? "Atualizando..." : "Atualizar"}
        </button>
      </div>

      <div className="relatorios-top-info">
        <div className="relatorios-user-card">
          <div className="relatorios-user-name">{corNome || "Corretor"}</div>
          <div className="relatorios-user-meta">Id: {corretorId || "-"}</div>
          <div className="relatorios-user-meta">Telefone: {corTel || "-"}</div>
        </div>

        <div className="relatorios-summary-card">
          <span className="relatorios-summary-label">Total de visitas</span>
          <strong className="relatorios-summary-value">
            {resumo.totalVisitas}
          </strong>
        </div>

        <div className="relatorios-summary-card">
          <span className="relatorios-summary-label">Imóveis visitados</span>
          <strong className="relatorios-summary-value">
            {resumo.totalImoveis}
          </strong>
        </div>

        <div className="relatorios-summary-card">
          <span className="relatorios-summary-label">Clientes</span>
          <strong className="relatorios-summary-value">
            {resumo.totalClientes}
          </strong>
        </div>

        <div className="relatorios-summary-card">
          <span className="relatorios-summary-label">Última visita</span>
          <strong className="relatorios-summary-value relatorios-summary-date">
            {resumo.ultimaVisita}
          </strong>
        </div>
      </div>

      {error && <div className="relatorios-error">{error}</div>}

      <div className="relatorios-grid">
        <section className="relatorios-list-card">
          <div className="relatorios-card-header">
            <h2>Visitas individuais</h2>
            <span>{visitas.length} registro(s)</span>
          </div>

          <div className="relatorios-list">
            {!visitas.length ? (
              <div className="relatorios-empty">Nenhuma visita encontrada.</div>
            ) : (
              visitas.map((visita) => (
                <button
                  key={visita.id_visita}
                  type="button"
                  className={`relatorios-item ${
                    visitaSelecionada?.id_visita === visita.id_visita
                      ? "is-active"
                      : ""
                  }`}
                  onClick={() => setVisitaSelecionadaId(visita.id_visita)}
                >
                  <div className="relatorios-item-title">
                    {texto(visita.cliente || visita.id_visita)}
                  </div>
                  <div className="relatorios-item-sub">
                    {texto(visita.dataVisita)} | Imovel {texto(visita.imovelId)}
                  </div>
                  <div className="relatorios-item-sub">
                    {texto(visita.proposta || visita.tipoCaptacao)}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="relatorios-detail-card">
          <div className="relatorios-card-header">
            <h2>Detalhes da visita</h2>
            <span>{texto(visitaSelecionada?.id_visita)}</span>
          </div>

          {!visitaSelecionada ? (
            <div className="relatorios-empty">Selecione uma visita.</div>
          ) : (
            <>
              <div className="relatorios-detail-grid">
                <div className="relatorios-detail-box">
                  <span className="relatorios-detail-label">Data</span>
                  <strong>{texto(visitaSelecionada.dataVisita)}</strong>
                </div>

                <div className="relatorios-detail-box">
                  <span className="relatorios-detail-label">Imovel</span>
                  <strong>{texto(visitaSelecionada.imovelId)}</strong>
                </div>

                <div className="relatorios-detail-box">
                  <span className="relatorios-detail-label">Proposta</span>
                  <strong>{texto(visitaSelecionada.proposta)}</strong>
                </div>

                <div className="relatorios-detail-box">
                  <span className="relatorios-detail-label">Tipo de captacao</span>
                  <strong>{texto(visitaSelecionada.tipoCaptacao)}</strong>
                </div>

                <div className="relatorios-detail-box relatorios-detail-box--full">
                  <span className="relatorios-detail-label">Clientes</span>
                  <strong>{textoLista(visitaSelecionada.clientes)}</strong>
                </div>

                <div className="relatorios-detail-box relatorios-detail-box--full">
                  <span className="relatorios-detail-label">Endereco externo</span>
                  <strong>{texto(visitaSelecionada.enderecoExterno)}</strong>
                </div>

                <div className="relatorios-detail-box">
                  <span className="relatorios-detail-label">Parceiros</span>
                  <strong>{textoLista(visitaSelecionada.parceiros)}</strong>
                </div>

                <div className="relatorios-detail-box">
                  <span className="relatorios-detail-label">Registrada em</span>
                  <strong>{texto(visitaSelecionada.createdAt)}</strong>
                </div>
              </div>

              <div className="relatorios-section">
                <div className="relatorios-detail-label">Avaliacoes</div>
                {!visitaSelecionada.avaliacoes?.length ? (
                  <div className="relatorios-empty">Sem avaliacao registrada.</div>
                ) : (
                  <div className="relatorios-evaluation-list">
                    {visitaSelecionada.avaliacoes.map((avaliacao, index) => (
                      <div className="relatorios-evaluation" key={`${avaliacao.cliente}-${index}`}>
                        <strong>{texto(avaliacao.cliente || `Avaliacao ${index + 1}`)}</strong>
                        <span>Nota geral: {texto(avaliacao.notaGeral)}</span>
                        <span>Localizacao: {texto(avaliacao.localizacao)}</span>
                        <span>Tamanho: {texto(avaliacao.tamanho)}</span>
                        <span>Preco: {texto(avaliacao.preco)}</span>
                        <span>Preco nota 10: {texto(avaliacao.precoNota10)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="relatorios-actions">
                {visitaSelecionada.linkImagem && (
                  <a
                    className="relatorios-secondary-btn relatorios-link-btn"
                    href={visitaSelecionada.linkImagem}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Abrir anexo
                  </a>
                )}
                {visitaSelecionada.linkAudio && (
                  <a
                    className="relatorios-secondary-btn relatorios-link-btn"
                    href={visitaSelecionada.linkAudio}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Abrir audio
                  </a>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
