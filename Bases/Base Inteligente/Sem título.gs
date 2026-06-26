
function buscarDataEntradaLead() {
  // =================================================================
  // CONFIGURAÇÃO - Substitua o ID da planilha de origem aqui
  // =================================================================
  const idPlanilhaNegocios = '1K2_LKnXABnnL-Z1bcJuEPf-6asXuJoqsrWY1o2rHGYk'; 
  // Exemplo: '1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t'
  //==================================================================

  const planilhaAtiva = SpreadsheetApp.getActiveSpreadsheet();
  const abaDestino = planilhaAtiva.getSheetByName('Fato_Venda');

  if (!abaDestino) {
    SpreadsheetApp.getUi().alert('A aba "Fato_Venda" não foi encontrada na planilha atual.');
    return;
  }

  try {
    const planilhaOrigem = SpreadsheetApp.openById(idPlanilhaNegocios);
    const abaOrigem = planilhaOrigem.getSheets()[0]; // Pega a primeira aba da planilha "Negocios 2025"
    
    // Pega os dados da planilha de origem (Negocios 2025)
    const dadosOrigemRange = abaOrigem.getDataRange();
    const valoresOrigem = dadosOrigemRange.getValues();
    
    // Cria um mapa para busca rápida: {código: data}
    const mapaDeDatas = {};
    for (let i = 1; i < valoresOrigem.length; i++) { // Começa em 1 para pular o cabeçalho
      const codigo = valoresOrigem[i][0]; // Coluna A (Código)
      const dataLead = valoresOrigem[i][1]; // Coluna B (AtendimentoDataEntradaLead)
      if (codigo && dataLead) {
        mapaDeDatas[codigo] = new Date(dataLead);
      }
    }

    // Pega os dados da planilha de destino (Fato_Venda)
    const ultimaLinhaDestino = abaDestino.getLastRow();
    const rangeDestino = abaDestino.getRange('A2:BF' + ultimaLinhaDestino); // Lê da coluna A até a BF
    const valoresDestino = rangeDestino.getValues();

    const novasDatasParaInserir = [];

    // Itera sobre a planilha de destino para encontrar os códigos e atualizar as datas
    for (let i = 0; i < valoresDestino.length; i++) {
      const codigoImovel = valoresDestino[i][0]; // Coluna A (Código do imóvel)
      let dataFormatada = ''; // Por padrão, a data é vazia

      if (codigoImovel && mapaDeDatas[codigoImovel]) {
        const data = mapaDeDatas[codigoImovel];
        // Formata a data para DD/MM/AAAA
        dataFormatada = Utilities.formatDate(data, Session.getScriptTimeZone(), 'dd/MM/yyyy');
      }
      
      novasDatasParaInserir.push([dataFormatada]);
    }

    // Insere todas as novas datas de uma vez na coluna BF para melhor performance
    if (novasDatasParaInserir.length > 0) {
      abaDestino.getRange('BF2:BF' + (novasDatasParaInserir.length + 1)).setValues(novasDatasParaInserir);
    }

    SpreadsheetApp.getUi().alert('A atualização foi concluída com sucesso!');

  } catch (e) {
    Logger.log(e);
    SpreadsheetApp.getUi().alert('Ocorreu um erro. Verifique se o ID da planilha "Negocios 2025" está correto e se você tem acesso a ela. Detalhes do erro: ' + e.message);
  }
}
