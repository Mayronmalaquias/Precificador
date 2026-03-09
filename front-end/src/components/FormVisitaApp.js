import React, { useEffect, useMemo, useState } from "react";
import "../assets/css/AppVisita.css";

const API_BASE = "/api";
//const API_BASE = "http://localhost:5000";

const HISTORICO_BASE_URL =
  "https://script.google.com/macros/s/AKfycbzDDQSdBL3NnPOx_zszEJwtd1r_2RpKzRbAn3LcamBbHizuPnvrr5DLuLVESjd8xScJaQ/exec";

function parseBrDate(dateStr) {
  if (!dateStr) return null;
  const parts = String(dateStr).split("/");
  if (parts.length !== 3) return null;
  const [dd, mm, yyyy] = parts.map(Number);
  if (!dd || !mm || !yyyy) return null;
  return new Date(yyyy, mm - 1, dd);
}

function formatDateSafe(dateStr) {
  return dateStr || "-";
}

export default function ApiForms() {
  const [corretorId, setCorretorId] = useState("");
  const [corTel, setCorTel] = useState("");
  const [corNome, setCorNome] = useState("");
  const [corInsta, setCorInsta] = useState("");
  const [corDesc, setCorDesc] = useState("");

  const [loadingPage, setLoadingPage] = useState(true);
  const [loadingVisitaPdf, setLoadingVisitaPdf] = useState(false);
  const [error, setError] = useState("");

  const [visitas, setVisitas] = useState([]);
  const [imoveis, setImoveis] = useState([]);

  const [filtroVisitas, setFiltroVisitas] = useState("");
  const [filtroImoveis, setFiltroImoveis] = useState("");

  const [itemSelecionado, setItemSelecionado] = useState(null);
  const [tipoSelecionado, setTipoSelecionado] = useState("");

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
      setCorInsta(userData.instagram || "");
      setCorDesc(userData.descricao || "");
    } catch (err) {
      console.error(err);
      setError("Erro ao carregar os dados do corretor.");
      setLoadingPage(false);
    }
  }, []);

  useEffect(() => {
    if (!corretorId) return;
    carregarTudo();
  }, [corretorId]);

  async function carregarTudo() {
    setLoadingPage(true);
    setError("");

    try {
      const [respVisitas, respImoveis] = await Promise.all([
        fetch(
          `${API_BASE}/visitas_busca?id_corretor=${encodeURIComponent(
            corretorId
          )}&q=&limit=200`,
          { method: "GET" }
        ),
        fetch(
          `${API_BASE}/imoveis_busca_corretor?id_corretor=${encodeURIComponent(
            corretorId
          )}&q=&limit=200`,
          { method: "GET" }
        ),
      ]);

      const dataVisitas = await respVisitas.json().catch(() => ({}));
      const dataImoveis = await respImoveis.json().catch(() => ({}));

      if (!respVisitas.ok || !dataVisitas.ok) {
        throw new Error(dataVisitas.error || "Erro ao carregar visitas.");
      }

      if (!respImoveis.ok || !dataImoveis.ok) {
        throw new Error(dataImoveis.error || "Erro ao carregar imóveis.");
      }

      const listaVisitas = Array.isArray(dataVisitas.lista)
        ? dataVisitas.lista
        : [];
      const listaImoveis = Array.isArray(dataImoveis.lista)
        ? dataImoveis.lista
        : [];

      setVisitas(listaVisitas);
      setImoveis(listaImoveis);

      if (listaVisitas.length > 0) {
        setTipoSelecionado("visita");
        setItemSelecionado(listaVisitas[0]);
      } else if (listaImoveis.length > 0) {
        setTipoSelecionado("imovel");
        setItemSelecionado(listaImoveis[0]);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || "Erro ao carregar os dados da página.");
    } finally {
      setLoadingPage(false);
    }
  }

  const visitasFiltradas = useMemo(() => {
    const q = filtroVisitas.trim().toLowerCase();
    if (!q) return visitas;

    return visitas.filter((item) => {
      const texto = [
        item.cliente,
        item.dataVisita,
        item.imovelId,
        item.id_visita,
        item.label,
      ]
        .join(" ")
        .toLowerCase();

      return texto.includes(q);
    });
  }, [visitas, filtroVisitas]);

  const imoveisFiltrados = useMemo(() => {
    const q = filtroImoveis.trim().toLowerCase();
    if (!q) return imoveis;

    return imoveis.filter((item) => {
      const texto = [
        item.id_imovel,
        item.ultima_data,
        item.label,
        Array.isArray(item.clientes) ? item.clientes.join(" ") : "",
      ]
        .join(" ")
        .toLowerCase();

      return texto.includes(q);
    });
  }, [imoveis, filtroImoveis]);

  const resumo = useMemo(() => {
    const totalVisitas = visitas.length;
    const totalImoveis = imoveis.length;

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
      ultimaVisita,
    };
  }, [visitas, imoveis]);

  function selecionarVisita(item) {
    setTipoSelecionado("visita");
    setItemSelecionado(item);
  }

  function selecionarImovel(item) {
    setTipoSelecionado("imovel");
    setItemSelecionado(item);
  }

  async function abrirPdfVisita() {
    if (!itemSelecionado || tipoSelecionado !== "visita") return;

    setLoadingVisitaPdf(true);
    try {
      const resp = await fetch(
        `${API_BASE}/visitas/pdf?visita_id=${encodeURIComponent(
          itemSelecionado.id_visita
        )}`,
        { method: "GET" }
      );

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao gerar o PDF da visita.");
      }

      if (!data.drive_url) {
        throw new Error("A API não retornou a URL do PDF.");
      }

      window.open(data.drive_url, "_blank");
    } catch (err) {
      console.error(err);
      alert(err.message || "Erro ao abrir o PDF da visita.");
    } finally {
      setLoadingVisitaPdf(false);
    }
  }

  function baixarPdfVisita() {
    if (!itemSelecionado || tipoSelecionado !== "visita") return;

    const url =
      `${API_BASE}/visitas/pdf/download` +
      `?visita_id=${encodeURIComponent(itemSelecionado.id_visita)}`;

    window.open(url, "_blank");
  }

  async function abrirHistoricoImovel() {
    if (!itemSelecionado || tipoSelecionado !== "imovel") return;

    try {
      const resp = await fetch(
        `${API_BASE}/imoveis/pdf?imovel_id=${encodeURIComponent(
          itemSelecionado.id_imovel
        )}`,
        { method: "GET" }
      );

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao gerar o PDF do imóvel.");
      }

      if (!data.drive_url) {
        throw new Error("A API não retornou a URL do PDF do imóvel.");
      }

      window.open(data.drive_url, "_blank");
    } catch (err) {
      console.error(err);
      alert(err.message || "Erro ao abrir o relatório do imóvel.");
    }
  }
  function baixarHistoricoImovel() {
    if (!itemSelecionado || tipoSelecionado !== "imovel") return;

    const url =
      `${API_BASE}/imoveis/pdf/download` +
      `?imovel_id=${encodeURIComponent(itemSelecionado.id_imovel)}`;

    window.open(url, "_blank");
  }

  return (
    <div className="relatorios-page">
      <div className="relatorios-header">
        <div>
          <h1 className="relatorios-title">Painel de Relatórios</h1>
          <p className="relatorios-subtitle">
            Visualize suas visitas e imóveis automaticamente e gere os PDFs com
            um clique.
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
            <h2>Visitas</h2>
            <span>{visitasFiltradas.length}</span>
          </div>

          <input
            type="text"
            className="relatorios-search"
            placeholder="Filtrar visitas por cliente, data ou imóvel..."
            value={filtroVisitas}
            onChange={(e) => setFiltroVisitas(e.target.value)}
          />

          <div className="relatorios-list">
            {loadingPage ? (
              <div className="relatorios-empty">Carregando visitas...</div>
            ) : visitasFiltradas.length === 0 ? (
              <div className="relatorios-empty">Nenhuma visita encontrada.</div>
            ) : (
              visitasFiltradas.map((item) => (
                <button
                  key={item.id_visita}
                  type="button"
                  className={`relatorios-item ${
                    tipoSelecionado === "visita" &&
                    itemSelecionado?.id_visita === item.id_visita
                      ? "is-active"
                      : ""
                  }`}
                  onClick={() => selecionarVisita(item)}
                >
                  <div className="relatorios-item-title">
                    {item.cliente || "Sem cliente"}
                  </div>
                  <div className="relatorios-item-sub">
                    {item.dataVisita ? `Data: ${item.dataVisita}` : ""}
                    {item.imovelId ? ` | Imóvel: ${item.imovelId}` : ""}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="relatorios-list-card">
          <div className="relatorios-card-header">
            <h2>Imóveis já visitados</h2>
            <span>{imoveisFiltrados.length}</span>
          </div>

          <input
            type="text"
            className="relatorios-search"
            placeholder="Filtrar imóveis ou clientes..."
            value={filtroImoveis}
            onChange={(e) => setFiltroImoveis(e.target.value)}
          />

          <div className="relatorios-list">
            {loadingPage ? (
              <div className="relatorios-empty">Carregando imóveis...</div>
            ) : imoveisFiltrados.length === 0 ? (
              <div className="relatorios-empty">Nenhum imóvel encontrado.</div>
            ) : (
              imoveisFiltrados.map((item) => (
                <button
                  key={item.id_imovel}
                  type="button"
                  className={`relatorios-item ${
                    tipoSelecionado === "imovel" &&
                    itemSelecionado?.id_imovel === item.id_imovel
                      ? "is-active"
                      : ""
                  }`}
                  onClick={() => selecionarImovel(item)}
                >
                  <div className="relatorios-item-title">
                    {item.id_imovel || "Sem imóvel"}
                  </div>
                  <div className="relatorios-item-sub">
                    {`Visitas: ${item.qtd_visitas ?? 0}`}
                    {item.ultima_data ? ` | Última: ${item.ultima_data}` : ""}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="relatorios-detail-card">
        {!itemSelecionado ? (
          <div className="relatorios-empty">
            Selecione uma visita ou um imóvel para visualizar os detalhes.
          </div>
        ) : tipoSelecionado === "visita" ? (
          <>
            <div className="relatorios-card-header">
              <h2>Detalhes da visita</h2>
              <span>{itemSelecionado.id_visita}</span>
            </div>

            <div className="relatorios-detail-grid">
              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Cliente</span>
                <strong>{itemSelecionado.cliente || "-"}</strong>
              </div>

              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Data</span>
                <strong>{formatDateSafe(itemSelecionado.dataVisita)}</strong>
              </div>

              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Imóvel</span>
                <strong>{itemSelecionado.imovelId || "-"}</strong>
              </div>

              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Id da visita</span>
                <strong>{itemSelecionado.id_visita || "-"}</strong>
              </div>
            </div>

            <div className="relatorios-actions">
              <button
                type="button"
                className="relatorios-primary-btn"
                onClick={abrirPdfVisita}
                disabled={loadingVisitaPdf}
              >
                {loadingVisitaPdf ? "Gerando PDF..." : "Abrir PDF da visita"}
              </button>

              <button
                type="button"
                className="relatorios-secondary-btn"
                onClick={baixarPdfVisita}
              >
                Baixar PDF
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="relatorios-card-header">
              <h2>Detalhes do imóvel</h2>
              <span>{itemSelecionado.id_imovel}</span>
            </div>

            <div className="relatorios-detail-grid">
              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Imóvel</span>
                <strong>{itemSelecionado.id_imovel || "-"}</strong>
              </div>

              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Total de visitas</span>
                <strong>{itemSelecionado.qtd_visitas ?? 0}</strong>
              </div>

              <div className="relatorios-detail-box">
                <span className="relatorios-detail-label">Última visita</span>
                <strong>{itemSelecionado.ultima_data || "-"}</strong>
              </div>

              <div className="relatorios-detail-box relatorios-detail-box--full">
                <span className="relatorios-detail-label">Clientes vinculados</span>
                <strong>
                  {Array.isArray(itemSelecionado.clientes) &&
                  itemSelecionado.clientes.length > 0
                    ? itemSelecionado.clientes.join(", ")
                    : "-"}
                </strong>
              </div>
            </div>

            <div className="relatorios-actions">
              <button
                type="button"
                className="relatorios-primary-btn"
                onClick={abrirHistoricoImovel}
              >
                Abrir PDF do imóvel
              </button>

              <button
                type="button"
                className="relatorios-secondary-btn"
                onClick={baixarHistoricoImovel}
              >
                Baixar PDF
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}