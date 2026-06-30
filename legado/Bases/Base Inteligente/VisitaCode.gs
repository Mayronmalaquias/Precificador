/**
 * @OnlyCurrentDoc
 * Este script cria um menu para importar e consolidar dados de imóveis a partir de arquivos CSV,
 * separando as métricas por fonte de dados.
 */

// Adiciona um menu personalizado à planilha quando ela é aberta.
function onOpen() {
  SpreadsheetApp.getUi()
    // .createMenu('Relatório de Imóveis')
    .addItem('Abrir Importador de Dados', 'showSidebar')
    .addToUi();
}

// Mostra a barra lateral (sidebar) com o formulário de upload.
function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('Importador de Bases')
    .setWidth(350);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Processa os arquivos CSV enviados pelo usuário.
 * @param {object} formObject - O objeto contendo o conteúdo dos arquivos como string.
 * @return {string} Uma mensagem de sucesso ou erro.
 */
function processFiles(formObject) {
  try {
    // Converte o conteúdo de texto dos arquivos CSV para dados estruturados
    const olxZapData = csvToData(formObject.olxZapFile);
    const c2sData = csvToData(formObject.c2sFile);
    const dfimoveisData = csvToData(formObject.dfimoveisFile);

    // Objeto para consolidar os dados
    const masterData = {};
    
    // Função auxiliar para garantir que o objeto de um imóvel exista
    const ensureImovel = (imovelId) => {
      if (!masterData[imovelId]) {
        masterData[imovelId] = {
          views_df: 0,
          leads_df: 0,
          views_olx: 0,
          leads_olx: 0,
          leads_c2s: 0,
          leads_c2s_imoview: 0
        };
      }
    };

    // 1. Processa o arquivo OLX/ZAP
    olxZapData.forEach(row => {
      const imovelId = row['Código do Imóvel'];
      if (!imovelId) return;
      ensureImovel(imovelId);
      masterData[imovelId].views_olx += parseInt(row['Total de visualizações'] || 0);
      masterData[imovelId].leads_olx += parseInt(row['Total de contatos'] || 0);
    });

    // 2. Processa o arquivo DFimoveis
    dfimoveisData.forEach(row => {
      const imovelId = row['CodigoDeBusca'];
      if (!imovelId) return;
      ensureImovel(imovelId);
      masterData[imovelId].views_df += parseInt(row['Acesso'] || 0);
      const leadsDf = parseInt(row['Emails'] || 0) + parseInt(row['Telefone'] || 0) + parseInt(row['WhatsAppEmailsGerados'] || 0);
      masterData[imovelId].leads_df += leadsDf;
    });

    // 3. Processa o arquivo C2S (contagem de leads)
    c2sData.forEach(row => {
      const imovelId = row['Código do Imóvel'];
      if (!imovelId || imovelId.toString().trim() === '') return;
      ensureImovel(imovelId);
      masterData[imovelId].leads_c2s++;
      if (row['Fonte'] == 'ImovelWeb') {
        masterData[imovelId].leads_c2s_imoview++;
      }
    });

    // Prepara os dados para serem escritos na planilha
    const outputData = Object.keys(masterData).map(imovelId => {
      return [
        imovelId,
        masterData[imovelId].views_df,
        masterData[imovelId].leads_df,
        masterData[imovelId].views_olx,
        masterData[imovelId].leads_olx,
        masterData[imovelId].leads_c2s,
        masterData[imovelId].leads_c2s_imoview,
      ];
    });

    // Escreve o resultado na planilha
    writeReport(outputData);

    return 'Relatório detalhado gerado com sucesso!';

  } catch (e) {
    Logger.log(e);
    return 'Erro ao processar os arquivos: ' + e.message;
  }
}

/**
 * Converte uma string CSV para um array de objetos.
 * @param {string} csvString - O conteúdo do arquivo CSV.
 * @return {object[]} Os dados do CSV como objetos.
 */
function csvToData(csvString) {
  const dataArray = Utilities.parseCsv(csvString);
  if (dataArray.length < 2) return []; // Retorna vazio se não tiver cabeçalho e dados

  const headers = dataArray.shift(); // Pega a primeira linha como cabeçalho
  
  return dataArray.map(row => {
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = row[index];
    });
    return obj;
  });
}


/**
 * Escreve os dados consolidados em uma nova aba na planilha.
 * @param {Array<Array<any>>} data - Os dados a serem escritos.
 */
function writeReport(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = 'Relatório Consolidado';
  let sheet = ss.getSheetByName(sheetName);

  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet(sheetName);
  }

  // Cabeçalho ATUALIZADO
  const header = [['Código do Imóvel', 'Views DF', 'Leads DF', 'Views OLX/ZAP', 'Leads OLX/ZAP', 'Leads C2S', 'Leads CS2 - Imoview']];
  
  // Escreve o cabeçalho
  sheet.getRange(1, 1, 1, header[0].length)
    .setValues(header)
    .setFontWeight('bold')
    .setHorizontalAlignment('center');

  if (data.length > 0) {
    // Escreve os dados
    sheet.getRange(2, 1, data.length, data[0].length).setValues(data);
  }
  
  // Ajusta o tamanho das colunas
  sheet.autoResizeColumns(1, header[0].length);
}
