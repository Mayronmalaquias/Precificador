// src/components/VisitaForm.jsx
import React, { useState, useEffect } from "react";
import "../assets/css/VisitaForm.css";

// const API_BASE = "http://localhost:5000/visitas";
// const API_BASE = "/api/visitas";
const API_BASE = "http://localhost:5000";


export default function VisitaForm() {
  const [corretorInfo, setCorretorInfo] = useState({
    id: "", // <- C61010 etc (vem do login)
    username: "",
    nome: "",
    telefone: "",
    instagram: "",
    descricao: "",
    email: "",
  });

  const [form, setForm] = useState({
    imovelId: "",
    dataVisita: new Date().toISOString().split("T")[0], // yyyy-mm-dd
    parceiroExterno: "NAO", // SIM / NAO
    situacaoImovel: "CAPTACAO_PROPRIA", // CAPTACAO_PROPRIA | CAPTACAO_PARCEIRO | IMOVEL_NAO_CAPTADO
    clienteNome: "",
    proposta: "Talvez", // Sim / Não / Talvez
    papelVisita: "Interessado", // Comprador | Interessado

    // campos extras (Sheets)
    enderecoExterno: "",

    // ✅ agora SEM IDs: só nomes
    parceiroNome: "",
    parceiroImobiliaria: "",

    clienteAssinanteNome: "",
    clienteAssinanteTelefone: "",
    clienteAssinanteEmail: "",

    assinatura: "",
    audioDescricaoClienteVisita: "",
    linkAudio: "",

    // notas 1–10
    localizacao: 10,
    tamanho: 10,
    planta: 10,
    acabamento: 10,
    conservacao: 10,
    condominio: 10,
    preco: 10, // ✅ ADICIONADO (porque seu CSV tem Preco e seu JSX usa renderNotaButtons("preco"))
    notaGeral: 10,

    precoNota10: "", // número (R$)
  });

  const [pdfFile, setPdfFile] = useState(null);
  const [loading, setLoading] = useState(false);

  // ✅ estados da busca por endereço
  const [enderecoQuery, setEnderecoQuery] = useState("");
  const [imoveisSugestoes, setImoveisSugestoes] = useState([]);
  const [loadingImoveis, setLoadingImoveis] = useState(false);
  const [showSugestoes, setShowSugestoes] = useState(false);

  // Carrega dados do usuário logado
  useEffect(() => {
    const userDataString = localStorage.getItem("userData");
    if (userDataString) {
      try {
        const userData = JSON.parse(userDataString);

        const corretorId =
          userData.idCorretor ||
          userData.id_corretor ||
          userData.codigoCorretor ||
          userData.codigo ||
          userData.id_usuarios ||
          "";

        setCorretorInfo({
          id: corretorId,
          username: userData.username || "",
          nome: userData.nome || "",
          telefone: userData.telefone || "",
          instagram: userData.instagram || "",
          descricao: userData.descricao || "",
          email: userData.email || "",
        });
      } catch (e) {
        console.error("Erro ao ler userData do localStorage", e);
      }
    }
  }, []);

  function updateField(field) {
    return (e) => {
      setForm((prev) => ({
        ...prev,
        [field]: e.target.value,
      }));
    };
  }

  function setRadio(field, value) {
    return () => {
      setForm((prev) => ({
        ...prev,
        [field]: value,
      }));
    };
  }

  // ✅ Busca no backend: /api/visitas/imoveis_busca?endereco=...
  async function buscarImoveisPorEndereco(query) {
    const q = (query || "").trim();
    if (q.length < 3) {
      setImoveisSugestoes([]);
      return;
    }

    setLoadingImoveis(true);
    try {
      const resp = await fetch(
        `${API_BASE}/imoveis_busca?endereco=${encodeURIComponent(q)}`,
        { method: "GET" }
      );

      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao buscar imóveis");
      }

      setImoveisSugestoes(Array.isArray(data.lista) ? data.lista : []);
    } catch (e) {
      console.error(e);
      setImoveisSugestoes([]);
    } finally {
      setLoadingImoveis(false);
    }
  }

  // ✅ debounce (evita chamar a API a cada tecla)
  useEffect(() => {
    if (!showSugestoes) return;
    const t = setTimeout(() => {
      buscarImoveisPorEndereco(enderecoQuery);
    }, 350);
    return () => clearTimeout(t);
  }, [enderecoQuery, showSugestoes]);

  async function uploadPdfIfAny({ idCorretor, imovelId, dataVisita }) {
    if (!pdfFile) return { drivePath: "", driveLink: "" };

    const fd = new FormData();
    fd.append("file", pdfFile);
    fd.append("idCorretor", idCorretor || "");
    fd.append("imovelId", imovelId || "");
    fd.append("dataVisita", dataVisita || "");

    const resp = await fetch(`${API_BASE}/upload_pdf`, {
      method: "POST",
      body: fd,
    });

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) {
      throw new Error(data.error || "Erro ao enviar PDF");
    }

    return {
      drivePath: data.drivePath || "",
      driveLink: data.driveLink || "",
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!corretorInfo.id) {
      alert("Erro: ID/Código do corretor não carregado. Faça login novamente.");
      return;
    }

    setLoading(true);
    try {
      // 1) Upload do PDF (se houver)
      const { drivePath, driveLink } = await uploadPdfIfAny({
        idCorretor: corretorInfo.id,
        imovelId: form.imovelId,
        dataVisita: form.dataVisita,
      });

      // 2) Payload final (grava caminho + link no Sheets)
      const payload = {
        ...form,

        idCorretor: corretorInfo.id,

        // Campos do Sheets (E e H no seu modelo)
        anexoFichaVisita: drivePath, // ex: Fato_Visitas_PDF/arquivo.pdf
        linkImagem: driveLink, // webViewLink do Drive

        // dados do corretor
        corretor: corretorInfo.nome || corretorInfo.username,
        corretorEmail: corretorInfo.email || "",
        telefoneCorretor: corretorInfo.telefone,
        instagramCorretor: corretorInfo.instagram,
        descricaoCorretor: corretorInfo.descricao,

        // ✅ agora inclui preco (nota 1-10)
        avaliacoes: {
          localizacao: Number(form.localizacao),
          tamanho: Number(form.tamanho),
          planta: Number(form.planta),
          acabamento: Number(form.acabamento),
          conservacao: Number(form.conservacao),
          condominio: Number(form.condominio),
          preco: Number(form.preco),
          notaGeral: Number(form.notaGeral),
        },
      };

      const resp = await fetch(API_BASE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao registrar visita");
      }

      alert(`Visita lançada com sucesso! Id: ${data.id_visita}`);

      // limpa alguns campos
      setForm((prev) => ({
        ...prev,
        imovelId: "",
        clienteNome: "",
        proposta: "Talvez",
        papelVisita: "Interessado",
        enderecoExterno: "",

        parceiroNome: "",
        parceiroImobiliaria: "",

        clienteAssinanteNome: "",
        clienteAssinanteTelefone: "",
        clienteAssinanteEmail: "",

        assinatura: "",
        audioDescricaoClienteVisita: "",
        linkAudio: "",

        precoNota10: "",
      }));

      // limpa busca
      setEnderecoQuery("");
      setImoveisSugestoes([]);
      setShowSugestoes(false);

      setPdfFile(null);
    } catch (err) {
      console.error(err);
      alert(err.message || "Erro inesperado");
    } finally {
      setLoading(false);
    }
  }

  function renderNotaButtons(field) {
    const value = Number(form[field]);
    return (
      <div className="nota-buttons">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            type="button"
            className={`nota-button ${value === n ? "nota-button-active" : ""}`}
            onClick={() =>
              setForm((prev) => ({
                ...prev,
                [field]: n,
              }))
            }
          >
            {n}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="visita-form-wrapper">
      <form className="visita-form" onSubmit={handleSubmit}>
        <h2>Lançar Visita</h2>

        {/* Corretor (somente leitura) */}
        <div className="vf-group">
          <label>Corretor</label>
          <div className="vf-readonly">
            {(corretorInfo.id ? `${corretorInfo.id} - ` : "") +
              (corretorInfo.nome || corretorInfo.username || "Não identificado")}
          </div>
        </div>

        {/* Parceiro Externo */}
        <div className="vf-group">
          <label>Visita com Parceiro Externo?</label>
          <div className="vf-toggle-row">
            <button
              type="button"
              className={`vf-toggle ${
                form.parceiroExterno === "NAO"
                  ? "vf-toggle-active vf-toggle-no"
                  : ""
              }`}
              onClick={setRadio("parceiroExterno", "NAO")}
            >
              NÃO
            </button>
            <button
              type="button"
              className={`vf-toggle ${
                form.parceiroExterno === "SIM"
                  ? "vf-toggle-active vf-toggle-yes"
                  : ""
              }`}
              onClick={setRadio("parceiroExterno", "SIM")}
            >
              SIM
            </button>
          </div>
        </div>

        {/* Situação do Imóvel */}
        <div className="vf-group">
          <label>Situação do Imóvel</label>
          <div className="vf-toggle-row">
            <button
              type="button"
              className={`vf-toggle ${
                form.situacaoImovel === "CAPTACAO_PROPRIA"
                  ? "vf-toggle-active"
                  : ""
              }`}
              onClick={setRadio("situacaoImovel", "CAPTACAO_PROPRIA")}
            >
              Captação Própria
            </button>
            <button
              type="button"
              className={`vf-toggle ${
                form.situacaoImovel === "CAPTACAO_PARCEIRO"
                  ? "vf-toggle-active"
                  : ""
              }`}
              onClick={setRadio("situacaoImovel", "CAPTACAO_PARCEIRO")}
            >
              Captação Parceiro
            </button>
            <button
              type="button"
              className={`vf-toggle ${
                form.situacaoImovel === "IMOVEL_NAO_CAPTADO"
                  ? "vf-toggle-active"
                  : ""
              }`}
              onClick={setRadio("situacaoImovel", "IMOVEL_NAO_CAPTADO")}
            >
              Imóvel não captado
            </button>
          </div>
        </div>

        {/* ✅ BUSCA POR ENDEREÇO */}
        <div className="vf-group">
          <label>Buscar imóvel por endereço</label>
          <input
            type="text"
            value={enderecoQuery}
            onChange={(e) => {
              setEnderecoQuery(e.target.value);
              setShowSugestoes(true);
            }}
            onFocus={() => setShowSugestoes(true)}
            placeholder="Ex: SQS 308, W3, Rua 12..."
          />

          {loadingImoveis && (
            <div className="vf-hint">Buscando...</div>
          )}

          {showSugestoes && imoveisSugestoes.length > 0 && (
            <div className="vf-sugestoes">
              {imoveisSugestoes.map((it) => (
                <button
                  type="button"
                  key={`${it.codigo}-${it.finalidade || ""}`}
                  className="vf-sugestao-item"
                  onClick={() => {
                    const enderecoFull = `${it.endereco || ""}${it.numero ? `, ${it.numero}` : ""}`;

                    setForm((prev) => ({
                      ...prev,
                      imovelId: String(it.codigo || ""),
                      enderecoExterno: enderecoFull, // opcional: salva o endereço escolhido
                    }));

                    setEnderecoQuery(enderecoFull);
                    setShowSugestoes(false);
                    setImoveisSugestoes([]);
                  }}
                >
                  <div className="vf-sugestao-title">
                    #{it.codigo} {it.finalidade ? `(${it.finalidade})` : ""}{" "}
                    {it.titulo || ""}
                  </div>
                  <div className="vf-sugestao-sub">
                    {it.endereco || ""}
                    {it.numero ? `, ${it.numero}` : ""}
                    {it.bairro ? ` - ${it.bairro}` : ""}
                    {it.cidade ? ` (${it.cidade}${it.uf ? `/${it.uf}` : ""})` : ""}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Imóvel (código) */}
        <div className="vf-group">
          <label>Imóvel (código)</label>
          <input
            type="text"
            value={form.imovelId}
            onChange={updateField("imovelId")}
            placeholder="Será preenchido ao selecionar um imóvel"
            required
          />
        </div>

        <div className="vf-group">
          <label>Data da Visita</label>
          <input
            type="date"
            value={form.dataVisita}
            onChange={updateField("dataVisita")}
            required
          />
        </div>

        {/* Cliente */}
        <div className="vf-group">
          <label>Cliente na Visita</label>
          <input
            type="text"
            value={form.clienteNome}
            onChange={updateField("clienteNome")}
            placeholder="Nome do cliente"
            required
          />
        </div>

        {/* Avaliações */}
        <div className="vf-section-title">Avaliações (1 a 10)</div>

        <div className="vf-group">
          <label>Localização</label>
          {renderNotaButtons("localizacao")}
        </div>

        <div className="vf-group">
          <label>Tamanho</label>
          {renderNotaButtons("tamanho")}
        </div>

        <div className="vf-group">
          <label>Planta do Imóvel</label>
          {renderNotaButtons("planta")}
        </div>

        <div className="vf-group">
          <label>Qualidade no acabamento</label>
          {renderNotaButtons("acabamento")}
        </div>

        <div className="vf-group">
          <label>Estado de conservação</label>
          {renderNotaButtons("conservacao")}
        </div>

        <div className="vf-group">
          <label>Condomínio e área comum</label>
          {renderNotaButtons("condominio")}
        </div>

        <div className="vf-group">
          <label>Preço (nota 1 a 10)</label>
          {renderNotaButtons("preco")}
        </div>

        <div className="vf-group">
          <label>Nota geral</label>
          {renderNotaButtons("notaGeral")}
        </div>

        <div className="vf-group">
          <label>Preço NOTA 10 (R$)</label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.precoNota10}
            onChange={updateField("precoNota10")}
            placeholder="0,00"
          />
        </div>

        {/* Papel na visita */}
        {/* <div className="vf-group">
          <label>Papel na visita</label>
          <div className="vf-toggle-row">
            <button
              type="button"
              className={`vf-toggle ${
                form.papelVisita === "Comprador" ? "vf-toggle-active" : ""
              }`}
              onClick={setRadio("papelVisita", "Comprador")}
            >
              Comprador
            </button>
            <button
              type="button"
              className={`vf-toggle ${
                form.papelVisita === "Interessado" ? "vf-toggle-active" : ""
              }`}
              onClick={setRadio("papelVisita", "Interessado")}
            >
              Interessado
            </button>
          </div>
        </div> */}

        {/* PDF */}
        <div className="vf-section-title">Anexo (PDF)</div>
        <div className="vf-group">
          <label>Anexar ficha da visita (PDF)</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) =>
              setPdfFile(e.target.files?.[0] || null)
            }
          />
        </div>

        {/* Proposta */}
        <div className="vf-group">
          <label>Proposta</label>
          <div className="vf-toggle-row">
            {["Sim", "Não", "Talvez"].map((opt) => (
              <button
                key={opt}
                type="button"
                className={`vf-toggle ${
                  form.proposta === opt ? "vf-toggle-active" : ""
                }`}
                onClick={setRadio("proposta", opt)}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        <button className="vf-submit" type="submit" disabled={loading}>
          {loading ? "Enviando..." : "Lançar Visita"}
        </button>
      </form>
    </div>
  );
}
