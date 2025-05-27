import React, { useRef,useState, useEffect, useCallback } from 'react';

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
  const [carregandoDados, setCarregandoDados] = useState(false); // Inicialize como true se for carregar imediatamente
  const [erroDadosVenda, setErroDadosVenda] = useState(null);
  const [erroDadosAluguel, setErroDadosAluguel] = useState(null);


// No início do seu componente Formulario (ou onde você define os refs)
const rangeRef = useRef(null);
const outputRef = useRef(null);

// ... dentro da função do componente

// ATENÇÃO: Este useEffect é para posicionar o <output>.
// Ele é separado do useEffect de carregamento de dados.
useEffect(() => {
if (rangeRef.current && outputRef.current) {
  const rangeInput = rangeRef.current;
  const outputElement = outputRef.current;

  const value = parseFloat(rangeInput.value);
  const min = parseFloat(rangeInput.min);
  const max = parseFloat(rangeInput.max);

  // Calcula a posição percentual do thumb no slider
  const percent = ((value - min) / (max - min)) * 100;

  // Obtém a largura do input range
  const rangeWidth = rangeInput.offsetWidth;

  // Calcula a nova posição 'left' para o output.
  // Isso posiciona o início do output na porcentagem correspondente da largura do range.
  const newPosition = (percent / 100) * rangeWidth;

  outputElement.style.left = `${newPosition}px`;
  // O transform no CSS do output cuidará de centralizá-lo.
}
// Esta dependência garante que a posição do output seja recalculada sempre que o valor do slider mudar.
// Adicione também formData.nrCluster se rangeRef.current.value não for suficiente para o timing.
}, [formData.nrCluster]);

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

const alterarClusterCopy = (valor) => {
  const novoCluster = valor === 'geral' ? '0' : valor.toString();
  setFormData((prev) => ({ ...prev, nrCluster: novoCluster }));
};

  const buscarDados = useCallback(() => {
    console.log("buscarDados chamada com:", formData);
    setCarregandoDados(true);
    setErroDadosVenda(null);
    setErroDadosAluguel(null);
    setDadosAPI(null);
    setDadosAPI2(null);

    const { tipoImovel, bairro, quartos, vagas, metragem, nrCluster } = formData;
    const url = `/api/imovel/venda?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;
    const url2 = `/api/imovel/aluguel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;

    const fetchVenda = fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.error || `Erro HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => setDadosAPI(data))
      .catch(err => {
        console.error('Erro ao buscar dados de venda:', err);
        setErroDadosVenda(`Erro análise venda!`);
      });

    const fetchAluguel = fetch(url2)
      .then(async (res) => {
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.error || `Erro HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => setDadosAPI2(data))
      .catch(err => {
        console.error('Erro ao buscar dados de aluguel:', err);
        setErroDadosAluguel(`Erro análise aluguel!`);
      });

    Promise.allSettled([fetchVenda, fetchAluguel])
      .finally(() => {
        setCarregandoDados(false);
      });
  }, [formData]); // formData como dependência é importante para que buscarDados sempre use os valores mais recentes QUANDO FOR CHAMADA

  // ADICIONADO: useEffect para carregamento inicial
  useEffect(() => {
    console.log("Componente montado. Carregando dados padrão...");
    // A função buscarDados aqui usará os valores iniciais de formData
    // definidos no useState, pois este efeito só roda uma vez na montagem.
    buscarDados();

    // A linha abaixo desabilita um aviso comum do ESLint (react-hooks/exhaustive-deps).
    // Fazemos isso conscientemente porque queremos que este efeito específico
    // execute buscarDados APENAS na montagem inicial, e não se a função buscarDados
    // (que é recriada quando formData muda) for alterada após a montagem inicial.
    // Se buscarDados fosse incluída no array de dependências e não houvesse este controle,
    // poderíamos voltar a ter atualizações automáticas.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Array de dependências VAZIO significa que este efeito roda apenas uma vez, após a montagem inicial.

  const alterarCluster = (valor) => {
    updateField('nrCluster', valor.toString());
  };

  const handleAplicarFiltros = () => {
    buscarDados();
  };

  const renderDataOrError = (data, error, field, formatOptions = { minimumFractionDigits: 2, maximumFractionDigits: 2 }, prefix = 'R$ ', suffix = '') => {
    if (error) {
      return <span style={{ color: 'red' }}> {error}</span>;
    }
    const value = data?.[field];
    if (value != null) {
      if (typeof value === 'number') {
        if (field === 'coeficienteVariacaoVenda' || field === 'coeficienteVariacaoAluguel') {
          return `${(value * 100).toLocaleString('pt-BR', formatOptions)}%`;
        } else {
          return `${prefix}${value.toLocaleString('pt-BR', formatOptions)}${suffix}`;
        }
      } else {
        return `${prefix}${value}${suffix}`;
      }
    }
    // Se carregandoDados for true E não houver erro, podemos mostrar um placeholder de loading aqui também
    // if (carregandoDados) return <span style={{ color: 'gray' }}>Carregando...</span>;
    return '-';
  };

  const renderRentabilidade = () => {
    if (erroDadosVenda || erroDadosAluguel) {
      return <span style={{ color: 'red' }}> Erro ao calcular rentabilidade</span>;
    }
    if (dadosAPI2?.valorAluguelNominal != null && dadosAPI?.valorVendaNominal != null && dadosAPI.valorVendaNominal !== 0) {
      return `${((dadosAPI2.valorAluguelNominal / dadosAPI.valorVendaNominal) * 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
    }
    // if (carregandoDados) return <span style={{ color: 'gray' }}>Carregando...</span>;
    return '-';
  };

  return (
    <div className="tab-content active-content" id="formulario">
      <div className="main-container">
        <form id="formularioAnalise">
          {/* Seus Inputs e Selects ... */}
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
            <button
              type="button"
              className={`botao-cluster ${formData.nrCluster === '1' ? 'botao-cluster-selecionado' : ''}`}
              onClick={() => alterarClusterCopy(1)}
            >
              ORIGINAL
            </button>
            <button
              type="button"
              className={`botao-cluster ${formData.nrCluster === '4' ? 'botao-cluster-selecionado' : ''}`}
              onClick={() => alterarClusterCopy(4)}
            >
              SEMI-REFORMADO
            </button>
            <button
              type="button"
              className={`botao-cluster ${formData.nrCluster === '7' ? 'botao-cluster-selecionado' : ''}`}
              onClick={() => alterarClusterCopy(7)}
            >
              REFORMADO
            </button>
          </div>

          <label htmlFor="nrCluster">Número de Clusters ({formData.minNrCluster || 0} a {formData.maxNrCluster || 8}):</label>
          {/* Div wrapper para o input range e seu output */}
          <div style={{ position: 'relative', width: '100%', marginTop: '30px', marginBottom: '15px' }}>
            <input
              type="range"
              id="nrCluster"
              name="nrCluster"
              min={formData.minNrCluster || "0"} // Use valores do estado se eles puderem mudar
              max={formData.maxNrCluster || "8"} // Ou use os valores fixos "0" e "8"
              value={formData.nrCluster}
              ref={rangeRef} // Adicionar ref
              onChange={(e) => updateField('nrCluster', e.target.value)}
              // Estilos inline para remover aparência padrão se for estilizar com CSS puro depois
              // style={{ WebkitAppearance: 'none', appearance: 'none', width: '100%', background: 'transparent' }}
            />
            <output
              htmlFor="nrCluster"
              ref={outputRef} // Adicionar ref
              style={{
                position: 'absolute',
                top: '-25px', // Posiciona acima do slider
                transform: 'translateX(-50%)', // Centraliza o output horizontalmente em relação ao seu 'left'
                backgroundColor: '#f0f0f0',
                color: '#e1005b',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '14px',
                fontWeight: 'bold',
                whiteSpace: 'nowrap', // Impede que o texto quebre
                // left será definido pelo useEffect
              }}
            >
              {formData.nrCluster}
            </output>
          </div>

          <div style={{ marginTop: '20px', marginBottom: '20px' }}>
            <button type="button" onClick={handleAplicarFiltros} style={{ padding: '10px 15px', fontSize: '16px' }}>
              Aplicar Filtros e Calcular
            </button>
          </div>
        </form>

        {/* Exibição dos dados ou mensagem de carregamento */}
        {carregandoDados ? (
          <div style={{ textAlign: 'center', margin: '20px' }}>
            <p>Carregando dados da análise...</p>
            {/* Você pode adicionar um spinner/loading visual aqui */}
          </div>
        ) : (
          <ul>
            <li><strong>Valor de M² de Venda:</strong>{renderDataOrError(dadosAPI, erroDadosVenda, 'valorM2Venda', undefined, ' R$ ', ' /m²')}</li>
            <li><strong>Valor de Venda Nominal:</strong>{renderDataOrError(dadosAPI, erroDadosVenda, 'valorVendaNominal', undefined, ' R$ ')}</li>
            <li><strong>Metragem Média de Venda:</strong>{renderDataOrError(dadosAPI, erroDadosVenda, 'metragemMediaVenda', undefined, ' ', ' m²')}</li>
            <li><strong>Coeficiente de Variação de Venda:</strong>{renderDataOrError(dadosAPI, erroDadosVenda, 'coeficienteVariacaoVenda')}</li>
            <li><strong>Tamanho da Amostra de Venda:</strong>{renderDataOrError(dadosAPI, erroDadosVenda, 'tamanhoAmostraVenda', { minimumFractionDigits: 0, maximumFractionDigits: 0 }, ' ')}</li>
            
            <li><strong>Valor de M² de Locação:</strong>{renderDataOrError(dadosAPI2, erroDadosAluguel, 'valorM2Aluguel', undefined, ' R$ ', ' /m²')}</li>
            <li><strong>Valor de Locação Nominal:</strong>{renderDataOrError(dadosAPI2, erroDadosAluguel, 'valorAluguelNominal', undefined, ' R$ ')}</li>
            <li><strong>Metragem Média de Locação:</strong>{renderDataOrError(dadosAPI2, erroDadosAluguel, 'metragemMediaAluguel', undefined, ' ', ' m²')}</li>
            <li><strong>Coeficiente de Variação de Locação:</strong>{renderDataOrError(dadosAPI2, erroDadosAluguel, 'coeficienteVariacaoAluguel')}</li>
            <li><strong>Tamanho da Amostra de Locação:</strong>{renderDataOrError(dadosAPI2, erroDadosAluguel, 'tamanhoAmostraAluguel', { minimumFractionDigits: 0, maximumFractionDigits: 0 }, ' ')}</li>
            
            <li><strong>Rentabilidade Média: </strong>{renderRentabilidade()}</li>
          </ul>
        )}
      </div>
    </div>
  );
}

export default Formulario;