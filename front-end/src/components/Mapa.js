import React, { useEffect, useRef, useState } from 'react';

function Mapa() {
  const [formData, setFormData] = useState({
    tipoImovel: 'Apartamento',
    bairro: 'ASA NORTE',
    quartos: '0',
    vagas: '10',
    metragem: '0',
    nrCluster: '5'
  });

  const [dadosAPI, setDadosAPI] = useState(null);
  const [mapaHtml, setMapaHtml] = useState('');
  const [carregandoMapa, setCarregandoMapa] = useState(false);

  const mapSelectorRef = useRef(null);
  const mapOptionRef = useRef(null);

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    buscarDados();
    carregarMapa();
  };

  const carregarMapa = () => {
    const tipo = mapSelectorRef.current?.value || 'mapaAnuncio';
    const tamanho = mapOptionRef.current?.value || 'mapaCluster';
    const cluster = formData.nrCluster || '5';

    setCarregandoMapa(true);
// const url = `http://localhost:5000/api/analise/imovel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;
    fetch(`/api/mapa/carregar?tipo=${tipo}&cluster=${cluster}&tamanho=${tamanho}`)
      .then((res) => res.text())
      .then(setMapaHtml)
      .catch(err => {
        console.error('Erro ao carregar o mapa:', err);
        alert("Erro ao carregar o mapa.");
      })
      .finally(() => setCarregandoMapa(false));
  };

  useEffect(() => {
    buscarDados();
    carregarMapa();
  }, [formData]);


  const buscarDados = () => {
    const { tipoImovel, bairro, quartos, vagas, metragem, nrCluster } = formData;
    const url = `/api/analise/imovel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;

    fetch(url)
      .then((res) => res.ok ? res.json() : res.json().then(err => { throw new Error(err.error || "Erro desconhecido") }))
      .then(setDadosAPI)
      .catch(err => console.error(err));
  };

  const alterarClusterCopy = (valor) => {
    const novoCluster = valor === 'geral' ? '0' : valor.toString();
    setFormData((prev) => ({ ...prev, nrCluster: novoCluster }));
  };

  return (
    <div className="tab-content">
      <div className="main-container">
        <label htmlFor="tipoImovelCopia">Tipo de Imóvel:</label>
        <select
          value={formData.tipoImovel}
          onChange={(e) => updateField('tipoImovel', e.target.value)}
        >
          <option value="Apartamento">Apartamento</option>
        </select>

        <label>Bairro:</label>
        <select
          value={formData.bairro}
          onChange={(e) => updateField('bairro', e.target.value)}
        >
          <option value="ASA NORTE">ASA NORTE</option>
          <option value="ASA SUL">ASA SUL</option>
          <option value="NOROESTE">NOROESTE</option>
          <option value="SUDOESTE">SUDOESTE</option>
          <option value="AGUAS CLARAS">AGUAS CLARAS</option>
        </select>

        <label>Quartos:</label>
        <select
          value={formData.quartos}
          onChange={(e) => updateField('quartos', e.target.value)}
        >
          <option value="0">Todos</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4+</option>
        </select>

        <label>Vagas:</label>
        <select
          value={formData.vagas}
          onChange={(e) => updateField('vagas', e.target.value)}
        >
          <option value="10">Todos</option>
          <option value="0">0</option>
          <option value="1">1+</option>
        </select>

        <label>Metragem (m²):</label>
        <input
          type="number"
          value={formData.metragem}
          onChange={(e) => updateField('metragem', e.target.value)}
          placeholder="Digite a metragem"
          min="0"
          step="1"
        />

        <div>
          <button type="button" onClick={() => alterarClusterCopy('geral')}>GERAL</button>
          <button type="button" onClick={() => alterarClusterCopy(2)}>ORIGINAL</button>
          <button type="button" onClick={() => alterarClusterCopy(5)}>SEMI-REFORMADO</button>
          <button type="button" onClick={() => alterarClusterCopy(8)}>REFORMADO</button>
        </div>
      </div>

      <div className="map-container" style={{ position: 'relative' }}>
        <div className="MapSelector">
          <select ref={mapSelectorRef} defaultValue="mapaAnuncio" onChange={carregarMapa}>
            <option value="mapaAnuncio">Mapa de anúncio</option>
            <option value="mapaM2">Mapa de valor de m2</option>
          </select>
          <select ref={mapOptionRef} defaultValue="mapaCluster" onChange={carregarMapa}>
            <option value="mapaCluster">Mapa Clusterizado</option>
            <option value="mapaCompleto">Mapa Completo</option>
          </select>
        </div>

        {carregandoMapa && (
          <div id="loading" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <div id="loading-spinner"></div>
            <p>Carregando o mapa...</p>
          </div>
        )}
        {mapaHtml && (
          <iframe
            title="Mapa Dinâmico"
            srcDoc={mapaHtml}
            style={{
              width: '100%',
              height: '600px',
              border: 'none',
              marginTop: '1rem'
            }}
          />
        )}
      </div>
    </div>
  );
}

export default Mapa;
