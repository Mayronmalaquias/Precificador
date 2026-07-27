// ApiForms.jsx
import React, { useState } from "react";
import "../assets/css/FormVisita.css";

const VISITAS_BASE_URL =
  "https://script.google.com/macros/s/AKfycbwULEpUbgyO1jcdO_xWachhfJoNptZMUjiMJz-csZHgfiKWJVPqRH6nvc0FTUBz9fyz8Q/exec";

const HISTORICO_BASE_URL =
  "https://script.google.com/macros/s/AKfycbzDDQSdBL3NnPOx_zszEJwtd1r_2RpKzRbAn3LcamBbHizuPnvrr5DLuLVESjd8xScJaQ/exec";

export default function ApiForms() {
  // --- Form Visitas ---
  const [visitaId, setVisitaId] = useState("");
  const [fone, setFone] = useState("");

  // --- Form Histórico ---
  const [imovelId, setImovelId] = useState("");
  const [corNome, setCorNome] = useState("");
  const [corTel, setCorTel] = useState("");
  const [corInsta, setCorInsta] = useState("");
  const [corDesc, setCorDesc] = useState("");

  function handleSubmitVisitas(e) {
    e.preventDefault();

    const url =
      `${VISITAS_BASE_URL}` +
      `?visitaId=${encodeURIComponent(visitaId)}` +
      `&fone=${encodeURIComponent(fone)}`;

    // abre na mesma aba ou em outra, como preferir:
    window.open(url, "_blank"); // nova aba
    // window.location.href = url; // mesma aba
  }

  function handleSubmitHistorico(e) {
    e.preventDefault();

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

        <div className="api-form-group">
          <label htmlFor="visitaId">Id da Visita</label>
          <input
            id="visitaId"
            type="text"
            value={visitaId}
            onChange={(e) => setVisitaId(e.target.value)}
            placeholder="Ex: e64cc50d"
            required
          />
        </div>

        <div className="api-form-group">
          <label htmlFor="fone">Telefone do Cliente (com DDI)</label>
          <input
            id="fone"
            type="text"
            value={fone}
            onChange={(e) => setFone(e.target.value)}
            placeholder="Ex: 61983040240"
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

        <div className="api-form-group">
          <label htmlFor="corNome">Nome do Corretor</label>
          <input
            id="corNome"
            type="text"
            value={corNome}
            onChange={(e) => setCorNome(e.target.value)}
            placeholder="Nome completo"
            required
          />
        </div>

        <div className="api-form-group">
          <label htmlFor="corTel">Telefone do Corretor</label>
          <input
            id="corTel"
            type="text"
            value={corTel}
            onChange={(e) => setCorTel(e.target.value)}
            placeholder="Telefone"
            required
          />
        </div>

        <div className="api-form-group">
          <label htmlFor="corInsta">Instagram do Corretor</label>
          <input
            id="corInsta"
            type="text"
            value={corInsta}
            onChange={(e) => setCorInsta(e.target.value)}
            placeholder="@seuinsta"
          />
        </div>

        <div className="api-form-group">
          <label htmlFor="corDesc">Descrição do Corretor</label>
          <textarea
            id="corDesc"
            value={corDesc}
            onChange={(e) => setCorDesc(e.target.value)}
            placeholder="Breve descrição / apresentação"
            rows={3}
          />
        </div>

        <button className="api-form-button" type="submit">
          Abrir link de Histórico
        </button>
      </form>
    </div>
  );
}
