// ════════════════════════════════════════════════════════════════════════════
//  runFilterAndTransfer1 — com toNum() robusto para pt-BR e en-US
//
//  Ajustes:
//    1. %_empresa_61 agora fica antes de %_Diretor no relatório Controle.
//    2. %_empresa_61 é calculado sobre Valor_Total_61.
//    3. Valor_Total_61 é a base interna da 61.
//    4. Valor_Comissao continua sendo a comissão total da venda.
// ════════════════════════════════════════════════════════════════════════════

function runFilterAndTransfer1() {
  const SPREADSHEET_ID   = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';
  const controlSheetName = 'Controle';
  const sourceSheetName  = 'Vendas';

  const ss           = SpreadsheetApp.openById(SPREADSHEET_ID);
  const controlSheet = ss.getSheetByName(controlSheetName);
  const sourceSheet  = ss.getSheetByName(sourceSheetName);

  limparFormatacao();

  const startDate = new Date(controlSheet.getRange('A2').getValue());
  const endDate   = new Date(controlSheet.getRange('B2').getValue());

  const columnsToCopy = [
    'Id_Contrato', 'Data_Contrato', 'Contrato',
    'Valor_Negocio', 'Valor_Comissao', 'Valor_Total_61',
    'NF_61_ Imoveis', 'Liquido_61',
    '%_Gerente_Venda', '%_Gerente_Captacao', '%_Diretor',
    '%_Corretor_Venda_1', '%_Corretor_Venda_2',
    '%_Corretor_Captação_1', '%_Corretor_Captação_2',
    '$_Gerente_Venda',    'Gerente_Venda_Nome',
    '$_Gerente_Captacao', 'Gerente_Captacao_Nome',
    '$_Diretor',          'Diretor_Nome',
    '$_Corretor_Venda_1', 'Corretor_Venda_1_Nome',
    '$_Corretor_Venda_2', 'Corretor_Venda_2_Nome',
    '$_Corretor_Captador_1', 'Corretor_Captador_1_Nome',
    '$_Corretor_Captador_2', 'Corretor_Captador_2_Nome'
  ];

  // Índices dentro de columnsToCopy
  const IDX_VC    = columnsToCopy.indexOf('Valor_Comissao');
  const IDX_VT61  = columnsToCopy.indexOf('Valor_Total_61');
  const IDX_GV    = columnsToCopy.indexOf('$_Gerente_Venda');
  const IDX_GC    = columnsToCopy.indexOf('$_Gerente_Captacao');
  const IDX_DIR   = columnsToCopy.indexOf('$_Diretor');
  const IDX_CV1   = columnsToCopy.indexOf('$_Corretor_Venda_1');
  const IDX_CV2   = columnsToCopy.indexOf('$_Corretor_Venda_2');
  const IDX_CC1   = columnsToCopy.indexOf('$_Corretor_Captador_1');
  const IDX_CC2   = columnsToCopy.indexOf('$_Corretor_Captador_2');
  const IDX_LIQ   = columnsToCopy.indexOf('Liquido_61');

  // Posição onde a coluna %_empresa_61 deve entrar no relatório Controle.
  // Ela ficará antes de %_Diretor.
  const INSERT_PCT_EMP_AT = columnsToCopy.indexOf('%_Diretor');

  if (INSERT_PCT_EMP_AT === -1) {
    throw new Error('Coluna %_Diretor não encontrada em columnsToCopy.');
  }

  const headers = sourceSheet.getRange(1, 1, 1, sourceSheet.getLastColumn()).getValues()[0];

  const missingColumns = columnsToCopy.filter(col => headers.indexOf(col) === -1);
  if (missingColumns.length > 0) {
    throw new Error(
      'As seguintes colunas não foram encontradas na aba Vendas:\n' +
      missingColumns.join('\n')
    );
  }

  const columnIndexes = columnsToCopy.map(col => headers.indexOf(col) + 1);
  const dateColIndex  = headers.indexOf('Data_Contrato');

  if (dateColIndex === -1) {
    throw new Error('Coluna Data_Contrato não encontrada na aba Vendas.');
  }

  // Limpa conteúdo antigo da linha 5 em diante
  const lastRow = controlSheet.getLastRow();
  if (lastRow > 4) {
    controlSheet.getRange(5, 1, lastRow - 4, controlSheet.getLastColumn()).clearContent();
  }

  const data = sourceSheet.getDataRange().getValues();

  const filteredData = data.filter((row, index) => {
    if (index === 0) return true;

    const date = new Date(row[dateColIndex]);
    return date >= startDate && date <= endDate;
  });

  const groupedData = {};

  filteredData.slice(1).forEach(row => {
    const date      = new Date(row[dateColIndex]);
    const monthYear = `${date.getMonth() + 1}/${date.getFullYear()}`;

    if (!groupedData[monthYear]) {
      groupedData[monthYear] = [];
    }

    groupedData[monthYear].push(row);
  });

  let currentRow = 5;

  const managerNames = [
    'José Marques', 'Marcelo Souza', 'Luana Salvinski',
    'Thais Tannús', 'Marcelo Pincinato', 'Helio Junio', 'Paolla Gardenia'
  ];

  // Cabeçalho base com as colunas copiadas
  const headerBase = columnIndexes.map(idx => headers[idx - 1]);

  // Insere %_empresa_61 antes de %_Diretor
  headerBase.splice(INSERT_PCT_EMP_AT, 0, '%_empresa_61');

  // Cabeçalho final: colunas da venda + gerentes
  const headerRow = [
    ...headerBase,
    ...managerNames
  ];

  controlSheet.getRange(currentRow, 1, 1, headerRow.length).setValues([headerRow]);
  currentRow++;

  // ── Transferência mês a mês ───────────────────────────────────────────────
  for (const monthYear in groupedData) {
    const monthData = groupedData[monthYear].map(row => {
      const rowData = columnIndexes.map(idx => row[idx - 1]);

      // ── toNum ROBUSTO: distingue pt-BR de en-US ───────────────────────────
      function toNum(v) {
        if (v === null || v === undefined || v === '' || v === '-' || v === '—') {
          return 0;
        }

        if (typeof v === 'number') {
          return isNaN(v) ? 0 : v;
        }

        let s = String(v)
          .replace(/R\$\s*/g, '')
          .replace(/\s/g, '')
          .trim();

        if (s === '' || s === '-' || s === '—') {
          return 0;
        }

        const hasComma = s.indexOf(',') !== -1;
        const hasDot   = s.indexOf('.') !== -1;

        if (hasComma && hasDot) {
          // O último separador indica o decimal
          if (s.lastIndexOf(',') > s.lastIndexOf('.')) {
            // pt-BR: 1.234,56 → 1234.56
            s = s.replace(/\./g, '').replace(',', '.');
          } else {
            // en-US: 1,234.56 → 1234.56
            s = s.replace(/,/g, '');
          }
        } else if (hasComma) {
          // pt-BR decimal: 1234,56 → 1234.56
          s = s.replace(/\./g, '').replace(',', '.');
        } else if (hasDot) {
          const dots = (s.match(/\./g) || []).length;

          if (dots === 1) {
            // Mantém como decimal, ex: 21351.33
          } else {
            // Milhar pt-BR sem vírgula: 1.234.567 → 1234567
            s = s.replace(/\./g, '');
          }
        }

        const n = parseFloat(s);
        return isNaN(n) ? 0 : n;
      }

      // % empresa 61 = (Valor_Total_61 − total atribuído) / Valor_Total_61
      const valorTotal61 = toNum(rowData[IDX_VT61]);

      const totalAtr = toNum(rowData[IDX_GV])  +
                       toNum(rowData[IDX_GC])  +
                       toNum(rowData[IDX_DIR]) +
                       toNum(rowData[IDX_CV1]) +
                       toNum(rowData[IDX_CV2]) +
                       toNum(rowData[IDX_CC1]) +
                       toNum(rowData[IDX_CC2]);

      const pctEmpresa = valorTotal61 > 0
        ? (valorTotal61 - totalAtr) / valorTotal61
        : 0;

      // Distribuição do Líquido 61 pelos gerentes envolvidos
      const gerenteVendaNome    = rowData[columnsToCopy.indexOf('Gerente_Venda_Nome')];
      const gerenteCaptacaoNome = rowData[columnsToCopy.indexOf('Gerente_Captacao_Nome')];
      const valorLiquido61      = toNum(rowData[IDX_LIQ]);

      const valoresGerentes           = new Array(managerNames.length).fill(0);
      const gerentesEnvolvidosIndexes = [];

      if (gerenteVendaNome === 'José Marques'      || gerenteCaptacaoNome === 'José Marques')      gerentesEnvolvidosIndexes.push(0);
      if (gerenteVendaNome === 'Marcelo Souza'     || gerenteCaptacaoNome === 'Marcelo Souza')     gerentesEnvolvidosIndexes.push(1);
      if (gerenteVendaNome === 'Luana Salvinski'   || gerenteCaptacaoNome === 'Luana Salvinski')   gerentesEnvolvidosIndexes.push(2);
      if (gerenteVendaNome === 'Thais Tannús'      || gerenteCaptacaoNome === 'Thais Tannús')      gerentesEnvolvidosIndexes.push(3);
      if (gerenteVendaNome === 'Marcelo Pincinato' || gerenteCaptacaoNome === 'Marcelo Pincinato') gerentesEnvolvidosIndexes.push(4);
      if (gerenteVendaNome === 'Helio Junio'       || gerenteCaptacaoNome === 'Helio Junio')       gerentesEnvolvidosIndexes.push(5);
      if (gerenteVendaNome === 'Paolla Gardenia'   || gerenteCaptacaoNome === 'Paolla Gardenia')   gerentesEnvolvidosIndexes.push(6);

      if (gerentesEnvolvidosIndexes.length > 0) {
        const valorDividido = valorLiquido61 / gerentesEnvolvidosIndexes.length;

        gerentesEnvolvidosIndexes.forEach(idx => {
          valoresGerentes[idx] = valorDividido;
        });
      }

      // Insere %_empresa_61 antes de %_Diretor na linha de dados
      const rowDataComEmpresa = [...rowData];
      rowDataComEmpresa.splice(INSERT_PCT_EMP_AT, 0, pctEmpresa);

      return [
        ...rowDataComEmpresa,
        ...valoresGerentes
      ];
    });

    controlSheet
      .getRange(currentRow, 1, monthData.length, headerRow.length)
      .setValues(monthData);

    currentRow += monthData.length + 7;
  }

  // Bordas
  controlSheet
    .getRange(5, 1, currentRow - 5, headerRow.length)
    .setBorder(true, true, true, true, true, true);

  aplicarFormatacaoColunas(controlSheet, columnsToCopy, currentRow, managerNames);

  Utilities.sleep(3000);
  calculateAndInsertTotalsWithManagers();
}


// ════════════════════════════════════════════════════════════════════════════
//  Utilitários
// ════════════════════════════════════════════════════════════════════════════

function getColumnLetter(columnNumber) {
  let temp;
  let letter = '';

  while (columnNumber > 0) {
    temp = (columnNumber - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    columnNumber = (columnNumber - temp - 1) / 26;
  }

  return letter;
}


// ════════════════════════════════════════════════════════════════════════════
//  Formatação de colunas monetárias e percentuais
// ════════════════════════════════════════════════════════════════════════════

function aplicarFormatacaoColunas(sheet, columnsToCopy, lastDataRow, managerNames) {
  const currencyColumns = [
    'Valor_Negocio', 'Valor_Comissao', 'Valor_Total_61',
    'NF_61_ Imoveis', 'Liquido_61',
    '$_Gerente_Venda', '$_Gerente_Captacao', '$_Diretor',
    '$_Corretor_Venda_1', '$_Corretor_Venda_2',
    '$_Corretor_Captador_1', '$_Corretor_Captador_2',
    ...managerNames
  ];

  const percentageColumns = [
    '%_empresa_61',
    '%_Gerente_Venda', '%_Gerente_Captacao', '%_Diretor',
    '%_Corretor_Venda_1', '%_Corretor_Venda_2',
    '%_Corretor_Captação_1', '%_Corretor_Captação_2'
  ];

  const headersOnSheet = sheet.getRange(5, 1, 1, sheet.getLastColumn()).getValues()[0];

  headersOnSheet.forEach((header, index) => {
    const colLetter = getColumnLetter(index + 1);
    const range = sheet.getRange(`${colLetter}6:${colLetter}${lastDataRow - 8}`);

    if (currencyColumns.includes(header)) {
      range.setNumberFormat('R$ #,##0.00');
    } else if (percentageColumns.includes(header)) {
      range.setNumberFormat('0.00%');
    }
  });
}


// ════════════════════════════════════════════════════════════════════════════
//  Limpar formatação
// ════════════════════════════════════════════════════════════════════════════

function limparFormatacao() {
  const SPREADSHEET_ID = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';
  const controlSheet   = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName('Controle');

  const lastRow    = controlSheet.getLastRow();
  const lastColumn = controlSheet.getLastColumn();

  if (lastRow >= 5) {
    const range = controlSheet.getRange(5, 1, lastRow - 4, lastColumn);

    range.setFontWeight('normal');
    range.setFontStyle('normal');
    range.clearContent();
  }
}


// ════════════════════════════════════════════════════════════════════════════
//  Totais mensais e anuais
// ════════════════════════════════════════════════════════════════════════════

function calculateAndInsertTotalsWithManagers() {
  const SPREADSHEET_ID = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';
  const controlSheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName('Controle');

  const headers = controlSheet.getRange(5, 1, 1, controlSheet.getLastColumn()).getValues()[0];

  const managerNames = [
    'José Marques', 'Marcelo Souza', 'Luana Salvinski',
    'Thais Tannús', 'Marcelo Pincinato', 'Helio Junio', 'Paolla Gardenia'
  ];

  // Colunas somadas nos totais
  // %_empresa_61 é tratada separadamente como média ponderada por Valor_Total_61.
  const numericColumns = [
    'Valor_Negocio', 'Valor_Comissao', 'Valor_Total_61',
    'NF_61_ Imoveis', 'Liquido_61',
    ...managerNames
  ];

  const directorExcludedManagerIndexes = managerNames.map((_, i) => i);

  const IDX_PCT_EMP    = headers.indexOf('%_empresa_61');
  const IDX_VT61_HDR   = headers.indexOf('Valor_Total_61');

  let currentRow          = 6;
  const lastRow           = controlSheet.getLastRow();

  let overallTotals       = headers.map(() => 0);
  let overallVT61Sum      = 0;
  let overallVT61xPct     = 0;

  let totalDiretorPPAccum = headers.map(() => 0);
  let totalDiretorACAccum = headers.map(() => 0);

  while (currentRow <= lastRow) {
    const monthData = [];

    while (
      currentRow <= lastRow &&
      controlSheet.getRange(currentRow, 1).getValue() !== ''
    ) {
      monthData.push(
        controlSheet.getRange(currentRow, 1, 1, headers.length).getValues()[0]
      );
      currentRow++;
    }

    if (monthData.length === 0) {
      currentRow++;
      continue;
    }

    // ── Totais numéricos do mês ─────────────────────────────────────────────
    const totals = headers.map((header, index) => {
      if (numericColumns.includes(header)) {
        const sum = monthData.reduce((acc, row) => {
          return acc + (parseFloat(row[index]) || 0);
        }, 0);

        overallTotals[index] += sum;
        return sum;
      }

      return '';
    });

    // ── % empresa: média ponderada pelo Valor_Total_61 ─────────────────────
    let mesVT61 = 0;
    let mesVT61xPct = 0;

    if (IDX_PCT_EMP !== -1 && IDX_VT61_HDR !== -1) {
      monthData.forEach(row => {
        const vt61 = parseFloat(row[IDX_VT61_HDR]) || 0;
        const pct  = parseFloat(row[IDX_PCT_EMP]) || 0;

        mesVT61     += vt61;
        mesVT61xPct += vt61 * pct;
      });

      overallVT61Sum  += mesVT61;
      overallVT61xPct += mesVT61xPct;
    }

    const pctEmpresaMes = mesVT61 > 0 ? mesVT61xPct / mesVT61 : 0;

    // ── Linha Total ─────────────────────────────────────────────────────────
    const totalRow = [
      'Total',
      ...totals.slice(1)
    ];

    if (IDX_PCT_EMP !== -1) {
      totalRow[IDX_PCT_EMP] = pctEmpresaMes;
    }

    controlSheet
      .getRange(currentRow + 1, 1, 1, headers.length)
      .setValues([totalRow]);

    controlSheet
      .getRange(currentRow + 1, 1, 1, headers.length)
      .setFontWeight('bold')
      .setFontStyle('italic');

    controlSheet
      .getRange(currentRow + 1, 2, 1, headers.length - 1)
      .setNumberFormat('R$ #,##0.00');

    if (IDX_PCT_EMP !== -1) {
      controlSheet
        .getRange(currentRow + 1, IDX_PCT_EMP + 1)
        .setNumberFormat('0.00%');
    }

    // ── Linha Rel. Percent. ─────────────────────────────────────────────────
    const negocioIdx = headers.indexOf('Valor_Negocio');

    const relationPercent = headers.map((header, index) => {
      if (numericColumns.includes(header) && index !== negocioIdx) {
        return totals[negocioIdx] !== 0
          ? totals[index] / totals[negocioIdx]
          : '';
      }

      return '';
    });

    if (IDX_PCT_EMP !== -1) {
      relationPercent[IDX_PCT_EMP] = pctEmpresaMes;
    }

    controlSheet
      .getRange(currentRow + 2, 1, 1, headers.length)
      .setValues([
        ['Rel. Percent.', ...relationPercent.slice(1)]
      ]);

    controlSheet
      .getRange(currentRow + 2, 1, 1, headers.length)
      .setFontWeight('bold')
      .setFontStyle('italic');

    controlSheet
      .getRange(currentRow + 2, 2, 1, headers.length - 1)
      .setNumberFormat('0.00%');

    // ── Total Diretor PP ───────────────────────────────────────────────────
    const totalDiretorPP = headers.map((header, colIndex) => {
      const mgrIdx = managerNames.indexOf(header);
      const isExcluded = directorExcludedManagerIndexes.includes(mgrIdx);

      if (numericColumns.includes(header) && !isExcluded) {
        return monthData
          .filter(row => {
            const dirNome = row[headers.indexOf('Diretor_Nome')];
            const gvNome  = row[headers.indexOf('Gerente_Venda_Nome')];
            const gcNome  = row[headers.indexOf('Gerente_Captacao_Nome')];

            return dirNome &&
              (
                gvNome === 'Marcelo Souza' ||
                gcNome === 'Thais Tannús' ||
                gvNome === '' ||
                gcNome === ''
              );
          })
          .reduce((acc, row) => {
            return acc + (parseFloat(row[colIndex]) || 0);
          }, 0);
      }

      return '';
    });

    controlSheet
      .getRange(currentRow + 3, 1, 1, headers.length)
      .setValues([
        ['Total Diretor PP', ...totalDiretorPP.slice(1)]
      ]);

    controlSheet
      .getRange(currentRow + 3, 1, 1, headers.length)
      .setFontWeight('bold');

    controlSheet
      .getRange(currentRow + 3, 2, 1, headers.length - 1)
      .setNumberFormat('R$ #,##0.00');

    totalDiretorPPAccum = totalDiretorPPAccum.map((v, i) => {
      return v + (parseFloat(totalDiretorPP[i]) || 0);
    });

    // ── Total Diretor AC ───────────────────────────────────────────────────
    const totalDiretorAC = headers.map((header, colIndex) => {
      const mgrIdx = managerNames.indexOf(header);
      const isExcluded = directorExcludedManagerIndexes.includes(mgrIdx);

      if (numericColumns.includes(header) && !isExcluded) {
        return monthData
          .filter(row => {
            const gvNome = row[headers.indexOf('Gerente_Venda_Nome')];
            const gcNome = row[headers.indexOf('Gerente_Captacao_Nome')];

            return gvNome === 'Luana Salvinski' || gcNome === 'Luana Salvinski';
          })
          .reduce((acc, row) => {
            return acc + (parseFloat(row[colIndex]) || 0);
          }, 0);
      }

      return '';
    });

    controlSheet
      .getRange(currentRow + 4, 1, 1, headers.length)
      .setValues([
        ['Total Diretor AC', ...totalDiretorAC.slice(1)]
      ]);

    controlSheet
      .getRange(currentRow + 4, 1, 1, headers.length)
      .setFontWeight('bold');

    controlSheet
      .getRange(currentRow + 4, 2, 1, headers.length - 1)
      .setNumberFormat('R$ #,##0.00');

    totalDiretorACAccum = totalDiretorACAccum.map((v, i) => {
      return v + (parseFloat(totalDiretorAC[i]) || 0);
    });

    currentRow += 7;
  }

  // ── % empresa anual ──────────────────────────────────────────────────────
  const pctEmpresaAnual = overallVT61Sum > 0
    ? overallVT61xPct / overallVT61Sum
    : 0;

  // ── Total Anual ──────────────────────────────────────────────────────────
  const generalTotals = overallTotals.map((total, index) => {
    return numericColumns.includes(headers[index]) ? total : '';
  });

  if (IDX_PCT_EMP !== -1) {
    generalTotals[IDX_PCT_EMP] = pctEmpresaAnual;
  }

  controlSheet
    .getRange(currentRow + 1, 1, 1, headers.length)
    .setValues([
      ['Total Anual', ...generalTotals.slice(1)]
    ]);

  controlSheet
    .getRange(currentRow + 1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setFontStyle('italic');

  controlSheet
    .getRange(currentRow + 1, 2, 1, headers.length - 1)
    .setNumberFormat('R$ #,##0.00');

  if (IDX_PCT_EMP !== -1) {
    controlSheet
      .getRange(currentRow + 1, IDX_PCT_EMP + 1)
      .setNumberFormat('0.00%');
  }

  // ── Rel. Percent. Anual ─────────────────────────────────────────────────
  const negocioIdxGlobal = headers.indexOf('Valor_Negocio');

  const generalRelationPercent = headers.map((header, index) => {
    if (numericColumns.includes(header) && index !== negocioIdxGlobal) {
      return generalTotals[negocioIdxGlobal] !== 0
        ? generalTotals[index] / generalTotals[negocioIdxGlobal]
        : '';
    }

    return '';
  });

  if (IDX_PCT_EMP !== -1) {
    generalRelationPercent[IDX_PCT_EMP] = pctEmpresaAnual;
  }

  controlSheet
    .getRange(currentRow + 2, 1, 1, headers.length)
    .setValues([
      ['Rel. Percent. Anual', ...generalRelationPercent.slice(1)]
    ]);

  controlSheet
    .getRange(currentRow + 2, 1, 1, headers.length)
    .setFontWeight('bold')
    .setFontStyle('italic');

  controlSheet
    .getRange(currentRow + 2, 2, 1, headers.length - 1)
    .setNumberFormat('0.00%');

  // ── Total Anual Diretor PP ───────────────────────────────────────────────
  const totalAnualDiretorPP = totalDiretorPPAccum.map((value, index) => {
    const mgrIdx = managerNames.indexOf(headers[index]);
    const isExcluded = directorExcludedManagerIndexes.includes(mgrIdx);

    return numericColumns.includes(headers[index]) && !isExcluded
      ? value
      : '';
  });

  controlSheet
    .getRange(currentRow + 3, 1, 1, headers.length)
    .setValues([
      ['Total Anual Diretor PP', ...totalAnualDiretorPP.slice(1)]
    ]);

  controlSheet
    .getRange(currentRow + 3, 1, 1, headers.length)
    .setFontWeight('bold');

  controlSheet
    .getRange(currentRow + 3, 2, 1, headers.length - 1)
    .setNumberFormat('R$ #,##0.00');

  // ── Total Anual Diretor AC ───────────────────────────────────────────────
  const totalAnualDiretorAC = totalDiretorACAccum.map((value, index) => {
    const mgrIdx = managerNames.indexOf(headers[index]);
    const isExcluded = directorExcludedManagerIndexes.includes(mgrIdx);

    return numericColumns.includes(headers[index]) && !isExcluded
      ? value
      : '';
  });

  controlSheet
    .getRange(currentRow + 4, 1, 1, headers.length)
    .setValues([
      ['Total Anual Diretor AC', ...totalAnualDiretorAC.slice(1)]
    ]);

  controlSheet
    .getRange(currentRow + 4, 1, 1, headers.length)
    .setFontWeight('bold');

  controlSheet
    .getRange(currentRow + 4, 2, 1, headers.length - 1)
    .setNumberFormat('R$ #,##0.00');
}