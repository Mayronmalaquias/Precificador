/**
 * Recalcula apenas:
 *  - neg_Gerado_V1 (BF)
 *  - neg_Gerado_V2 (BG)
 *  - neg_Gerado_C1 (BH)
 *  - neg_Gerado_C2 (BI)
 *  - vgv_v1        (BJ)
 *  - vgv_v2        (BK)
 *  - vgv_c1        (BL)
 *  - vgv_c2        (BM)
 * para um intervalo de linhas [startRow, endRow].
 *
 * Usa a MESMA lógica numérica de calculateCommissions1.
 */
function recalculateNegociosRange(startRow = 357, endRow = 476) {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName('Vendas');

  // Se só passar um número, trata como única linha
  if (endRow === undefined || endRow === null) {
    endRow = startRow;
  }

  // Linha explícita com início e fim do intervalo
  Logger.log('Recalculo de NG/VGV - linha inicial: ' + startRow + ', linha final: ' + endRow);

  for (var row = startRow; row <= endRow; row++) {

    // Entradas (mesmas usadas em calculateCommissions1)
    var valorComissao          = toNumberSafe(sheet.getRange('E' + row).getValue());
    var valorTotal61           = toNumberSafe(sheet.getRange('F' + row).getValue());
    var valorNegocio           = toNumberSafe(sheet.getRange('D' + row).getValue());
    var $_Corretor_Venda_1     = toNumberSafe(sheet.getRange('U' + row).getValue());
    var $_Corretor_Venda_2     = toNumberSafe(sheet.getRange('W' + row).getValue() || 0);
    var $_Corretor_Captador_1  = toNumberSafe(sheet.getRange('Y' + row).getValue());
    var $_Corretor_Captador_2  = toNumberSafe(sheet.getRange('AA' + row).getValue() || 0);

    // Proteção básica (mesmo critério de antes)
    if (valorComissao === 0 || valorNegocio === 0) {
      Logger.log('Linha ' + row + ': valorComissao ou valorNegocio é zero. Recalculo ignorado.');
      continue;
    }

    // === Mesma lógica de correção de negócio geral (NG_61) ===
    var correcaoTemp  = valorTotal61 !== 0 ? valorTotal61 / valorComissao : 0;
    var correcaoNG_61 = correcaoTemp === 1 ? 1 : (correcaoTemp < 1 ? correcaoTemp * 2 : correcaoTemp);
    var vgvCorrigido  = correcaoNG_61 * valorNegocio;

    // Soma por tipo (Vendas e Captação)
    var somaV = toNumberSafe($_Corretor_Venda_1)    + toNumberSafe($_Corretor_Venda_2);
    var somaC = toNumberSafe($_Corretor_Captador_1) + toNumberSafe($_Corretor_Captador_2);

    // Proporções (mesma lógica do calculateCommissions1)
    var correcaoNG_V1 = somaV !== 0 ? toNumberSafe($_Corretor_Venda_1)    / somaV : 0;
    var correcaoNG_V2 = somaV !== 0 ? toNumberSafe($_Corretor_Venda_2)    / somaV : 0;
    var correcaoNG_C1 = somaC !== 0 ? toNumberSafe($_Corretor_Captador_1) / somaC : 0;
    var correcaoNG_C2 = somaC !== 0 ? toNumberSafe($_Corretor_Captador_2) / somaC : 0;

    // === Cálculos de negócio gerado (NG) ===
    var neg_Gerado_V1 = correcaoNG_V1 * vgvCorrigido;
    var neg_Gerado_V2 = correcaoNG_V2 * vgvCorrigido;
    var neg_Gerado_C1 = correcaoNG_C1 * vgvCorrigido;
    var neg_Gerado_C2 = correcaoNG_C2 * vgvCorrigido;

    // === Cálculos de VGV por corretor ===
    var vgv_v1 = correcaoNG_V1 * valorNegocio;
    var vgv_v2 = correcaoNG_V2 * valorNegocio;
    var vgv_c1 = correcaoNG_C1 * valorNegocio;
    var vgv_c2 = correcaoNG_C2 * valorNegocio;

    Logger.log('Linha ' + row + ' – Recalculando NG/VGV:');
    Logger.log('neg_Gerado_V1: ' + neg_Gerado_V1);
    Logger.log('neg_Gerado_V2: ' + neg_Gerado_V2);
    Logger.log('neg_Gerado_C1: ' + neg_Gerado_C1);
    Logger.log('neg_Gerado_C2: ' + neg_Gerado_C2);
    Logger.log('vgv_v1: ' + vgv_v1);
    Logger.log('vgv_v2: ' + vgv_v2);
    Logger.log('vgv_c1: ' + vgv_c1);
    Logger.log('vgv_c2: ' + vgv_c2);

    // Escrita nas MESMAS colunas já usadas:
    sheet.getRange('BF' + row).setValue(neg_Gerado_V1);
    sheet.getRange('BG' + row).setValue(neg_Gerado_V2);
    sheet.getRange('BH' + row).setValue(neg_Gerado_C1);
    sheet.getRange('BI' + row).setValue(neg_Gerado_C2);
    sheet.getRange('BJ' + row).setValue(vgv_v1);
    sheet.getRange('BK' + row).setValue(vgv_v2);
    sheet.getRange('BL' + row).setValue(vgv_c1);
    sheet.getRange('BM' + row).setValue(vgv_c2);
  }
}
