// src/components/VisitaForm.jsx
import React, { useState, useEffect } from "react";
import "../assets/css/VisitaForm.css";

const API_BASE = "/api";
//const API_BASE = "http://localhost:5000"

// ─── Ícones simples (evita dependência extra) ─────────────────────────────────
const Icon = ({ ch, label }) => (
  <span role="img" aria-label={label} className="vf-section-icon">{ch}</span>
);
export default function VisitaForm() {
  const [successMessage, setSuccessMessage] = useState("");

  const [corretorInfo, setCorretorInfo] = useState({
    id: "", username: "", nome: "", telefone: "", instagram: "", descricao: "", email: "",
  });

  const [form, setForm] = useState({
    imovelId: "",
    dataVisita: new Date().toISOString().split("T")[0],
    parceiroExterno: "NAO",
    situacaoImovel: "CAPTACAO_PROPRIA",

    clienteNome: "",
    clienteTelefone: "",
    clienteEmail: "",

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

    localizacao: 10, tamanho: 10, planta: 10, acabamento: 10,
    conservacao: 10, condominio: 10, preco: 10, notaGeral: 10,
    precoNota10: "",
  });

  const [pdfFile, setPdfFile]   = useState(null);
  const [loading, setLoading]   = useState(false);

  const [enderecoQuery, setEnderecoQuery]         = useState("");
  const [imoveisSugestoes, setImoveisSugestoes]   = useState([]);
  const [loadingImoveis, setLoadingImoveis]       = useState(false);
  const [showSugestoes, setShowSugestoes]         = useState(false);

  const [clientesDoCorretor, setClientesDoCorretor]           = useState([]);
  const [clientesSugestoes, setClientesSugestoes]             = useState([]);
  const [loadingClientes, setLoadingClientes]                 = useState(false);
  const [showClientesSugestoes, setShowClientesSugestoes]     = useState(false);
  const [clienteSelecionado, setClienteSelecionado]           = useState(null);
  const [clienteStatus, setClienteStatus]                     = useState("NOVO");

  const isImovelNaoCaptado = form.situacaoImovel === "IMOVEL_NAO_CAPTADO";

  // ─── Carregar usuário do localStorage ──────────────────────────────────────
  useEffect(() => {
    const raw = localStorage.getItem("userData");
    if (!raw) return;
    try {
      const u = JSON.parse(raw);
      const id = u.idCorretor || u.id_corretor || u.codigoCorretor || u.codigo || u.id_usuarios || "";
      const corretor = {
        id, username: u.username || "", nome: u.nome || "",
        telefone: u.telefone || "", instagram: u.instagram || "",
        descricao: u.descricao || "", email: u.email || "",
      };
      setCorretorInfo(corretor);
      if (id) carregarClientesDoCorretor(id);
    } catch (e) { console.error(e); }
  }, []);

  // ─── Imóvel não captado → imovelId = "0000" ────────────────────────────────
  useEffect(() => {
    if (isImovelNaoCaptado) {
      setForm(p => ({ ...p, imovelId: "0000" }));
      setEnderecoQuery(""); setImoveisSugestoes([]); setShowSugestoes(false);
    } else if (form.imovelId === "0000") {
      setForm(p => ({ ...p, imovelId: "" }));
    }
  }, [isImovelNaoCaptado]);

  // ─── Filtro de clientes ao digitar ─────────────────────────────────────────
  useEffect(() => {
    const termo = (form.clienteNome || "").trim().toLowerCase();
    if (!termo) {
      setClientesSugestoes([]); setClienteSelecionado(null); setClienteStatus("NOVO"); return;
    }
    const filtrados = clientesDoCorretor.filter(c => (c.nome || "").toLowerCase().includes(termo));
    setClientesSugestoes(filtrados);
    const exato = clientesDoCorretor.find(c => (c.nome || "").trim().toLowerCase() === termo);
    if (exato) setClienteStatus("EXISTENTE");
    else { setClienteStatus("NOVO"); setClienteSelecionado(null); }
  }, [form.clienteNome, clientesDoCorretor]);

  // ─── Debounce busca de imóveis ──────────────────────────────────────────────
  useEffect(() => {
    if (isImovelNaoCaptado || !showSugestoes) return;
    const t = setTimeout(() => buscarImoveisPorEndereco(enderecoQuery), 350);
    return () => clearTimeout(t);
  }, [enderecoQuery, showSugestoes, isImovelNaoCaptado]);

  function updateField(field) {
    return e => setForm(p => ({ ...p, [field]: e.target.value }));
  }

  function setRadio(field, value) {
    return () => setForm(p => ({ ...p, [field]: value }));
  }

  // ─── API calls ─────────────────────────────────────────────────────────────
  async function carregarClientesDoCorretor(idCorretor) {
    setLoadingClientes(true);
    try {
      const r = await fetch(`${API_BASE}/clientes?id_corretor=${encodeURIComponent(idCorretor)}`);
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) setClientesDoCorretor(Array.isArray(d.lista) ? d.lista : []);
    } catch (e) { console.error(e); }
    finally { setLoadingClientes(false); }
  }

  function selecionarCliente(c) {
    setClienteSelecionado(c); setClienteStatus("EXISTENTE");
    setForm(p => ({ ...p, clienteNome: c.nome || "", clienteTelefone: c.telefone || "", clienteEmail: c.email || "" }));
    setShowClientesSugestoes(false); setClientesSugestoes([]);
  }

  async function buscarImoveisPorEndereco(query) {
    const q = (query || "").trim();
    if (isImovelNaoCaptado || q.length < 3) { setImoveisSugestoes([]); return; }
    setLoadingImoveis(true);
    try {
      const r = await fetch(`${API_BASE}/imoveis_busca?endereco=${encodeURIComponent(q)}`);
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) setImoveisSugestoes(Array.isArray(d.lista) ? d.lista : []);
    } catch (e) { console.error(e); }
    finally { setLoadingImoveis(false); }
  }

  async function uploadArquivoObrigatorio({ idCorretor, imovelId, dataVisita }) {
    const fd = new FormData();
    fd.append("file", pdfFile);
    fd.append("idCorretor", idCorretor || "");
    fd.append("imovelId", imovelId || "");
    fd.append("dataVisita", dataVisita || "");
    const r = await fetch(`${API_BASE}/upload_pdf`, { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok || !d.ok) throw new Error(d.error || "Erro ao enviar arquivo");
    return { drivePath: d.drivePath || "", driveLink: d.driveLink || "" };
  }

  async function criarClienteSeNecessario() {
    const nome     = (form.clienteNome || "").trim();
    const telefone = (form.clienteTelefone || "").trim();
    const email    = (form.clienteEmail || "").trim();
    if (!nome) throw new Error("Informe o nome do cliente.");
    if (clienteStatus === "EXISTENTE" && clienteSelecionado?.id_cliente) return clienteSelecionado.id_cliente;

    const r = await fetch(`${API_BASE}/clientes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, telefone, email, id_corretor: corretorInfo.id, corretor_email: corretorInfo.email || "" }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok || !d.ok) throw new Error(d.error || "Erro ao criar cliente");
    const novoId = d.id_cliente || null;
    const novoCliente = { id_cliente: novoId, nome, telefone, email };
    setClientesDoCorretor(prev => {
      const jaExiste = prev.some(c =>
        (c.nome||"").trim().toLowerCase() === nome.toLowerCase() &&
        (c.telefone||"").trim() === telefone &&
        (c.email||"").trim().toLowerCase() === email.toLowerCase()
      );
      if (jaExiste) return prev;
      return [...prev, novoCliente].sort((a,b) => (a.nome||"").localeCompare(b.nome||"", "pt-BR", { sensitivity:"base" }));
    });
    setClienteSelecionado(novoCliente); setClienteStatus("EXISTENTE");
    return novoId;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!corretorInfo.id) { alert("Erro: faça login novamente."); return; }
    if (!pdfFile)         { alert("Selecione uma foto ou PDF antes de enviar."); return; }
    if (!form.clienteNome.trim()) { alert("Informe o nome do cliente."); return; }
    setLoading(true);
    try {
      const idCliente = await criarClienteSeNecessario();
      const { drivePath, driveLink } = await uploadArquivoObrigatorio({
        idCorretor: corretorInfo.id, imovelId: form.imovelId, dataVisita: form.dataVisita,
      });
      const payload = {
        ...form,
        imovelId: isImovelNaoCaptado ? "0000" : form.imovelId,
        idCorretor: corretorInfo.id, idCliente: idCliente || "",
        anexoFichaVisita: drivePath, linkImagem: driveLink,
        corretor: corretorInfo.nome || corretorInfo.username,
        corretorEmail: corretorInfo.email || "",
        telefoneCorretor: corretorInfo.telefone,
        instagramCorretor: corretorInfo.instagram,
        descricaoCorretor: corretorInfo.descricao,
        avaliacoes: {
          localizacao: Number(form.localizacao), tamanho: Number(form.tamanho),
          planta: Number(form.planta), acabamento: Number(form.acabamento),
          conservacao: Number(form.conservacao), condominio: Number(form.condominio),
          preco: Number(form.preco), notaGeral: Number(form.notaGeral),
        },
      };
      const r = await fetch(`${API_BASE}/visitas`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || !d.ok) throw new Error(d.error || "Erro ao registrar visita");
      setSuccessMessage(`Visita lançada com sucesso! ID: ${d.id_visita}`);
      setTimeout(() => setSuccessMessage(""), 2500);
      // Reset
      setForm({ imovelId:"", dataVisita: new Date().toISOString().split("T")[0], parceiroExterno:"NAO", situacaoImovel:"CAPTACAO_PROPRIA", clienteNome:"", clienteTelefone:"", clienteEmail:"", proposta:"Talvez", papelVisita:"Interessado", enderecoExterno:"", parceiroNome:"", parceiroImobiliaria:"", clienteAssinanteNome:"", clienteAssinanteTelefone:"", clienteAssinanteEmail:"", assinatura:"", audioDescricaoClienteVisita:"", linkAudio:"", localizacao:10, tamanho:10, planta:10, acabamento:10, conservacao:10, condominio:10, preco:10, notaGeral:10, precoNota10:"" });
      setEnderecoQuery(""); setImoveisSugestoes([]); setShowSugestoes(false); setPdfFile(null);
      setClienteSelecionado(null); setClienteStatus("NOVO"); setClientesSugestoes([]); setShowClientesSugestoes(false);
    } catch (err) {
      console.error(err);
      alert(err.message || "Erro inesperado. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  // ─── Botões de nota 1-10 com gradiente de cor ──────────────────────────────
  function renderNotaButtons(field) {
    const value = Number(form[field]);
    const legendas = { 1:"Péssimo", 2:"Muito ruim", 3:"Ruim", 4:"Regular", 5:"Médio", 6:"Razoável", 7:"Bom", 8:"Muito bom", 9:"Ótimo", 10:"Excelente" };
    return (
      <>
        <div className="nota-grid">
          {Array.from({ length: 10 }, (_, i) => i + 1).map(n => (
            <button
              key={n}
              type="button"
              data-nota={String(n)}
              className={`nota-btn${value === n ? " nota-btn-active" : ""}`}
              onClick={() => setForm(p => ({ ...p, [field]: n }))}
              aria-label={`Nota ${n}: ${legendas[n]}`}
              aria-pressed={value === n}
            >
              {n}
            </button>
          ))}
        </div>
        {value > 0 && (
          <div className="nota-legenda">
            Selecionado: <strong>{value} — {legendas[value]}</strong>
          </div>
        )}
      </>
    );
  }

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="visita-form-wrapper">
      {successMessage && (
        <div className="vf-success-toast" role="status" aria-live="polite">
          <div className="vf-success-check">✓</div>
          <div className="vf-success-text">{successMessage}</div>
        </div>
      )}
      <form className="visita-form" onSubmit={handleSubmit} noValidate>

        {/* Cabeçalho */}
        <div className="vf-header">
          <h2>🏠 Lançar Visita</h2>
          <p>Preencha os campos abaixo. Os marcados com <span style={{color:"#e1005b"}}>*</span> são obrigatórios.</p>
        </div>

        {/* ── SEÇÃO 1: Corretor ──────────────────────────────────────────── */}
        <div className="vf-section">
          <div className="vf-section-title">
            <Icon ch="👤" label="corretor" /> Corretor
          </div>
          <div className="vf-group">
            <label>Você está logado como</label>
            <div className="vf-readonly">
              🏷️ {(corretorInfo.id ? `${corretorInfo.id} — ` : "") + (corretorInfo.nome || corretorInfo.username || "Não identificado")}
            </div>
          </div>
        </div>

        {/* ── SEÇÃO 2: Imóvel ───────────────────────────────────────────── */}
        <div className="vf-section">
          <div className="vf-section-title">
            <Icon ch="🏢" label="imovel" /> Imóvel
          </div>

          {/* Situação do imóvel */}
          <div className="vf-group">
            <label>O imóvel é da nossa captação?<span className="vf-obrigatorio">*</span></label>
            <div className="vf-toggle-row">
              {[
                { val: "CAPTACAO_PROPRIA",   label: "Sim, captação própria" },
                { val: "CAPTACAO_PARCEIRO",  label: "Sim, captação parceiro" },
                { val: "IMOVEL_NAO_CAPTADO", label: "Não, imóvel externo" },
              ].map(op => (
                <button
                  key={op.val}
                  type="button"
                  className={`vf-toggle${form.situacaoImovel === op.val ? " vf-toggle-active" : ""}`}
                  onClick={setRadio("situacaoImovel", op.val)}
                  aria-pressed={form.situacaoImovel === op.val}
                >
                  {op.label}
                </button>
              ))}
            </div>
          </div>

          {/* Parceiro externo */}
          <div className="vf-group">
            <label>Tem parceiro externo na visita?<span className="vf-obrigatorio">*</span></label>
            <div className="vf-toggle-row">
              <button
                type="button"
                className={`vf-toggle vf-toggle-no${form.parceiroExterno === "NAO" ? " vf-toggle-active" : ""}`}
                onClick={setRadio("parceiroExterno", "NAO")}
                aria-pressed={form.parceiroExterno === "NAO"}
              >
                ✗ Não
              </button>
              <button
                type="button"
                className={`vf-toggle vf-toggle-yes${form.parceiroExterno === "SIM" ? " vf-toggle-active" : ""}`}
                onClick={setRadio("parceiroExterno", "SIM")}
                aria-pressed={form.parceiroExterno === "SIM"}
              >
                ✓ Sim
              </button>
            </div>
          </div>

          {/* Busca de imóvel ou endereço manual */}
          {!isImovelNaoCaptado ? (
            <div className="vf-group">
              <label htmlFor="buscaImovel">Buscar imóvel pelo endereço<span className="vf-obrigatorio">*</span></label>
              <input
                id="buscaImovel"
                type="text"
                value={enderecoQuery}
                onChange={e => { setEnderecoQuery(e.target.value); setShowSugestoes(true); }}
                onFocus={() => setShowSugestoes(true)}
                placeholder="Ex: SQS 308, W3, Rua 12..."
                autoComplete="off"
              />
              {loadingImoveis && <div className="vf-hint">⏳ Buscando imóveis...</div>}
              {showSugestoes && imoveisSugestoes.length > 0 && (
                <div className="vf-sugestoes">
                  {imoveisSugestoes.map(it => (
                    <button
                      type="button"
                      key={`${it.codigo}-${it.finalidade||""}`}
                      className="vf-sugestao-item"
                      onClick={() => {
                        const end = `${it.endereco||""}${it.numero ? `, ${it.numero}` : ""}`;
                        setForm(p => ({ ...p, imovelId: String(it.codigo||""), enderecoExterno: end }));
                        setEnderecoQuery(end); setShowSugestoes(false); setImoveisSugestoes([]);
                      }}
                    >
                      <div className="vf-sugestao-sub">
                      {it.endereco || ""}
                      {it.numero ? `, ${it.numero}` : ""}
                      {it.bairro ? ` — ${it.bairro}` : ""}
                      {it.cidade ? ` (${it.cidade}${it.uf ? `/${it.uf}` : ""})` : ""}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="vf-group">
              <label htmlFor="enderecoManual">Endereço do imóvel<span className="vf-obrigatorio">*</span></label>
              <input
                id="enderecoManual"
                type="text"
                value={form.enderecoExterno}
                onChange={updateField("enderecoExterno")}
                placeholder="Digite o endereço completo"
                required
              />
            </div>
          )}

          {!isImovelNaoCaptado && (
            <div className="vf-group">
              <label htmlFor="imovelCodigo">Código do imóvel<span className="vf-obrigatorio">*</span></label>
              <input
                id="imovelCodigo"
                type="text"
                value={form.imovelId}
                onChange={updateField("imovelId")}
                placeholder="Preenchido ao selecionar acima"
                required
              />
            </div>
          )}

          {/* Data */}
          <div className="vf-group">
            <label htmlFor="dataVisita">Data da visita<span className="vf-obrigatorio">*</span></label>
            <input
              id="dataVisita"
              type="date"
              value={form.dataVisita}
              onChange={updateField("dataVisita")}
              required
            />
          </div>
        </div>

        {/* ── SEÇÃO 3: Cliente ──────────────────────────────────────────── */}
        <div className="vf-section">
          <div className="vf-section-title">
            <Icon ch="🧑" label="cliente" /> Cliente
          </div>

          <div className="vf-group">
            <label htmlFor="clienteNome">Nome do cliente<span className="vf-obrigatorio">*</span></label>
            <input
              id="clienteNome"
              type="text"
              value={form.clienteNome}
              onChange={e => {
                const nome = e.target.value;
                setForm(p => ({ ...p, clienteNome: nome, ...(nome.trim() ? {} : { clienteTelefone:"", clienteEmail:"" }) }));
                setShowClientesSugestoes(true); setClienteSelecionado(null);
              }}
              onFocus={() => setShowClientesSugestoes(true)}
              placeholder="Nome completo do cliente"
              autoComplete="off"
              required
            />
            {loadingClientes && <div className="vf-hint">⏳ Carregando clientes...</div>}
            {!!form.clienteNome && (
              <span className={`vf-badge ${clienteStatus === "EXISTENTE" ? "vf-badge--existente" : "vf-badge--novo"}`}>
                {clienteStatus === "EXISTENTE" ? "✓ Cliente já cadastrado" : "✦ Novo cliente"}
              </span>
            )}
            {showClientesSugestoes && clientesSugestoes.length > 0 && (
              <div className="vf-sugestoes">
                {clientesSugestoes.map(c => (
                  <button type="button" key={c.id_cliente} className="vf-sugestao-item" onClick={() => selecionarCliente(c)}>
                    <div className="vf-sugestao-title">{c.nome}</div>
                    <div className="vf-sugestao-sub">{c.telefone || "Sem telefone"}{c.email ? ` — ${c.email}` : ""}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="vf-group">
            <label htmlFor="clienteTelefone">
              Telefone do cliente
              <span style={{fontWeight:400, color:"#71717a", fontSize:"0.88rem"}}> (opcional)</span>
            </label>
            <input
              id="clienteTelefone"
              type="tel"
              value={form.clienteTelefone}
              onChange={updateField("clienteTelefone")}
              placeholder="(00) 00000-0000"
            />
          </div>

          <div className="vf-group">
            <label htmlFor="clienteEmail">
              E-mail do cliente
              <span style={{fontWeight:400, color:"#71717a", fontSize:"0.88rem"}}> (opcional)</span>
            </label>
            <input
              id="clienteEmail"
              type="email"
              value={form.clienteEmail}
              onChange={updateField("clienteEmail")}
              placeholder="email@exemplo.com"
            />
          </div>
        </div>

        {/* ── SEÇÃO 4: Avaliações ───────────────────────────────────────── */}
        <div className="vf-section">
          <div className="vf-section-title">
            <Icon ch="⭐" label="avaliacoes" /> Avaliações do Imóvel
          </div>
          <div className="vf-hint" style={{marginBottom:14}}>
            Toque no número para dar a nota. 1 = pior, 10 = melhor.
          </div>

          {[
            { field:"localizacao",  label:"Localização" },
            { field:"tamanho",      label:"Tamanho" },
            { field:"planta",       label:"Planta do imóvel" },
            { field:"acabamento",   label:"Qualidade do acabamento" },
            { field:"conservacao",  label:"Estado de conservação" },
            { field:"condominio",   label:"Condomínio e área comum" },
            { field:"preco",        label:"Preço" },
            { field:"notaGeral",    label:"Nota geral" },
          ].map(({ field, label }) => (
            <div className="vf-group" key={field}>
              <label>{label}</label>
              {renderNotaButtons(field)}
            </div>
          ))}

          <div className="vf-group">
            <label htmlFor="precoNota10">
              Qual seria o preço ideal (nota 10)? <span style={{fontWeight:400,color:"#71717a",fontSize:"0.88rem"}}>(R$, opcional)</span>
            </label>
            <input
              id="precoNota10"
              type="number"
              min="0"
              step="1000"
              value={form.precoNota10}
              onChange={updateField("precoNota10")}
              placeholder="Ex: 450000"
            />
          </div>
        </div>

        {/* ── SEÇÃO 5: Proposta ─────────────────────────────────────────── */}
        <div className="vf-section">
          <div className="vf-section-title">
            <Icon ch="📋" label="proposta" /> Proposta
          </div>
          <div className="vf-group">
            <label>O cliente vai fazer proposta?<span className="vf-obrigatorio">*</span></label>
            <div className="vf-toggle-row">
              {[
                { val:"Sim",    cls:"vf-toggle-yes", icon:"✓" },
                { val:"Não",    cls:"vf-toggle-no",  icon:"✗" },
                { val:"Talvez", cls:"",               icon:"?" },
              ].map(op => (
                <button
                  key={op.val}
                  type="button"
                  className={`vf-toggle ${op.cls}${form.proposta === op.val ? " vf-toggle-active" : ""}`}
                  onClick={setRadio("proposta", op.val)}
                  aria-pressed={form.proposta === op.val}
                >
                  {op.icon} {op.val}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── SEÇÃO 6: Foto / PDF ───────────────────────────────────────── */}
        <div className="vf-section">
          <div className="vf-section-title">
            <Icon ch="📸" label="foto" /> Foto ou PDF
          </div>
          <div className="vf-group">
            <label>Tire uma foto ou anexe o PDF<span className="vf-obrigatorio">*</span></label>
            <label className={`vf-upload-label${pdfFile ? " has-file" : ""}`}>
              <span className="vf-upload-icon">{pdfFile ? "✅" : "📷"}</span>
              <span>
                {pdfFile
                  ? `Arquivo: ${pdfFile.name}`
                  : "Toque aqui para tirar foto ou escolher arquivo"}
              </span>
              <input
                type="file"
                className="vf-upload-input"
                accept="image/*,application/pdf"
                capture="environment"
                required
                onChange={e => setPdfFile(e.target.files?.[0] || null)}
              />
            </label>
            {!pdfFile && (
              <div className="vf-hint">📌 Obrigatório: anexe a ficha assinada pelo cliente.</div>
            )}
          </div>
        </div>

        {/* ── Botão final ───────────────────────────────────────────────── */}
        <button className="vf-submit" type="submit" disabled={loading}>
          {loading ? "⏳ Enviando visita..." : "✅ Lançar Visita"}
        </button>

      </form>
    </div>
  );
}