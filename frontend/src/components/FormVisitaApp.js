import React, { useCallback, useEffect, useMemo, useState } from "react";
import "../assets/css/AppVisita.css";
import "../assets/css/AppVisitaPolish.css";
import { useToast } from "../context/ToastContext";

import { BASE } from "../services/api";

// Normalizacao de texto para a busca das abas.
const semAcento = (v) => String(v || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
// `imovelId` guarda o codigo do Imoview, mas em algumas linhas antigas veio endereco.
const codigoImovel = (valor) => (/^\d+$/.test(String(valor || "").trim()) ? String(valor).trim() : "");

const CRITERIOS_AVALIACAO = [
  { key: "localizacao", label: "Localização" },
  { key: "tamanho", label: "Tamanho" },
  { key: "planta", label: "Planta" },
  { key: "acabamento", label: "Acabamento" },
  { key: "conservacao", label: "Conservação" },
  { key: "condominio", label: "Condomínio" },
  { key: "preco", label: "Preço" },
  { key: "notaGeral", label: "Nota Geral" },
];

function AvaliacaoEditor({ av, onChange }) {
  return (
    <div className="ev-card">
      {av.cliente && <div className="ev-card-cliente">{av.cliente}</div>}
      <div className="ev-grid">
        {CRITERIOS_AVALIACAO.map(({ key, label }) => {
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
                type="range"
                min={0} max={10} step={1}
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

  const [editModal, setEditModal] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [savingEdit, setSavingEdit] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [deletingVisita, setDeletingVisita] = useState(false);
  const [baixando, setBaixando] = useState("");
  // Codigos que o corretor CAPTOU, vindos da API do Imoview (`codigocaptador`).
  // `visitas.tipo_captacao` nao serve: acertou so 53% na medicao de 13/08/2026.
  const [codigosCaptados, setCodigosCaptados] = useState([]);
  const toast = useToast();

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


  /** Baixa um PDF do backend.
   *
   * O endpoint responde `application/pdf` no sucesso e **JSON** no erro (ex.: 403 de
   * imóvel que não é captação própria). Por isso o content-type decide o caminho — sem
   * isso o navegador salvaria um arquivo .pdf contendo a mensagem de erro.
   */
  const baixarPdf = useCallback(async (chave, url, nomeArquivo) => {
    setBaixando(chave);
    try {
      const resposta = await fetch(url);
      const tipo = resposta.headers.get("content-type") || "";
      if (!resposta.ok || !tipo.includes("pdf")) {
        const corpo = await resposta.json().catch(() => ({}));
        throw new Error(corpo.error || "Não foi possível gerar o PDF.");
      }
      const blob = await resposta.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = nomeArquivo;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      toast(err.message || "Erro ao gerar o PDF.", "error");
    } finally {
      setBaixando("");
    }
  }, [toast]);

  const carregarTudo = useCallback(async () => {
    if (!corretorId) return;

    setLoadingPage(true);
    setError("");

    try {
      const query = `id_corretor=${encodeURIComponent(corretorId)}&q=&limit=100000`;
      const [respVisitas, respImoveis, respClientes, respCaptados] = await Promise.all([
        fetch(`${BASE}/visitas_busca?${query}`, { method: "GET" }),
        fetch(`${BASE}/imoveis_busca_corretor?${query}`, { method: "GET" }),
        fetch(`${BASE}/clientes_busca?${query}`, { method: "GET" }),
        fetch(`${BASE}/imoveis/captados?id_corretor=${encodeURIComponent(corretorId)}`, { method: "GET" }),
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


      // Falha aqui nao derruba a pagina: sem a lista nenhum botao de relatorio de imovel
      // aparece — e o servidor barraria de qualquer forma.
      const dataCaptados = await respCaptados.json().catch(() => ({}));
      setCodigosCaptados(Array.isArray(dataCaptados.lista) ? dataCaptados.lista : []);
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

  // ── Abas ────────────────────────────────────────────────────────────────────
  // A pagina mostrava so visitas; imoveis e clientes eram carregados apenas para o
  // contador. Agora cada um tem sua aba, com o PDF correspondente.
  const [aba, setAba] = useState("visitas");
  const [busca, setBusca] = useState("");
  const [clienteSelId, setClienteSelId] = useState("");
  const [imovelSelId, setImovelSelId] = useState("");

  // Trocar de aba com um filtro digitado deixava a proxima lista vazia sem explicacao.
  useEffect(() => { setBusca(""); }, [aba]);

  const contem = useCallback((valor) => {
    const alvo = semAcento(busca).trim();
    return !alvo || semAcento(valor).includes(alvo);
  }, [busca]);

  // Quem captou o imovel vem da API do Imoview (rota /imoveis/captados), NAO de
  // `visitas.tipo_captacao`: aquele campo e um rotulo digitado por visita e erra. Das 274
  // visitas marcadas "Captacao Propria", so 146 tinham o corretor como captador de fato,
  // e outras 768 visitas eram de imovel captado por ele SEM estar marcadas assim.
  const captadosSet = useMemo(
    () => new Set(codigosCaptados.map((c) => codigoImovel(c) || String(c))),
    [codigosCaptados],
  );
  const euCaptei = useCallback(
    (idImovel) => captadosSet.has(codigoImovel(idImovel) || String(idImovel || "")),
    [captadosSet],
  );

  // Rotulo declarado na visita: serve de informacao na tela, nunca de permissao.
  const tiposPorImovel = useMemo(() => {
    const mapa = {};
    visitas.forEach((v) => {
      const cod = String(v.imovelId || "").trim();
      if (!cod) return;
      if (!mapa[cod]) mapa[cod] = [];
      if (v.tipoCaptacao && !mapa[cod].includes(v.tipoCaptacao)) mapa[cod].push(v.tipoCaptacao);
    });
    return mapa;
  }, [visitas]);

  const visitasFiltradas = useMemo(
    () => visitas.filter((v) => contem(`${v.cliente || ""} ${v.imovelId || ""} ${v.enderecoExterno || ""} ${v.dataVisita || ""}`)),
    [visitas, contem],
  );
  const clientesFiltrados = useMemo(
    () => clientes.filter((c) => contem(`${c.nome || ""} ${c.telefone || ""} ${c.email || ""}`)),
    [clientes, contem],
  );
  const imoveisFiltrados = useMemo(
    () => imoveis.filter((i) => contem(`${i.id_imovel || ""} ${i.endereco_externo || ""}`)),
    [imoveis, contem],
  );

  const clienteSelecionado = useMemo(
    () => clientesFiltrados.find((c) => c.id_cliente === clienteSelId) || clientesFiltrados[0] || null,
    [clientesFiltrados, clienteSelId],
  );
  const imovelSelecionado = useMemo(
    () => imoveisFiltrados.find((i) => i.id_imovel === imovelSelId) || imoveisFiltrados[0] || null,
    [imoveisFiltrados, imovelSelId],
  );

  const ABAS = [
    ["visitas", "Visitas", visitas.length],
    ["clientes", "Clientes", clientes.length],
    ["imoveis", "Imóveis", imoveis.length],
  ];

  const visitaSelecionada = useMemo(() => {
    if (!visitas.length) return null;
    return (
      visitas.find((visita) => visita.id_visita === visitaSelecionadaId) ||
      visitas[0]
    );
  }, [visitas, visitaSelecionadaId]);

  const abrirEditModal = (visita) => {
    const ddmmyyyy = visita.dataVisita || "";
    let isoDate = "";
    if (ddmmyyyy && ddmmyyyy.includes("/")) {
      const [dd, mm, yyyy] = ddmmyyyy.split("/");
      isoDate = `${yyyy}-${mm}-${dd}`;
    }
    let situacao = "CAPTACAO_PROPRIA";
    if (visita.imovelNaoCaptado === "TRUE") situacao = "IMOVEL_NAO_CAPTADO";
    else if (visita.tipoCaptacao) situacao = "CAPTACAO_61";

    const avaliacoes = (visita.avaliacoes || []).map((av) => ({
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

    setEditForm({
      dataVisita: isoDate,
      enderecoExterno: visita.enderecoExterno || "",
      proposta: visita.proposta || "",
      motivoTalvez: visita.motivoTalvez || visita.motivo_talvez || "",
      situacaoImovel: situacao,
      avaliacoes,
    });
    setEditModal(visita);
  };

  const salvarEdicao = async () => {
    if (!editModal) return;
    setSavingEdit(true);
    try {
      const resp = await fetch(`${BASE}/visitas/${editModal.id_visita}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editForm),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "Erro ao salvar.");
      setEditModal(null);
      await carregarTudo();
    } catch (err) {
      alert(err.message || "Erro ao salvar edição.");
    } finally {
      setSavingEdit(false);
    }
  };

  const confirmarExclusao = async () => {
    if (!deleteConfirm) return;
    setDeletingVisita(true);
    try {
      const resp = await fetch(`${BASE}/visitas/${deleteConfirm.id_visita}`, { method: "DELETE" });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "Erro ao excluir.");
      setDeleteConfirm(null);
      if (visitaSelecionadaId === deleteConfirm.id_visita) setVisitaSelecionadaId("");
      await carregarTudo();
    } catch (err) {
      alert(err.message || "Erro ao excluir visita.");
    } finally {
      setDeletingVisita(false);
    }
  };

  const texto = (valor) => {
    const limpo = String(valor || "").trim();
    return limpo || "-";
  };

  const textoLista = (items, campo = "nome") => {
    if (!Array.isArray(items) || !items.length) return "-";
    return items.map((item) => item?.[campo]).filter(Boolean).join(", ") || "-";
  };

  return (
    <>
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

      <div className="rel-abas">
        {ABAS.map(([chave, rotulo, total]) => (
          <button
            key={chave}
            type="button"
            className={aba === chave ? "is-ativa" : ""}
            onClick={() => setAba(chave)}
          >
            {rotulo} <em>{total}</em>
          </button>
        ))}
        <input
          className="rel-busca"
          placeholder={aba === "visitas" ? "Buscar por cliente, imóvel ou endereço"
            : aba === "clientes" ? "Buscar por nome, telefone ou e-mail"
              : "Buscar por código ou endereço"}
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
      </div>

      <div className="relatorios-grid">
        <section className="relatorios-list-card">
          <div className="relatorios-card-header">
            <h2>{aba === "visitas" ? "Visitas individuais" : aba === "clientes" ? "Meus clientes" : "Imóveis visitados"}</h2>
            <span>{(aba === "visitas" ? visitasFiltradas : aba === "clientes" ? clientesFiltrados : imoveisFiltrados).length} registro(s)</span>
          </div>

          <div className="relatorios-list">
            {aba === "visitas" && (!visitasFiltradas.length ? (
              <div className="relatorios-empty">Nenhuma visita encontrada.</div>
            ) : visitasFiltradas.map((visita) => (
              <button
                key={visita.id_visita}
                type="button"
                className={`relatorios-item ${visitaSelecionada?.id_visita === visita.id_visita ? "is-active" : ""}`}
                onClick={() => setVisitaSelecionadaId(visita.id_visita)}
              >
                <div className="relatorios-item-title">{texto(visita.cliente || visita.id_visita)}</div>
                <div className="relatorios-item-sub">{texto(visita.dataVisita)} · Imóvel {texto(visita.imovelId)}</div>
                <div className="relatorios-item-sub">{texto(visita.proposta || visita.tipoCaptacao)}</div>
              </button>
            )))}

            {aba === "clientes" && (!clientesFiltrados.length ? (
              <div className="relatorios-empty">Nenhum cliente encontrado.</div>
            ) : clientesFiltrados.map((cliente) => (
              <button
                key={cliente.id_cliente}
                type="button"
                className={`relatorios-item ${clienteSelecionado?.id_cliente === cliente.id_cliente ? "is-active" : ""}`}
                onClick={() => setClienteSelId(cliente.id_cliente)}
              >
                <div className="relatorios-item-title">{texto(cliente.nome)}</div>
                <div className="relatorios-item-sub">{texto(cliente.telefone) || "Sem telefone"}</div>
                <div className="relatorios-item-sub">{cliente.qtd_visitas || 0} visita(s) · última {texto(cliente.ultima_data)}</div>
              </button>
            )))}

            {aba === "imoveis" && (!imoveisFiltrados.length ? (
              <div className="relatorios-empty">Nenhum imóvel encontrado.</div>
            ) : imoveisFiltrados.map((imovel) => (
              <button
                key={imovel.id_imovel}
                type="button"
                className={`relatorios-item ${imovelSelecionado?.id_imovel === imovel.id_imovel ? "is-active" : ""}`}
                onClick={() => setImovelSelId(imovel.id_imovel)}
              >
                <div className="relatorios-item-title">
                  {texto(imovel.id_imovel)}
                  {euCaptei(imovel.id_imovel) && (
                    <em className="rel-tag-propria">captei este imóvel</em>
                  )}
                </div>
                <div className="relatorios-item-sub">{texto(imovel.endereco_externo)}</div>
                <div className="relatorios-item-sub">{imovel.qtd_visitas || 0} visita(s) · última {texto(imovel.ultima_data)}</div>
              </button>
            )))}
          </div>
        </section>

        <section className="relatorios-detail-card">
          {aba === "visitas" && (<>
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

              {/* Documentos: o corretor baixa a papelada da visita sem pedir a ninguem.
                  A ficha do imovel so aparece em CAPTACAO PROPRIA — imovel da 61 ou de
                  parceiro nao e dele para distribuir. */}
              <div className="relatorios-section rel-docs">
                <div className="relatorios-detail-label">Documentos</div>
                <div className="rel-docs-lista">
                  <button
                    type="button"
                    className="rel-doc-btn"
                    disabled={baixando === "visita"}
                    onClick={() => baixarPdf(
                      "visita",
                      `${BASE}/visitas/pdf/download?visita_id=${encodeURIComponent(visitaSelecionada.id_visita)}`,
                      `Relatorio_Visita_${visitaSelecionada.id_visita}.pdf`,
                    )}
                  >
                    <b>Relatório da visita</b>
                    <span>{baixando === "visita" ? "Gerando…" : "PDF com avaliações e assinatura"}</span>
                  </button>

                  {(visitaSelecionada.clientes || []).filter((c) => c.id_cliente).map((c) => (
                    <button
                      key={c.id_cliente}
                      type="button"
                      className="rel-doc-btn"
                      disabled={baixando === `cliente-${c.id_cliente}`}
                      onClick={() => baixarPdf(
                        `cliente-${c.id_cliente}`,
                        `${BASE}/clientes/pdf/download?id_cliente=${encodeURIComponent(c.id_cliente)}`,
                        `Relatorio_Cliente_${c.id_cliente}.pdf`,
                      )}
                    >
                      <b>Ficha do cliente</b>
                      <span>{baixando === `cliente-${c.id_cliente}` ? "Gerando…" : c.nome || c.id_cliente}</span>
                    </button>
                  ))}

                  {euCaptei(visitaSelecionada.imovelId) && (
                    <button
                      type="button"
                      className="rel-doc-btn rel-doc-btn--imovel"
                      disabled={baixando === "imovel"}
                      onClick={() => baixarPdf(
                        "imovel",
                        `${BASE}/imoveis/pdf/download?imovel_id=${encodeURIComponent(visitaSelecionada.imovelId)}`
                        + `&id_corretor=${encodeURIComponent(corretorId)}`,
                        `Relatorio_Imovel_${visitaSelecionada.imovelId}.pdf`,
                      )}
                    >
                      <b>Relatório do imóvel</b>
                      <span>{baixando === "imovel" ? "Gerando…" : "Visitas, clientes e avaliações"}</span>
                    </button>
                  )}
                </div>
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
                <button
                  type="button"
                  className="relatorios-secondary-btn"
                  onClick={() => abrirEditModal(visitaSelecionada)}
                >
                  Editar
                </button>
                <button
                  type="button"
                  className="relatorios-delete-btn"
                  onClick={() => setDeleteConfirm(visitaSelecionada)}
                >
                  Excluir
                </button>
              </div>
            </>
          )}
          </>)}

          {aba === "clientes" && (<>
            <div className="relatorios-card-header">
              <h2>Detalhes do cliente</h2>
              <span>{texto(clienteSelecionado?.id_cliente)}</span>
            </div>
            {!clienteSelecionado ? (
              <div className="relatorios-empty">Selecione um cliente.</div>
            ) : (
              <>
                <div className="relatorios-detail-grid">
                  <div className="relatorios-detail-box relatorios-detail-box--full">
                    <span className="relatorios-detail-label">Nome</span>
                    <strong>{texto(clienteSelecionado.nome)}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Telefone</span>
                    <strong>{texto(clienteSelecionado.telefone)}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">E-mail</span>
                    <strong>{texto(clienteSelecionado.email)}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Visitas</span>
                    <strong>{clienteSelecionado.qtd_visitas || 0}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Última visita</span>
                    <strong>{texto(clienteSelecionado.ultima_data)}</strong>
                  </div>
                  <div className="relatorios-detail-box relatorios-detail-box--full">
                    <span className="relatorios-detail-label">Imóveis visitados</span>
                    <strong>{textoLista(clienteSelecionado.imoveis)}</strong>
                  </div>
                </div>

                <div className="relatorios-section rel-docs">
                  <div className="relatorios-detail-label">Documentos</div>
                  <div className="rel-docs-lista">
                    <button
                      type="button"
                      className="rel-doc-btn"
                      disabled={baixando === `cliente-${clienteSelecionado.id_cliente}`}
                      onClick={() => baixarPdf(
                        `cliente-${clienteSelecionado.id_cliente}`,
                        `${BASE}/clientes/pdf/download?id_cliente=${encodeURIComponent(clienteSelecionado.id_cliente)}`,
                        `Relatorio_Cliente_${clienteSelecionado.id_cliente}.pdf`,
                      )}
                    >
                      <b>Relatório do cliente</b>
                      <span>{baixando === `cliente-${clienteSelecionado.id_cliente}` ? "Gerando…" : "Histórico de visitas e avaliações"}</span>
                    </button>
                    {clienteSelecionado.telefone && (
                      <a
                        className="rel-doc-btn rel-doc-btn--zap"
                        target="_blank"
                        rel="noreferrer"
                        href={`https://wa.me/${String(clienteSelecionado.telefone).replace(/\D/g, "")}`}
                      >
                        <b>Chamar no WhatsApp</b>
                        <span>{texto(clienteSelecionado.telefone)}</span>
                      </a>
                    )}
                  </div>
                </div>
              </>
            )}
          </>)}

          {aba === "imoveis" && (<>
            <div className="relatorios-card-header">
              <h2>Detalhes do imóvel</h2>
              <span>{texto(imovelSelecionado?.id_imovel)}</span>
            </div>
            {!imovelSelecionado ? (
              <div className="relatorios-empty">Selecione um imóvel.</div>
            ) : (
              <>
                <div className="relatorios-detail-grid">
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Código</span>
                    <strong>{texto(imovelSelecionado.id_imovel)}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Visitas</span>
                    <strong>{imovelSelecionado.qtd_visitas || 0}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Última visita</span>
                    <strong>{texto(imovelSelecionado.ultima_data)}</strong>
                  </div>
                  <div className="relatorios-detail-box">
                    <span className="relatorios-detail-label">Captação</span>
                    <strong>{(tiposPorImovel[String(imovelSelecionado.id_imovel)] || []).join(", ") || "-"}</strong>
                  </div>
                  <div className="relatorios-detail-box relatorios-detail-box--full">
                    <span className="relatorios-detail-label">Endereço</span>
                    <strong>{texto(imovelSelecionado.endereco_externo)}</strong>
                  </div>
                  <div className="relatorios-detail-box relatorios-detail-box--full">
                    <span className="relatorios-detail-label">Clientes que visitaram</span>
                    <strong>{textoLista(imovelSelecionado.clientes)}</strong>
                  </div>
                </div>

                <div className="relatorios-section rel-docs">
                  <div className="relatorios-detail-label">Documentos</div>
                  <div className="rel-docs-lista">
                    {euCaptei(imovelSelecionado.id_imovel) && (
                      <button
                        type="button"
                        className="rel-doc-btn rel-doc-btn--imovel"
                        disabled={baixando === "imovel"}
                        onClick={() => baixarPdf(
                          "imovel",
                          `${BASE}/imoveis/pdf/download?imovel_id=${encodeURIComponent(imovelSelecionado.id_imovel)}`
                          + `&id_corretor=${encodeURIComponent(corretorId)}`,
                          `Relatorio_Imovel_${imovelSelecionado.id_imovel}.pdf`,
                        )}
                      >
                        <b>Relatório do imóvel</b>
                        <span>{baixando === "imovel" ? "Gerando…" : "Visitas, clientes e avaliações"}</span>
                      </button>
                    )}
                  </div>
                </div>
              </>
            )}
          </>)}
        </section>
      </div>
    </div>

      {/* Modal de edição */}
      {editModal && (
        <div className="relatorios-modal-overlay" onClick={() => !savingEdit && setEditModal(null)}>
          <div className="relatorios-modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="relatorios-modal-title">Editar Visita</h3>
            <p className="relatorios-modal-sub">ID: {editModal.id_visita}</p>

            <div className="relatorios-edit-form">
              <label>
                Data da visita
                <input
                  type="date"
                  value={editForm.dataVisita}
                  onChange={(e) => setEditForm((f) => ({ ...f, dataVisita: e.target.value }))}
                />
              </label>

              <label>
                Situação do imóvel
                <select
                  value={editForm.situacaoImovel}
                  onChange={(e) => setEditForm((f) => ({ ...f, situacaoImovel: e.target.value }))}
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
                  value={editForm.enderecoExterno}
                  onChange={(e) => setEditForm((f) => ({ ...f, enderecoExterno: e.target.value }))}
                />
              </label>

              <label>
                Proposta
                <input
                  type="text"
                  value={editForm.proposta}
                  onChange={(e) => setEditForm((f) => ({ ...f, proposta: e.target.value }))}
                />
              </label>

              {String(editForm.proposta || "").trim().toLowerCase() === "talvez" && (
                <label>
                  Motivo do talvez
                  <input
                    type="text"
                    value={editForm.motivoTalvez || ""}
                    onChange={(e) => setEditForm((f) => ({ ...f, motivoTalvez: e.target.value }))}
                  />
                </label>
              )}
            </div>

            {(editForm.avaliacoes || []).length > 0 && (
              <div className="ev-section">
                <div className="ev-section-title">Avaliações</div>
                {editForm.avaliacoes.map((av, idx) => (
                  <AvaliacaoEditor
                    key={av.id_avaliacao || idx}
                    av={av}
                    onChange={(campo, valor) =>
                      setEditForm((f) => {
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
                type="button"
                className="relatorios-secondary-btn"
                onClick={() => setEditModal(null)}
                disabled={savingEdit}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="relatorios-primary-btn"
                onClick={salvarEdicao}
                disabled={savingEdit}
              >
                {savingEdit ? "Salvando..." : "Salvar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmação de exclusão */}
      {deleteConfirm && (
        <div className="relatorios-modal-overlay" onClick={() => !deletingVisita && setDeleteConfirm(null)}>
          <div className="relatorios-modal relatorios-modal--danger" onClick={(e) => e.stopPropagation()}>
            <h3 className="relatorios-modal-title">Confirmar exclusão</h3>
            <p className="relatorios-modal-sub">
              Tem certeza que deseja excluir a visita de{" "}
              <strong>{deleteConfirm.cliente || deleteConfirm.id_visita}</strong> em{" "}
              <strong>{deleteConfirm.dataVisita}</strong>?
            </p>
            <p className="relatorios-modal-warn">
              Esta ação não pode ser desfeita. Todos os dados relacionados (avaliações, clientes, parceiros) serão removidos.
            </p>
            <div className="relatorios-modal-actions">
              <button
                type="button"
                className="relatorios-secondary-btn"
                onClick={() => setDeleteConfirm(null)}
                disabled={deletingVisita}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="relatorios-delete-btn"
                onClick={confirmarExclusao}
                disabled={deletingVisita}
              >
                {deletingVisita ? "Excluindo..." : "Excluir visita"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
