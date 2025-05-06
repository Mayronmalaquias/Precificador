import React, { useEffect, useState, useRef } from 'react';
import Logo61 from '../assets/img/LOGO 61 PNG (3).png';
import '../assets/css/footerPaginaUnica.css';
import '../assets/css/reportPaginaUnica.css';
import '../assets/css/stylesPaginaUnica.css';
import '../assets/css/chat.css';

function FormularioAnalise() {
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
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  useEffect(() => {
    buscarDados();
  }, [formData]);

  const buscarDados = () => { // /api/.. resto da rota
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
        alert('Erro ao carregar o mapa.');
      })
      .finally(() => setCarregandoMapa(false));
  };

  const alterarCluster = (valor) => {
    updateField('nrCluster', valor.toString());
  };

  return (
    <main>
      <div className="main-container">
        <form>
          <label>Tipo de Imóvel:</label>
          <select value={formData.tipoImovel} onChange={e => updateField('tipoImovel', e.target.value)}>
            <option value="Apartamento">Apartamento</option>
          </select>

          <label>Bairro:</label>
          <select value={formData.bairro} onChange={e => updateField('bairro', e.target.value)}>
            <option value="ASA NORTE">ASA NORTE</option>
            <option value="ASA SUL">ASA SUL</option>
            <option value="NOROESTE">NOROESTE</option>
            <option value="SUDOESTE">SUDOESTE</option>
            <option value="AGUAS CLARAS">AGUAS CLARAS</option>
          </select>

          <label>Quartos:</label>
          <select value={formData.quartos} onChange={e => updateField('quartos', e.target.value)}>
            <option value="0">Todos</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4+</option>
          </select>

          <label>Vagas:</label>
          <select value={formData.vagas} onChange={e => updateField('vagas', e.target.value)}>
            <option value="10">Todos</option>
            <option value="0">0</option>
            <option value="1">1+</option>
          </select>

          <label>Metragem (m²):</label>
          <input
            type="number"
            value={formData.metragem}
            onChange={e => updateField('metragem', e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                e.preventDefault();
              }
            }}
          />

          <div style={{ marginTop: 10 }}>
            <button type="button" onClick={() => alterarCluster(2)}>ORIGINAL</button>
            <button type="button" onClick={() => alterarCluster(5)}>SEMI-REFORMADO</button>
            <button type="button" onClick={() => alterarCluster(8)}>REFORMADO</button>
          </div>

          <ul className="lista-com-imagem">
            <li className="negrito"><strong>Valor de M² de Venda:</strong> R$ {dadosAPI?.valorM2Venda != null ? dadosAPI.valorM2Venda.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'} /m²</li>
            <li className="negrito"><strong>Valor de Venda Nominal:</strong> R$ {dadosAPI?.valorVendaNominal != null ? dadosAPI?.valorVendaNominal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</li>
            <li className="negrito"><strong>Valor de M² de Locação:</strong> R$ {dadosAPI2?.valorM2Aluguel != null ? dadosAPI2?.valorM2Aluguel.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'} /m²</li>
            <li className="negrito"><strong>Valor de Locação Nominal:</strong> R$ {dadosAPI2?.valorAluguelNominal != null ? dadosAPI2?.valorAluguelNominal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</li>
            {/* <li><strong>Rentabilidade Média:</strong> {dadosAPI?.rentabilidadeMedia}</li> */}
          </ul>

          <div className="container">
            <label for="nrCluster" className="TituloCluster">Número de Clusters (1 a 9):</label>
            <input
              type="range"
              min="1"
              id="nrCluster" 
              name="nrCluster"
              max="9"
              value={formData.nrCluster}
              onChange={(e) => updateField('nrCluster', e.target.value)}
            />
            <output id="outCluster">{formData.nrCluster}</output>
            <img src={Logo61} alt="Imagem sobre o campo" className="imagem-sobreposta" />
          </div>
        </form>

        <div style={{ marginTop: '20px' }}>
          <div style={{ display: carregandoMapa ? 'block' : 'none' }}>Carregando mapa...</div>
          <div dangerouslySetInnerHTML={{ __html: mapaHtml }} style={{ display: carregandoMapa ? 'none' : 'block' }} />
        </div>
      </div>
    </main>
  );
}

export default FormularioAnalise;
