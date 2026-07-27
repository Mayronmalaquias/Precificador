import React, { useCallback, useEffect, useMemo, useState } from "react";
import "../assets/css/AppVisita.css";

import { BASE } from "../services/api";

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
      const query = `id_corretor=${encodeURIComponent(corretorId)}&q=&limit=100000`;
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
