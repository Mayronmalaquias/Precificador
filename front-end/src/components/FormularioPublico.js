import React, { useEffect, useState, useRef, useCallback } from 'react';
import Logo61 from '../assets/img/LOGO 61 PNG (3).png';
import { BASE } from '../services/api';
import '../assets/css/footerPaginaUnica.css';
import '../assets/css/reportPaginaUnica.css';
import '../assets/css/stylesPaginaUnica.css';
import '../assets/css/chat.css';
import grafico from '../assets/img/Evolução M2.png';
// import ChatWidget from './ChatWidget'; // desativado temporariamente



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
  const [carregandoDados, setCarregandoDados] = useState(false);
  const [erroDadosVenda, setErroDadosVenda] = useState(null);
  const [erroDadosAluguel, setErroDadosAluguel] = useState(null);

  const mapSelectorRef = useRef(null); // Presumo que você terá <select> com esta ref
  const mapOptionRef = useRef(null);   // Presumo que você terá <select> com esta ref

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

const alterarClusterCopy = (valor) => {
  const novoCluster = valor === 'geral' ? '0' : valor.toString();
  setFormData((prev) => ({ ...prev, nrCluster: novoCluster }));
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

  // --- NOVOS ESTADOS PARA O GRÁFICO ---
const [graficoLinha, setGraficoLinha] = useState('');
const [carregandoGrafico, setCarregandoGrafico] = useState(false);
const [erroGrafico, setErroGrafico] = useState(null);
// --- NOVA FUNÇÃO PARA BUSCAR O GRÁFICO ---
const buscarGrafico = useCallback(() => {
  console.log("Buscando gráfico de linha...");
  setCarregandoGrafico(true);
  setErroGrafico(null);
  setGraficoLinha(''); // Limpa o gráfico anterior

  const url = `${BASE}/graph/graficoLinha`;

  fetch(url)
      .then(async (res) => {
          if (!res.ok) {
              const errorData = await res.json().catch(() => ({}));
              throw new Error(errorData.error || `Erro HTTP ${res.status}`);
          }
          return res.json();
      })
      .then(data => {
          if (data.image_base64) {
              setGraficoLinha(data.image_base64);
          } else {
              throw new Error("A resposta da API não continha a imagem do gráfico.");
          }
      })
      .catch(err => {
          console.error('Erro ao buscar o gráfico de linha:', err);
          setErroGrafico('Não foi possível carregar o gráfico.');
      })
      .finally(() => {
          setCarregandoGrafico(false);
      });
}, []); // Sem dependências, pois a rota do gráfico não usa filtros por enquanto.


  // Envolver buscarDados com useCallback
const buscarDados = useCallback(() => {
    console.log("buscarDados chamada com:", formData);
    setCarregandoDados(true);
    setErroDadosVenda(null);
    setErroDadosAluguel(null);
    setDadosAPI(null);
    setDadosAPI2(null);

    const { tipoImovel, bairro, quartos, vagas, metragem, nrCluster } = formData;
    const url = `${BASE}/imovel/venda?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;
    const urlAluguelOriginal = `${BASE}/imovel/aluguel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=${quartos}&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;

    // A requisição de Venda permanece a mesma
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

    // --- LÓGICA DE REQUISIÇÃO E RETENTATIVA PARA ALUGUEL ---
    const fetchAluguel = fetch(urlAluguelOriginal)
      .then(async (res) => {
        if (!res.ok) {
          // Se não estiver OK, joga um erro para ser pego pelo .catch()
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.error || `Erro HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        // Se a primeira tentativa deu certo, atualiza o estado e pronto.
        setDadosAPI2(data);
      })
      .catch(err => {
        // A PRIMEIRA TENTATIVA FALHOU. VAMOS TENTAR DE NOVO.
        console.warn('1ª tentativa de aluguel falhou. Tentando novamente com 0 quartos...', err.message);

        // Cria a nova URL com quartos=0
        const urlAluguelRetry = `${BASE}/imovel/aluguel?tipoImovel=${tipoImovel}&bairro=${bairro}&quartos=0&vagas=${vagas}&metragem=${metragem}&nrCluster=${nrCluster}`;
        
        // Retorna a nova promessa de fetch para que o Promise.allSettled espere por ela
        return fetch(urlAluguelRetry)
          .then(async (res) => {
            if (!res.ok) {
              // Se a segunda tentativa também falhar, joga um erro final.
              const errorData = await res.json().catch(() => ({}));
              throw new Error(errorData.error || `Erro HTTP ${res.status} na retentativa`);
            }
            return res.json();
          })
          .then(data => {
            // A SEGUNDA TENTATIVA DEU CERTO!
            console.log('2ª tentativa (0 quartos) bem-sucedida!');
            setDadosAPI2(data);
          })
          .catch(retryErr => {
            // A SEGUNDA TENTATIVA TAMBÉM FALHOU. AGORA MOSTRAMOS O ERRO.
            console.error('2ª tentativa (0 quartos) também falhou:', retryErr.message);
            setErroDadosAluguel(`Erro análise aluguel!`);
          });
      });

    Promise.allSettled([fetchVenda, fetchAluguel])
      .finally(() => {
        setCarregandoDados(false);
      });
}, [formData]);

  // REMOVER o useEffect que dispara com formData
  // useEffect(() => {
  //   buscarDados();
  //   // Se o mapa também deve atualizar automaticamente com formData, adicione carregarMapa() aqui.
  //   // Mas para o comportamento de botão, vamos remover.
  // }, [formData]);

  // useEffect para carregamento inicial (dados e mapa)
  useEffect(() => {
    console.log("Componente FormularioAnalise montado. Carregando dados e mapa padrão...");
    buscarDados();
    // carregarMapa();
    // buscarGrafico();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Array VAZIO para rodar apenas na montagem inicial

  const alterarCluster = (valor) => {
    updateField('nrCluster', valor.toString());
  };

  // Função para o botão "Aplicar Filtros"
  const handleAplicarFiltros = () => {
    console.log("Botão Aplicar Filtros clicado.");
    buscarDados();
    // carregarMapa(); // Mapa também é atualizado com os novos filtros
    // buscarGrafico();
  };

  return (
    <main className="home-page">
      <div className="main-container home-workspace">
        {/* <iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe> */}

        <form className="home-pricing-panel">

          <section
            aria-labelledby="mini-tutorial-title"
            className="home-intro-panel"
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: 16,
              marginBottom: 20,
              background: '#fafafa'
            }}
          >
            <h3 id="mini-tutorial-title" style={{ margin: 0, marginBottom: 8, fontSize: 18 }}>
              Como usar os filtros
            </h3>

            <ol style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
              <li>
                Selecione <strong>Tipo de Imóvel</strong>, <strong>Bairro</strong> e <strong>Quartos</strong>.
              </li>
              <li>
                Escolha uma opção: <strong>ORIGINAL</strong>, <strong>SEMI-REFORMADO</strong> ou <strong>REFORMADO</strong>.
              </li>
              <li>
                Clique em <strong>Aplicar Filtros e Atualizar</strong>.
              </li>
            </ol>
          </section>

          {/* --- Seus inputs e selects --- */}
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
            <option value="Águas Claras">Águas Claras</option>
          </select>

          <label>Quartos:</label>
          <select value={formData.quartos} onChange={e => updateField('quartos', e.target.value)}>
            <option value="0">Todos</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4+</option>
          </select>

          {/* <label>Vagas:</label>
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
                // Opcional: Chamar handleAplicarFiltros() no Enter também
                handleAplicarFiltros();
                }
                }}
                /> */}

          <div className="home-condition-tabs">
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

          {/* --- Botão Aplicar Filtros --- */}
          <div className="home-action-row">
            <button type="button" className="home-primary-action" onClick={handleAplicarFiltros}>
              Aplicar Filtros e Atualizar
            </button>
          </div>

          {/* --- Exibição de dados e erros --- */}
          {carregandoDados ? (
            <div style={{ textAlign: 'center', margin: '20px' }}>
              <p>Carregando dados da análise...</p>
            </div>
          ) : (
            <ul className="lista-com-imagem home-results">
              <li className="negrito">
                <strong>Valor de M² de Venda:</strong>
                {erroDadosVenda ?
                  <span style={{ color: 'red' }}> {erroDadosVenda}</span> :
                  ` R$ ${dadosAPI?.valorM2Venda != null ? dadosAPI.valorM2Venda.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'} /m²`
                }
              </li>
              <li className="negrito">
                <strong>Valor de Venda Nominal:</strong>
                {erroDadosVenda ?
                  <span style={{ color: 'red' }}> {erroDadosVenda}</span> :
                  ` R$ ${dadosAPI?.valorVendaNominal != null ? dadosAPI?.valorVendaNominal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}`
                }
              </li>
              <li className="negrito">
                <strong>Valor de M² de Locação:</strong>
                {erroDadosAluguel ?
                  <span style={{ color: 'red' }}> {erroDadosAluguel}</span> :
                  ` R$ ${dadosAPI2?.valorM2Aluguel != null ? dadosAPI2?.valorM2Aluguel.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'} /m²`
                }
              </li>
              <li className="negrito">
                <strong>Valor de Locação Nominal:</strong>
                {erroDadosAluguel ?
                  <span style={{ color: 'red' }}> {erroDadosAluguel}</span> :
                  ` R$ ${dadosAPI2?.valorAluguelNominal != null ? dadosAPI2?.valorAluguelNominal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}`
                }
              </li>
              <li><strong>Rentabilidade Média: </strong>{renderRentabilidade()}</li>
            </ul>
          )}

          {/* --- NOVA SEÇÃO PARA EXIBIR O GRÁFICO ---
        <div className="grafico-container" style={{ marginTop: '30px', padding: '20px', border: '1px solid #eee', borderRadius: '8px', backgroundColor: '#f9f9f9', textAlign: 'center' }}>
          <h3>Evolução de Preço Histórica</h3>
          {carregandoGrafico ? (
            <p>Carregando gráfico...</p>
          ) : erroGrafico ? (
            <p style={{ color: 'red' }}>{erroGrafico}</p>
          ) : graficoLinha ? (
            <img 
              src={`data:image/png;base64,${graficoLinha}`} 
              alt="Gráfico de evolução de preços por data" 
              style={{ maxWidth: '100%', height: 'auto', border: '1px solid #ccc', borderRadius: '8px' }}
              onError={(e) => {
                // Substitui a fonte da imagem pela imagem de fallback
                e.currentTarget.src = '/grafico_fallback.png';
                // Opcional: Altera o texto alternativo para indicar o erro
                e.currentTarget.alt = 'Erro ao carregar o gráfico. Exibindo imagem alternativa.';
              }}
            />
          ) : (
            <p>Gráfico não disponível.</p>
          )}
        </div> */}
            {/* --- NOVA SEÇÃO PARA EXIBIR O GRÁFICO --- */}
        {/* <div 
          className="grafico-container" 
          style={{ 
            marginTop: '30px', 
            padding: '20px', 
            border: '1px solid #eee', 
            borderRadius: '8px', 
            backgroundColor: '#f9f9f9', 
            textAlign: 'center' 
          }}
        >
          <h3>Evolução de Preço Histórica</h3>
          
          <img 
            src={grafico} // Use a variável importada aqui
            alt="Gráfico de evolução de preços" 
            style={{ 
              maxWidth: '100%', 
              height: 'auto', 
              border: '1px solid #ccc', 
              borderRadius: '8px' 
            }}
            onError={(e) => {
              // e.currentTarget.src = graficoAlternativo; // E aqui também
              e.currentTarget.alt = 'Erro ao carregar o gráfico. Exibindo imagem alternativa.';
            }}
          />
        </div> */}

          <div className="container-central">
              <a className="ZapComentario" href="https://api.whatsapp.com/send?phone=5561998786161" target="_blank" rel="noreferrer">Fale com corretor 61</a>
          </div>
          <ul className="guias">
            <li><a href="https://lp.61imoveis.com/guia-61-de-venda-de-imoveis" target="_blank" rel="noreferrer">Guia de Venda</a></li>
            <li><a href="https://lp.61imoveis.com/guia-61-de-aluguel-de-imoveis" target="_blank" rel="noreferrer">Guia de Locação</a></li>
            <li><a href="https://lp.61imoveis.com/guia-61-do-comprador-de-imoveis" target="_blank" rel="noreferrer">Guia do Comprador de Imoveis</a></li>
            <li><a href="https://lp.61imoveis.com/lp-guia-61-do-inventario-de-imoveis" target="_blank" rel="noreferrer">Guia do inventario de imoveis</a></li>
          </ul>

          {/* <div className="container">
            <label htmlFor="nrCluster" className="TituloCluster">Número de Clusters (1 a 9):</label>
            <input
            type="range"
            min="1" // Ajustado para 1 conforme label
            id="nrCluster"
            name="nrCluster"
            max="9" // Ajustado para 9 conforme label
            value={formData.nrCluster}
              onChange={(e) => updateField('nrCluster', e.target.value)}
            />
            <output id="outCluster">{formData.nrCluster}</output>
            <img src={Logo61} alt="Imagem sobre o campo" className="imagem-sobreposta" />
          </div> */}
        </form>
      <div className="home-video-panel">
        <iframe width="560" height="315" src="https://www.youtube.com/embed/q_qsPITTfK8?si=W4XwmBvTVv5hBXMX" title="YouTube video player" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen></iframe>
      </div>
      </div>
      {/* <ChatWidget /> */}
    </main>
  );
}

export default FormularioAnalise;
