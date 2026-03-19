// src/components/VisitaForm.jsx
import React, { useState, useEffect } from "react";
import "../assets/css/VisitaForm.css";

// const API_BASE = "http://localhost:5000/visitas";
const API_BASE = "/api";
//const API_BASE = "http://localhost:5000";

export default function VisitaForm() {
  const [corretorInfo, setCorretorInfo] = useState({
    id: "",
    username: "",
    nome: "",
    telefone: "",
    instagram: "",
    descricao: "",
    email: "",
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

    localizacao: 10,
    tamanho: 10,
    planta: 10,
    acabamento: 10,
    conservacao: 10,
    condominio: 10,
    preco: 10,
    notaGeral: 10,

    precoNota10: "",
  });

  const [pdfFile, setPdfFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const [enderecoQuery, setEnderecoQuery] = useState("");
  const [imoveisSugestoes, setImoveisSugestoes] = useState([]);
  const [loadingImoveis, setLoadingImoveis] = useState(false);
  const [showSugestoes, setShowSugestoes] = useState(false);

  const [clientesDoCorretor, setClientesDoCorretor] = useState([]);
  const [clientesSugestoes, setClientesSugestoes] = useState([]);
  const [loadingClientes, setLoadingClientes] = useState(false);
  const [showClientesSugestoes, setShowClientesSugestoes] = useState(false);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [clienteStatus, setClienteStatus] = useState("NOVO"); // EXISTENTE | NOVO

  const isImovelNaoCaptado = form.situacaoImovel === "IMOVEL_NAO_CAPTADO";

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

        const corretor = {
          id: corretorId,
          username: userData.username || "",
          nome: userData.nome || "",
          telefone: userData.telefone || "",
          instagram: userData.instagram || "",
          descricao: userData.descricao || "",
          email: userData.email || "",
        };

        setCorretorInfo(corretor);

        if (corretorId) {
          carregarClientesDoCorretor(corretorId);
        }
      } catch (e) {
        console.error("Erro ao ler userData do localStorage", e);
      }
    }
  }, []);

  useEffect(() => {
    if (isImovelNaoCaptado) {
      setForm((prev) => ({
        ...prev,
        imovelId: "0000",
      }));
      setEnderecoQuery("");
      setImoveisSugestoes([]);
      setShowSugestoes(false);
    } else if (form.imovelId === "0000") {
      setForm((prev) => ({
        ...prev,
        imovelId: "",
      }));
    }
  }, [isImovelNaoCaptado]);

  useEffect(() => {
    const termo = (form.clienteNome || "").trim().toLowerCase();

    if (!termo) {
      setClientesSugestoes([]);
      setClienteSelecionado(null);
      setClienteStatus("NOVO");
      return;
    }

    const filtrados = clientesDoCorretor.filter((c) =>
      (c.nome || "").toLowerCase().includes(termo)
    );

    setClientesSugestoes(filtrados);

    const matchExato = clientesDoCorretor.find(
      (c) => (c.nome || "").trim().toLowerCase() === termo
    );

    if (matchExato) {
      setClienteStatus("EXISTENTE");
    } else {
      setClienteStatus("NOVO");
      setClienteSelecionado(null);
    }
  }, [form.clienteNome, clientesDoCorretor]);

  useEffect(() => {
    if (isImovelNaoCaptado) return;
    if (!showSugestoes) return;

    const t = setTimeout(() => {
      buscarImoveisPorEndereco(enderecoQuery);
    }, 350);

    return () => clearTimeout(t);
  }, [enderecoQuery, showSugestoes, isImovelNaoCaptado]);

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

  async function carregarClientesDoCorretor(idCorretor) {
    if (!idCorretor) return;

    setLoadingClientes(true);
    try {
      const resp = await fetch(
        `${API_BASE}/clientes?id_corretor=${encodeURIComponent(idCorretor)}`,
        { method: "GET" }
      );

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao buscar clientes");
      }

      const lista = Array.isArray(data.lista) ? data.lista : [];
      setClientesDoCorretor(lista);
    } catch (e) {
      console.error(e);
      setClientesDoCorretor([]);
    } finally {
      setLoadingClientes(false);
    }
  }

  function selecionarCliente(cliente) {
    setClienteSelecionado(cliente);
    setClienteStatus("EXISTENTE");

    setForm((prev) => ({
      ...prev,
      clienteNome: cliente.nome || "",
      clienteTelefone: cliente.telefone || "",
      clienteEmail: cliente.email || "",
    }));

    setShowClientesSugestoes(false);
    setClientesSugestoes([]);
  }

  async function buscarImoveisPorEndereco(query) {
    const q = (query || "").trim();

    if (isImovelNaoCaptado) {
      setImoveisSugestoes([]);
      return;
    }

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

  async function uploadArquivoObrigatorio({ idCorretor, imovelId, dataVisita }) {
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
      throw new Error(data.error || "Erro ao enviar arquivo");
    }

    return {
      drivePath: data.drivePath || "",
      driveLink: data.driveLink || "",
    };
  }

  async function criarClienteSeNecessario() {
    const nome = (form.clienteNome || "").trim();
    const telefone = (form.clienteTelefone || "").trim();
    const email = (form.clienteEmail || "").trim();

    if (!nome) {
      throw new Error("Informe o nome do cliente.");
    }

    if (clienteStatus === "EXISTENTE" && clienteSelecionado?.id_cliente) {
      return clienteSelecionado.id_cliente;
    }

    const resp = await fetch(`${API_BASE}/clientes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome,
        telefone,
        email,
        id_corretor: corretorInfo.id,
        corretor_email: corretorInfo.email || "",
      }),
    });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok || !data.ok) {
      throw new Error(data.error || "Erro ao criar cliente");
    }

    const novoId = data.id_cliente || null;

    // Atualiza cache local para o autocomplete já reconhecer depois
    const novoCliente = {
      id_cliente: novoId,
      nome,
      telefone,
      email,
    };

    setClientesDoCorretor((prev) => {
      const jaExiste = prev.some(
        (c) =>
          (c.nome || "").trim().toLowerCase() === nome.toLowerCase() &&
          (c.telefone || "").trim() === telefone &&
          (c.email || "").trim().toLowerCase() === email.toLowerCase()
      );
      if (jaExiste) return prev;
      return [...prev, novoCliente].sort((a, b) =>
        (a.nome || "").localeCompare(b.nome || "", "pt-BR", { sensitivity: "base" })
      );
    });

    setClienteSelecionado(novoCliente);
    setClienteStatus("EXISTENTE");

    return novoId;
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!corretorInfo.id) {
      alert("Erro: ID/Código do corretor não carregado. Faça login novamente.");
      return;
    }

    if (!pdfFile) {
      alert("O anexo é obrigatório. Selecione uma foto ou PDF antes de enviar.");
      return;
    }

    if (!form.clienteNome.trim()) {
      alert("Informe o nome do cliente.");
      return;
    }

    setLoading(true);
    try {
      const idCliente = await criarClienteSeNecessario();

      const { drivePath, driveLink } = await uploadArquivoObrigatorio({
        idCorretor: corretorInfo.id,
        imovelId: form.imovelId,
        dataVisita: form.dataVisita,
      });

      const payload = {
        ...form,
        imovelId: isImovelNaoCaptado ? "0000" : form.imovelId,
        idCorretor: corretorInfo.id,
        idCliente: idCliente || "",

        anexoFichaVisita: drivePath,
        linkImagem: driveLink,

        corretor: corretorInfo.nome || corretorInfo.username,
        corretorEmail: corretorInfo.email || "",
        telefoneCorretor: corretorInfo.telefone,
        instagramCorretor: corretorInfo.instagram,
        descricaoCorretor: corretorInfo.descricao,

        clienteNome: form.clienteNome,
        clienteTelefone: form.clienteTelefone,
        clienteEmail: form.clienteEmail,

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

      const resp = await fetch(`${API_BASE}/visitas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Erro ao registrar visita");
      }

      alert(`Visita lançada com sucesso! Id: ${data.id_visita}`);

      setForm({
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

        localizacao: 10,
        tamanho: 10,
        planta: 10,
        acabamento: 10,
        conservacao: 10,
        condominio: 10,
        preco: 10,
        notaGeral: 10,

        precoNota10: "",
      });

      setEnderecoQuery("");
      setImoveisSugestoes([]);
      setShowSugestoes(false);
      setPdfFile(null);

      setClienteSelecionado(null);
      setClienteStatus("NOVO");
      setClientesSugestoes([]);
      setShowClientesSugestoes(false);
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

        <div className="vf-group">
          <label>Corretor</label>
          <div className="vf-readonly">
            {(corretorInfo.id ? `${corretorInfo.id} - ` : "") +
              (corretorInfo.nome || corretorInfo.username || "Não identificado")}
          </div>
        </div>

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
              Imóvel não captado pela 61
            </button>
          </div>
        </div>

        {!isImovelNaoCaptado ? (
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

            {loadingImoveis && <div className="vf-hint">Buscando...</div>}

            {showSugestoes && imoveisSugestoes.length > 0 && (
              <div className="vf-sugestoes">
                {imoveisSugestoes.map((it) => (
                  <button
                    type="button"
                    key={`${it.codigo}-${it.finalidade || ""}`}
                    className="vf-sugestao-item"
                    onClick={() => {
                      const enderecoFull = `${it.endereco || ""}${
                        it.numero ? `, ${it.numero}` : ""
                      }`;

                      setForm((prev) => ({
                        ...prev,
                        imovelId: String(it.codigo || ""),
                        enderecoExterno: enderecoFull,
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
        ) : (
          <div className="vf-group">
            <label>Endereço do imóvel</label>
            <input
              type="text"
              value={form.enderecoExterno}
              onChange={updateField("enderecoExterno")}
              placeholder="Digite o endereço manualmente"
              required
            />
          </div>
        )}

        {!isImovelNaoCaptado && (
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
        )}

        <div className="vf-group">
          <label>Data da Visita</label>
          <input
            type="date"
            value={form.dataVisita}
            onChange={updateField("dataVisita")}
            required
          />
        </div>

        <div className="vf-group">
          <label>Cliente na Visita</label>
          <input
            type="text"
            value={form.clienteNome}
            onChange={(e) => {
              const nome = e.target.value;

              setForm((prev) => ({
                ...prev,
                clienteNome: nome,
              }));

              setShowClientesSugestoes(true);
              setClienteSelecionado(null);

              if (!nome.trim()) {
                setForm((prev) => ({
                  ...prev,
                  clienteTelefone: "",
                  clienteEmail: "",
                }));
              }
            }}
            onFocus={() => setShowClientesSugestoes(true)}
            placeholder="Digite o nome do cliente"
            required
          />

          {loadingClientes && (
            <div className="vf-hint">Carregando clientes...</div>
          )}

          {!!form.clienteNome && (
            <div className="vf-hint">
              Status do cliente:{" "}
              <strong>
                {clienteStatus === "EXISTENTE"
                  ? "Cliente já cadastrado"
                  : "Novo cliente"}
              </strong>
            </div>
          )}

          {showClientesSugestoes && clientesSugestoes.length > 0 && (
            <div className="vf-sugestoes">
              {clientesSugestoes.map((cliente) => (
                <button
                  type="button"
                  key={cliente.id_cliente}
                  className="vf-sugestao-item"
                  onClick={() => selecionarCliente(cliente)}
                >
                  <div className="vf-sugestao-title">{cliente.nome}</div>
                  <div className="vf-sugestao-sub">
                    {cliente.telefone || "Sem telefone"}
                    {cliente.email ? ` - ${cliente.email}` : ""}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="vf-group">
          <label>Telefone do Cliente</label>
          <input
            type="text"
            value={form.clienteTelefone}
            onChange={updateField("clienteTelefone")}
            placeholder="Telefone do cliente"
          />
        </div>

        <div className="vf-group">
          <label>E-mail do Cliente</label>
          <input
            type="email"
            value={form.clienteEmail}
            onChange={updateField("clienteEmail")}
            placeholder="email@exemplo.com"
          />
        </div>

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

        <div className="vf-section-title">Anexo (Foto da Câmera ou PDF)</div>
        <div className="vf-group">
          <label>Tirar foto ou anexar PDF</label>
          <input
            type="file"
            accept="image/*,application/pdf"
            capture="environment"
            required
            onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
          />
          {pdfFile && (
            <div className="vf-hint">
              Arquivo selecionado: <strong>{pdfFile.name}</strong>
            </div>
          )}
        </div>

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