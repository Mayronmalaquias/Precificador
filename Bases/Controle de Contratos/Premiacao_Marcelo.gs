function runFilterAndTransferPremiacaoMar() {
  const premiacaoSpreadsheetId = "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y"; // ID da planilha "Premiação Marcelo"
  const vendasSpreadsheetId = "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y"; // ID da planilha "Vendas"
  const controlSheetName = 'Premiação Marcelo';
  const sourceSheetName = 'Vendas';
  const gerenteFiltrado = 'Marcelo Souza';  // Nome do gerente a ser filtrado

  // Acessa as planilhas "Premiação Marcelo" e "Vendas"
  const premiacaoSs = SpreadsheetApp.openById(premiacaoSpreadsheetId);
  const vendasSs = SpreadsheetApp.openById(vendasSpreadsheetId);

  // Obtém as abas específicas
  const controlSheet = premiacaoSs.getSheetByName(controlSheetName);
  const sourceSheet = vendasSs.getSheetByName(sourceSheetName);

  // Limpa a formatação antes de iniciar a transferência
  limparFormatacaoPremiacaoMar(controlSheet); 

  const startDate = new Date(controlSheet.getRange('A2').getValue());
  const endDate = new Date(controlSheet.getRange('B2').getValue());

  const columnsToCopy = ['Id_Contrato', 'Data_Contrato', 'Contrato', 'Valor_Negocio', 'Valor_Comissao', 'Valor_Total_61', 'NF_61_ Imoveis', 'Liquido_61', 'Percentual_Premiacao_Marcelo', '$_Gerente_Venda', 'Gerente_Venda_Nome', '$_Gerente_Captacao', 'Gerente_Captacao_Nome'];
  const dateColumn = 'Data_Contrato';

  const headers = sourceSheet.getRange(1, 1, 1, sourceSheet.getLastColumn()).getValues()[0];
  const columnIndexes = columnsToCopy.map(column => headers.indexOf(column) + 1);
  const dateColIndex = headers.indexOf(dateColumn);

  if (dateColIndex === -1) {
    throw new Error('Coluna de datas não encontrada.');
  }

  const lastRow = controlSheet.getLastRow();
  if (lastRow > 4) {
    controlSheet.getRange(5, 1, lastRow - 4, controlSheet.getLastColumn()).clearContent();
  }

  const dataRange = sourceSheet.getDataRange();
  const data = dataRange.getValues();

  const filteredData = data.filter((row, index) => {
    if (index === 0) return true;
    const date = new Date(row[dateColIndex]);
    const gerenteVendaNome = row[headers.indexOf('Gerente_Venda_Nome')];
    const gerenteCaptacaoNome = row[headers.indexOf('Gerente_Captacao_Nome')];
    return date >= startDate && date <= endDate && (gerenteVendaNome === gerenteFiltrado || gerenteCaptacaoNome === gerenteFiltrado);
  });

  const groupedData = {};
  filteredData.slice(1).forEach(row => {
    const date = new Date(row[dateColIndex]);
    const monthYear = `${date.getMonth() + 1}/${date.getFullYear()}`;
    if (!groupedData[monthYear]) {
      groupedData[monthYear] = [];
    }
    groupedData[monthYear].push(row);
  });

  let currentRow = 5;
  controlSheet.getRange(currentRow, 1, 1, columnIndexes.length + 1).setValues([[...columnIndexes.map(index => headers[index - 1]), 'Comissao_Gerente']]);
  currentRow++;

  for (const monthYear in groupedData) {
    const monthData = groupedData[monthYear].map(row => {
      const rowData = columnIndexes.map(index => row[index - 1]);
      const gerenteVendaNome = rowData[columnsToCopy.indexOf('Gerente_Venda_Nome')];
      const gerenteCaptacaoNome = rowData[columnsToCopy.indexOf('Gerente_Captacao_Nome')];
      const valorGerenteVenda = parseFloat(rowData[columnsToCopy.indexOf('$_Gerente_Venda')]) || 0;
      const valorGerenteCaptacao = parseFloat(rowData[columnsToCopy.indexOf('$_Gerente_Captacao')]) || 0;
      let comissaoTotal = 0;
      if (gerenteVendaNome === gerenteFiltrado) {
        comissaoTotal += valorGerenteVenda;
      }
      if (gerenteCaptacaoNome === gerenteFiltrado) {
        comissaoTotal += valorGerenteCaptacao;
      }
      rowData.push(comissaoTotal); // Adiciona Comissao_Gerente na última posição de cada linha
      return rowData;
    });

    controlSheet.getRange(currentRow, 1, monthData.length, columnIndexes.length + 1).setValues(monthData);
    currentRow += monthData.length + 4; // Espaço extra para legibilidade
  }

  controlSheet.getRange(5, 1, currentRow - 5, columnIndexes.length + 1).setBorder(true, true, true, true, true, true);
  Utilities.sleep(3000);
  calculateAndInsertTotalsMar();

  // Aplicar formatação nas colunas específicas após a transferência
  aplicarFormatacaoPremiacaoMar(controlSheet, currentRow - 1, columnsToCopy);

  // Formatar as linhas que contém "Rel. Percent." como percentual
  for (let row = 6; row <= controlSheet.getLastRow(); row++) {
    const cellValue = controlSheet.getRange(row, 1).getValue();
    if (cellValue === 'Rel. Percent.') {
      controlSheet.getRange(row, 2, 1, controlSheet.getLastColumn() - 1).setNumberFormat('0.00%');
    }
  }
}

function limparFormatacaoPremiacaoMar(sheet) {
  const lastRow = sheet.getLastRow();
  const lastColumn = sheet.getLastColumn();

  if (lastRow >= 5) {
    const range = sheet.getRange(5, 1, lastRow - 4, lastColumn);
    range.setFontWeight('normal');
    range.setFontStyle('normal');
    range.setNumberFormat('@STRING@'); // Define as células para texto simples
  }
}

function aplicarFormatacaoPremiacaoMar(sheet, lastRow, columnsToCopy) {
  // Define as colunas com valores monetários
  const currencyColumns = ['Valor_Negocio', 'Valor_Comissao', 'Valor_Total_61', 'NF_61_ Imoveis', 'Liquido_61', 'Comissao_Gerente'];
  currencyColumns.forEach(colName => {
    const colIndex = columnsToCopy.indexOf(colName) + 1;  // Encontra o índice da coluna na lista
    const colLetter = getColumnLetter(colIndex);          // Converte o índice para a letra correspondente da coluna
    const range = sheet.getRange(`${colLetter}5:${colLetter}${lastRow}`);
    range.setNumberFormat('R$ #,##0.00');                // Aplica formato de moeda
  });

  // Define a coluna percentual
  const percentualColumnIndex = columnsToCopy.indexOf('Percentual_Premiacao_Marcelo') + 1;
  const percentualColLetter = getColumnLetter(percentualColumnIndex);
  sheet.getRange(`${percentualColLetter}5:${percentualColLetter}${lastRow}`).setNumberFormat('0.00%');

  // Adiciona formatação de data para a coluna 'Data_Contrato'
  const dateColumnIndex = columnsToCopy.indexOf('Data_Contrato') + 1;
  const dateColLetter = getColumnLetter(dateColumnIndex);
  sheet.getRange(`${dateColLetter}5:${dateColLetter}${lastRow}`).setNumberFormat('dd/MM/yyyy');  // Aplica formato de data
}

function getColumnLetter(columnNumber) {
  let temp, letter = '';
  while (columnNumber > 0) {
    temp = (columnNumber - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    columnNumber = (columnNumber - temp - 1) / 26;
  }
  return letter;
}

function calculateAndInsertTotalsMar() {
  const premiacaoSpreadsheetId = "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y"; // Substitua pelo ID da planilha "Premiação Marcelo"
  const controlSheetName = 'Premiação Marcelo';

  const premiacaoSs = SpreadsheetApp.openById(premiacaoSpreadsheetId);
  const controlSheet = premiacaoSs.getSheetByName(controlSheetName);

  const headers = controlSheet.getRange(5, 1, 1, controlSheet.getLastColumn()).getValues()[0];

  const numericColumns = ['Valor_Negocio', 'Valor_Comissao', 'Valor_Total_61', 'NF_61_ Imoveis', 'Liquido_61', 'Comissao_Gerente']; // Inclui Comissao_Gerente nas colunas numéricas
  let currentRow = 6;
  const lastRow = controlSheet.getLastRow();

  let overallTotals = headers.map(() => 0); // Acumula os totais gerais

  while (currentRow <= lastRow) {
    let monthData = [];
    while (currentRow <= lastRow && controlSheet.getRange(currentRow, 1).getValue() !== '') {
      monthData.push(controlSheet.getRange(currentRow, 1, 1, headers.length).getValues()[0]);
      currentRow++;
    }

    if (monthData.length > 0) {
      const totals = headers.map((header, index) => {
        if (numericColumns.includes(header)) {
          const sum = monthData.reduce((acc, row) => acc + (parseFloat(row[index]) || 0), 0);
          overallTotals[index] += sum; // Acumula os totais gerais
          return sum;
        }
        return '';
      });

      // Insere a linha de totais
      const totalRow = currentRow + 1;
      controlSheet.getRange(totalRow, 1, 1, headers.length).setValues([['Totais', ...totals.slice(1)]]);
      
      // Coloca a linha de totais em negrito e itálico
      controlSheet.getRange(totalRow, 1, 1, headers.length).setFontWeight('bold').setFontStyle('italic');

      // Calcula as relações percentuais
      const relationPercent = headers.map((header, index) => {
        if (header === 'Valor_Comissao') {
          return totals[headers.indexOf('Valor_Negocio')] !== 0
            ? totals[headers.indexOf('Valor_Comissao')] / totals[headers.indexOf('Valor_Negocio')]
            : '';
        }
        if (header === 'Valor_Total_61') {
          return totals[headers.indexOf('Valor_Negocio')] !== 0
            ? totals[headers.indexOf('Valor_Total_61')] / totals[headers.indexOf('Valor_Negocio')]
            : '';
        }
        if (header === 'NF_61_ Imoveis') {
          return totals[headers.indexOf('Valor_Negocio')] !== 0
            ? totals[headers.indexOf('NF_61_ Imoveis')] / totals[headers.indexOf('Valor_Negocio')]
            : '';
        }
        if (header === 'Liquido_61') {
          return totals[headers.indexOf('Valor_Negocio')] !== 0
            ? totals[headers.indexOf('Liquido_61')] / totals[headers.indexOf('Valor_Negocio')]
            : '';
        }
        return '';
      });

      // Insere a linha "Rel. Percent."
      const relPercentRow = currentRow + 2;
      controlSheet.getRange(relPercentRow, 1, 1, headers.length).setValues([['Rel. Percent.', ...relationPercent.slice(1)]]);
      
      // Coloca a linha "Rel. Percent." em negrito e itálico
      controlSheet.getRange(relPercentRow, 1, 1, headers.length).setFontWeight('bold').setFontStyle('italic');

      currentRow += 4; // Pula quatro linhas após os totais e percentuais para o próximo mês
    } else {
      currentRow++;
    }
  }

  // Insere o total geral na planilha
  const generalTotals = overallTotals.map((total, index) => {
    if (numericColumns.includes(headers[index])) {
      return total;
    }
    return ''; // Para colunas não numéricas
  });

  const generalTotalRow = currentRow + 1;
  controlSheet.getRange(generalTotalRow, 1, 1, headers.length).setValues([['Total Geral', ...generalTotals.slice(1)]]);
  
  // Coloca a linha de "Total Geral" em negrito e itálico
  controlSheet.getRange(generalTotalRow, 1, 1, headers.length).setFontWeight('bold').setFontStyle('italic');

  // Calcula as relações percentuais para o "Total Geral"
  const generalRelationPercent = headers.map((header, index) => {
    if (header === 'Valor_Comissao') {
      return generalTotals[headers.indexOf('Valor_Negocio')] !== 0
        ? generalTotals[headers.indexOf('Valor_Comissao')] / generalTotals[headers.indexOf('Valor_Negocio')]
        : '';
    }
    if (header === 'Valor_Total_61') {
      return generalTotals[headers.indexOf('Valor_Negocio')] !== 0
        ? generalTotals[headers.indexOf('Valor_Total_61')] / generalTotals[headers.indexOf('Valor_Negocio')]
        : '';
    }
    if (header === 'NF_61_ Imoveis') {
      return generalTotals[headers.indexOf('Valor_Negocio')] !== 0
        ? generalTotals[headers.indexOf('NF_61_ Imoveis')] / generalTotals[headers.indexOf('Valor_Negocio')]
        : '';
    }
    if (header === 'Liquido_61') {
      return generalTotals[headers.indexOf('Valor_Negocio')] !== 0
        ? generalTotals[headers.indexOf('Liquido_61')] / generalTotals[headers.indexOf('Valor_Negocio')]
        : '';
    }
    return '';
  });

  const generalRelPercentRow = currentRow + 2;
  controlSheet.getRange(generalRelPercentRow, 1, 1, headers.length).setValues([['Rel. Percent.', ...generalRelationPercent.slice(1)]]);

  // Coloca a linha de "Rel. Percent." para o total geral em negrito e itálico
  controlSheet.getRange(generalRelPercentRow, 1, 1, headers.length).setFontWeight('bold').setFontStyle('italic');

  // Formata as colunas numéricas como moeda
  headers.forEach((header, index) => {
    const colIndex = index + 1;
    if (numericColumns.includes(header)) {
      controlSheet.getRange(6, colIndex, lastRow - 5).setNumberFormat('R$ #,##0.00');
      controlSheet.getRange(generalTotalRow, colIndex).setNumberFormat('R$ #,##0.00'); // Formata o Total Geral como monetário
    }
  });

  // Agora vamos procurar todas as linhas que possuem "Rel. Percent." na coluna A e formatar essas linhas como percentuais.
  for (let row = 6; row <= controlSheet.getLastRow(); row++) {
    const cellValue = controlSheet.getRange(row, 1).getValue();
    if (cellValue === 'Rel. Percent.') {
      controlSheet.getRange(row, 2, 1, headers.length - 1).setNumberFormat('0.00%');
    }
  }

  // Adiciona bordas aos totais e ao total geral
  controlSheet.getRange(generalTotalRow, 1, 1, headers.length).setBorder(true, true, true, true, true, true);
  controlSheet.getRange(generalRelPercentRow, 1, 1, headers.length).setBorder(true, true, true, true, true, true); // Borda para "Rel. Percent."
}

