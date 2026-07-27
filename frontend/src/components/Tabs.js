import React, { useState } from 'react';
import Formulario from './Formulario';
import Mapa from './Mapa';
import Relatorio from './Relatorio';

function Tabs() {
  const [abaAtiva, setAbaAtiva] = useState('formulario');

  const mudarAba = (novaAba) => {
    setAbaAtiva(novaAba);
  };

  return (
    <>
      <div className="tabs">
        <div
          className={`tab ${abaAtiva === 'formulario' ? 'active-tab' : ''}`}
          onClick={() => mudarAba('formulario')}
        >
          Formulário
        </div>
        <div
          className={`tab ${abaAtiva === 'mapa' ? 'active-tab' : ''}`}
          onClick={() => mudarAba('mapa')}
        >
          Mapa
        </div>
        <div
          className={`tab ${abaAtiva === 'relatorio' ? 'active-tab' : ''}`}
          onClick={() => mudarAba('relatorio')}
        >
          Relatório
        </div>
      </div>

      {abaAtiva === 'formulario' && <Formulario />}
      {abaAtiva === 'mapa' && <Mapa />}
      {abaAtiva === 'relatorio' && <Relatorio />}
    </>
  );
}

export default Tabs;
