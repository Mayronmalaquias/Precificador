import React, { useEffect, useMemo, useState } from "react";
import "../assets/css/RelatorioGerente.css";

function RelatorioGerente() {
  //const API_BASE = useMemo(() => "http://localhost:5000/gerente-dashboard", []);
  //const API_VISITAS_BASE = useMemo(() => "http://localhost:5000", []);
  //const API_IMOVEIS_BASE = useMemo(() => "http://localhost:5000", []);

  const API_BASE = useMemo(() => "/api/gerente-dashboard", []);
  const API_VISITAS_BASE = useMemo(() => "/api", []);
  const API_IMOVEIS_BASE = useMemo(() => "/api", []);

  const [abaAtiva, setAbaAtiva] = useState("relatoriogerente");
  const [opcaoAtiva, setOpcaoAtiva] = useState("visaoGeral");

  const hoje = new Date();
  const primeiroDiaMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
    .toISOString()
    .slice(0, 10);
  const hojeStr = hoje.toISOString().slice(0, 10);

  const [filtros, setFiltros] = useState({
    id_gerente: "",
    start: primeiroDiaMes,
    end: hojeStr,
    q: "",
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

  const [itemSelecionado, setItemSelecionado] = useState(null);
  const [tipoSelecionado, setTipoSelecionado] = useState("");

  const [loadingPdfVisita, setLoadingPdfVisita] = useState(false);
  const [loadingPdfCliente, setLoadingPdfCliente] = useState(false);
  const [loadingPdfImovel, setLoadingPdfImovel] = useState(false);

  const opcoes = [
    { id: "visaoGeral", label: "Visão Geral", labelMobile: "Visão Geral" },
    { id: "ranking", label: "Ranking", labelMobile: "Ranking" },
    { id: "visitas", label: "Visitas", labelMobile: "Visitas" },
    { id: "imoveis", label: "Imóveis", labelMobile: "Imóveis" },
    { id: "clientes", label: "Clientes", labelMobile: "Clientes" },
    { id: "pdfs", label: "Relatórios PDF", labelMobile: "PDFs" },
  ];

  const gerentesFixos = [
    { id: "G61010", nome: "Gerente 1" },
    { id: "2", nome: "Gerente 2" },
    { id: "3", nome: "Gerente 3" },
  ];

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

      setFiltros((prev) => ({
        ...prev,
        id_gerente: idGerente,
      }));
    } catch (err) {
      console.error(err);
      setErro("Erro ao carregar os dados do gerente logado.");
    }
  }, []);

  useEffect(() => {
    if (filtros.id_gerente) {
      carregarDados();
    }
  }, [filtros.id_gerente, filtros.start, filtros.end]);

  const buildQuery = (extra = {}) => {
    const params = new URLSearchParams();

    const finalParams = {
      id_gerente: filtros.id_gerente,
      start: filtros.start,
      end: filtros.end,
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

    setLoading(true);
    setErro("");

    try {
      const [
        dashboardRes,
        corretoresRes,
        rankingVisitasRes,
        rankingClientesRes,
      ] = await Promise.all([
        fetchJson(`${API_BASE}/dashboard?${buildQuery()}`),
        fetchJson(`${API_BASE}/corretores?${buildQuery()}`),
        fetchJson(`${API_BASE}/ranking?${buildQuery({ tipo: "visitas" })}`),
        fetchJson(`${API_BASE}/ranking?${buildQuery({ tipo: "clientes" })}`),
      ]);

      setDashboard(dashboardRes);
      setCorretores(corretoresRes.lista || []);
      setRankingVisitas(rankingVisitasRes.lista || []);
      setRankingClientes(rankingClientesRes.lista || []);

      await carregarListas();
    } catch (e) {
      setErro(e.message || "Erro ao carregar dashboard.");
    } finally {
      setLoading(false);
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

  const handleFiltroChange = (campo, valor) => {
    setFiltros((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const aplicarBusca = async () => {
    if (!filtros.id_gerente) return;
    setLoading(true);
    setErro("");
    try {
      await carregarListas();
    } catch (e) {
      setErro(e.message || "Erro ao aplicar filtro.");
    } finally {
      setLoading(false);
    }
  };

  const abrirPdfGerente = () => {
    if (!filtros.id_gerente) return;
    const url = `${API_BASE}/gerente/pdf?${buildQuery()}`;
    window.open(url, "_blank");
  };

  const baixarPdfGerente = () => {
    if (!filtros.id_gerente) return;
    const url = `${API_BASE}/gerente/pdf/download?${buildQuery()}`;
    window.open(url, "_blank");
  };

  const abrirPdfCorretor = () => {
    if (!corretorSelecionado) {
      alert("Selecione um corretor.");
      return;
    }
    const params = new URLSearchParams({ id_corretor: corretorSelecionado });
    window.open(`${API_BASE}/corretor/pdf?${params.toString()}`, "_blank");
  };

  const baixarPdfCorretor = () => {
    if (!corretorSelecionado) {
      alert("Selecione um corretor.");
      return;
    }
    const params = new URLSearchParams({ id_corretor: corretorSelecionado });
    window.open(`${API_BASE}/corretor/pdf/download?${params.toString()}`, "_blank");
  };

  const selecionarVisita = (item) => {
    setTipoSelecionado("visita");
    setItemSelecionado(item);
  };

  const selecionarImovel = (item) => {
    setTipoSelecionado("imovel");
    setItemSelecionado(item);
  };

  const selecionarCliente = (item) => {
    setTipoSelecionado("cliente");
    setItemSelecionado(item);
  };

  async function abrirPdfVisita() {
    if (!itemSelecionado || tipoSelecionado !== "visita") return;

    setLoadingPdfVisita(true);
    try {
      const resp = await fetch(
        `${API_VISITAS_BASE}/visitas/pdf?visita_id=${encodeURIComponent(
          itemSelecionado.id_visita
        )}`
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
      alert(err.message || "Erro ao abrir o PDF da visita.");
    } finally {
      setLoadingPdfVisita(false);
    }
  }

  function baixarPdfVisita() {
    if (!itemSelecionado || tipoSelecionado !== "visita") return;

    const url =
      `${API_VISITAS_BASE}/visitas/pdf/download?visita_id=${encodeURIComponent(
        itemSelecionado.id_visita
      )}`;

    window.open(url, "_blank");
  }

  async function abrirPdfImovel() {
    if (!itemSelecionado || tipoSelecionado !== "imovel") return;

    setLoadingPdfImovel(true);
    try {
      const resp = await fetch(
        `${API_IMOVEIS_BASE}/imoveis/pdf?imovel_id=${encodeURIComponent(
          itemSelecionado.id_imovel
        )}`
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
      alert(err.message || "Erro ao abrir o PDF do imóvel.");
    } finally {
      setLoadingPdfImovel(false);
    }
  }

  function baixarPdfImovel() {
    if (!itemSelecionado || tipoSelecionado !== "imovel") return;

    const url =
      `${API_IMOVEIS_BASE}/imoveis/pdf/download?imovel_id=${encodeURIComponent(
        itemSelecionado.id_imovel
      )}`;

    window.open(url, "_blank");
  }

  async function abrirPdfCliente() {
    if (!itemSelecionado || tipoSelecionado !== "cliente") return;

    setLoadingPdfCliente(true);
    try {
      const resp = await fetch(
        `${API_VISITAS_BASE}/clientes/pdf?id_cliente=${encodeURIComponent(
          itemSelecionado.id_cliente
        )}`
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
      alert(err.message || "Erro ao abrir o PDF do cliente.");
    } finally {
      setLoadingPdfCliente(false);
    }
  }

  function baixarPdfCliente() {
    if (!itemSelecionado || tipoSelecionado !== "cliente") return;

    const url =
      `${API_VISITAS_BASE}/clientes/pdf/download?id_cliente=${encodeURIComponent(
        itemSelecionado.id_cliente
      )}`;

    window.open(url, "_blank");
  }

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

      <div className="tabela-wrapper">
        <table className="tabela-relatorio">
          <thead>
            <tr>
              <th>Data</th>
              <th>Corretor</th>
              <th>Imóvel</th>
              <th>Clientes</th>
              <th>Proposta</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {!visitas.length ? (
              <tr>
                <td colSpan="6">Nenhuma visita encontrada.</td>
              </tr>
            ) : (
              visitas.map((item) => (
                <tr
                  key={item.id_visita}
                  className={
                    tipoSelecionado === "visita" &&
                    itemSelecionado?.id_visita === item.id_visita
                      ? "linha-ativa"
                      : ""
                  }
                >
                  <td>{item.data_visita || "-"}</td>
                  <td>{item.corretor || "-"}</td>
                  <td>{item.id_imovel || "-"}</td>
                  <td>{Array.isArray(item.clientes) ? item.clientes.join(", ") : "-"}</td>
                  <td>{item.proposta || "-"}</td>
                  <td>
                    <div className="acoes-tabela">
                      <button
                        className="botao-secundario"
                        onClick={() => selecionarVisita(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="botao-secundario"
                        onClick={() => window.open(item.pdf_download_url, "_blank")}
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
            {!imoveis.length ? (
              <tr>
                <td colSpan="6">Nenhum imóvel encontrado.</td>
              </tr>
            ) : (
              imoveis.map((item) => (
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
                  <td>{Array.isArray(item.corretores) ? item.corretores.join(", ") : "-"}</td>
                  <td>
                    <div className="acoes-tabela">
                      <button
                        className="botao-secundario"
                        onClick={() => selecionarImovel(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="botao-secundario"
                        onClick={() =>
                          window.open(
                            item.pdf_download_url ||
                              `${API_IMOVEIS_BASE}/imoveis/pdf/download?imovel_id=${encodeURIComponent(item.id_imovel)}`,
                            "_blank"
                          )
                        }
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

  const renderTabelaClientes = () => (
    <div className="card-padrao">
      <h3 className="card-titulo">Clientes do time</h3>

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
            {!clientes.length ? (
              <tr>
                <td colSpan="7">Nenhum cliente encontrado.</td>
              </tr>
            ) : (
              clientes.map((item) => (
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
                  <td>{Array.isArray(item.corretores) ? item.corretores.join(", ") : "-"}</td>
                  <td>{item.qtd_visitas ?? 0}</td>
                  <td>{item.ultima_visita || "-"}</td>
                  <td>
                    <div className="acoes-tabela">
                      <button
                        className="botao-secundario"
                        onClick={() => selecionarCliente(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="botao-secundario"
                        onClick={() => window.open(item.pdf_download_url, "_blank")}
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

  const renderVisaoGeral = () => {
    const resumo = dashboard?.resumo || {};
    const grafVisitas = dashboard?.graficos?.visitas_por_dia || {};
    const grafClientes = dashboard?.graficos?.clientes_por_dia || {};

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
            className={`tab-interna ${tipoRankingAtivo === "visitas" ? "ativa" : ""}`}
            onClick={() => setTipoRankingAtivo("visitas")}
          >
            Ranking por visitas
          </button>
          <button
            className={`tab-interna ${tipoRankingAtivo === "clientes" ? "ativa" : ""}`}
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
            <button className="botao-principal" onClick={abrirPdfGerente}>
              Ver PDF
            </button>
            <button className="botao-secundario" onClick={baixarPdfGerente}>
              Baixar PDF
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
              <option key={corretor.IdCorretor} value={corretor.IdCorretor}>
                {corretor.Nome}
              </option>
            ))}
          </select>

          <div className="acoes-pdf">
            <button className="botao-principal" onClick={abrirPdfCorretor}>
              Ver PDF
            </button>
            <button className="botao-secundario" onClick={baixarPdfCorretor}>
              Baixar PDF
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
            <h3 className="card-titulo">Detalhes da ultima visita</h3>
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
                {Array.isArray(itemSelecionado.clientes) && itemSelecionado.clientes.length > 0
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
                {Array.isArray(itemSelecionado.clientes) && itemSelecionado.clientes.length > 0
                  ? itemSelecionado.clientes.join(", ")
                  : "-"}
              </strong>
            </div>

            <div className="detalhe-box detalhe-box-full">
              <span className="detalhe-label">Corretores vinculados</span>
              <strong>
                {Array.isArray(itemSelecionado.corretores) && itemSelecionado.corretores.length > 0
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
            <button className="botao-secundario" onClick={baixarPdfImovel}>
              Baixar PDF
            </button>
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
              {Array.isArray(itemSelecionado.corretores) && itemSelecionado.corretores.length > 0
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
          <button className="botao-secundario" onClick={baixarPdfCliente}>
            Baixar PDF
          </button>
        </div>
      </section>
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
      default:
        return (
          <div className="card-padrao">
            <h3 className="card-titulo">Relatório Gerente</h3>
            <p className="card-texto">Selecione uma opção.</p>
          </div>
        );
    }
  };

  return (
    <div className="pagina-relatorio">
      <div className="titulo-pagina">Relatório Gerente</div>

      <div className="aba-topo" onClick={() => setAbaAtiva("relatoriogerente")}>
        Relatório Gerente
      </div>

      <div className="bloco-filtros-gerente">

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

        <div className="filtro-item filtro-acoes">
          <label>&nbsp;</label>
          <button className="botao-principal" onClick={aplicarBusca}>
            Aplicar
          </button>
        </div>
      </div>

      {loading && <div className="box-status">Carregando dados...</div>}
      {erro && <div className="box-erro">{erro}</div>}

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
              </div>
            ))}
          </div>

          <div className="conteudo-area">
            {renderizarConteudo()}
            <div style={{ marginTop: "18px" }}>{renderDetalheSelecionado()}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RelatorioGerente;