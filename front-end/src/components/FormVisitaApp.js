import React, { useState, useEffect } from "react";
import "../assets/css/AppVisita.css";

const API_BASE = "/api";
//const API_BASE = "http://localhost:5000";


const VISITAS_BASE_URL =
  "https://script.google.com/macros/s/AKfycbwULEpUbgyO1jcdO_xWachhfJoNptZMUjiMJz-csZHgfiKWJVPqRH6nvc0FTUBz9fyz8Q/exec";

const HISTORICO_BASE_URL =
  "https://script.google.com/macros/s/AKfycbzDDQSdBL3NnPOx_zszEJwtd1r_2RpKzRbAn3LcamBbHizuPnvrr5DLuLVESjd8xScJaQ/exec";

export default function ApiForms() {
  // --- VISITAS ---
  const [visitaId, setVisitaId] = useState("");

  // --- HISTÓRICO ---
  const [imovelId, setImovelId] = useState("");

  // --- Dados do Usuário Logado ---
  const [corretorId, setCorretorId] = useState("");
  const [corTel, setCorTel] = useState("");
  const [corNome, setCorNome] = useState("");
  const [corInsta, setCorInsta] = useState("");
  const [corDesc, setCorDesc] = useState("");

  // --- Busca de Visitas (dropdown) ---
  const [visitaQuery, setVisitaQuery] = useState("");
  const [visitasSugestoes, setVisitasSugestoes] = useState([]);
  const [loadingVisitas, setLoadingVisitas] = useState(false);
  const [showSugestoesVisitas, setShowSugestoesVisitas] = useState(false);

  // Carrega userData do localStorage
  useEffect(() => {
    const userDataString = localStorage.getItem("userData");
    if (!userDataString) return;

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

      if (userData.telefone) setCorTel(userData.telefone);
      if (userData.nome) setCorNome(userData.nome);
      if (userData.instagram) setCorInsta(userData.instagram);
      if (userData.descricao) setCorDesc(userData.descricao);
    } catch (error) {
      console.error("Erro ao fazer parse dos dados do usuário:", error);
    }
  }, []);

  async function buscarVisitas(q) {
    const qq = (q || "").trim();

    if (!corretorId) {
      setVisitasSugestoes([]);
      return;
    }

    setLoadingVisitas(true);
    try {
      const resp = await fetch(
        `${API_BASE}/visitas_busca?id_corretor=${encodeURIComponent(
          corretorId
        )}&q=${encodeURIComponent(qq)}&limit=30`,
        { method: "GET" }
      );

      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao buscar visitas");
      }

      setVisitasSugestoes(Array.isArray(data.lista) ? data.lista : []);
    } catch (e) {
      console.error(e);
      setVisitasSugestoes([]);
    } finally {
      setLoadingVisitas(false);
    }
  }

  // Debounce
  useEffect(() => {
    if (!showSugestoesVisitas) return;
    const t = setTimeout(() => {
      buscarVisitas(visitaQuery);
    }, 300);
    return () => clearTimeout(t);
  }, [visitaQuery, showSugestoesVisitas, corretorId]);

  function handleSubmitVisitas(e) {
    e.preventDefault();

    if (!corTel) {
      alert("Erro: Telefone do corretor não carregado. Faça login novamente.");
      return;
    }

    if (!visitaId) {
      alert("Selecione uma visita pelo nome do cliente.");
      return;
    }

    const url =
      `${VISITAS_BASE_URL}` +
      `?visitaId=${encodeURIComponent(visitaId)}` +
      `&fone=${encodeURIComponent(corTel)}`;

    window.open(url, "_blank");
  }

  function handleSubmitHistorico(e) {
    e.preventDefault();

    if (!corNome || !corTel) {
      alert("Erro: Dados do corretor não carregados. Faça login novamente.");
      return;
    }

    if (!imovelId) {
      alert("Informe o Id do imóvel.");
      return;
    }

    const url =
      `${HISTORICO_BASE_URL}` +
      `?imovelId=${encodeURIComponent(imovelId)}` +
      `&corNome=${encodeURIComponent(corNome)}` +
      `&corTel=${encodeURIComponent(corTel)}` +
      `&corInsta=${encodeURIComponent(corInsta)}` +
      `&corDesc=${encodeURIComponent(corDesc)}`;

    window.open(url, "_blank");
  }

  return (
    <div className="api-forms-container">
      {/* Form VISITAS */}
      <form className="api-form" onSubmit={handleSubmitVisitas}>
        <h2 className="api-form-title">Chamada de Visitas</h2>

        {/* Dropdown: mostra NOME do cliente */}
        <div className="api-form-group">
          <label>Escolher cliente (clique no nome)</label>
          <input
            type="text"
            value={visitaQuery}
            onChange={(e) => {
              setVisitaQuery(e.target.value);
              setShowSugestoesVisitas(true);
            }}
            onFocus={() => {
              setShowSugestoesVisitas(true);
              // quando focar, se estiver vazio, lista as últimas visitas
              if (!visitaQuery.trim()) buscarVisitas("");
            }}
            onBlur={() => {
              // dá tempo do clique registrar antes de fechar
              setTimeout(() => setShowSugestoesVisitas(false), 150);
            }}
            placeholder="Digite parte do nome, data ou id do imóvel..."
          />

          {loadingVisitas && <div className="api-form-hint">Buscando...</div>}

          {showSugestoesVisitas && visitasSugestoes.length > 0 && (
            <div className="api-sugestoes">
              {visitasSugestoes.map((it) => (
                <button
                  key={it.id_visita}
                  type="button"
                  className="api-sugestao-item"
                  onMouseDown={(e) => e.preventDefault()} // evita perder foco antes do click
                  onClick={() => {
                    setVisitaId(it.id_visita);
                    // deixa o input mostrando o nome selecionado
                    setVisitaQuery(it.cliente || "");
                    setShowSugestoesVisitas(false);
                    setVisitasSugestoes([]);
                  }}
                >
                  {/* TÍTULO: NOME DO CLIENTE */}
                  <div className="api-sugestao-title">
                    {it.cliente || "Sem nome"}
                  </div>

                  {/* SUB: detalhes (sem row) */}
                  <div className="api-sugestao-sub">
                    {it.dataVisita ? `Data: ${it.dataVisita}` : ""}
                    {it.imovelId ? ` | Imóvel: ${it.imovelId}` : ""}
                    {` | Id: ${it.id_visita}`}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* id_visita preenchido automaticamente */}
        <div className="api-form-group">
          <label htmlFor="visitaId">Id da Visita (preenchido ao clicar)</label>
          <input
            id="visitaId"
            type="text"
            value={visitaId}
            onChange={(e) => setVisitaId(e.target.value)}
            placeholder="Clique em um cliente acima"
            required
          />
        </div>

        <button className="api-form-button" type="submit">
          Abrir link de Visita
        </button>
      </form>

      {/* Form HISTÓRICO */}
      <form className="api-form" onSubmit={handleSubmitHistorico}>
        <h2 className="api-form-title">Chamada de Histórico</h2>

        <div className="api-form-group">
          <label htmlFor="imovelId">Id do Imóvel</label>
          <input
            id="imovelId"
            type="text"
            value={imovelId}
            onChange={(e) => setImovelId(e.target.value)}
            placeholder="Ex: IMV-001"
            required
          />
        </div>

        <button className="api-form-button" type="submit">
          Abrir link de Histórico
        </button>
      </form>
    </div>
  );
}