/**************************************
 * Conversão numérica robusta
 **************************************/
function toNumberSafe(value) {
  if (value === null || value === '' || typeof value === 'undefined') {
    return 0;
  }

  // Já é número
  if (typeof value === 'number') {
    return isNaN(value) ? 0 : value;
  }

  // Datas indevidas em coluna monetária → 0
  if (value instanceof Date) {
    return 0;
  }

  // Checkbox, etc.
  if (typeof value === 'boolean') {
    return value ? 1 : 0;
  }

  var s = String(value).trim();
  if (s === '') {
    return 0;
  }

  // Erros de planilha (#NUM!, #DIV/0!, etc.)
  if (s.indexOf('#') !== -1) {
    return 0;
  }

  // Datas no formato brasileiro em texto (01/04/4187, 25/09/1914, etc.) → 0
  if (/^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(s)) {
    return 0;
  }

  // Remove espaços
  s = s.replace(/\s/g, '');

  // Remove qualquer coisa que não seja dígito, ponto, vírgula ou sinal
  // Isso tira "R$", "%", letras, etc.
  s = s.replace(/[^\d.,\-]/g, '');

  if (s === '' || s === '-' || s === '+') {
    return 0;
  }

  var hasComma = s.indexOf(',') !== -1;
  var hasDot   = s.indexOf('.') !== -1;

  if (hasComma && hasDot) {
    // Tem vírgula e ponto → o último símbolo é o decimal
    var lastComma = s.lastIndexOf(',');
    var lastDot   = s.lastIndexOf('.');
    if (lastComma > lastDot) {
      // Ex.: 1.234,56 → vírgula = decimal, ponto = milhar
      s = s.replace(/\./g, '');
      s = s.replace(',', '.');
    } else {
      // Ex.: 1,234.56 → ponto = decimal, vírgula = milhar
      s = s.replace(/,/g, '');
    }
  } else if (hasComma) {
    // Só vírgula → assume decimal BR
    s = s.replace(/\./g, '');
    s = s.replace(',', '.');
  } else {
    // Só ponto ou nenhum → remove vírgula sobrando (milhar)
    s = s.replace(/,/g, '');
  }

  var n = Number(s);
  return isNaN(n) ? 0 : n;
}

/**************************************
 * Conversão de valores de data em Date
 * (aceita Date ou string dd/MM/yyyy)
 **************************************/
function toDateSafe(value) {
  if (!value) return null;

  if (value instanceof Date) {
    return value;
  }

  var s = String(value).trim();
  if (s === '') return null;

  // dd/MM/yyyy
  var parts = s.split('/');
  if (parts.length === 3) {
    var dia = parseInt(parts[0], 10);
    var mes = parseInt(parts[1], 10) - 1;
    var ano = parseInt(parts[2], 10);
    if (!isNaN(dia) && !isNaN(mes) && !isNaN(ano)) {
      return new Date(ano, mes, dia);
    }
  }

  var t = Date.parse(s);
  if (!isNaN(t)) {
    return new Date(t);
  }

  return null;
}

/**************************************
 * Normalização de endereço / contrato
 **************************************/
function normalizeEndereco(valor) {
  if (valor === null || typeof valor === 'undefined') return '';
  var s = String(valor).toLowerCase();

  // Remove acentos
  if (s.normalize) {
    s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  // Mantém apenas letras, números e espaços
  s = s.replace(/[^a-z0-9]/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}

/**************************************
 * Mapeamento de colunas destino Fato_Venda
 **************************************/
var FATOVENDA_DESTINATION_COLUMNS = {
  Id_Contrato: 'BG',
  Data_Contrato: 'C',
  Contrato: 'F',
  Valor_Negocio: 'I',
  Valor_Comissao: 'J',
  Valor_Total_61: 'L',
  NF_61_Imoveis: 'P',
  Liquido_61: 'Q',
  Percent_Gerente_Venda: 'Z',
  Percent_Gerente_Captacao: 'AS',
  Percent_Corretor_Venda_1: 'W',
  Percent_Corretor_Venda_2: 'AF',
  Percent_Corretor_Cap_1: 'AP',
  Percent_Corretor_Cap_2: 'AY',
  Gerente_Venda_Nome: 'Y',
  $_Gerente_Venda: 'AA',
  Gerente_Captacao_Nome: 'AR',
  $_Gerente_Captacao: 'AT',
  Corretor_Venda_1_Nome: 'U',
  $_Corretor_Venda_1: 'X',
  Corretor_Venda_2_Nome: 'AE',
  $_Corretor_Venda_2: 'AG',
  Corretor_Captador_1_Nome: 'AN',
  $_Corretor_Captador_1: 'AQ',
  Corretor_Captador_2_Nome: 'AX',
  $_Corretor_Captador_2: 'AZ',
  neg_Gerado_V1: 'T',
  neg_Gerado_V2: 'AD',
  neg_Gerado_C1: 'AM',
  neg_Gerado_C2: 'AW',
  vgv_v1: 'S',
  vgv_v2: 'AC',
  vgv_c1: 'AL',
  vgv_c2: 'AV',
  percent_comissao_61: 'K',
  bairro: 'E',
  tipo: 'G'
};

/**************************************
 * Última linha usada em uma coluna específica
 **************************************/
function getLastRowInColumn(sheet, columnLetter) {
  var colValues = sheet.getRange(columnLetter + ':' + columnLetter).getValues();
  for (var i = colValues.length - 1; i >= 0; i--) {
    var v = colValues[i][0];
    if (v !== '' && v !== null && typeof v !== 'undefined') {
      return i + 1;
    }
  }
  return 0;
}

/**************************************
 * Monta mapa nome → id para Dim_Gerente / Dim_Corretor
 **************************************/
function buildNameToIdMap(sheet) {
  var map = {};
  if (!sheet) return map;

  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return map;

  var values = sheet.getRange('A2:B' + lastRow).getValues(); // A=id, B=nome
  for (var i = 0; i < values.length; i++) {
    var id   = values[i][0];
    var nome = values[i][1];
    if (nome !== '' && nome !== null && typeof nome !== 'undefined') {
      map[String(nome)] = id;
    }
  }
  return map;
}

/**************************************
 * Versão por linha (getRange) — usada em ranking()
 **************************************/
function buildFatoVendaDataFromSourceRow(sourceSheet, gerenteMap, corretorMap, rowIndex) {
  var gerenteVendaNome      = sourceSheet.getRange('P' + rowIndex).getValue();
  var gerenteCaptacaoNome   = sourceSheet.getRange('R' + rowIndex).getValue();
  var corretorVenda1Nome    = sourceSheet.getRange('V' + rowIndex).getValue();
  var corretorVenda2Nome    = sourceSheet.getRange('X' + rowIndex).getValue();
  var corretorCaptador1Nome = sourceSheet.getRange('Z' + rowIndex).getValue();
  var corretorCaptador2Nome = sourceSheet.getRange('AB' + rowIndex).getValue();

  var gerenteVendaId      = gerenteMap[String(gerenteVendaNome)]       || null;
  var gerenteCaptacaoId   = gerenteMap[String(gerenteCaptacaoNome)]    || null;
  var corretorVenda1Id    = corretorMap[String(corretorVenda1Nome)]    || null;
  var corretorVenda2Id    = corretorMap[String(corretorVenda2Nome)]    || null;
  var corretorCaptador1Id = corretorMap[String(corretorCaptador1Nome)] || null;
  var corretorCaptador2Id = corretorMap[String(corretorCaptador2Nome)] || null;

  var data = {
    Id_Contrato:     sourceSheet.getRange('A' + rowIndex).getValue(),
    Data_Contrato:   sourceSheet.getRange('B' + rowIndex).getValue(),
    Contrato:        sourceSheet.getRange('C' + rowIndex).getValue(),

    Valor_Negocio:   toNumberSafe(sourceSheet.getRange('D' + rowIndex).getValue()),
    Valor_Comissao:  toNumberSafe(sourceSheet.getRange('E' + rowIndex).getValue()),
    Valor_Total_61:  toNumberSafe(sourceSheet.getRange('F' + rowIndex).getValue()),
    NF_61_Imoveis:   toNumberSafe(sourceSheet.getRange('G' + rowIndex).getValue()),
    Liquido_61:      toNumberSafe(sourceSheet.getRange('BE' + rowIndex).getValue()),

    Percent_Gerente_Venda:      toNumberSafe(sourceSheet.getRange('H' + rowIndex).getValue()),
    Percent_Gerente_Captacao:   toNumberSafe(sourceSheet.getRange('I' + rowIndex).getValue()),
    Percent_Corretor_Venda_1:   toNumberSafe(sourceSheet.getRange('K' + rowIndex).getValue()),
    Percent_Corretor_Venda_2:   toNumberSafe(sourceSheet.getRange('M' + rowIndex).getValue()),
    Percent_Corretor_Cap_1:     toNumberSafe(sourceSheet.getRange('L' + rowIndex).getValue()),
    Percent_Corretor_Cap_2:     toNumberSafe(sourceSheet.getRange('N' + rowIndex).getValue()),

    Gerente_Venda_Nome:         gerenteVendaId,
    $_Gerente_Venda:            toNumberSafe(sourceSheet.getRange('O' + rowIndex).getValue()),
    Gerente_Captacao_Nome:      gerenteCaptacaoId,
    $_Gerente_Captacao:         toNumberSafe(sourceSheet.getRange('Q' + rowIndex).getValue()),
    Corretor_Venda_1_Nome:      corretorVenda1Id,
    $_Corretor_Venda_1:         toNumberSafe(sourceSheet.getRange('U' + rowIndex).getValue()),
    Corretor_Venda_2_Nome:      corretorVenda2Id,
    $_Corretor_Venda_2:         toNumberSafe(sourceSheet.getRange('W' + rowIndex).getValue()),
    Corretor_Captador_1_Nome:   corretorCaptador1Id,
    $_Corretor_Captador_1:      toNumberSafe(sourceSheet.getRange('Y' + rowIndex).getValue()),
    Corretor_Captador_2_Nome:   corretorCaptador2Id,
    $_Corretor_Captador_2:      toNumberSafe(sourceSheet.getRange('AA' + rowIndex).getValue()),

    neg_Gerado_V1:    toNumberSafe(sourceSheet.getRange('BF' + rowIndex).getValue()),
    neg_Gerado_V2:    toNumberSafe(sourceSheet.getRange('BG' + rowIndex).getValue()),
    neg_Gerado_C1:    toNumberSafe(sourceSheet.getRange('BH' + rowIndex).getValue()),
    neg_Gerado_C2:    toNumberSafe(sourceSheet.getRange('BI' + rowIndex).getValue()),
    vgv_v1:           toNumberSafe(sourceSheet.getRange('BJ' + rowIndex).getValue()),
    vgv_v2:           toNumberSafe(sourceSheet.getRange('BK' + rowIndex).getValue()),
    vgv_c1:           toNumberSafe(sourceSheet.getRange('BL' + rowIndex).getValue()),
    vgv_c2:           toNumberSafe(sourceSheet.getRange('BM' + rowIndex).getValue()),
    percent_comissao_61: toNumberSafe(sourceSheet.getRange('BN' + rowIndex).getValue()),

    bairro: sourceSheet.getRange('CU' + rowIndex).getValue(),
    tipo:   sourceSheet.getRange('CV' + rowIndex).getValue()
  };

  return data;
}

/**************************************
 * Versão a partir dos valores da linha (A–CV) — usada nos loops
 **************************************/
function buildFatoVendaDataFromRowValues(rowValues, gerenteMap, corretorMap) {
  var gerenteVendaNome      = rowValues[15]; // P
  var gerenteCaptacaoNome   = rowValues[17]; // R
  var corretorVenda1Nome    = rowValues[21]; // V
  var corretorVenda2Nome    = rowValues[23]; // X
  var corretorCaptador1Nome = rowValues[25]; // Z
  var corretorCaptador2Nome = rowValues[27]; // AB

  var gerenteVendaId      = gerenteMap[String(gerenteVendaNome)]       || null;
  var gerenteCaptacaoId   = gerenteMap[String(gerenteCaptacaoNome)]    || null;
  var corretorVenda1Id    = corretorMap[String(corretorVenda1Nome)]    || null;
  var corretorVenda2Id    = corretorMap[String(corretorVenda2Nome)]    || null;
  var corretorCaptador1Id = corretorMap[String(corretorCaptador1Nome)] || null;
  var corretorCaptador2Id = corretorMap[String(corretorCaptador2Nome)] || null;

  var data = {
    Id_Contrato:     rowValues[0],   // A
    Data_Contrato:   rowValues[1],   // B
    Contrato:        rowValues[2],   // C

    Valor_Negocio:   toNumberSafe(rowValues[3]),  // D
    Valor_Comissao:  toNumberSafe(rowValues[4]),  // E
    Valor_Total_61:  toNumberSafe(rowValues[5]),  // F
    NF_61_Imoveis:   toNumberSafe(rowValues[6]),  // G
    Liquido_61:      toNumberSafe(rowValues[56]), // BE

    Percent_Gerente_Venda:      toNumberSafe(rowValues[7]),  // H
    Percent_Gerente_Captacao:   toNumberSafe(rowValues[8]),  // I
    Percent_Corretor_Venda_1:   toNumberSafe(rowValues[10]), // K
    Percent_Corretor_Venda_2:   toNumberSafe(rowValues[12]), // M
    Percent_Corretor_Cap_1:     toNumberSafe(rowValues[11]), // L
    Percent_Corretor_Cap_2:     toNumberSafe(rowValues[13]), // N

    Gerente_Venda_Nome:         gerenteVendaId,
    $_Gerente_Venda:            toNumberSafe(rowValues[14]), // O
    Gerente_Captacao_Nome:      gerenteCaptacaoId,
    $_Gerente_Captacao:         toNumberSafe(rowValues[16]), // Q
    Corretor_Venda_1_Nome:      corretorVenda1Id,
    $_Corretor_Venda_1:         toNumberSafe(rowValues[20]), // U
    Corretor_Venda_2_Nome:      corretorVenda2Id,
    $_Corretor_Venda_2:         toNumberSafe(rowValues[22]), // W
    Corretor_Captador_1_Nome:   corretorCaptador1Id,
    $_Corretor_Captador_1:      toNumberSafe(rowValues[24]), // Y
    Corretor_Captador_2_Nome:   corretorCaptador2Id,
    $_Corretor_Captador_2:      toNumberSafe(rowValues[26]), // AA

    neg_Gerado_V1:    toNumberSafe(rowValues[57]), // BF
    neg_Gerado_V2:    toNumberSafe(rowValues[58]), // BG
    neg_Gerado_C1:    toNumberSafe(rowValues[59]), // BH
    neg_Gerado_C2:    toNumberSafe(rowValues[60]), // BI
    vgv_v1:           toNumberSafe(rowValues[61]), // BJ
    vgv_v2:           toNumberSafe(rowValues[62]), // BK
    vgv_c1:           toNumberSafe(rowValues[63]), // BL
    vgv_c2:           toNumberSafe(rowValues[64]), // BM
    percent_comissao_61: toNumberSafe(rowValues[65]), // BN

    bairro: rowValues[98], // CU
    tipo:   rowValues[99]  // CV
  };

  return data;
}

/**************************************
 * Escreve um objeto de dados em uma linha da Fato_Venda
 **************************************/
function writeFatoVendaRow(destinationSheet, data, destRow) {
  for (var key in data) {
    if (!data.hasOwnProperty(key)) continue;
    var col = FATOVENDA_DESTINATION_COLUMNS[key];
    if (!col) continue; // só escreve se tiver mapeamento
    destinationSheet.getRange(col + destRow).setValue(data[key]);
  }
}

/**************************************
 * ranking(): envia última linha de Vendas para Fato_Venda
 **************************************/
function ranking() {
  var sourceSpreadsheetUrl      = 'https://docs.google.com/spreadsheets/d/1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y/edit?gid=775461933#gid=775461933';
  var destinationSpreadsheetUrl = 'https://docs.google.com/spreadsheets/d/1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw/edit?gid=380280845#gid=380280845';
  var sourceSheetName           = 'Vendas';
  var destinationSheetName      = 'Fato_Venda';

  var sourceSpreadsheet      = SpreadsheetApp.openByUrl(sourceSpreadsheetUrl);
  var destinationSpreadsheet = SpreadsheetApp.openByUrl(destinationSpreadsheetUrl);
  var sourceSheet            = sourceSpreadsheet.getSheetByName(sourceSheetName);
  var destinationSheet       = destinationSpreadsheet.getSheetByName(destinationSheetName);

  var dimGerenteSheet  = destinationSpreadsheet.getSheetByName('Dim_Gerente');
  var dimCorretorSheet = destinationSpreadsheet.getSheetByName('Dim_Corretor');

  var gerenteMap  = buildNameToIdMap(dimGerenteSheet);
  var corretorMap = buildNameToIdMap(dimCorretorSheet);

  var lastSourceRow = sourceSheet.getLastRow();

  Logger.log('ranking() - Enviando linha ' + lastSourceRow + ' da aba Vendas para Fato_Venda');

  var data = buildFatoVendaDataFromSourceRow(sourceSheet, gerenteMap, corretorMap, lastSourceRow);
  var lastDestRow = destinationSheet.getLastRow() + 1;

  writeFatoVendaRow(destinationSheet, data, lastDestRow);
}

/**************************************
 * syncRankingUltimos6Meses(): mãe → filha (últimos 6 meses)
 * (mantido como está; se quiser depois trocamos para 12 meses)
 **************************************/
function syncRankingUltimos6Meses() {
  var sourceSpreadsheetUrl      = 'https://docs.google.com/spreadsheets/d/1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y/edit?gid=775461933#gid=775461933';
  var destinationSpreadsheetUrl = 'https://docs.google.com/spreadsheets/d/1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw/edit?gid=380280845#gid=380280845';
  var sourceSheetName           = 'Vendas';
  var destinationSheetName      = 'Fato_Venda';

  var sourceSpreadsheet      = SpreadsheetApp.openByUrl(sourceSpreadsheetUrl);
  var destinationSpreadsheet = SpreadsheetApp.openByUrl(destinationSpreadsheetUrl);
  var sourceSheet            = sourceSpreadsheet.getSheetByName(sourceSheetName);
  var destinationSheet       = destinationSpreadsheet.getSheetByName(destinationSheetName);

  var dimGerenteSheet  = destinationSpreadsheet.getSheetByName('Dim_Gerente');
  var dimCorretorSheet = destinationSpreadsheet.getSheetByName('Dim_Corretor');

  var gerenteMap  = buildNameToIdMap(dimGerenteSheet);
  var corretorMap = buildNameToIdMap(dimCorretorSheet);

  var lastSourceRow = sourceSheet.getLastRow();
  var lastDestRow   = destinationSheet.getLastRow();

  if (lastSourceRow < 2 || lastDestRow < 2) {
    Logger.log('syncRankingUltimos6Meses() - Poucos dados para sincronizar.');
    return;
  }

  var sourceData = sourceSheet.getRange('A2:CV' + lastSourceRow).getValues();

  var idDestRange  = destinationSheet.getRange('BG2:BG' + lastDestRow).getValues();
  var destRowById  = {};
  for (var i = 0; i < idDestRange.length; i++) {
    var id = idDestRange[i][0];
    if (id !== '' && id !== null && typeof id !== 'undefined') {
      destRowById[String(id)] = i + 2;
    }
  }

  var hoje         = new Date();
  var sixMonthsAgo = new Date(hoje.getTime());
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

  Logger.log('Sincronizando últimos 6 meses (Vendas → Fato_Venda): de ' + sixMonthsAgo + ' até ' + hoje);

  for (var r = 0; r < sourceData.length; r++) {
    var rowValues = sourceData[r];
    var rowIndex  = r + 2;

    var dataContrato = rowValues[1]; // B
    if (!dataContrato) continue;

    var dataContratoDate = toDateSafe(dataContrato);
    if (!dataContratoDate) continue;

    if (dataContratoDate < sixMonthsAgo || dataContratoDate > hoje) {
      continue;
    }

    var idContrato = rowValues[0]; // A
    if (!idContrato && idContrato !== 0) continue;

    var destRow = destRowById[String(idContrato)];
    if (!destRow) continue;

    var data = buildFatoVendaDataFromRowValues(rowValues, gerenteMap, corretorMap);

    Logger.log('Atualizando (6 meses) Id_Contrato ' + idContrato +
               ' na linha destino ' + destRow +
               ' a partir da linha ' + rowIndex + ' da Vendas.');

    writeFatoVendaRow(destinationSheet, data, destRow);
  }

  Logger.log('syncRankingUltimos6Meses() - Sincronização concluída.');
}

/**************************************
 * verifyAndSyncFatoVendaFromVendas():
 *  - Opera APENAS com dados do ÚLTIMO ANO (Data_Contrato na mãe/filha)
 *  - Sincroniza filha ← mãe (Id_Contrato)
 *  - Cria registros faltantes:
 *      quarteto:
 *        Valor_Negócio (D/I)
 *        Valor_Comissão (E/J)
 *        Valor_Total_61 (F/L)
 *        Endereço / Contrato (C/F) normalizado
 *    quando a filha tem BG vazio.
 *  - Detecta duplicatas e remove, mantendo apenas a linha de menor número
 *  - Sanitiza colunas numéricas (vazio / erro → 0) apenas no último ano
 **************************************/
function verifyAndSyncFatoVendaFromVendas() {
  var sourceSpreadsheetUrl      = 'https://docs.google.com/spreadsheets/d/1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y/edit?gid=775461933#gid=775461933';
  var destinationSpreadsheetUrl = 'https://docs.google.com/spreadsheets/d/1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw/edit?gid=380280845#gid=380280845';
  var sourceSheetName           = 'Vendas';
  var destinationSheetName      = 'Fato_Venda';

  var sourceSpreadsheet      = SpreadsheetApp.openByUrl(sourceSpreadsheetUrl);
  var destinationSpreadsheet = SpreadsheetApp.openByUrl(destinationSpreadsheetUrl);
  var sourceSheet            = sourceSpreadsheet.getSheetByName(sourceSheetName);
  var destinationSheet       = destinationSpreadsheet.getSheetByName(destinationSheetName);

  var dimGerenteSheet  = destinationSpreadsheet.getSheetByName('Dim_Gerente');
  var dimCorretorSheet = destinationSpreadsheet.getSheetByName('Dim_Corretor');

  var gerenteMap  = buildNameToIdMap(dimGerenteSheet);
  var corretorMap = buildNameToIdMap(dimCorretorSheet);

  var lastSourceRow = sourceSheet.getLastRow();
  var lastDestRow   = getLastRowInColumn(destinationSheet, 'BG'); // última linha com Id_Contrato

  if (lastSourceRow < 2) {
    Logger.log('verifyAndSyncFatoVendaFromVendas() - Poucos dados na aba Vendas.');
    return;
  }

  var hoje       = new Date();
  var oneYearAgo = new Date(hoje.getTime());
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

  Logger.log('verifyAndSyncFatoVendaFromVendas() - Iniciando verificação e sincronização filha ← mãe (último ano).');
  Logger.log('Intervalo de datas considerado: de ' + oneYearAgo + ' até ' + hoje);
  Logger.log('Última linha em Vendas: ' + lastSourceRow +
             ' | última linha com Id_Contrato em Fato_Venda: ' + lastDestRow);

  var sourceData = sourceSheet.getRange('A2:CV' + lastSourceRow).getValues();

  /****************************************
   * 1) Mapa Id_Contrato → índice da linha na mãe,
   *    MAS APENAS PARA O ÚLTIMO ANO
   ****************************************/
  var sourceRowById = {};
  for (var i = 0; i < sourceData.length; i++) {
    var rowValues = sourceData[i];
    var idSource  = rowValues[0]; // A
    if (idSource === '' || idSource === null || typeof idSource === 'undefined') continue;

    var dataContrato = rowValues[1]; // B
    var dataContratoDate = toDateSafe(dataContrato);
    if (!dataContratoDate) continue;

    if (dataContratoDate < oneYearAgo || dataContratoDate > hoje) {
      // fora do último ano → ignora
      continue;
    }

    var key = String(idSource);
    if (!sourceRowById.hasOwnProperty(key)) {
      sourceRowById[key] = i;
    }
  }

  /****************************************
   * 2) Mapa Id_Contrato → lista de linhas na filha (Fato_Venda)
   ****************************************/
  var destRowsById = {};
  if (lastDestRow >= 2) {
    var destIdValues = destinationSheet.getRange('BG2:BG' + lastDestRow).getValues();
    for (var j = 0; j < destIdValues.length; j++) {
      var idDest = destIdValues[j][0];
      if (idDest === '' || idDest === null || typeof idDest === 'undefined') continue;
      var destRowIndex = j + 2;
      var keyDest = String(idDest);
      if (!destRowsById[keyDest]) {
        destRowsById[keyDest] = [];
      }
      destRowsById[keyDest].push(destRowIndex);
    }
  }

  var totalIds   = 0;
  var duplicados = 0;
  var semMae     = 0;

  // Linhas da filha a serem excluídas ao final
  var rowsToDelete = [];

  /****************************************
   * 3) Para cada Id_Contrato presente na filha:
   *    - Só atualiza/deduplica se esse Id estiver na mãe
   *      dentro do último ano (sourceRowById).
   ****************************************/
  for (var idContratoStr in destRowsById) {
    if (!destRowsById.hasOwnProperty(idContratoStr)) continue;

    var idxMae = sourceRowById[idContratoStr];

    // Se não há mãe no último ano, ignoramos esse Id (dados antigos)
    if (typeof idxMae === 'undefined') {
      semMae++;
      continue;
    }

    totalIds++;

    var linhasFilha = destRowsById[idContratoStr];
    if (linhasFilha.length > 1) {
      duplicados++;
      Logger.log('Id_Contrato duplicado em Fato_Venda (último ano): ' + idContratoStr +
                 ' | linhas: ' + linhasFilha.join(', '));
    }

    var rowValuesMae = sourceData[idxMae];
    var rowMaeIndex  = idxMae + 2; // linha real em Vendas

    var dataMae = buildFatoVendaDataFromRowValues(rowValuesMae, gerenteMap, corretorMap);

    // Atualiza todas as linhas da filha para esse Id_Contrato
    for (var k = 0; k < linhasFilha.length; k++) {
      var linhaFilha = linhasFilha[k];
      Logger.log('Atualizando Fato_Venda Id_Contrato ' + idContratoStr +
                 ' na linha ' + linhaFilha +
                 ' com base na linha ' + rowMaeIndex + ' da Vendas (último ano).');
      writeFatoVendaRow(destinationSheet, dataMae, linhaFilha);
    }

    // Se houver duplicatas, manter somente a linha de MENOR NÚMERO (mais alta)
    if (linhasFilha.length > 1) {
      var keepRow = null;

      for (var m = 0; m < linhasFilha.length; m++) {
        var rFilha = linhasFilha[m];
        if (keepRow === null || rFilha < keepRow) {
          keepRow = rFilha;
        }
      }

      Logger.log('Para Id_Contrato ' + idContratoStr +
                 ', mantendo linha ' + keepRow +
                 ' (linha de menor número).');

      for (var n = 0; n < linhasFilha.length; n++) {
        var rDel = linhasFilha[n];
        if (rDel !== keepRow) {
          rowsToDelete.push(rDel);
        }
      }
    }
  }

  // Exclusão física das linhas duplicadas na filha (apenas dos Ids do último ano)
  if (rowsToDelete.length > 0) {
    rowsToDelete.sort(function(a, b) {
      return b - a; // decrescente
    });

    Logger.log('Excluindo ' + rowsToDelete.length +
               ' linhas duplicadas em Fato_Venda (último ano, mantendo sempre a linha de menor número).');

    for (var z = 0; z < rowsToDelete.length; z++) {
      var rowToDelete = rowsToDelete[z];
      Logger.log('Deletando linha ' + rowToDelete + ' em Fato_Venda.');
      destinationSheet.deleteRow(rowToDelete);
    }
  }

  /****************************************
   * 4) Criar registros faltantes (último ano):
   *    Ids que existem na Vendas (mãe) no último ano
   *    mas ainda não existem na Fato_Venda (filha),
   *    usando o QUARTETO:
   *      - Valor_Negócio  (mãe: D / filha: I)
   *      - Valor_Comissão (mãe: E / filha: J)
   *      - Valor_Total_61 (mãe: F / filha: L)
   *      - Endereço/Contrato (mãe: C / filha: F) normalizado
   *
   *    Se houver linha na filha com esse quarteto e BG vazio
   *    (e data dentro do último ano),
   *    ela é atualizada e recebe o Id_Contrato.
   *    Caso contrário, cria-se nova linha.
   ****************************************/
  var novos       = 0;
  var vinculados  = 0;

  // Após a exclusão de duplicatas, recalculamos o tamanho da filha
  var lastRowAfterCleanup = destinationSheet.getLastRow();

  // Montar mapa por quarteto (Val_Neg, Val_Com, Val_Total, Endereço) na filha,
  // apenas para linhas cuja Data_Contrato está no último ano
  var quartetMap = {};
  var bgAllValues = [];

  if (lastRowAfterCleanup >= 2) {
    var valNegRange   = destinationSheet.getRange('I2:I' + lastRowAfterCleanup).getValues(); // Valor_Negocio
    var valComRange   = destinationSheet.getRange('J2:J' + lastRowAfterCleanup).getValues(); // Valor_Comissao
    var valTotRange   = destinationSheet.getRange('L2:L' + lastRowAfterCleanup).getValues(); // Valor_Total_61
    var contratoRange = destinationSheet.getRange('F2:F' + lastRowAfterCleanup).getValues(); // Contrato / Endereco (filha)
    var dataDestRange = destinationSheet.getRange('C2:C' + lastRowAfterCleanup).getValues(); // Data_Contrato (filha)
    bgAllValues       = destinationSheet.getRange('BG2:BG' + lastRowAfterCleanup).getValues(); // Id_Contrato (filha)

    for (var r = 0; r < valNegRange.length; r++) {
      var dataDest = dataDestRange[r][0];
      var dataDestDate = toDateSafe(dataDest);
      if (!dataDestDate) continue;
      if (dataDestDate < oneYearAgo || dataDestDate > hoje) {
        // fora do último ano → não entra no mapa de quarteto
        continue;
      }

      var vNeg = toNumberSafe(valNegRange[r][0]);
      var vCom = toNumberSafe(valComRange[r][0]);
      var vTot = toNumberSafe(valTotRange[r][0]);
      var endFilhaNorm = normalizeEndereco(contratoRange[r][0]);
      var idBg = bgAllValues[r][0];

      var keyQuartet = vNeg + '|' + vCom + '|' + vTot + '|' + endFilhaNorm;
      if (!quartetMap[keyQuartet]) {
        quartetMap[keyQuartet] = [];
      }
      quartetMap[keyQuartet].push({
        row: r + 2,   // linha real
        id:  idBg     // Id_Contrato atual nessa linha
      });
    }
  }

  // Para cada Id da mãe (último ano)
  for (var idMaeStr in sourceRowById) {
    if (!sourceRowById.hasOwnProperty(idMaeStr)) continue;

    // Já existe na filha (mesmo após limpeza de duplicatas)? pula
    if (destRowsById[idMaeStr]) continue;

    var idxMae2       = sourceRowById[idMaeStr];
    var rowValuesMae2 = sourceData[idxMae2];

    var dataContratoMae = rowValuesMae2[1];
    var dataContratoMaeDate = toDateSafe(dataContratoMae);
    if (!dataContratoMaeDate) continue;
    if (dataContratoMaeDate < oneYearAgo || dataContratoMaeDate > hoje) {
      // por garantia, só último ano
      continue;
    }

    var dataMae2      = buildFatoVendaDataFromRowValues(rowValuesMae2, gerenteMap, corretorMap);

    // Obter dados do quarteto na mãe
    var vNegMae   = dataMae2.Valor_Negocio;
    var vComMae   = dataMae2.Valor_Comissao;
    var vTotMae   = dataMae2.Valor_Total_61;
    var endMaeNorm = normalizeEndereco(dataMae2.Contrato);

    var quartetKeyMae = vNegMae + '|' + vComMae + '|' + vTotMae + '|' + endMaeNorm;
    var candidateRows = quartetMap[quartetKeyMae] || [];

    var chosenRow = null;

    // Procurar linha na filha com mesmo quarteto e BG vazio
    if (candidateRows.length > 0) {
      for (var c = 0; c < candidateRows.length; c++) {
        var cand = candidateRows[c];
        var candId = cand.id;
        if (candId === '' || candId === null || typeof candId === 'undefined') {
          chosenRow = cand.row;
          break;
        }
      }
    }

    if (chosenRow !== null) {
      // Atualiza essa linha, preenchendo também o Id_Contrato
      Logger.log('Vinculando Id_Contrato ' + idMaeStr +
                 ' à linha existente ' + chosenRow +
                 ' em Fato_Venda via quarteto (Valor_Negócio, Valor_Comissão, Valor_Total_61, Endereço) no último ano.');

      writeFatoVendaRow(destinationSheet, dataMae2, chosenRow);
      vinculados++;
    } else {
      // Não há linha com mesmo quarteto e BG vazio → cria nova linha
      var newRow = destinationSheet.getLastRow() + 1;
      writeFatoVendaRow(destinationSheet, dataMae2, newRow);
      novos++;

      Logger.log('Criando nova linha em Fato_Venda para Id_Contrato ' + idMaeStr +
                 ' na linha ' + newRow +
                 ' (não existia na filha nem por Id_Contrato nem por quarteto numérico+endereço no último ano).');
    }
  }

  Logger.log('verifyAndSyncFatoVendaFromVendas() - Sincronização concluída (último ano). ' +
             'Ids distintos na filha (considerando último ano): ' + totalIds +
             ', com duplicatas (antes da limpeza): ' + duplicados +
             ', Ids da filha sem mãe no último ano: ' + semMae +
             ', linhas vinculadas por quarteto: ' + vinculados +
             ', novos registros criados a partir da mãe: ' + novos + '.');

  /****************************************
   * 5) Sanitizar colunas numéricas na Fato_Venda
   *    - Preencher vazio / erro / lixo como 0
   *    - Apenas para linhas do ÚLTIMO ANO
   ****************************************/
  var finalLastRow = destinationSheet.getLastRow();
  if (finalLastRow < 2) {
    Logger.log('Nenhuma linha para sanitizar em Fato_Venda.');
    return;
  }

  // Só colunas numéricas ligadas ao script (não mexe em BG / Id_Contrato)
  var numericCols = [
    'I','J','L','P','Q',          // valores principais
    'Z','AS','W','AF','AP','AY',  // percentuais
    'AA','AT','X','AG','AQ','AZ', // valores $ por pessoa
    'T','AD','AM','AW',           // neg_Gerado
    'S','AC','AL','AV',           // vgv
    'K'                           // percent_comissao_61
  ];

  // Data_Contrato na filha
  var dataColRange = destinationSheet.getRange('C2:C' + finalLastRow).getValues();

  numericCols.forEach(function(col) {
    var range  = destinationSheet.getRange(col + '2:' + col + finalLastRow);
    var values = range.getValues();
    var changed = false;

    for (var r = 0; r < values.length; r++) {
      var dataDestVal = dataColRange[r][0];
      var dataDestDate = toDateSafe(dataDestVal);
      if (!dataDestDate) continue;
      if (dataDestDate < oneYearAgo || dataDestDate > hoje) {
        // fora do último ano → não sanitiza
        continue;
      }

      var original  = values[r][0];
      var converted = toNumberSafe(original);
      if (converted !== original) {
        values[r][0] = converted;
        changed = true;
      }
    }

    if (changed) {
      range.setValues(values);
    }
  });

  Logger.log('verifyAndSyncFatoVendaFromVendas() - Sanitização de colunas numéricas concluída (último ano).');
}

/**************************************
 * Auxiliar para data em ISO (mantido para uso geral)
 **************************************/
function formatDateISO(date) {
  if (!date) return '';
  var isoDate = new Date(date);
  return isoDate.toISOString().split('T')[0];
}
