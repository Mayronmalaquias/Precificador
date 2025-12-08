import React, { useState, useEffect } from "react";
import "../assets/css/AppVisita.css";

const VISITAS_BASE_URL =
  "https://script.google.com/macros/s/AKfycbwULEpUbgyO1jcdO_xWachhfJoNptZMUjiMJz-csZHgfiKWJVPqRH6nvc0FTUBz9fyz8Q/exec";

const HISTORICO_BASE_URL =
  "https://script.google.com/macros/s/AKfycbzDDQSdBL3NnPOx_zszEJwtd1r_2RpKzRbAn3LcamBbHizuPnvrr5DLuLVESjd8xScJaQ/exec";

export default function ApiForms() {
  // --- Dados que o usuário PREENCHE (IDs únicos) ---
  const [visitaId, setVisitaId] = useState("");
  const [imovelId, setImovelId] = useState(""); // Deve ser preenchido manualmente
 
  // --- Dados do Usuário Logado (Carregados Ocultamente) ---
  const [corTel, setCorTel] = useState("");
  const [corNome, setCorNome] = useState("");
  const [corInsta, setCorInsta] = useState("");
  const [corDesc, setCorDesc] = useState("");


  // 🔑 Efeito para carregar os dados do usuário logado do localStorage
  useEffect(() => {
    const userDataString = localStorage.getItem('userData');
    if (userDataString) {
      try {
        const userData = JSON.parse(userDataString);
        
        // Dados para o formulário de VISITAS
        if (userData.telefone) setCorTel(userData.telefone);
        
        // Dados para o formulário de HISTÓRICO
        if (userData.nome) setCorNome(userData.nome);
        if (userData.instagram) setCorInsta(userData.instagram);
        if (userData.descricao) setCorDesc(userData.descricao);

      } catch (error) {
        console.error("Erro ao fazer parse dos dados do usuário:", error);
      }
    }
  }, []);


  function handleSubmitVisitas(e) {
    e.preventDefault();

    // 1. O fone agora vem do estado 'corTel' (que é o telefone do usuário logado)
    if (!corTel) {
        alert("Erro: Telefone do corretor não carregado. Faça login novamente.");
        return;
    }
    
    const url =
      `${VISITAS_BASE_URL}` +
      `?visitaId=${encodeURIComponent(visitaId)}` +
      `&fone=${encodeURIComponent(corTel)}`; // USANDO corTel (telefone logado)

    window.open(url, "_blank");
  }

  function handleSubmitHistorico(e) {
    e.preventDefault();

    // 1. Verifica se os dados do corretor foram carregados
    if (!corNome || !corTel) {
        alert("Erro: Dados do corretor não carregados. Faça login novamente.");
        return;
    }
    
    // 2. Todos os dados são anexados à URL, usando os dados preenchidos no estado
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
      {/* Form VISITAS - SOMENTE ID DA VISITA */}
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
        {/* Campo de Telefone REMOVIDO */}

        <button className="api-form-button" type="submit">
          Abrir link de Visita
        </button>
      </form>

---

      {/* Form HISTÓRICO - SOMENTE ID DO IMÓVEL */}
      <form className="api-form" onSubmit={handleSubmitHistorico}>
        <h2 className="api-form-title">Chamada de Histórico</h2>

        <div className="api-form-group">
          <label htmlFor="imovelId">Id do Imóvel</label>
          <input
            id="imovelId"
            type="text"
            value={imovelId} 
            onChange={(e) => setImovelId(e.target.value)} // Permite digitar o ID
            placeholder="Ex: IMV-001"
            required
          />
        </div>

        {/* CAMPOS DE CORRETOR REMOVIDOS */}

        <button className="api-form-button" type="submit">
          Abrir link de Histórico
        </button>
      </form>
    </div>
  );
}