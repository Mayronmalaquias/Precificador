import React from 'react';

function Relatorio() {
  return (
    <div className="tab-content" id="relatorio">
      <div id="report">
        <iframe
          title="Bi Valor_m2-Preco"
          src="https://app.powerbi.com/view?r=eyJrIjoiZWM4NTEyY2MtYTVhMy00ZmE5LThmYjMtN2Q3MDBlMzJmMDY5IiwidCI6ImMxNWY0MDJjLTAyMjUtNGU2Ni1hMDJiLTZiOWM3ODAzYWIzYiJ9"
          frameBorder="0"
          allowFullScreen
          width="100%"
          height="800"
        />
      </div>
    </div>
  );
}

export default Relatorio;
