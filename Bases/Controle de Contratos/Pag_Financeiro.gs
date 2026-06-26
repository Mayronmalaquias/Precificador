function runFilterAndTransferFinanceiro() {
  const financeiroSpreadsheetId = "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y";
  const vendasSpreadsheetId = "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y";
  const recebidosSpreadsheetId = "151HXN4U-iFi3LnlxB7UefJ_RP6sX9Aw3ygbYFVX2DbY";
  const controlSheetName = 'Financeiro';
  const sourceSheetName = 'Vendas';
  const recebidosSheetName = 'Recebidos';

  const financeiroSs = SpreadsheetApp.openById(financeiroSpreadsheetId);
  const vendasSs = SpreadsheetApp.openById(vendasSpreadsheetId);
  const recebidosSs = SpreadsheetApp.openById(recebidosSpreadsheetId);

  const controlSheet = financeiroSs.getSheetByName(controlSheetName);
  const sourceSheet = vendasSs.getSheetByName(sourceSheetName);
  const recebidosSheet = recebidosSs.getSheetByName(recebidosSheetName);

  clearFormatting(controlSheet);

  const startDate = parseDate(controlSheet.getRange('A2').getValue());
  const endDate = parseDate(controlSheet.getRange('B2').getValue());

  const columnsToCopy = ['Id_Contrato', 'Data_Contrato', 'Contrato', 'Valor_Total_61', 'NF_61_ Imoveis'];
  const dateColumn = 'Data_Contrato';

  const headers = sourceSheet.getRange(1, 1, 1, sourceSheet.getLastColumn()).getValues()[0];
  const columnIndexes = columnsToCopy.map(column => headers.indexOf(column) + 1);
  const dateColIndex = headers.indexOf(dateColumn);

  if (dateColIndex === -1) {
    throw new Error('Coluna de datas não encontrada.');
  }

  const dataParcelaColumn = 'Data_Parcela';
  const valorParcelaColumn = 'Valor_Parcela';
  const recebidoColumn = 'Recebido';
  const dataRecebimentoColumn = 'Data_Recebimento';
  const saldoFinalColumn = 'Saldo_Final';

  const lastRow = controlSheet.getLastRow();
  if (lastRow > 5) {
    controlSheet.getRange(6, 1, lastRow - 5, controlSheet.getLastColumn()).clearContent();
  }

  const dataRange = sourceSheet.getDataRange();
  const data = dataRange.getValues();
  
  const recebidosData = recebidosSheet.getDataRange().getValues();
  const recebidosHeaders = recebidosData[0];
  const recebidoDataIndex = recebidosHeaders.indexOf("Data");
  const recebidoContratoIndex = recebidosHeaders.indexOf("Num_Contrato");
  const recebidoValorIndex = recebidosHeaders.indexOf("Valor_Recebido");

  const newHeaders = [...columnsToCopy, dataParcelaColumn, valorParcelaColumn, recebidoColumn, dataRecebimentoColumn, saldoFinalColumn];
  controlSheet.getRange(5, 1, 1, newHeaders.length).setValues([newHeaders]);

  const filteredData = [];
  let antecipadosData = [];
  let atrasadosData = [];

  data.forEach((row, index) => {
    if (index === 0) return;

    const baseData = columnIndexes.map(index => row[index - 1]);
    const dataParcelas = [
      parseDate(row[headers.indexOf('Data_Parcela1_Comissão')]),
      parseDate(row[headers.indexOf('Data_Parcela2_Comissão')]),
      parseDate(row[headers.indexOf('Data_Parcela3_Comissão')]),
      parseDate(row[headers.indexOf('Data_Parcela4_Comissão')]),
      parseDate(row[headers.indexOf('Data_Parcela5_Comissão')])
    ];

    const valorParcelas = [
      row[headers.indexOf('Valor_Parcela_Comissao_1')],
      row[headers.indexOf('Valor_Parcela_Comissao_2')],
      row[headers.indexOf('Valor_Parcela_Comissao_3')],
      row[headers.indexOf('Valor_Parcela_Comissao_4')],
      row[headers.indexOf('Valor_Parcela_Comissao_5')]
    ];

    dataParcelas.forEach((parcelaDate, i) => {
      if (parcelaDate && parcelaDate >= startDate && parcelaDate <= endDate) {
        const [recebido, dataPagamento] = getRecebidoStatus(recebidosData, row[headers.indexOf('Id_Contrato')], parcelaDate, recebidoDataIndex, recebidoContratoIndex, recebidoValorIndex);
        const saldoFinal = (valorParcelas[i] || 0) - (recebido || 0);

        if (recebido) {
          const pagamentoInfo = {
            contrato: row[headers.indexOf('Id_Contrato')],
            valorRecebido: recebido,
            dataPagamento: formatDate(dataPagamento),
            dataParcelaPrevista: formatDate(parcelaDate)
          };

          if (dataPagamento < parcelaDate) {
            antecipadosData.push(pagamentoInfo);
          } else if (dataPagamento > parcelaDate) {
            atrasadosData.push(pagamentoInfo);
          }
        }

        filteredData.push([...baseData, parcelaDate, valorParcelas[i] || '', recebido || 0, dataPagamento || '', saldoFinal]);
      }
    });
  });

  filteredData.sort((a, b) => a[a.length - 5] - b[a.length - 5]);

  let currentRow = 6;
  let currentMonth = '';
  let monthData = [];

  filteredData.forEach(row => {
    const parcelaDate = row[row.length - 5];
    const monthYear = `${parcelaDate.getMonth() + 1}/${parcelaDate.getFullYear()}`;

    if (currentMonth !== monthYear) {
      if (currentMonth !== '') {
        insertMonthTotals(controlSheet, monthData, newHeaders, currentRow);
        currentRow += 5;
        monthData = [];
      }
      currentMonth = monthYear;
    }

    controlSheet.getRange(currentRow, 1, 1, newHeaders.length).setValues([row]);
    monthData.push(row);
    currentRow++;
  });

  if (monthData.length > 0) {
    insertMonthTotals(controlSheet, monthData, newHeaders, currentRow);
  }

  controlSheet.getRange(6, 1, currentRow - 6, newHeaders.length).setBorder(true, true, true, true, true, true);
  applyFinalFormatting(controlSheet);
  showPagamentosPopup(antecipadosData, atrasadosData);
}

function clearFormatting(sheet) {
  const range = sheet.getRange(6, 1, sheet.getLastRow() - 5, sheet.getLastColumn());
  range.setNumberFormat("@").setFontWeight("normal");
}

function applyFinalFormatting(sheet) {
  const rangeDataParcela = sheet.getRange(6, 6, sheet.getLastRow() - 5);
  const rangeValorParcela = sheet.getRange(6, 7, sheet.getLastRow() - 5);
  const rangeRecebido = sheet.getRange(6, 8, sheet.getLastRow() - 5);
  const rangeDataRecebimento = sheet.getRange(6, 9, sheet.getLastRow() - 5);
  const rangeSaldoFinal = sheet.getRange(6, 10, sheet.getLastRow() - 5);
  const rangeValorTotal = sheet.getRange(6, 4, sheet.getLastRow() - 5);
  const rangeNFImoveis = sheet.getRange(6, 5, sheet.getLastRow() - 5);

  rangeDataParcela.setNumberFormat("dd/MM/yyyy");
  rangeValorParcela.setNumberFormat("R$ #,##0.00");
  rangeRecebido.setNumberFormat("R$ #,##0.00");
  rangeDataRecebimento.setNumberFormat("dd/MM/yyyy");
  rangeSaldoFinal.setNumberFormat("R$ #,##0.00");
  rangeValorTotal.setNumberFormat("R$ #,##0.00");
  rangeNFImoveis.setNumberFormat("R$ #,##0.00");

  const lastRow = sheet.getLastRow();
  const recebidoColIndex = 8;

  const rangeColumnA = sheet.getRange("A6:A" + lastRow);
  const valuesColumnA = rangeColumnA.getValues();

  valuesColumnA.forEach((row, index) => {
    if (row[0] === "Rel. Percent.") {
      const rowIndex = index + 6;
      sheet.getRange(rowIndex, recebidoColIndex).setNumberFormat("0.00%").setFontWeight("bold");
    }
  });
}

function getRecebidoStatus(recebidosData, contratoId, parcelaDate, dataIndex, contratoIndex, valorIndex) {
  let recebido = 0;
  let dataPagamento = null;

  for (let i = 1; i < recebidosData.length; i++) {
    const [recDate, recContrato, recValor] = [recebidosData[i][dataIndex], recebidosData[i][contratoIndex], recebidosData[i][valorIndex]];
    const recDateObj = adjustDateForTimezone(new Date(recDate));

    if (recContrato === contratoId) {
      const valorRecebido = parseFloat(recValor) || 0;

      if (recDateObj <= parcelaDate) {
        recebido += valorRecebido;
        dataPagamento = recDateObj;
      } else if (recDateObj > parcelaDate) {
        recebido += valorRecebido;
        dataPagamento = recDateObj;
      }
    }
  }

  return [recebido, dataPagamento];
}

function insertMonthTotals(sheet, monthData, headers, currentRow) {
  const numericColumns = ['Valor_Total_61', 'NF_61_ Imoveis', 'Valor_Parcela', 'Recebido', 'Saldo_Final'];
  const totals = headers.map((header, index) => numericColumns.includes(header) ? monthData.reduce((acc, row) => acc + (parseFloat(row[index]) || 0), 0) : '');
  sheet.getRange(currentRow + 1, 1, 1, headers.length).setValues([['Totais', ...totals.slice(1)]]);
  sheet.getRange(currentRow + 1, 1, 1, headers.length).setFontWeight("bold");

  const totalRecebido = totals[headers.indexOf("Recebido")];
  const totalParcela = totals[headers.indexOf("Valor_Parcela")];
  const relPercent = totalParcela ? totalRecebido / totalParcela : 0;

  const relPercentRow = Array(headers.length).fill('');
  relPercentRow[headers.indexOf("Recebido")] = relPercent;

  sheet.getRange(currentRow + 2, 1, 1, headers.length).setValues([['Rel. Percent.', ...relPercentRow.slice(1)]]);
  sheet.getRange(currentRow + 2, headers.indexOf("Recebido") + 1).setNumberFormat("0.00%");
  sheet.getRange(currentRow + 2, 1, 1, headers.length).setFontWeight("bold");
}

function parseDate(dateString) {
  if (typeof dateString === 'string') {
    const [year, month, day] = dateString.split('-').map(Number);
    return new Date(year, month - 1, day);
  } else if (dateString instanceof Date) {
    return dateString;
  } else {
    throw new Error('Formato de data inválido.');
  }
}

function adjustDateForTimezone(date) {
  return new Date(date.getTime() + date.getTimezoneOffset() * 60 * 1000);
}

function formatDate(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), "dd/MM/yyyy");
}

function showPagamentosPopup(antecipadosData, atrasadosData) {
  let htmlContent = `
    <html>
      <body>
        <h3>Pagamentos Antecipados</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
          <tr>
            <th>Contrato</th>
            <th>Valor Recebido</th>
            <th>Data do Pagamento</th>
            <th>Data Parcela Prevista</th>
          </tr>`;
          
  antecipadosData.forEach(item => {
    htmlContent += `
      <tr>
        <td>${item.contrato}</td>
        <td>R$${item.valorRecebido.toFixed(2)}</td>
        <td>${item.dataPagamento}</td>
        <td>${item.dataParcelaPrevista}</td>
      </tr>`;
  });

  htmlContent += `
        </table>
        <h3>Pagamentos Atrasados</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
          <tr>
            <th>Contrato</th>
            <th>Valor Recebido</th>
            <th>Data do Pagamento</th>
            <th>Data Parcela Prevista</th>
          </tr>`;

  atrasadosData.forEach(item => {
    htmlContent += `
      <tr>
        <td>${item.contrato}</td>
        <td>R$${item.valorRecebido.toFixed(2)}</td>
        <td>${item.dataPagamento}</td>
        <td>${item.dataParcelaPrevista}</td>
      </tr>`;
  });

  htmlContent += `
        </table>
      </body>
    </html>`;

  const htmlOutput = HtmlService.createHtmlOutput(htmlContent).setWidth(500).setHeight(400);
  SpreadsheetApp.getUi().showModalDialog(htmlOutput, 'Pagamentos Antecipados e Atrasados');
}
