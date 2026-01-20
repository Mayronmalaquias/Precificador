// src/components/VisitaForm.jsx
import React, { useState, useEffect } from "react";
import "../assets/css/VisitaForm.css";

const API_BASE = "http://52.67.252.192:5000/visitas";

export default function VisitaForm() {
  const [corretorInfo, setCorretorInfo] = useState({
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

    // notas 1–10
    localizacao: 10,
    tamanho: 10,
    planta: 10,
    acabamento: 10,
    conservacao: 10,
    condominio: 10,
    notaGeral: 10,

    precoNota10: "", // número (R$)
  });

  const [loading, setLoading] = useState(false);

  // Carrega dados do usuário logado
  useEffect(() => {
    const userDataString = localStorage.getItem("userData");
    if (userDataString) {
      try {
        const userData = JSON.parse(userDataString);
        setCorretorInfo({
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

  async function handleSubmit(e) {
    e.preventDefault();

    if (!corretorInfo.telefone) {
      alert("Erro: telefone do corretor não carregado. Faça login novamente.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        ...form,
        // dados do corretor
        corretor: corretorInfo.nome || corretorInfo.username,
        corretorEmail: corretorInfo.email || "",
        telefoneCorretor: corretorInfo.telefone,
        instagramCorretor: corretorInfo.instagram,
        descricaoCorretor: corretorInfo.descricao,
        avaliacoes: {
          localizacao: Number(form.localizacao),
          tamanho: Number(form.tamanho),
          planta: Number(form.planta),
          acabamento: Number(form.acabamento),
          conservacao: Number(form.conservacao),
          condominio: Number(form.condominio),
          notaGeral: Number(form.notaGeral),
        },
      };

      const resp = await fetch(API_BASE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();

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
      }));
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  // helper para renderizar os botões 1–10
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
            {corretorInfo.nome || corretorInfo.username || "Não identificado"}
          </div>
        </div>

        {/* Parceiro Externo */}
        <div className="vf-group">
          <label>Visita com Parceiro Externo?</label>
          <div className="vf-toggle-row">
            <button
              type="button"
              className={`vf-toggle ${
                form.parceiroExterno === "NAO" ? "vf-toggle-active vf-toggle-no" : ""
              }`}
              onClick={setRadio("parceiroExterno", "NAO")}
            >
              NÃO
            </button>
            <button
              type="button"
              className={`vf-toggle ${
                form.parceiroExterno === "SIM" ? "vf-toggle-active vf-toggle-yes" : ""
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

        {/* Imóvel + Data */}
        <div className="vf-group">
          <label>Imóvel (Id)</label>
          <input
            type="text"
            value={form.imovelId}
            onChange={updateField("imovelId")}
            placeholder="Ex: COD-1234"
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

        {/* Cliente na Visita */}
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

        {/* Notas 1–10 */}
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
          <label>Nota geral</label>
          {renderNotaButtons("notaGeral")}
        </div>

        {/* Preço Nota 10 */}
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
        <div className="vf-group">
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
        </div>

        <button className="vf-submit" type="submit" disabled={loading}>
          {loading ? "Enviando..." : "Lançar Visita"}
        </button>
      </form>
    </div>
  );
}
