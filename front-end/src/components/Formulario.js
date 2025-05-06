import React, { useState, useEffect, useRef } from 'react';


function Formulario() {
  const [formData, setFormData] = useState({
    tipoImovel: 'Apartamento',
    bairro: 'ASA NORTE',
    quartos: '0',
    vagas: '10',
    metragem: '0',
    nrCluster: '5',
  });

  const [dadosAPI, setDadosAPI] = useState(null);
  const [dadosAPI2, setDadosAPI2] = useState(null);
  const [mapaHtml, setMapaHtml] = useState('');
  const [carregandoMapa, setCarregandoMapa] = useState(false);

  const mapSelectorRef = useRef(null);
  const mapOptionRef = useRef(null);

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  useEffect(() => {
    buscarDados();
    // carregarMapa();
  }, [formData]);

  const buscarDados = () => {
    const { tipoImovel, bairro, quartos, vagas, metragem, nrCluster } = formData;
    const url = `http://localhost:5000/imovel/venda?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;
    const url2 = `http://localhost:5000/imovel/aluguel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;


    fetch(url)
      .then((res) => res.ok ? res.json() : res.json().then(err => { throw new Error(err.error || "Erro desconhecido") }))
      .then(setDadosAPI)
      .catch(err => console.error(err));

    fetch(url2)
      .then((res) => res.ok ? res.json() : res.json().then(err => { throw new Error(err.error || "Erro desconhecido") }))
      .then(setDadosAPI2)
      .catch(err => console.error(err));
  };

  const carregarMapa = () => {
    const tipo = mapSelectorRef.current?.value || 'mapaAnuncio';
    const cluster = formData.nrCluster || 5;
    const tamanho = mapOptionRef.current?.value || 'mapaCluster';

    setCarregandoMapa(true);

    fetch(`/carregar_mapa?tipo=${tipo}&cluster=${cluster}&tamanho=${tamanho}`)
      .then(res => res.text())
      .then(html => setMapaHtml(html))
      .catch(err => {
        console.error('Erro ao carregar o mapa:', err);
        alert("Erro ao carregar o mapa.");
      })
      .finally(() => setCarregandoMapa(false));
  };

  const alterarCluster = (valor) => {
    if (valor === "geral") {
      carregarMapa();
    } else {
      updateField('nrCluster', valor.toString());
    }
  };

  return (
    <div className="tab-content active-content" id="formulario">
      <div className="main-container">
        <form id="formularioAnalise">
          <label htmlFor="tipoImovel">Tipo de Imóvel:</label>
          <select id="tipoImovel" value={formData.tipoImovel} onChange={(e) => updateField('tipoImovel', e.target.value)}>
            <option value="Apartamento">Apartamento</option>
          </select>

          <label htmlFor="bairro">Bairro:</label>
          <select id="bairro" value={formData.bairro} onChange={(e) => updateField('bairro', e.target.value)}>
            <option value="ASA NORTE">ASA NORTE</option>
            <option value="ASA SUL">ASA SUL</option>
            <option value="NOROESTE">NOROESTE</option>
            <option value="SUDOESTE">SUDOESTE</option>
            <option value="AGUAS CLARAS">AGUAS CLARAS</option>
          </select>

          <label htmlFor="quartos">Quartos:</label>
          <select id="quartos" value={formData.quartos} onChange={(e) => updateField('quartos', e.target.value)}>
            <option value="0">Todos</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4+</option>
          </select>

          <label htmlFor="vagas">Vagas:</label>
          <select id="vagas" value={formData.vagas} onChange={(e) => updateField('vagas', e.target.value)}>
            <option value="10">Todos</option>
            <option value="0">0</option>
            <option value="1">1+</option>
          </select>

          <label htmlFor="metragem">Metragem (m²):</label>
          <input
            type="number"
            id="metragem"
            value={formData.metragem}
            onChange={(e) => updateField('metragem', e.target.value)}
            placeholder="Digite a metragem"
            min="0"
            step="1"
          />

          <div>
            <button type="button" onClick={() => alterarCluster(1)}>ORIGINAL</button>
            <button type="button" onClick={() => alterarCluster(4)}>SEMI-REFORMADO</button>
            <button type="button" onClick={() => alterarCluster(7)}>REFORMADO</button>
          </div>

          <label htmlFor="nrCluster">Número de Clusters (0 a 8):</label>
          <input
            type="range"
            // id="nrCluster"
            min="0"
            max="8"
            value={formData.nrCluster}
            onChange={(e) => updateField('nrCluster', e.target.value)}
          />
          <output>{(formData.nrCluster)}</output>
        </form>

        <ul>
          <li><strong>Valor de M² de Venda:</strong> R$ {dadosAPI?.valorM2Venda != null ? dadosAPI.valorM2Venda.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'} /m²</li>
          <li><strong>Valor de Venda Nominal:</strong> R$ {dadosAPI?.valorVendaNominal != null ? dadosAPI?.valorVendaNominal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</li>
          <li><strong>Metragem Média de Venda:</strong> {dadosAPI?.metragemMediaVenda != null ? dadosAPI.metragemMediaVenda.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</li>
          <li><strong>Coeficiente de Variação de Venda:</strong> {dadosAPI?.coeficienteVariacaoVenda != null ? (dadosAPI.coeficienteVariacaoVenda * 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}%</li>
          <li><strong>Tamanho da Amostra de Venda:</strong> {dadosAPI?.tamanhoAmostraVenda}</li>
          <li><strong>Valor de M² de Locação:</strong> R$ {dadosAPI2?.valorM2Aluguel != null ? dadosAPI2?.valorM2Aluguel.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'} /m²</li>
          <li><strong>Valor de Locação Nominal:</strong> R$ {dadosAPI2?.valorAluguelNominal != null ? dadosAPI2?.valorAluguelNominal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</li>
          <li><strong>Metragem Média de Locação:</strong> {dadosAPI2?.metragemMediaAluguel != null ? dadosAPI2.metragemMediaAluguel.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</li>
          <li><strong>Coeficiente de Variação de Locação:</strong> {dadosAPI2?.coeficienteVariacaoAluguel != null ? (dadosAPI2.coeficienteVariacaoAluguel * 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}%</li>
          <li><strong>Tamanho da Amostra de Locação:</strong> {dadosAPI2?.tamanhoAmostraAluguel}</li>
          <li><strong>Rentabilidade Média: </strong> 
            {dadosAPI2?.valorAluguelNominal != null && dadosAPI?.valorVendaNominal != null
              ? ((dadosAPI2.valorAluguelNominal / dadosAPI.valorVendaNominal)* 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
              : '-'}
          %</li>
        </ul>
      </div>
    </div>
  );
}

export default Formulario;
