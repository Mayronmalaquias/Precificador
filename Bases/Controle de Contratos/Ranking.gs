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
 * Busca ID por nome (Dim_Gerente / Dim_Corretor)
 **************************************/
function getIdByName(sheet, nome) {
  if (!nome) return null;

  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return null;

  var nomeRange = sheet.getRange('B2:B' + lastRow).getValues();
  var idRange   = sheet.getRange('A2:A' + lastRow).getValues();

  for (var i = 0; i < nomeRange.length; i++) {
    if (nomeRange[i][0] === nome) {
      return idRange[i][0];
    }
  }
  return null;
}

/**************************************
 * VERSÃO ORIGINAL (por linha, usando getRange)
 * — usada pelo ranking() (uma linha só)
 **************************************/
function buildFatoVendaDataFromSourceRow(sourceSheet, dimGerenteSheet, dimCorretorSheet, rowIndex) {
  // Nomes dos envolvidos
  var gerenteVendaNome      = sourceSheet.getRange('P' + rowIndex).getValue();
  var gerenteCaptacaoNome   = sourceSheet.getRange('R' + rowIndex).getValue();
  var corretorVenda1Nome    = sourceSheet.getRange('V' + rowIndex).getValue();
  var corretorVenda2Nome    = sourceSheet.getRange('X' + rowIndex).getValue();
  var corretorCaptador1Nome = sourceSheet.getRange('Z' + rowIndex).getValue();
  var corretorCaptador2Nome = sourceSheet.getRange('AB' + rowIndex).getValue();

  // IDs nas dimensões
  var gerenteVendaId      = getIdByName(dimGerenteSheet, gerenteVendaNome);
  var gerenteCaptacaoId   = getIdByName(dimGerenteSheet, gerenteCaptacaoNome);
  var corretorVenda1Id    = getIdByName(dimCorretorSheet, corretorVenda1Nome);
  var corretorVenda2Id    = getIdByName(dimCorretorSheet, corretorVenda2Nome);
  var corretorCaptador1Id = getIdByName(dimCorretorSheet, corretorCaptador1Nome);
  var corretorCaptador2Id = getIdByName(dimCorretorSheet, corretorCaptador2Nome);

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
 * NOVO: mesma montagem, mas a partir do array da linha (A–CV)
 * — usado nas funções pesadas (sync, verify) para não ficar chamando getRange
 **************************************/
function buildFatoVendaDataFromRowValues(rowValues, dimGerenteSheet, dimCorretorSheet) {
  // Índices (coluna - 1):
  // A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, K=10, L=11, M=12, N=13, O=14, Q=16,
  // P=15, R=17, V=21, X=23, Z=25, AB=27
  // BE=57→idx56, BF=58→57, BG=59→58, BH=60→59, BI=61→60,
  // BJ=62→61, BK=63→62, BL=64→63, BM=65→64, BN=66→65,
  // CU=99→98, CV=100→99

  var gerenteVendaNome      = rowValues[15]; // P
  var gerenteCaptacaoNome   = rowValues[17]; // R
  var corretorVenda1Nome    = rowValues[21]; // V
  var corretorVenda2Nome    = rowValues[23]; // X
  var corretorCaptador1Nome = rowValues[25]; // Z
  var corretorCaptador2Nome = rowValues[27]; // AB

  var gerenteVendaId      = getIdByName(dimGerenteSheet,  gerenteVendaNome);
  var gerenteCaptacaoId   = getIdByName(dimGerenteSheet,  gerenteCaptacaoNome);
  var corretorVenda1Id    = getIdByName(dimCorretorSheet, corretorVenda1Nome);
  var corretorVenda2Id    = getIdByName(dimCorretorSheet, corretorVenda2Nome);
  var corretorCaptador1Id = getIdByName(dimCorretorSheet, corretorCaptador1Nome);
  var corretorCaptador2Id = getIdByName(dimCorretorSheet, corretorCaptador2Nome);

  var data = {
    Id_Contrato:     rowValues[0],   // A
    Data_Contrato:   rowValues[1],   // B
    Contrato:        rowValues[2],   // C

    Valor_Negocio:   toNumberSafe(rowValues[3]),  // D
    Valor_Comissao:  toNumberSafe(rowValues[4]),  // E
    Valor_Total_61:  toNumberSafe(rowValues[5]),  // F
    NF_61_Imoveis:   toNumberSafe(rowValues[6]),  // G
    Liquido_61:      toNumberSafe(rowValues[56]), // BE (57-1)

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
 * FUNÇÃO PRINCIPAL: envia a ÚLTIMA linha de Vendas para Fato_Venda
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

  var lastSourceRow = sourceSheet.getLastRow();

  // Substituindo getLastRow() pelo número da linha desejada 
  // var lastSourceRow = 296; // Use o número da linha que deseja usar

  Logger.log('ranking() - Enviando linha ' + lastSourceRow + ' da aba Vendas para Fato_Venda');

  var data = buildFatoVendaDataFromSourceRow(sourceSheet, dimGerenteSheet, dimCorretorSheet, lastSourceRow);
  var lastDestRow = destinationSheet.getLastRow() + 1;

  writeFatoVendaRow(destinationSheet, data, lastDestRow);
}

/**************************************
 * SINCRONIZAÇÃO: últimos 6 meses (otimizada)
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

  var lastSourceRow = sourceSheet.getLastRow();
  var lastDestRow   = destinationSheet.getLastRow();

  if (lastSourceRow < 2 || lastDestRow < 2) {
    Logger.log('syncRankingUltimos6Meses() - Poucos dados para sincronizar.');
    return;
  }

  // Lê TODA a área A2:CV de uma vez
  var sourceData = sourceSheet.getRange('A2:CV' + lastSourceRow).getValues();

  // Mapa Id_Contrato → linha em Fato_Venda (coluna BG)
  var idDestRange  = destinationSheet.getRange('BG2:BG' + lastDestRow).getValues();
  var destRowById  = {};
  for (var i = 0; i < idDestRange.length; i++) {
    var id = idDestRange[i][0];
    if (id !== '' && id !== null && typeof id !== 'undefined') {
      destRowById[String(id)] = i + 2;
    }
  }

  // Data limite: hoje - 6 meses
  var hoje         = new Date();
  var sixMonthsAgo = new Date(hoje.getTime());
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

  Logger.log('Sincronizando últimos 6 meses (Vendas → Fato_Venda): de ' + sixMonthsAgo + ' até ' + hoje);

  for (var r = 0; r < sourceData.length; r++) {
    var rowValues = sourceData[r];
    var rowIndex  = r + 2; // linha real na planilha

    var dataContrato = rowValues[1]; // B
    if (!dataContrato) continue;

    var dataContratoDate = dataContrato;
    if (!(dataContratoDate instanceof Date)) {
      var s = String(dataContrato).trim();
      var parts = s.split('/');
      if (parts.length === 3) {
        var dia = parseInt(parts[0], 10);
        var mes = parseInt(parts[1], 10) - 1;
        var ano = parseInt(parts[2], 10);
        dataContratoDate = new Date(ano, mes, dia);
      } else {
        continue;
      }
    }

    if (dataContratoDate < sixMonthsAgo || dataContratoDate > hoje) {
      continue;
    }

    var idContrato = rowValues[0]; // A
    if (!idContrato && idContrato !== 0) continue;

    var destRow = destRowById[String(idContrato)];
    if (!destRow) continue; // quem cria é o ranking()

    var data = buildFatoVendaDataFromRowValues(rowValues, dimGerenteSheet, dimCorretorSheet);

    Logger.log('Atualizando (6 meses) Id_Contrato ' + idContrato + ' na linha destino ' + destRow + ' a partir da linha ' + rowIndex + ' da Vendas.');

    writeFatoVendaRow(destinationSheet, data, destRow);
  }

  Logger.log('syncRankingUltimos6Meses() - Sincronização concluída.');
}

/**************************************
 * VERIFICAÇÃO NA FILHA + ATUALIZAÇÃO (otimizada)
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

  var lastSourceRow = sourceSheet.getLastRow();
  var lastDestRow   = destinationSheet.getLastRow();

  if (lastSourceRow < 2 || lastDestRow < 2) {
    Logger.log('verifyAndSyncFatoVendaFromVendas() - Poucos dados para sincronizar.');
    return;
  }

  Logger.log('verifyAndSyncFatoVendaFromVendas() - Iniciando verificação e sincronização filha ← mãe.');

  // Lê a mãe em bloco
  var sourceData = sourceSheet.getRange('A2:CV' + lastSourceRow).getValues();

  // 1) Mapa Id_Contrato → índice da linha na mãe (array)
  var sourceRowById = {};
  for (var i = 0; i < sourceData.length; i++) {
    var rowValues = sourceData[i];
    var idSource  = rowValues[0]; // A
    if (idSource === '' || idSource === null || typeof idSource === 'undefined') continue;
    var key = String(idSource);
    if (!sourceRowById.hasOwnProperty(key)) {
      sourceRowById[key] = i; // índice no array (não na planilha)
    }
  }

  // 2) Mapa Id_Contrato → lista de linhas na filha (Fato_Venda)
  var destIdValues = destinationSheet.getRange('BG2:BG' + lastDestRow).getValues();
  var destRowsById = {};
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

  var totalIds   = 0;
  var duplicados = 0;
  var semMae     = 0;

  // 3) Para cada Id_Contrato presente na filha:
  for (var idContratoStr in destRowsById) {
    if (!destRowsById.hasOwnProperty(idContratoStr)) continue;
    totalIds++;

    var linhasFilha = destRowsById[idContratoStr];
    if (linhasFilha.length > 1) {
      duplicados++;
      Logger.log('Id_Contrato duplicado em Fato_Venda: ' + idContratoStr + ' | linhas: ' + linhasFilha.join(', '));
    }

    var idxMae = sourceRowById[idContratoStr];
    if (typeof idxMae === 'undefined') {
      semMae++;
      Logger.log('Id_Contrato em Fato_Venda sem correspondente em Vendas: ' + idContratoStr);
      continue; // não altera se não existir na mãe
    }

    var rowValuesMae = sourceData[idxMae];
    var rowMaeIndex  = idxMae + 2; // linha real na planilha Vendas

    var dataMae = buildFatoVendaDataFromRowValues(rowValuesMae, dimGerenteSheet, dimCorretorSheet);

    for (var k = 0; k < linhasFilha.length; k++) {
      var linhaFilha = linhasFilha[k];
      Logger.log('Atualizando Fato_Venda Id_Contrato ' + idContratoStr +
                 ' na linha ' + linhaFilha +
                 ' com base na linha ' + rowMaeIndex + ' da Vendas.');
      writeFatoVendaRow(destinationSheet, dataMae, linhaFilha);
    }
  }

  Logger.log('verifyAndSyncFatoVendaFromVendas() - Finalizado. ' +
             'Ids distintos na filha: ' + totalIds +
             ', com duplicatas: ' + duplicados +
             ', sem correspondência na mãe: ' + semMae + '.');
}

/**************************************
 * Auxiliar para data em ISO
 **************************************/
function formatDateISO(date) {
  if (!date) return '';
  var isoDate = new Date(date);
  return isoDate.toISOString().split('T')[0];
}
