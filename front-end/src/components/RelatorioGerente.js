import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BASE } from '../services/api';
import "../assets/css/RelatorioGerente.css";
import { useToast } from '../context/ToastContext';

const CRITERIOS_AV = [
  { key: "localizacao", label: "Localização" },
  { key: "tamanho", label: "Tamanho" },
  { key: "planta", label: "Planta" },
  { key: "acabamento", label: "Acabamento" },
  { key: "conservacao", label: "Conservação" },
  { key: "condominio", label: "Condomínio" },
  { key: "preco", label: "Preço" },
  { key: "notaGeral", label: "Nota Geral" },
];

function AvaliacaoEditorG({ av, onChange }) {
  return (
    <div className="ev-card">
      {av.cliente && <div className="ev-card-cliente">{av.cliente}</div>}
      <div className="ev-grid">
        {CRITERIOS_AV.map(({ key, label }) => {
          const val = Number(av[key]) || 0;
          return (
            <div key={key} className="ev-item">
              <div className="ev-item-head">
                <span className="ev-item-label">{label}</span>
                <span className="ev-item-val" style={{ color: val >= 8 ? "#16a34a" : val >= 5 ? "#2563eb" : "#ef4444" }}>
                  {val}
                </span>
              </div>
              <input
                type="range" min={0} max={10} step={1}
                value={val}
                className="ev-slider"
                onChange={(e) => onChange(key, e.target.value)}
              />
            </div>
          );
        })}
        <div className="ev-item ev-item--full">
          <label className="ev-item-label">Preço Nota 10</label>
          <input
            type="text"
            className="ev-preco-input"
            value={av.precoNota10 || ""}
            placeholder="Ex: 450000"
            onChange={(e) => onChange("precoNota10", e.target.value.replace(/\D/g, ""))}
          />
        </div>
      </div>
    </div>
  );
}

function RelatorioGerente() {
  const toast = useToast();
  const API_BASE = `${BASE}/gerente-dashboard`;

  const [abaAtiva, setAbaAtiva] = useState("relatoriogerente");
  const [opcaoAtiva, setOpcaoAtiva] = useState("visaoGeral");
  const [idGerenteLogado, setIdGerenteLogado] = useState("");

  const hoje = new Date();
  const primeiroDiaMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
    .toISOString()
    .slice(0, 10);
  const hojeStr = hoje.toISOString().slice(0, 10);

  const [filtros, setFiltros] = useState({
    id_gerente: "",
    corretor_geral: "",
    start: primeiroDiaMes,
    end: hojeStr,
    q: "",
  });

  const [todoPeriodo, setTodoPeriodo] = useState(false);
  const periodoEfetivo = todoPeriodo
    ? { start: "", end: "" }
    : { start: filtros.start, end: filtros.end };

  const [filtrosVisitas, setFiltrosVisitas] = useState({
    imovel: "",
  });

  const [filtrosImoveis, setFiltrosImoveis] = useState({
    imovel: "",
  });

  const [filtrosClientes, setFiltrosClientes] = useState({
    cliente: "",
  });

  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  const [corretores, setCorretores] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [rankingVisitas, setRankingVisitas] = useState([]);
  const [rankingClientes, setRankingClientes] = useState([]);
  const [visitas, setVisitas] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [imoveis, setImoveis] = useState([]);

  const [tipoRankingAtivo, setTipoRankingAtivo] = useState("visitas");
  const [corretorSelecionado, setCorretorSelecionado] = useState("");
  const [dashboardEquipes, setDashboardEquipes] = useState(null);
  const [loadingEquipes, setLoadingEquipes] = useState(false);

  const [itemSelecionado, setItemSelecionado] = useState(null);
  const [tipoSelecionado, setTipoSelecionado] = useState("");

  const detalheRef = useRef(null);
  const carregarDadosSeqRef = useRef(0);

  const [loadingPdfVisita, setLoadingPdfVisita] = useState(false);
  const [loadingPdfCliente, setLoadingPdfCliente] = useState(false);
  const [loadingPdfImovel, setLoadingPdfImovel] = useState(false);
  const [loadingVerGerente, setLoadingVerGerente] = useState(false);
  const [loadingBaixarGerente, setLoadingBaixarGerente] = useState(false);
  const [loadingVerCorretor, setLoadingVerCorretor] = useState(false);
  const [loadingBaixarCorretor, setLoadingBaixarCorretor] = useState(false);

  const [visitasVisualizadas, setVisitasVisualizadas] = useState(new Set());
  const [modalViewer, setModalViewer] = useState(null);
  const [loadingPdfModal, setLoadingPdfModal] = useState(false);
  const [detalheVisita, setDetalheVisita] = useState(null);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);

  const [editVisitaModal, setEditVisitaModal] = useState(null);
  const [editVisitaForm, setEditVisitaForm] = useState({});
  const [savingEditVisita, setSavingEditVisita] = useState(false);
  const [deleteVisitaConfirm, setDeleteVisitaConfirm] = useState(null);
  const [deletingVisita, setDeletingVisita] = useState(false);

  const opcoes = [
    { id: "visaoGeral", label: "Visão Geral", labelMobile: "Visão Geral" },
    { id: "ranking", label: "Ranking", labelMobile: "Ranking" },
    { id: "visitas", label: "Visitas", labelMobile: "Visitas" },
    { id: "imoveis", label: "Imóveis", labelMobile: "Imóveis" },
    { id: "clientes", label: "Clientes", labelMobile: "Clientes" },
    { id: "pdfs", label: "Relatórios PDF", labelMobile: "PDFs" },
  ];

  const gerentesFixos = [
    { id: "G61010", nome: "Thais Tannús" },
    { id: "G61001", nome: "José Marques" },
    { id: "G61002", nome: "Marcelo Souza" },
    { id: "G61003", nome: "Luana Salvinski" },
    { id: "G61014", nome: "Marcelo Pincinato" },
    { id: "G61015", nome: "Helio Junio" },
    { id: "G61016", nome: "Paolla Gardenia" },
  ];

  const normalizarTexto = (valor) => {
    return String(valor || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  };

  const contemTexto = (texto, filtro) => {
    if (!filtro) return true;
    return normalizarTexto(texto).includes(normalizarTexto(filtro));
  };

  const obterNomeCorretor = (item) => {
    if (Array.isArray(item?.corretores)) {
      return item.corretores.join(", ");
    }

    return (
      item?.corretor_nome ||
      item?.nome_corretor ||
      item?.corretor ||
      item?.nomeCorretor ||
      item?.Corretor ||
      item?.NomeCorretor ||
      item?.nome ||
      ""
    );
  };

  const obterTextoImovel = (item) => {
    return [
      item?.codigo,
      item?.codigo_imovel,
      item?.id_imovel,
      item?.imovel,
      item?.titulo,
      item?.endereco,
      item?.endereco_externo,
      item?.bairro,
      item?.tipo_imovel,
    ]
      .filter(Boolean)
      .join(" - ");
  };

  const obterNomeCliente = (item) => {
    return (
      item?.cliente_nome ||
      item?.nome_cliente ||
      item?.cliente ||
      item?.nome ||
      item?.Nome ||
      ""
    );
  };

  const primeiroValor = (...valores) => {
    return valores.find(
      (valor) => valor !== undefined && valor !== null && String(valor).trim() !== ""
    );
  };

  const montarUrlPdf = (recurso, id, download = false, comPeriodo = false) => {
    if (!id) return "";

    const params = new URLSearchParams();
    const chavesPorRecurso = {
      visitas: "visita_id",
      clientes: "id_cliente",
      imoveis: "imovel_id",
    };
    const chave = chavesPorRecurso[recurso];

    if (!chave) return "";

    params.set(chave, String(id));

    if (comPeriodo) {
      if (periodoEfetivo.start) params.set("start", periodoEfetivo.start);
      if (periodoEfetivo.end) params.set("end", periodoEfetivo.end);
    }

    return `${BASE}/${recurso}/pdf${download ? "/download" : ""}?${params.toString()}`;
  };

  const renderAcoesDownloadPdf = (recurso, id, mensagemErro, className = "botao-secundario") => {
    if (recurso !== "imoveis" && recurso !== "clientes") {
      return (
        <button
          className={className}
          onClick={() => abrirUrl(montarUrlPdf(recurso, id, true), mensagemErro)}
        >
          Download
        </button>
      );
    }

    return (
      <>
        {!todoPeriodo && (
          <button
            className={className}
            onClick={() => abrirUrl(montarUrlPdf(recurso, id, true, true), mensagemErro)}
          >
            Baixar período
          </button>
        )}
        <button
          className={className}
          onClick={() => abrirUrl(montarUrlPdf(recurso, id, true, false), mensagemErro)}
        >
          Baixar tudo
        </button>
      </>
    );
  };

  const obterIdVisita = (item) =>
    primeiroValor(item?.id_visita, item?.Id_Visita, item?.visita_id);

  const obterIdImovel = (item) =>
    primeiroValor(item?.id_imovel, item?.Id_Imovel, item?.imovel_id, item?.codigo);

  const obterIdCliente = (item) =>
    primeiroValor(item?.id_cliente, item?.Id_Cliente, item?.cliente_id);

  const abrirUrl = (url, mensagemErro = "Link não disponível.") => {
    if (!url) {
      toast(mensagemErro, "error");
      return;
    }

    window.open(url, "_blank");
  };

  const listaCorretoresFiltro = useMemo(() => {
    const mapa = new Map();

    (corretores || []).forEach((corretor) => {
      const id =
        corretor.IdCorretor ||
        corretor.id_corretor ||
        corretor.id ||
        corretor.codigo ||
        "";

      const nome =
        corretor.Nome ||
        corretor.nome ||
        corretor.corretor ||
        corretor.nome_corretor ||
        id ||
        "";

      if (nome) {
        mapa.set(nome, {
          id,
          nome,
        });
      }
    });

    return Array.from(mapa.values()).sort((a, b) =>
      a.nome.localeCompare(b.nome, "pt-BR")
    );
  }, [corretores]);

  const visitasFiltradas = useMemo(() => {
    return (visitas || []).filter((visita) => {
      const corretor = obterNomeCorretor(visita);
      const imovel = obterTextoImovel(visita);

      return (
        contemTexto(corretor, filtros.corretor_geral) &&
        contemTexto(imovel, filtrosVisitas.imovel)
      );
    });
  }, [visitas, filtros.corretor_geral, filtrosVisitas]);

  const imoveisFiltrados = useMemo(() => {
    return (imoveis || []).filter((imovel) => {
      const corretor = obterNomeCorretor(imovel);
      const textoImovel = obterTextoImovel(imovel);

      return (
        contemTexto(corretor, filtros.corretor_geral) &&
        contemTexto(textoImovel, filtrosImoveis.imovel)
      );
    });
  }, [imoveis, filtros.corretor_geral, filtrosImoveis]);

  const clientesFiltrados = useMemo(() => {
    return (clientes || []).filter((cliente) => {
      const nomeCliente = obterNomeCliente(cliente);
      const corretor = obterNomeCorretor(cliente);

      return (
        contemTexto(corretor, filtros.corretor_geral) &&
        contemTexto(nomeCliente, filtrosClientes.cliente)
      );
    });
  }, [clientes, filtros.corretor_geral, filtrosClientes]);

  const visaoGeralFiltrada = useMemo(() => {
    if (!filtros.corretor_geral) return null;

    const parseData = (ddmmyyyy) => {
      const [d, m, y] = (ddmmyyyy || "").split("/");
      return d && m && y ? new Date(+y, +m - 1, +d) : null;
    };

    const visitasBucket = {};
    visitasFiltradas.forEach((v) => {
      const raw = v.data_visita || "";
      if (!raw) return;
      if (!visitasBucket[raw]) visitasBucket[raw] = { label: raw.slice(0, 5), count: 0 };
      visitasBucket[raw].count++;
    });

    const clientesBucket = {};
    visitasFiltradas.forEach((v) => {
      const raw = v.data_visita || "";
      if (!raw) return;
      if (!clientesBucket[raw]) clientesBucket[raw] = { label: raw.slice(0, 5), nomes: new Set() };
      (v.clientes || []).forEach((c) => clientesBucket[raw].nomes.add(c));
    });

    const sort = (obj) =>
      Object.entries(obj).sort(([a], [b]) => {
        const da = parseData(a), db = parseData(b);
        return da && db ? da - db : 0;
      });

    return {
      resumo: {
        total_corretores: 1,
        corretores_ativos: visitasFiltradas.length > 0 ? 1 : 0,
        corretores_sem_visita: visitasFiltradas.length > 0 ? 0 : 1,
        total_visitas: visitasFiltradas.length,
        total_clientes: clientesFiltrados.length,
        total_imoveis: imoveisFiltrados.length,
      },
      graficos: {
        visitas_por_dia: {
          labels: sort(visitasBucket).map(([, v]) => v.label),
          valores: sort(visitasBucket).map(([, v]) => v.count),
        },
        clientes_por_dia: {
          labels: sort(clientesBucket).map(([, v]) => v.label),
          valores: sort(clientesBucket).map(([, v]) => v.nomes.size),
        },
      },
    };
  }, [filtros.corretor_geral, visitasFiltradas, clientesFiltrados, imoveisFiltrados]);

  const visitasNaoVisualizadas = useMemo(() => {
    return (visitasFiltradas || []).filter((v) => {
      const id = obterIdVisita(v);
      return id && !visitasVisualizadas.has(String(id));
    });
  }, [visitasFiltradas, visitasVisualizadas]);

  useEffect(() => {
    const userDataString = localStorage.getItem("userData");

    if (!userDataString) {
      setErro("Usuário não encontrado no localStorage. Faça login novamente.");
      return;
    }

    try {
      const userData = JSON.parse(userDataString);

      const idGerente =
        userData.idCorretor ||
        userData.id_gerente ||
        userData.codigoGerente ||
        userData.codigo_gerente ||
        userData.codigo ||
        userData.id_usuarios ||
        "";

      if (!idGerente) {
        setErro("Não foi encontrado um id de gerente no usuário logado.");
        return;
      }

      const idGerenteStr = String(idGerente);

      setIdGerenteLogado(idGerenteStr);

      setFiltros((prev) => ({
        ...prev,
        id_gerente: idGerenteStr,
      }));
    } catch (err) {
      console.error(err);
      setErro("Erro ao carregar os dados do gerente logado.");
    }
  }, []);

  useEffect(() => {
    if (!visitas || visitas.length === 0) return;
    const ids = [...new Set(visitas.map(v => v.id_gerente_corretor).filter(Boolean))];
    if (ids.length === 0) return;
    fetch(`${BASE}/visitas/vistas?id_gerente=${encodeURIComponent(ids.join(","))}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) setVisitasVisualizadas(new Set(d.ids));
        else console.error("[vistas GET] erro:", d);
      })
      .catch(e => console.error("[vistas GET] fetch falhou:", e));
  }, [visitas]);

  useEffect(() => {
    if (filtros.id_gerente) {
      carregarDados();
    }
  }, [filtros.id_gerente]);

  const buildQuery = (extra = {}) => {
    const params = new URLSearchParams();

    const finalParams = {
      id_gerente: filtros.id_gerente,
      start: periodoEfetivo.start,
      end: periodoEfetivo.end,
      ...extra,
    };

    Object.entries(finalParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        params.append(key, value);
      }
    });

    return params.toString();
  };

  const fetchJson = async (url) => {
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok || data.ok === false) {
      throw new Error(data?.error || "Erro ao carregar dados.");
    }

    return data;
  };

  const carregarDados = async () => {
    if (!filtros.id_gerente) return;

    const requestId = carregarDadosSeqRef.current + 1;
    carregarDadosSeqRef.current = requestId;
    const query = buildQuery();

    setLoading(true);
    setErro("");

    try {
      const [
        dashboardRes,
        corretoresRes,
        rankingVisitasRes,
        rankingClientesRes,
      ] = await Promise.all([
        fetchJson(`${API_BASE}/dashboard?${query}`),
        fetchJson(`${API_BASE}/corretores?${query}`),
        fetchJson(`${API_BASE}/ranking?${query}&tipo=visitas`),
        fetchJson(`${API_BASE}/ranking?${query}&tipo=clientes`),
      ]);

      if (requestId !== carregarDadosSeqRef.current) return;

      setDashboard(dashboardRes);
      setCorretores(corretoresRes.lista || []);
      setRankingVisitas(rankingVisitasRes.lista || []);
      setRankingClientes(rankingClientesRes.lista || []);
    } catch (e) {
      if (requestId !== carregarDadosSeqRef.current) return;
      setErro(e.message || "Erro ao carregar dashboard.");
    } finally {
      if (requestId === carregarDadosSeqRef.current) {
        setLoading(false);
      }
    }
  };

  const carregarListas = async () => {
    try {
      const [visitasRes, clientesRes, imoveisRes] = await Promise.all([
        fetchJson(`${API_BASE}/visitas?${buildQuery({ q: filtros.q, limit: 200 })}`),
        fetchJson(`${API_BASE}/clientes?${buildQuery({ q: filtros.q, limit: 200 })}`),
        fetchJson(`${API_BASE}/imoveis?${buildQuery({ q: filtros.q, limit: 200 })}`),
      ]);

      const visitasLista = visitasRes.lista || [];
      const clientesLista = clientesRes.lista || [];
      const imoveisLista = imoveisRes.lista || [];

      setVisitas(visitasLista);
      setClientes(clientesLista);
      setImoveis(imoveisLista);

      if (!itemSelecionado) {
        if (visitasLista.length > 0) {
          setTipoSelecionado("visita");
          setItemSelecionado(visitasLista[0]);
        } else if (imoveisLista.length > 0) {
          setTipoSelecionado("imovel");
          setItemSelecionado(imoveisLista[0]);
        } else if (clientesLista.length > 0) {
          setTipoSelecionado("cliente");
          setItemSelecionado(clientesLista[0]);
        }
      }
    } catch (e) {
      setErro(e.message || "Erro ao carregar listas.");
    }
  };

  const carregarEquipes = async () => {
    setLoadingEquipes(true);
    try {
      const params = new URLSearchParams();
      if (periodoEfetivo.start) params.set('start', periodoEfetivo.start);
      if (periodoEfetivo.end) params.set('end', periodoEfetivo.end);
      const res = await fetchJson(`${API_BASE}/equipes/dashboard?${params.toString()}`);
      setDashboardEquipes(res);
    } catch (e) {
      toast(e.message || 'Erro ao carregar dados de equipes.', 'error');
    } finally {
      setLoadingEquipes(false);
    }
  };

  const handleFiltroChange = (campo, valor) => {
    setFiltros((prev) => ({
      ...prev,
      [campo]: valor,
      ...(campo === "id_gerente" ? { corretor_geral: "" } : {}),
    }));

    if (campo === "id_gerente") {
      setCorretorSelecionado("");
      setItemSelecionado(null);
      setTipoSelecionado("");
    }
  };

  const aplicarBusca = async () => {
    if (!filtros.id_gerente) return;

    setLoading(true);
    setErro("");

    try {
      await carregarDados();
      if (dashboardEquipes !== null) {
        await carregarEquipes();
      }
    } catch (e) {
      setErro(e.message || "Erro ao aplicar filtro.");
    } finally {
      setLoading(false);
    }
  };

  const abrirEditVisita = (item) => {
    const ddmmyyyy = item.data_visita || "";
    let isoDate = "";
    if (ddmmyyyy && ddmmyyyy.includes("/")) {
      const [dd, mm, yyyy] = ddmmyyyy.split("/");
      isoDate = `${yyyy}-${mm}-${dd}`;
    }
    let situacao = "CAPTACAO_PROPRIA";
    const imovelNaoCaptado = item.imovel_nao_captado === true ||
      String(item.imovel_nao_captado || "").toUpperCase() === "TRUE";
    if (imovelNaoCaptado) situacao = "IMOVEL_NAO_CAPTADO";
    else if (item.tipo_captacao) situacao = "CAPTACAO_61";

    const avaliacoes = (item.avaliacoes || []).map((av) => ({
      id_avaliacao: av.id_avaliacao || "",
      cliente: av.cliente || "",
      localizacao: av.localizacao || "10",
      tamanho: av.tamanho || "10",
      planta: av.planta || "10",
      acabamento: av.acabamento || "10",
      conservacao: av.conservacao || "10",
      condominio: av.condominio || "10",
      preco: av.preco || "10",
      notaGeral: av.notaGeral || "10",
      precoNota10: av.precoNota10 || "",
    }));

    setEditVisitaForm({
      dataVisita: isoDate,
      enderecoExterno: item.endereco_externo || "",
      proposta: item.proposta || "",
      motivoTalvez: item.motivoTalvez || item.motivo_talvez || "",
      situacaoImovel: situacao,
      avaliacoes,
    });
    setEditVisitaModal(item);
  };

  const salvarEdicaoVisita = async () => {
    if (!editVisitaModal) return;
    setSavingEditVisita(true);
    try {
      const id = obterIdVisita(editVisitaModal);
      if (!id) throw new Error("ID da visita não encontrado.");
      const resp = await fetch(`${BASE}/visitas/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editVisitaForm),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "Erro ao salvar.");
      setEditVisitaModal(null);
      await carregarListas();
    } catch (err) {
      toast(err.message || "Erro ao salvar edição.", "error");
    } finally {
      setSavingEditVisita(false);
    }
  };

  const confirmarExclusaoVisita = async () => {
    if (!deleteVisitaConfirm) return;
    setDeletingVisita(true);
    try {
      const id = obterIdVisita(deleteVisitaConfirm);
      const resp = await fetch(`${BASE}/visitas/${id}`, { method: "DELETE" });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "Erro ao excluir.");
      setDeleteVisitaConfirm(null);
      if (itemSelecionado && obterIdVisita(itemSelecionado) === id) setItemSelecionado(null);
      await carregarListas();
    } catch (err) {
      toast(err.message || "Erro ao excluir visita.", "error");
    } finally {
      setDeletingVisita(false);
    }
  };

  const _downloadViaAnchor = (url, filename) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const abrirPdfGerente = async () => {
    if (!filtros.id_gerente) {
      toast("Selecione um gerente.", "error");
      return;
    }
    setLoadingVerGerente(true);
    try {
      const res = await fetchJson(`${API_BASE}/gerente/pdf?${buildQuery()}`);
      if (res.drive_url) {
        window.open(res.drive_url, "_blank");
      } else {
        toast("URL do PDF não disponível.", "error");
      }
    } catch (e) {
      toast(e.message || "Erro ao gerar PDF.", "error");
    } finally {
      setLoadingVerGerente(false);
    }
  };

  const baixarPdfGerente = async () => {
    if (!filtros.id_gerente) {
      toast("Selecione um gerente.", "error");
      return;
    }
    setLoadingBaixarGerente(true);
    try {
      const url = `${API_BASE}/gerente/pdf/download?${buildQuery()}`;
      _downloadViaAnchor(url, `relatorio_gerente_${filtros.id_gerente}.pdf`);
    } finally {
      setLoadingBaixarGerente(false);
    }
  };

  const abrirPdfCorretor = async () => {
    if (!corretorSelecionado) {
      toast("Selecione um corretor.", "error");
      return;
    }
    setLoadingVerCorretor(true);
    try {
      const params = new URLSearchParams({ id_corretor: corretorSelecionado });
      const res = await fetchJson(`${API_BASE}/corretor/pdf?${params.toString()}`);
      if (res.drive_url) {
        window.open(res.drive_url, "_blank");
      } else {
        toast("URL do PDF não disponível.", "error");
      }
    } catch (e) {
      toast(e.message || "Erro ao gerar PDF.", "error");
    } finally {
      setLoadingVerCorretor(false);
    }
  };

  const baixarPdfCorretor = async () => {
    if (!corretorSelecionado) {
      toast("Selecione um corretor.", "error");
      return;
    }
    setLoadingBaixarCorretor(true);
    try {
      const params = new URLSearchParams({ id_corretor: corretorSelecionado });
      const url = `${API_BASE}/corretor/pdf/download?${params.toString()}`;
      _downloadViaAnchor(url, `relatorio_corretor_${corretorSelecionado}.pdf`);
    } finally {
      setLoadingBaixarCorretor(false);
    }
  };

  const rolarParaDetalhes = () => {
  setTimeout(() => {
    detalheRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, 100);
};

  const selecionarVisita = (item) => {
    setTipoSelecionado("visita");
    setItemSelecionado(item);
    rolarParaDetalhes();
  };

  const selecionarImovel = (item) => {
    setTipoSelecionado("imovel");
    setItemSelecionado(item);
    rolarParaDetalhes();
  };

  const selecionarCliente = (item) => {
    setTipoSelecionado("cliente");
    setItemSelecionado(item);
    rolarParaDetalhes();
  };

  const marcarComoVisualizada = useCallback((idVisita, idGerenteVisita) => {
    if (!idVisita) return;
    const gerenteKey = idGerenteVisita || idGerenteLogado;
    if (!gerenteKey) return;
    setVisitasVisualizadas((prev) => {
      if (prev.has(String(idVisita))) return prev;
      const next = new Set(prev);
      next.add(String(idVisita));
      return next;
    });
    fetch(`${BASE}/visitas/vistas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_gerente: gerenteKey, id_visita: String(idVisita) }),
    })
      .then(r => r.json())
      .then(d => { if (!d.ok) console.error("[vistas POST] erro:", d); })
      .catch(e => console.error("[vistas POST] fetch falhou:", e));
  }, [idGerenteLogado]);

  const abrirModalViewer = useCallback(async (tipo, item) => {
    setModalViewer({ tipo, item });
    setDetalheVisita(null);

    if (tipo === "visita") {
      const id = obterIdVisita(item);
      if (id) {
        marcarComoVisualizada(String(id), item?.id_gerente_corretor);
        setLoadingDetalhe(true);
        try {
          const resp = await fetch(`${API_BASE}/visita/detalhe?visita_id=${encodeURIComponent(id)}`);
          const data = await resp.json().catch(() => ({}));
          if (resp.ok && data.ok) setDetalheVisita(data);
        } catch {}
        finally { setLoadingDetalhe(false); }
      }
    }
  }, [marcarComoVisualizada, API_BASE]);

  const fecharModal = useCallback(() => {
    setModalViewer(null);
    setLoadingPdfModal(false);
    setDetalheVisita(null);
    setLoadingDetalhe(false);
  }, []);

  const abrirPdfModal = useCallback(async (pdfUrl) => {
    if (!pdfUrl) return;
    setLoadingPdfModal(true);
    try {
      const resp = await fetch(pdfUrl);
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data.ok) throw new Error(data.error || "Erro ao gerar PDF.");
      if (!data.drive_url) throw new Error("URL do PDF não retornada.");
      window.open(data.drive_url, "_blank");
    } catch (err) {
      toast(err.message || "Erro ao abrir PDF.", "error");
    } finally {
      setLoadingPdfModal(false);
    }
  }, [toast]);

  async function abrirPdfVisita() {
    if (!itemSelecionado || tipoSelecionado !== "visita") return;

    setLoadingPdfVisita(true);

    try {
      const resp = await fetch(
        montarUrlPdf("visitas", obterIdVisita(itemSelecionado))
      );

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao gerar o PDF da visita.");
      }

      if (!data.drive_url) {
        throw new Error("A API não retornou a URL do PDF da visita.");
      }

      window.open(data.drive_url, "_blank");
    } catch (err) {
      toast(err.message || "Erro ao abrir o PDF da visita.", "error");
    } finally {
      setLoadingPdfVisita(false);
    }
  }

  function baixarPdfVisita() {
    if (!itemSelecionado || tipoSelecionado !== "visita") return;

    abrirUrl(
      montarUrlPdf("visitas", obterIdVisita(itemSelecionado), true),
      "Não foi encontrado o id da visita para download."
    );
  }

  async function abrirPdfImovel() {
    if (!itemSelecionado || tipoSelecionado !== "imovel") return;

    setLoadingPdfImovel(true);

    try {
      const resp = await fetch(
        montarUrlPdf("imoveis", obterIdImovel(itemSelecionado))
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
      toast(err.message || "Erro ao abrir o PDF do imóvel.", "error");
    } finally {
      setLoadingPdfImovel(false);
    }
  }

  async function abrirPdfCliente() {
    if (!itemSelecionado || tipoSelecionado !== "cliente") return;

    setLoadingPdfCliente(true);

    try {
      const resp = await fetch(
        montarUrlPdf("clientes", obterIdCliente(itemSelecionado))
      );

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao gerar o PDF do cliente.");
      }

      if (!data.drive_url) {
        throw new Error("A API não retornou a URL do PDF do cliente.");
      }

      window.open(data.drive_url, "_blank");
    } catch (err) {
      toast(err.message || "Erro ao abrir o PDF do cliente.", "error");
    } finally {
      setLoadingPdfCliente(false);
    }
  }

  const renderModalViewer = () => {
    if (!modalViewer) return null;
    const { tipo, item } = modalViewer;

    const titulo =
      tipo === "visita" ? "Detalhes da visita" :
      tipo === "imovel" ? "Detalhes do imóvel" :
      "Detalhes do cliente";

    const renderCampos = () => {
      if (tipo === "visita") {
        return (
          <div className="detalhe-grid">
            <div className="detalhe-box">
              <span className="detalhe-label">Data da visita</span>
              <strong>{item.data_visita || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Registrado em</span>
              <strong>{item.created_at || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Corretor</span>
              <strong>{item.corretor || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Imóvel</span>
              <strong>{item.id_imovel || "-"}</strong>
            </div>
            {item.endereco_externo && (
              <div className="detalhe-box detalhe-box-full">
                <span className="detalhe-label">Endereço externo</span>
                <strong>{item.endereco_externo}</strong>
              </div>
            )}
            <div className="detalhe-box">
              <span className="detalhe-label">Tipo de captação</span>
              <strong>{item.tipo_captacao || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Proposta</span>
              <strong>{item.proposta || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Visita com parceiro</span>
              <strong>{item.visita_com_parceiro ? "Sim" : "Não"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Imóvel não captado</span>
              <strong>{item.imovel_nao_captado ? "Sim" : "Não"}</strong>
            </div>
            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Clientes</span>
              <strong>
                {Array.isArray(item.clientes) && item.clientes.length > 0
                  ? item.clientes.join(", ")
                  : "-"}
              </strong>
            </div>
            {Array.isArray(item.parceiros) && item.parceiros.length > 0 && (
              <div className="detalhe-box detalhe-box-full">
                <span className="detalhe-label">Parceiros</span>
                <strong>{item.parceiros.join(", ")}</strong>
              </div>
            )}
            {/* Link da ficha */}
            {loadingDetalhe && (
              <div className="detalhe-box detalhe-box-full">
                <span className="detalhe-label">Ficha e avaliações</span>
                <span className="texto-avaliacao-info">Carregando...</span>
              </div>
            )}
            {!loadingDetalhe && detalheVisita && (
              <>
                {detalheVisita.link_imagem && (
                  <div className="detalhe-box detalhe-box-full">
                    <span className="detalhe-label">Link da imagem</span>
                    <a
                      href={detalheVisita.link_imagem}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="link-ficha-btn"
                    >
                      Ver imagem →
                    </a>
                  </div>
                )}
{detalheVisita.link_audio && (
                  <div className="detalhe-box detalhe-box-full">
                    <span className="detalhe-label">Áudio descrição</span>
                    <a
                      href={detalheVisita.link_audio}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="link-ficha-btn"
                    >
                      Ouvir áudio →
                    </a>
                  </div>
                )}
                {detalheVisita.avaliacoes && detalheVisita.avaliacoes.length > 0 && (
                  <div className="detalhe-box detalhe-box-full">
                    <span className="detalhe-label">Avaliações</span>
                    <div className="avaliacoes-lista">
                      {detalheVisita.avaliacoes.map((av, idx) => (
                        <div key={idx} className="avaliacao-grupo">
                          {detalheVisita.avaliacoes.length > 1 && av.nome_cliente && (
                            <div className="avaliacao-cliente-nome">{av.nome_cliente}</div>
                          )}
                          <div className="avaliacao-grid">
                            {[
                              ["Localização", av["Localização"]],
                              ["Tamanho", av["Tamanho"]],
                              ["Planta", av["Planta"]],
                              ["Acabamento", av["Acabamento"]],
                              ["Conservação", av["Conservação"]],
                              ["Condomínio", av["Condomínio"]],
                              ["Preço", av["Preço"]],
                              ["Nota Geral", av["Nota Geral"]],
                              ["Preço Nota 10", av["Preço Nota 10"]],
                            ].map(([label, val]) => (
                              <div key={label} className="avaliacao-item">
                                <span className="avaliacao-label">{label}</span>
                                <span className={`avaliacao-nota ${!val ? "avaliacao-vazia" : ""}`}>
                                  {val || "—"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {detalheVisita.avaliacoes && detalheVisita.avaliacoes.length === 0 && (
                  <div className="detalhe-box detalhe-box-full">
                    <span className="detalhe-label">Avaliações</span>
                    <span className="texto-avaliacao-info">Nenhuma avaliação registrada.</span>
                  </div>
                )}
              </>
            )}
          </div>
        );
      }
      if (tipo === "imovel") {
        return (
          <div className="detalhe-grid">
            <div className="detalhe-box">
              <span className="detalhe-label">Imóvel</span>
              <strong>{item.id_imovel || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Endereço</span>
              <strong>{item.endereco_externo || "-"}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Total de visitas</span>
              <strong>{item.qtd_visitas ?? 0}</strong>
            </div>
            <div className="detalhe-box">
              <span className="detalhe-label">Última visita</span>
              <strong>{item.ultima_data || "-"}</strong>
            </div>
            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Corretores vinculados</span>
              <strong>
                {Array.isArray(item.corretores) && item.corretores.length > 0
                  ? item.corretores.join(", ")
                  : "-"}
              </strong>
            </div>
            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Clientes vinculados</span>
              <strong>
                {Array.isArray(item.clientes) && item.clientes.length > 0
                  ? item.clientes.join(", ")
                  : "-"}
              </strong>
            </div>
          </div>
        );
      }
      return (
        <div className="detalhe-grid">
          <div className="detalhe-box">
            <span className="detalhe-label">Cliente</span>
            <strong>{item.nome || "-"}</strong>
          </div>
          <div className="detalhe-box">
            <span className="detalhe-label">Telefone</span>
            <strong>{item.telefone || "-"}</strong>
          </div>
          <div className="detalhe-box">
            <span className="detalhe-label">E-mail</span>
            <strong>{item.email || "-"}</strong>
          </div>
          <div className="detalhe-box">
            <span className="detalhe-label">Qtd. visitas</span>
            <strong>{item.qtd_visitas ?? 0}</strong>
          </div>
          <div className="detalhe-box">
            <span className="detalhe-label">Última visita</span>
            <strong>{item.ultima_visita || "-"}</strong>
          </div>
          <div className="detalhe-box detalhe-box-full">
            <span className="detalhe-label">Corretores vinculados</span>
            <strong>
              {Array.isArray(item.corretores) && item.corretores.length > 0
                ? item.corretores.join(", ")
                : "-"}
            </strong>
          </div>
        </div>
      );
    };

    const idParaDownload =
      tipo === "visita" ? obterIdVisita(item) :
      tipo === "imovel" ? obterIdImovel(item) :
      obterIdCliente(item);

    const recursoDownload =
      tipo === "visita" ? "visitas" :
      tipo === "imovel" ? "imoveis" :
      "clientes";

    return (
      <div className="modal-overlay" onClick={fecharModal}>
        <div className="modal-container" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <span className="modal-titulo-viewer">{titulo}</span>
            <button className="modal-fechar" onClick={fecharModal}>✕</button>
          </div>
          <div className="modal-body">
            {renderCampos()}
          </div>
          <div className="modal-footer">
            {renderAcoesDownloadPdf(recursoDownload, idParaDownload, "ID não encontrado para download.")}
            <button className="botao-secundario" onClick={fecharModal}>
              Fechar
            </button>
          </div>
        </div>
      </div>
    );
  };

  const cardNumero = (titulo, valor) => (
    <div className="card-numero">
      <div className="card-numero-titulo">{titulo}</div>
      <div className="card-numero-valor">{valor ?? 0}</div>
    </div>
  );

  const renderBarrasSimples = (titulo, labels = [], valores = []) => {
    const maior = Math.max(...valores, 1);

    return (
      <div className="card-padrao">
        <h3 className="card-titulo">{titulo}</h3>

        {!labels.length ? (
          <p className="card-texto">Sem dados para exibir.</p>
        ) : (
          <div className="grafico-barras">
            {labels.map((label, index) => {
              const valor = valores[index] || 0;
              const largura = `${(valor / maior) * 100}%`;

              return (
                <div key={`${label}-${index}`} className="grafico-linha">
                  <div className="grafico-label">{label}</div>

                  <div className="grafico-barra-area">
                    <div
                      className="grafico-barra-fill"
                      style={{ width: largura }}
                    />
                  </div>

                  <div className="grafico-valor">{valor}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const renderRanking = (titulo, dados, unidade = "visitas") => (
    <div className="card-padrao">
      <h3 className="card-titulo">{titulo}</h3>

      {!dados.length ? (
        <p className="card-texto">Nenhum dado encontrado.</p>
      ) : (
        <div className="ranking-lista">
          {dados.map((item, index) => (
            <div key={`${item.id_corretor}-${index}`} className="ranking-item">
              <div className="ranking-nome">
                {index + 1}º - {item.corretor}
              </div>

              <div className="ranking-badge">
                {item.total} {unidade}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderTabelaVisitas = () => (
    <div className="card-padrao">
      <h3 className="card-titulo">Visitas do time</h3>

      <div className="filtros-lista-relatorio">
        <div className="grupo-filtro-lista">
          <label>Imóvel</label>
          <input
            type="text"
            placeholder="Filtrar por código ou imóvel"
            value={filtrosVisitas.imovel}
            onChange={(e) =>
              setFiltrosVisitas((prev) => ({
                ...prev,
                imovel: e.target.value,
              }))
            }
          />
        </div>

        <button
          type="button"
          className="botao-limpar-lista"
          onClick={() =>
            setFiltrosVisitas({
              imovel: "",
            })
          }
        >
          Limpar filtro da aba
        </button>
      </div>

      <p className="contador-filtros-lista">
        Exibindo {visitasFiltradas.length} de {(visitas || []).length} visitas
      </p>

      <div className="tabela-wrapper">
        <table className="tabela-relatorio">
          <thead>
            <tr>
              <th>Status</th>
              <th>Data</th>
              <th>Corretor</th>
              <th>Imóvel</th>
              <th>Clientes</th>
              <th>Proposta</th>
              <th>Motivo do talvez</th>
              <th>Ações</th>
            </tr>
          </thead>

          <tbody>
            {!visitasFiltradas.length ? (
              <tr>
                <td colSpan="8">Nenhuma visita encontrada.</td>
              </tr>
            ) : (
              visitasFiltradas.map((item) => (
                <tr
                  key={item.id_visita}
                  className={
                    tipoSelecionado === "visita" &&
                    itemSelecionado?.id_visita === item.id_visita
                      ? "linha-ativa"
                      : ""
                  }
                >
                  <td>
                    {visitasVisualizadas.has(String(obterIdVisita(item))) ? (
                      <span className="icone-status icone-visto" title="Visualizada">✓</span>
                    ) : (
                      <span className="icone-status icone-pendente" title="Não visualizada">●</span>
                    )}
                  </td>
                  <td>{item.data_visita || "-"}</td>
                  <td>{item.corretor || "-"}</td>
                  <td>{item.id_imovel || "-"}</td>
                  <td>
                    {Array.isArray(item.clientes)
                      ? item.clientes.join(", ")
                      : "-"}
                  </td>
                  <td>{item.proposta || "-"}</td>
                  <td>{item.motivoTalvez || item.motivo_talvez || "-"}</td>

                  <td>
                    <div className="acoes-tabela">
                      <button
                        type="button"
                        className="botao-secundario botao-editar"
                        onClick={() => abrirEditVisita(item)}
                        title="Editar visita"
                      >
                        Editar
                      </button>
                      <button
                        className="botao-excluir"
                        onClick={() => setDeleteVisitaConfirm(item)}
                        title="Excluir visita"
                      >
                        Excluir
                      </button>
                      <button
                        className="botao-secundario"
                        onClick={() => abrirModalViewer("visita", item)}
                      >
                        Ver
                      </button>

                      <button
                        className="botao-secundario"
                        onClick={() => {
                          const id = obterIdVisita(item);
                          if (id) marcarComoVisualizada(String(id), item?.id_gerente_corretor);
                          abrirUrl(
                            montarUrlPdf("visitas", id, true),
                            "Não foi encontrado o id da visita para download."
                          );
                        }}
                      >
                        Download
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderTabelaImoveis = () => (
    <div className="card-padrao">
      <h3 className="card-titulo">Imóveis do time</h3>

      <div className="filtros-lista-relatorio">
        <div className="grupo-filtro-lista">
          <label>Imóvel</label>
          <input
            type="text"
            placeholder="Filtrar por código, endereço ou imóvel"
            value={filtrosImoveis.imovel}
            onChange={(e) =>
              setFiltrosImoveis((prev) => ({
                ...prev,
                imovel: e.target.value,
              }))
            }
          />
        </div>

        <button
          type="button"
          className="botao-limpar-lista"
          onClick={() =>
            setFiltrosImoveis({
              imovel: "",
            })
          }
        >
          Limpar filtro da aba
        </button>
      </div>

      <p className="contador-filtros-lista">
        Exibindo {imoveisFiltrados.length} de {(imoveis || []).length} imóveis
      </p>

      <div className="tabela-wrapper">
        <table className="tabela-relatorio">
          <thead>
            <tr>
              <th>Imóvel</th>
              <th>Endereço</th>
              <th>Visitas</th>
              <th>Última visita</th>
              <th>Corretores</th>
              <th>Ações</th>
            </tr>
          </thead>

          <tbody>
            {!imoveisFiltrados.length ? (
              <tr>
                <td colSpan="6">Nenhum imóvel encontrado.</td>
              </tr>
            ) : (
              imoveisFiltrados.map((item) => (
                <tr
                  key={item.id_imovel}
                  className={
                    tipoSelecionado === "imovel" &&
                    itemSelecionado?.id_imovel === item.id_imovel
                      ? "linha-ativa"
                      : ""
                  }
                >
                  <td>{item.id_imovel || "-"}</td>
                  <td>{item.endereco_externo || "-"}</td>
                  <td>{item.qtd_visitas ?? 0}</td>
                  <td>{item.ultima_data || "-"}</td>
                  <td>
                    {Array.isArray(item.corretores)
                      ? item.corretores.join(", ")
                      : "-"}
                  </td>

                  <td>
                    <div className="acoes-tabela">
                      <button
                        className="botao-secundario"
                        onClick={() => abrirModalViewer("imovel", item)}
                      >
                        Ver
                      </button>

                      {renderAcoesDownloadPdf(
                        "imoveis",
                        obterIdImovel(item),
                        "Não foi encontrado o id do imóvel para download."
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderTabelaClientes = () => (
    <div className="card-padrao">
      <h3 className="card-titulo">Clientes do time</h3>

      <div className="filtros-lista-relatorio">
        <div className="grupo-filtro-lista">
          <label>Cliente</label>
          <input
            type="text"
            placeholder="Filtrar por cliente"
            value={filtrosClientes.cliente}
            onChange={(e) =>
              setFiltrosClientes((prev) => ({
                ...prev,
                cliente: e.target.value,
              }))
            }
          />
        </div>

        <button
          type="button"
          className="botao-limpar-lista"
          onClick={() =>
            setFiltrosClientes({
              cliente: "",
            })
          }
        >
          Limpar filtro da aba
        </button>
      </div>

      <p className="contador-filtros-lista">
        Exibindo {clientesFiltrados.length} de {(clientes || []).length} clientes
      </p>

      <div className="tabela-wrapper">
        <table className="tabela-relatorio">
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Telefone</th>
              <th>E-mail</th>
              <th>Corretores</th>
              <th>Qtd. visitas</th>
              <th>Última visita</th>
              <th>Ações</th>
            </tr>
          </thead>

          <tbody>
            {!clientesFiltrados.length ? (
              <tr>
                <td colSpan="7">Nenhum cliente encontrado.</td>
              </tr>
            ) : (
              clientesFiltrados.map((item) => (
                <tr
                  key={item.id_cliente}
                  className={
                    tipoSelecionado === "cliente" &&
                    itemSelecionado?.id_cliente === item.id_cliente
                      ? "linha-ativa"
                      : ""
                  }
                >
                  <td>{item.nome || "-"}</td>
                  <td>{item.telefone || "-"}</td>
                  <td>{item.email || "-"}</td>
                  <td>
                    {Array.isArray(item.corretores)
                      ? item.corretores.join(", ")
                      : "-"}
                  </td>
                  <td>{item.qtd_visitas ?? 0}</td>
                  <td>{item.ultima_visita || "-"}</td>

                  <td>
                    <div className="acoes-tabela">
                      <button
                        className="botao-secundario"
                        onClick={() => abrirModalViewer("cliente", item)}
                      >
                        Ver
                      </button>

                      {renderAcoesDownloadPdf(
                        "clientes",
                        obterIdCliente(item),
                        "Não foi encontrado o id do cliente para download."
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderVisaoGeral = () => {
    const fonte = visaoGeralFiltrada || dashboard;
    const resumo = fonte?.resumo || {};
    const grafVisitas = fonte?.graficos?.visitas_por_dia || {};
    const grafClientes = fonte?.graficos?.clientes_por_dia || {};

    return (
      <div>
        <div className="secao-titulo">Visão Geral</div>

        <div className="grid-cards-quantidades">
          {cardNumero("Total de corretores", resumo.total_corretores)}
          {cardNumero("Corretores ativos", resumo.corretores_ativos)}
          {cardNumero("Corretores sem visita", resumo.corretores_sem_visita)}
          {cardNumero("Total de visitas", resumo.total_visitas)}
          {cardNumero("Total de imóveis", imoveis.length)}
          {cardNumero("Total de clientes", resumo.total_clientes)}
        </div>

        <div className="grid-graficos">
          {renderBarrasSimples(
            "Visitas por dia",
            grafVisitas.labels || [],
            grafVisitas.valores || []
          )}

          {renderBarrasSimples(
            "Clientes por dia",
            grafClientes.labels || [],
            grafClientes.valores || []
          )}
        </div>
      </div>
    );
  };

  const renderConteudoRanking = () => {
    const dadosAtivos =
      tipoRankingAtivo === "visitas" ? rankingVisitas : rankingClientes;

    return (
      <div>
        <div className="secao-titulo">Ranking</div>

        <div className="tabs-internas">
          <button
            className={`tab-interna ${
              tipoRankingAtivo === "visitas" ? "ativa" : ""
            }`}
            onClick={() => setTipoRankingAtivo("visitas")}
          >
            Ranking por visitas
          </button>

          <button
            className={`tab-interna ${
              tipoRankingAtivo === "clientes" ? "ativa" : ""
            }`}
            onClick={() => setTipoRankingAtivo("clientes")}
          >
            Ranking por clientes
          </button>
        </div>

        {renderRanking(
          tipoRankingAtivo === "visitas"
            ? "Ranking de visitas por corretor"
            : "Ranking de clientes por corretor",
          dadosAtivos,
          tipoRankingAtivo === "visitas" ? "visitas" : "clientes"
        )}

        {renderBarrasSimples(
          tipoRankingAtivo === "visitas"
            ? "Comparativo de visitas"
            : "Comparativo de clientes",
          dadosAtivos.map((item) => item.corretor),
          dadosAtivos.map((item) => item.total)
        )}
      </div>
    );
  };

  const renderPdfs = () => (
    <div>
      <div className="secao-titulo">Relatórios PDF</div>

      <div className="grid-pdfs">
        <div className="card-padrao">
          <h3 className="card-titulo">Relatório consolidado do gerente</h3>

          <p className="card-texto">
            Gera o relatório consolidado com resumo, ranking e visitas do período.
          </p>

          <div className="acoes-pdf">
            <button
              className="botao-principal"
              onClick={abrirPdfGerente}
              disabled={loadingVerGerente || loadingBaixarGerente}
            >
              {loadingVerGerente ? "Gerando..." : "Ver PDF"}
            </button>

            <button
              className="botao-secundario"
              onClick={baixarPdfGerente}
              disabled={loadingVerGerente || loadingBaixarGerente}
            >
              {loadingBaixarGerente ? "Baixando..." : "Baixar PDF"}
            </button>
          </div>
        </div>

        <div className="card-padrao">
          <h3 className="card-titulo">Relatório individual do corretor</h3>

          <p className="card-texto">
            Selecione um corretor para gerar o relatório individual.
          </p>

          <select
            className="campo-filtro"
            value={corretorSelecionado}
            onChange={(e) => setCorretorSelecionado(e.target.value)}
          >
            <option value="">Selecione um corretor</option>

            {corretores.map((corretor) => (
              <option
                key={corretor.IdCorretor || corretor.id_corretor || corretor.Nome}
                value={corretor.IdCorretor || corretor.id_corretor || ""}
              >
                {corretor.Nome || corretor.nome || corretor.corretor}
              </option>
            ))}
          </select>

          <div className="acoes-pdf">
            <button
              className="botao-principal"
              onClick={abrirPdfCorretor}
              disabled={loadingVerCorretor || loadingBaixarCorretor}
            >
              {loadingVerCorretor ? "Gerando..." : "Ver PDF"}
            </button>

            <button
              className="botao-secundario"
              onClick={baixarPdfCorretor}
              disabled={loadingVerCorretor || loadingBaixarCorretor}
            >
              {loadingBaixarCorretor ? "Baixando..." : "Baixar PDF"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderDetalheSelecionado = () => {
    if (!itemSelecionado) {
      return (
        <section className="card-padrao">
          <div className="card-texto">
            Selecione uma visita, imóvel ou cliente para visualizar os detalhes.
          </div>
        </section>
      );
    }

    if (tipoSelecionado === "visita") {
      return (
        <section className="card-padrao">
          <div className="card-header-flex">
            <h3 className="card-titulo">Detalhes da última visita</h3>
            <span className="badge-info">{itemSelecionado.id_visita}</span>
          </div>

          <div className="detalhe-grid">
            <div className="detalhe-box">
              <span className="detalhe-label">Data</span>
              <strong>{itemSelecionado.data_visita || "-"}</strong>
            </div>

            <div className="detalhe-box">
              <span className="detalhe-label">Corretor</span>
              <strong>{itemSelecionado.corretor || "-"}</strong>
            </div>

            <div className="detalhe-box">
              <span className="detalhe-label">Imóvel</span>
              <strong>{itemSelecionado.id_imovel || "-"}</strong>
            </div>

            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Clientes</span>
              <strong>
                {Array.isArray(itemSelecionado.clientes) &&
                itemSelecionado.clientes.length > 0
                  ? itemSelecionado.clientes.join(", ")
                  : "-"}
              </strong>
            </div>
          </div>

          <div className="acoes-pdf">
            <button
              className="botao-principal"
              onClick={abrirPdfVisita}
              disabled={loadingPdfVisita}
            >
              {loadingPdfVisita ? "Gerando PDF..." : "Abrir PDF da visita"}
            </button>

            <button className="botao-secundario" onClick={baixarPdfVisita}>
              Baixar PDF
            </button>
          </div>
        </section>
      );
    }

    if (tipoSelecionado === "imovel") {
      return (
        <section className="card-padrao">
          <div className="card-header-flex">
            <h3 className="card-titulo">Detalhes do imóvel</h3>
            <span className="badge-info">{itemSelecionado.id_imovel}</span>
          </div>

          <div className="detalhe-grid">
            <div className="detalhe-box">
              <span className="detalhe-label">Imóvel</span>
              <strong>{itemSelecionado.id_imovel || "-"}</strong>
            </div>

            <div className="detalhe-box">
              <span className="detalhe-label">Endereço</span>
              <strong>{itemSelecionado.endereco_externo || "-"}</strong>
            </div>

            <div className="detalhe-box">
              <span className="detalhe-label">Total de visitas</span>
              <strong>{itemSelecionado.qtd_visitas ?? 0}</strong>
            </div>

            <div className="detalhe-box">
              <span className="detalhe-label">Última visita</span>
              <strong>{itemSelecionado.ultima_data || "-"}</strong>
            </div>

            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Clientes vinculados</span>
              <strong>
                {Array.isArray(itemSelecionado.clientes) &&
                itemSelecionado.clientes.length > 0
                  ? itemSelecionado.clientes.join(", ")
                  : "-"}
              </strong>
            </div>

            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Corretores vinculados</span>
              <strong>
                {Array.isArray(itemSelecionado.corretores) &&
                itemSelecionado.corretores.length > 0
                  ? itemSelecionado.corretores.join(", ")
                  : "-"}
              </strong>
            </div>
          </div>

          <div className="acoes-pdf">
            <button
              className="botao-principal"
              onClick={abrirPdfImovel}
              disabled={loadingPdfImovel}
            >
              {loadingPdfImovel ? "Gerando PDF..." : "Abrir PDF do imóvel"}
            </button>

            {renderAcoesDownloadPdf(
              "imoveis",
              obterIdImovel(itemSelecionado),
              "Não foi encontrado o id do imóvel para download."
            )}
          </div>
        </section>
      );
    }

    return (
      <section className="card-padrao">
        <div className="card-header-flex">
          <h3 className="card-titulo">Detalhes do cliente</h3>
          <span className="badge-info">{itemSelecionado.id_cliente}</span>
        </div>

        <div className="detalhe-grid">
          <div className="detalhe-box">
            <span className="detalhe-label">Cliente</span>
            <strong>{itemSelecionado.nome || "-"}</strong>
          </div>

          <div className="detalhe-box">
            <span className="detalhe-label">Telefone</span>
            <strong>{itemSelecionado.telefone || "-"}</strong>
          </div>

          <div className="detalhe-box">
            <span className="detalhe-label">E-mail</span>
            <strong>{itemSelecionado.email || "-"}</strong>
          </div>

          <div className="detalhe-box">
            <span className="detalhe-label">Qtd. visitas</span>
            <strong>{itemSelecionado.qtd_visitas ?? 0}</strong>
          </div>

          <div className="detalhe-box">
            <span className="detalhe-label">Última visita</span>
            <strong>{itemSelecionado.ultima_visita || "-"}</strong>
          </div>

          <div className="detalhe-box detalhe-box-full">
            <span className="detalhe-label">Corretores vinculados</span>
            <strong>
              {Array.isArray(itemSelecionado.corretores) &&
              itemSelecionado.corretores.length > 0
                ? itemSelecionado.corretores.join(", ")
                : "-"}
            </strong>
          </div>
        </div>

        <div className="acoes-pdf">
          <button
            className="botao-principal"
            onClick={abrirPdfCliente}
            disabled={loadingPdfCliente}
          >
            {loadingPdfCliente ? "Gerando PDF..." : "Abrir PDF do cliente"}
          </button>

          {renderAcoesDownloadPdf(
            "clientes",
            obterIdCliente(itemSelecionado),
            "Não foi encontrado o id do cliente para download."
          )}
        </div>
      </section>
    );
  };

  const renderGeralEquipes = () => {
    if (loadingEquipes) {
      return <div className="box-status">Carregando dados de equipes...</div>;
    }

    if (!dashboardEquipes) {
      return (
        <div className="card-padrao">
          <p className="card-texto">Clique em <strong>Carregar equipes</strong> para visualizar o relatório consolidado por equipe.</p>
          <div className="acoes-pdf" style={{ marginTop: 14 }}>
            <button className="botao-principal" onClick={carregarEquipes}>Carregar equipes</button>
          </div>
        </div>
      );
    }

    const equipes = dashboardEquipes.equipes || [];
    const totais = dashboardEquipes.totais || {};

    const baixarPdfEquipes = () => {
      const params = new URLSearchParams();
      if (periodoEfetivo.start) params.set('start', periodoEfetivo.start);
      if (periodoEfetivo.end) params.set('end', periodoEfetivo.end);
      window.open(`${API_BASE}/equipes/pdf/download?${params.toString()}`, '_blank');
    };

    const rankingEquipesVisitas = equipes.map((e) => ({
      id_corretor: e.equipe,
      corretor: e.equipe,
      total: e.total_visitas,
    }));

    const rankingEquipesClientes = equipes.map((e) => ({
      id_corretor: e.equipe,
      corretor: e.equipe,
      total: e.total_clientes,
    }));

    return (
      <div>
        <div className="secao-titulo">Geral por Equipe</div>

        <div className="grid-cards-quantidades">
          {cardNumero('Total de visitas', totais.total_visitas)}
          {cardNumero('Total de clientes únicos', totais.total_clientes)}
          {cardNumero('Total de corretores', totais.total_corretores)}
        </div>

        <div className="grid-graficos">
          {renderBarrasSimples(
            'Visitas por equipe',
            equipes.map((e) => e.equipe),
            equipes.map((e) => e.total_visitas)
          )}
          {renderBarrasSimples(
            'Clientes por equipe',
            equipes.map((e) => e.equipe),
            equipes.map((e) => e.total_clientes)
          )}
        </div>

        <div className="grid-graficos">
          {renderRanking('Ranking — visitas', rankingEquipesVisitas, 'visitas')}
          {renderRanking('Ranking — clientes', rankingEquipesClientes, 'clientes')}
        </div>

        <div className="acoes-pdf" style={{ marginTop: 18 }}>
          <button className="botao-secundario" onClick={carregarEquipes} disabled={loadingEquipes}>
            Atualizar
          </button>
          <button className="botao-principal" onClick={baixarPdfEquipes}>
            Baixar PDF Geral por Equipe
          </button>
        </div>
      </div>
    );
  };

  const renderizarConteudo = () => {
    switch (opcaoAtiva) {
      case "visaoGeral":
        return renderVisaoGeral();

      case "ranking":
        return renderConteudoRanking();

      case "visitas":
        return renderTabelaVisitas();

      case "imoveis":
        return renderTabelaImoveis();

      case "clientes":
        return renderTabelaClientes();

      case "pdfs":
        return renderPdfs();

      case "geralEquipes":
        return renderGeralEquipes();

      default:
        return (
          <div className="card-padrao">
            <h3 className="card-titulo">Relatório Gerente</h3>
            <p className="card-texto">Selecione uma opção.</p>
          </div>
        );
    }
  };

  const podeVerFiltroGerente =
    idGerenteLogado === "12345678" ||
    idGerenteLogado === "G61001" ||
    idGerenteLogado === "ADM001";

  return (
    <div className="pagina-relatorio">
      <div className="titulo-pagina">Relatório Gerente</div>

      <div className="aba-topo" onClick={() => setAbaAtiva("relatoriogerente")}>
        Relatório Gerente
      </div>

      <div className="bloco-filtros-gerente">
        {podeVerFiltroGerente && (
          <div className="filtro-item">
            <label>Gerente</label>

            <select
              className="campo-filtro"
              value={filtros.id_gerente}
              onChange={(e) => handleFiltroChange("id_gerente", e.target.value)}
            >
              <option value="">Selecione</option>

              {gerentesFixos.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nome}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="filtro-item">
          <label>Corretor</label>

          <select
            className="campo-filtro"
            value={filtros.corretor_geral}
            onChange={(e) => handleFiltroChange("corretor_geral", e.target.value)}
          >
            <option value="">Todos os corretores</option>

            {listaCorretoresFiltro.map((corretor) => (
              <option key={corretor.id || corretor.nome} value={corretor.nome}>
                {corretor.nome}
              </option>
            ))}
          </select>
        </div>

        {!todoPeriodo && (
          <>
            <div className="filtro-item">
              <label>Data inicial</label>

              <input
                type="date"
                className="campo-filtro"
                value={filtros.start}
                onChange={(e) => handleFiltroChange("start", e.target.value)}
              />
            </div>

            <div className="filtro-item">
              <label>Data final</label>

              <input
                type="date"
                className="campo-filtro"
                value={filtros.end}
                onChange={(e) => handleFiltroChange("end", e.target.value)}
              />
            </div>
          </>
        )}

        <div className="filtro-item filtro-checkbox">
          <label>&nbsp;</label>
          <label className="filtro-toggle">
            <input
              type="checkbox"
              checked={todoPeriodo}
              onChange={(e) => setTodoPeriodo(e.target.checked)}
            />
            <span className="filtro-toggle-track">
              <span className="filtro-toggle-thumb" />
            </span>
            <span className="filtro-toggle-label">Todo o período</span>
          </label>
        </div>

        <div className="filtro-item filtro-acoes">
          <label>&nbsp;</label>

          <button className="botao-principal" onClick={aplicarBusca}>
            Aplicar
          </button>
        </div>
      </div>

      {loading && <div className="box-status">Carregando dados...</div>}
      {erro && <div className="box-erro">{erro}</div>}

      {visitasNaoVisualizadas.length > 0 && (
        <div
          className="alerta-visitas-nao-vistas"
          onClick={() => setOpcaoAtiva("visitas")}
        >
          <span>
            Você tem {visitasNaoVisualizadas.length} visita{visitasNaoVisualizadas.length !== 1 ? "s" : ""} não visualizada{visitasNaoVisualizadas.length !== 1 ? "s" : ""}.
          </span>
          <span className="alerta-link">Ver visitas →</span>
        </div>
      )}

      {abaAtiva === "relatoriogerente" && (
        <div className="relatorio-container">
          <div className="menu-lateral">
            {opcoes.map((opcao) => (
              <div
                key={opcao.id}
                onClick={() => setOpcaoAtiva(opcao.id)}
                className={`menu-item ${opcaoAtiva === opcao.id ? "ativo" : ""}`}
              >
                <span className="label-desktop">{opcao.label}</span>
                <span className="label-mobile">{opcao.labelMobile}</span>
                {opcao.id === "visitas" && visitasNaoVisualizadas.length > 0 && (
                  <span className="badge-contador">{visitasNaoVisualizadas.length}</span>
                )}
              </div>
            ))}
            {podeVerFiltroGerente && (
              <div
                onClick={() => setOpcaoAtiva("geralEquipes")}
                className={`menu-item ${opcaoAtiva === "geralEquipes" ? "ativo" : ""}`}
              >
                <span className="label-desktop">Geral Equipes</span>
                <span className="label-mobile">Equipes</span>
              </div>
            )}
          </div>

          <div className="conteudo-area">
            {renderizarConteudo()}

            <div ref={detalheRef} className="detalhe-scroll-anchor" style={{ marginTop: "18px" }}>{renderDetalheSelecionado()}</div>
          </div>
        </div>
      )}
      {renderModalViewer()}

      {/* Modal editar visita (gerente) */}
      {editVisitaModal && (
        <div className="relatorio-gerente-modal-backdrop" onClick={() => !savingEditVisita && setEditVisitaModal(null)}>
          <div
            className="relatorio-gerente-modal"
            style={{ width: "min(560px,96vw)", padding: "24px 28px", maxHeight: "92vh", overflowY: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem" }}>Editar Visita</h3>
            <p style={{ margin: "0 0 16px", fontSize: "0.85rem", color: "#64748b" }}>
              ID: {obterIdVisita(editVisitaModal)} · {editVisitaModal.corretor || ""}
            </p>

            <div className="relatorios-edit-form">
              <label>
                Data da visita
                <input
                  type="date"
                  value={editVisitaForm.dataVisita}
                  onChange={(e) => setEditVisitaForm((f) => ({ ...f, dataVisita: e.target.value }))}
                />
              </label>

              <label>
                Situação do imóvel
                <select
                  value={editVisitaForm.situacaoImovel}
                  onChange={(e) => setEditVisitaForm((f) => ({ ...f, situacaoImovel: e.target.value }))}
                >
                  <option value="CAPTACAO_61">Captação 61</option>
                  <option value="CAPTACAO_PROPRIA">Captação Própria</option>
                  <option value="CAPTACAO_PARCEIRO">Captação Parceiro</option>
                  <option value="IMOVEL_NAO_CAPTADO">Imóvel não captado</option>
                </select>
              </label>

              <label>
                Endereço externo
                <input
                  type="text"
                  value={editVisitaForm.enderecoExterno}
                  onChange={(e) => setEditVisitaForm((f) => ({ ...f, enderecoExterno: e.target.value }))}
                />
              </label>

              <label>
                Proposta
                <input
                  type="text"
                  value={editVisitaForm.proposta}
                  onChange={(e) => setEditVisitaForm((f) => ({ ...f, proposta: e.target.value }))}
                />
              </label>

              <label>
                Motivo do talvez
                <input
                  type="text"
                  value={editVisitaForm.motivoTalvez}
                  onChange={(e) => setEditVisitaForm((f) => ({ ...f, motivoTalvez: e.target.value }))}
                />
              </label>
            </div>

            {(editVisitaForm.avaliacoes || []).length > 0 && (
              <div className="ev-section">
                <div className="ev-section-title">Avaliações</div>
                {editVisitaForm.avaliacoes.map((av, idx) => (
                  <AvaliacaoEditorG
                    key={av.id_avaliacao || idx}
                    av={av}
                    onChange={(campo, valor) =>
                      setEditVisitaForm((f) => {
                        const avs = [...f.avaliacoes];
                        avs[idx] = { ...avs[idx], [campo]: valor };
                        return { ...f, avaliacoes: avs };
                      })
                    }
                  />
                ))}
              </div>
            )}

            <div className="relatorios-modal-actions">
              <button
                className="botao-secundario"
                onClick={() => setEditVisitaModal(null)}
                disabled={savingEditVisita}
              >
                Cancelar
              </button>
              <button
                className="botao-principal"
                onClick={salvarEdicaoVisita}
                disabled={savingEditVisita}
              >
                {savingEditVisita ? "Salvando..." : "Salvar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmar exclusão visita (gerente) */}
      {deleteVisitaConfirm && (
        <div className="relatorio-gerente-modal-backdrop" onClick={() => !deletingVisita && setDeleteVisitaConfirm(null)}>
          <div
            className="relatorio-gerente-modal"
            style={{ width: "min(480px,96vw)", padding: "24px 28px" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: "1.1rem", color: "#dc2626" }}>Confirmar exclusão</h3>
            <p style={{ margin: "0 0 8px" }}>
              Excluir visita de{" "}
              <strong>{deleteVisitaConfirm.corretor || obterIdVisita(deleteVisitaConfirm)}</strong>{" "}
              em <strong>{deleteVisitaConfirm.data_visita}</strong>?
            </p>
            <p style={{ margin: "0 0 20px", fontSize: "0.85rem", color: "#64748b" }}>
              Todos os registros relacionados (avaliações, clientes, parceiros) serão removidos permanentemente.
            </p>
            <div className="relatorios-modal-actions">
              <button
                className="botao-secundario"
                onClick={() => setDeleteVisitaConfirm(null)}
                disabled={deletingVisita}
              >
                Cancelar
              </button>
              <button
                className="botao-excluir"
                onClick={confirmarExclusaoVisita}
                disabled={deletingVisita}
              >
                {deletingVisita ? "Excluindo..." : "Excluir"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RelatorioGerente;
