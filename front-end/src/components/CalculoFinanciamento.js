import React, { useMemo, useState } from 'react';
import '../assets/css/Financiamento.css';
// Ajuste o caminho da logo depois:
import logo from '../assets/img/LOGO 61 PNG (2).png';

function CalculadoraFinanciamento() {
  const [precoImovel, setPrecoImovel] = useState('');
  const [valorDinheiro, setValorDinheiro] = useState('');

  const formatarMoedaInput = (valor) => {
    const somenteNumeros = valor.replace(/\D/g, '');
    const numero = Number(somenteNumeros) / 100;

    return numero.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  };

  const converterMoedaParaNumero = (valor) => {
    if (!valor) return 0;

    return Number(
      valor
        .replace(/\s/g, '')
        .replace('R$', '')
        .replace(/\./g, '')
        .replace(',', '.')
    ) || 0;
  };

  const handlePrecoImovelChange = (e) => {
    const valorFormatado = formatarMoedaInput(e.target.value);
    setPrecoImovel(valorFormatado);
  };

  const handleValorDinheiroChange = (e) => {
    const valorFormatado = formatarMoedaInput(e.target.value);
    setValorDinheiro(valorFormatado);
  };

  const resultados = useMemo(() => {
    const preco = converterMoedaParaNumero(precoImovel);
    const dinheiro = converterMoedaParaNumero(valorDinheiro);

    const valorFinanciamento = Math.max(preco - dinheiro, 0);
    const prestacaoEstimada = valorFinanciamento * 0.0125;
    const valorVendaEsti = prestacaoEstimada / 0.3;
    const total420Meses = prestacaoEstimada * 420;

    return {
      preco,
      dinheiro,
      valorFinanciamento,
      prestacaoEstimada,
      valorVendaEsti,
      total420Meses,
    };
  }, [precoImovel, valorDinheiro]);

  const formatarMoeda = (valor) => {
    return valor.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  };

  const limparCampos = () => {
    setPrecoImovel('');
    setValorDinheiro('');
  };

  return (
    <div className="pagina-calculadora">
      <div className="card-calculadora">
        <div className="topo-calculadora">
          <div className="logo-area">
            {/* Troque aqui pela sua logo */}
            <img src={logo} alt="Logo da empresa" className="logo-calculadora" />

            {/*<div className="logo-placeholder">
              SUA LOGO
            </div>*/}
          </div>

          <div className="titulo-area">
            <h1>Calculadora de Financiamento</h1>
            <p>
              Ferramenta simples para o corretor simular financiamento e capacidade estimada de compra.
            </p>
          </div>
        </div>

        <div className="tutorial-box">
          <h2>Tutorial rápido</h2>
          <ol>
            <li>Digite o preço do imóvel.</li>
            <li>Digite o valor em dinheiro que o cliente possui.</li>
            <li>O sistema calculará automaticamente o valor a financiar.</li>
            <li>Também será exibida a prestação estimada e a estimativa de valor de venda com base na regra informada.</li>
          </ol>
          <p className="observacao">
            Observação: este cálculo é estimativo e serve como apoio comercial inicial.
          </p>
        </div>

        <div className="formulario-calculadora">
          <div className="campo">
            <label htmlFor="precoImovel">Preço do Imóvel</label>
            <input
              id="precoImovel"
              type="text"
              value={precoImovel}
              onChange={handlePrecoImovelChange}
              placeholder="R$ 0,00"
            />
          </div>

          <div className="campo">
            <label htmlFor="valorDinheiro">Valor em Dinheiro</label>
            <input
              id="valorDinheiro"
              type="text"
              value={valorDinheiro}
              onChange={handleValorDinheiroChange}
              placeholder="R$ 0,00"
            />
          </div>
        </div>

        <div className="botoes-area">
          <button type="button" className="btn-limpar" onClick={limparCampos}>
            Limpar
          </button>
        </div>

        <div className="resultados-grid">
          <div className="resultado-card destaque">
            <span className="resultado-label">Valor do Financiamento</span>
            <strong>{formatarMoeda(resultados.valorFinanciamento)}</strong>
            <small>Preço do imóvel - valor em dinheiro</small>
          </div>

          <div className="resultado-card">
            <span className="resultado-label">Valor Estimado da 1ª Parcela</span>
            <strong>{formatarMoeda(resultados.prestacaoEstimada)}</strong>
            <small>prazo 420 meses</small>
          </div>

          <div className="resultado-card">
            <span className="resultado-label">Renda estimada Necessária</span>
            <strong>{formatarMoeda(resultados.valorVendaEsti)}</strong>
          </div>

        </div>
      </div>
    </div>
  );
}

export default CalculadoraFinanciamento;