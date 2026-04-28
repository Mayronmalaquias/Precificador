import React, { useEffect, useMemo, useState } from "react";
import "../assets/css/AppVisita.css";

const API_BASE = "/api";
//const API_BASE = "http://localhost:5000";

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

  useEffect(() => {
    if (!corretorId) return;
    carregarTudo();
  }, [corretorId]);

  async function carregarTudo() {
    setLoadingPage(true);
    setError("");

    try {
      const [respVisitas, respImoveis, respClientes] = await Promise.all([
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
        fetch(
          `${API_BASE}/clientes_busca?id_corretor=${encodeURIComponent(
            corretorId
          )}&q=&limit=200`,
          { method: "GET" }
        ),
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
  }

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
    </div>
  );
}