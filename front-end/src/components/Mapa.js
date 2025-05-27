import React, { useEffect, useRef, useState, useCallback } from 'react';

function Mapa() {
  const [formData, setFormData] = useState({
    tipoImovel: 'Apartamento',
    bairro: 'ASA NORTE',
    quartos: '0',
    vagas: '10',
    metragem: '0',
    nrCluster: '5'
  });

  const [dadosAPI, setDadosAPI] = useState(null); // Embora não usado no JSX, mantido se buscarDados for necessário para algo
  const [dadosAPI2, setDadosAPI2] = useState(null); // Mesmo caso acima
  const [mapaHtml, setMapaHtml] = useState('');
  const [carregandoMapa, setCarregandoMapa] = useState(false);

  const mapSelectorRef = useRef(null);
  const mapOptionRef = useRef(null);

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const carregarMapa = useCallback(() => {
    const tipo = mapSelectorRef.current?.value || 'mapaAnuncio';
    const tamanho = mapOptionRef.current?.value || 'mapaCluster';
    const cluster = formData.nrCluster || '5';

    console.log("Mapa.js: carregarMapa chamada com:", { tipo, tamanho, cluster }); // Log para debug
    setCarregandoMapa(true);
    const mapurl = `/api/mapa/carregar?tipo=${tipo}&cluster=${cluster}&tamanho=${tamanho}`;
    fetch(mapurl)
      .then((res) => res.text())
      .then(setMapaHtml)
      .catch(err => {
        console.error('Erro ao carregar o mapa:', err);
        // Removido o alert para não ser intrusivo, erro já logado.
        // Considere uma forma mais amigável de notificar o usuário se necessário.
      })
      .finally(() => setCarregandoMapa(false));
  }, [formData.nrCluster]); // mapSelectorRef e mapOptionRef.current não precisam ser dependências de useCallback

  const buscarDados = useCallback(() => {
    console.log("Mapa.js: buscarDados chamada com:", formData); // Log para debug
    // Limpar estados de dadosAPI e dadosAPI2 ou erros, se houver.
    setDadosAPI(null);
    setDadosAPI2(null);
    // Adicionar setCarregandoDados(true/false) se esta função realmente fizer algo demorado.

    const { tipoImovel, bairro, quartos, vagas, metragem, nrCluster } = formData;
    const url = `/api/imovel/venda?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;
    const url2 = `/api/imovel/aluguel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;

    // Exemplo de como as chamadas fetch poderiam ser (ajuste conforme sua necessidade)
    fetch(url)
      .then((res) => res.ok ? res.json() : res.json().then(err => { throw new Error(err.error || "Erro desconhecido na API de venda") }))
      .then(setDadosAPI)
      .catch(err => console.error('Erro ao buscar dados de venda:', err));

    fetch(url2)
      .then((res) => res.ok ? res.json() : res.json().then(err => { throw new Error(err.error || "Erro desconhecido na API de aluguel") }))
      .then(setDadosAPI2)
      .catch(err => console.error('Erro ao buscar dados de aluguel:', err));
  }, [formData]);

  // CORRIGIDO: useEffect para carregamento inicial
  useEffect(() => {
    console.log("Mapa.js: Carregamento inicial (componente montado)."); // Log para debug
    buscarDados();
    carregarMapa();
    // AVISO ESLINT: A linha abaixo desabilita o aviso de dependências exaustivas.
    // Isso é intencional aqui porque queremos que este efeito rode APENAS na montagem inicial.
    // As funções buscarDados e carregarMapa chamadas aqui usarão o formData inicial.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Array de dependências VAZIO garante que rode só uma vez.

  const alterarClusterCopy = (valor) => {
    const novoCluster = valor === 'geral' ? '0' : valor.toString();
    setFormData((prev) => ({ ...prev, nrCluster: valor }));
  };

  const handleAplicarFiltros = () => {
    console.log("Mapa.js: Botão Aplicar Filtros clicado."); // Log para debug
    buscarDados(); // buscarDados usará o formData mais recente devido ao useCallback
    carregarMapa(); // carregarMapa também
  };

  return (
    <div className="tab-content">
      <div className="main-container">
        <label htmlFor="tipoImovelCopia">Tipo de Imóvel:</label>
        <select
          id="tipoImovelCopia" // Adicionado id para o htmlFor
          value={formData.tipoImovel}
          onChange={(e) => updateField('tipoImovel', e.target.value)}
        >
          <option value="Apartamento">Apartamento</option>
        </select>

        <label htmlFor="bairroMapa">Bairro:</label> {/* Alterado htmlFor para evitar duplicidade se houver outro id 'bairro' */}
        <select
          id="bairroMapa" // Adicionado id
          value={formData.bairro}
          onChange={(e) => updateField('bairro', e.target.value)}
        >
          <option value="ASA NORTE">ASA NORTE</option>
          <option value="ASA SUL">ASA SUL</option>
          <option value="NOROESTE">NOROESTE</option>
          <option value="SUDOESTE">SUDOESTE</option>
          <option value="AGUAS CLARAS">AGUAS CLARAS</option>
        </select>

        <label htmlFor="quartosMapa">Quartos:</label> {/* Alterado htmlFor */}
        <select
          id="quartosMapa" // Adicionado id
          value={formData.quartos}
          onChange={(e) => updateField('quartos', e.target.value)}
        >
          <option value="0">Todos</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4+</option>
        </select>

        <label htmlFor="vagasMapa">Vagas:</label> {/* Alterado htmlFor */}
        <select
          id="vagasMapa" // Adicionado id
          value={formData.vagas}
          onChange={(e) => updateField('vagas', e.target.value)}
        >
          <option value="10">Todos</option>
          <option value="0">0</option>
          <option value="1">1+</option>
        </select>

        <label htmlFor="metragemMapa">Metragem (m²):</label> {/* Alterado htmlFor */}
        <input
          type="number"
          id="metragemMapa" // Adicionado id
          value={formData.metragem}
          onChange={(e) => updateField('metragem', e.target.value)}
          placeholder="Digite a metragem"
          min="0"
          step="1"
        />

        <div>
          <button
            type="button"
            className={`botao-cluster ${formData.nrCluster === '0' ? 'botao-cluster-selecionado' : ''}`}
            onClick={() => alterarClusterCopy(0)}
          >
            GERAL
          </button>
          <button
            type="button"
            className={`botao-cluster ${formData.nrCluster === '2' ? 'botao-cluster-selecionado' : ''}`}
            onClick={() => alterarClusterCopy(2)}
          >
            ORIGINAL
          </button>
          <button
            type="button"
            className={`botao-cluster ${formData.nrCluster === '5' ? 'botao-cluster-selecionado' : ''}`}
            onClick={() => alterarClusterCopy(5)}
          >
            SEMI-REFORMADO
          </button>
          <button
            type="button"
            className={`botao-cluster ${formData.nrCluster === '8' ? 'botao-cluster-selecionado' : ''}`}
            onClick={() => alterarClusterCopy(8)}
          >
            REFORMADO
          </button>
        </div>

      </div>

      <div className="map-container" style={{ position: 'relative' }}>
        <div className="MapSelector">
          {/* Se os selects de tipo/tamanho do mapa DEVEM recarregar o mapa IMEDIATAMENTE, adicione onChange={carregarMapa} */}
          {/* Exemplo: <select ref={mapSelectorRef} defaultValue="mapaAnuncio" onChange={carregarMapa}> */}
          <label htmlFor="mapTypeSelect" style={{ marginRight: '5px' }}>Tipo de Mapa:</label>
          <select id="mapTypeSelect" ref={mapSelectorRef} defaultValue="mapaAnuncio">
            <option value="mapaAnuncio">Mapa de anúncio</option>
            <option value="mapaM2">Mapa de valor de m2</option>
          </select>
          <label htmlFor="mapSizeSelect" style={{ marginLeft: '10px', marginRight: '5px' }}>Opção de Mapa:</label>
          <select id="mapSizeSelect" ref={mapOptionRef} defaultValue="mapaCluster">
            <option value="mapaCluster">Mapa Clusterizado</option>
            <option value="mapaCompleto">Mapa Completo</option>
          </select>
        </div>
        <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
          <button type="button" onClick={handleAplicarFiltros} style={{ padding: '10px 20px', fontSize: '16px' }}>
            Aplicar Filtros e Atualizar Mapa
          </button>
        </div>

        {carregandoMapa && (
          <div id="loading" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '1rem' }}>
            {/* Você pode adicionar um spinner aqui se desejar */}
            <p>Carregando o mapa...</p>
          </div>
        )}
        {/* Renderiza o iframe apenas se não estiver carregando E houver HTML */}
        {!carregandoMapa && mapaHtml && (
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
        {/* Se não estiver carregando e não houver HTML, pode mostrar uma mensagem ou nada */}
        {!carregandoMapa && !mapaHtml && (
             <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <p>Mapa não carregado ou sem dados para exibir. Aplique os filtros.</p>
             </div>
        )}
      </div>
    </div>
  );
}

export default Mapa;