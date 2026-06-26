// ============================================================
//  EDITAR CONTRATO — Apps Script
//  Mantém compatibilidade total com validatePercentuais,
//  validarLancamentoFormulario e calculateCommissions
//  já definidos em Calculos.gs / Validacoes.gs
// ============================================================

var LINK_EDICAO = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';

// ──────────────────────────────────────────────────────────
//  getContractDetailsByIndex
//  Retorna todos os campos da linha para preencher o formulário
// ──────────────────────────────────────────────────────────
function getContractDetailsByIndex(index) {
  var sheet = SpreadsheetApp.openById(LINK_EDICAO).getSheetByName('Vendas');

  function safeDate(val) {
    if (!val) return '';
    try {
      return Utilities.formatDate(new Date(val), Session.getScriptTimeZone(), 'dd/MM/yyyy');
    } catch(e) {
      return String(val);
    }
  }
  function safeNum(val) {
    var n = parseFloat(val);
    return isNaN(n) ? 0 : n;
  }
  function safeBool(val) {
    if (typeof val === 'boolean') return val;
    return String(val).trim().toUpperCase() === 'TRUE';
  }

  return {
    // ── Identificação ──
    Id_Contrato:    sheet.getRange('A' + index).getValue(),
    Data_Contrato:  safeDate(sheet.getRange('B' + index).getValue()),
    Contrato:       sheet.getRange('C' + index).getValue(),

    // ── Valores ──
    Valor_Negocio:  safeNum(sheet.getRange('D' + index).getValue()),
    Valor_Comissao: safeNum(sheet.getRange('E' + index).getValue()),
    Valor_Total_61: safeNum(sheet.getRange('F' + index).getValue()),
    NF_61_Imoveis:  safeNum(sheet.getRange('G' + index).getValue()),

    // ── Percentuais (H-N) — gravados como decimal, ex: 0.10 ──
    '%_Gerente_Venda':      safeNum(sheet.getRange('H' + index).getValue()),
    '%_Gerente_Captacao':   safeNum(sheet.getRange('I' + index).getValue()),
    '%_Diretor':            safeNum(sheet.getRange('J' + index).getValue()),
    '%_Corretor_Venda_1':   safeNum(sheet.getRange('K' + index).getValue()),
    '%_Corretor_Captação_1':safeNum(sheet.getRange('L' + index).getValue()),
    '%_Corretor_Venda_2':   safeNum(sheet.getRange('M' + index).getValue()),
    '%_Corretor_Captação_2':safeNum(sheet.getRange('N' + index).getValue()),

    // ── Valores monetários da equipe ──
    '$_Gerente_Venda':       safeNum(sheet.getRange('O' + index).getValue()),
    Gerente_Venda_Nome:      sheet.getRange('P' + index).getValue(),
    '$_Gerente_Captacao':    safeNum(sheet.getRange('Q' + index).getValue()),
    Gerente_Captacao_Nome:   sheet.getRange('R' + index).getValue(),
    '$_Diretor':             safeNum(sheet.getRange('S' + index).getValue()),
    Diretor_Nome:            sheet.getRange('T' + index).getValue(),
    '$_Corretor_Venda_1':    safeNum(sheet.getRange('U' + index).getValue()),
    Corretor_Venda_1_Nome:   sheet.getRange('V' + index).getValue(),
    '$_Corretor_Venda_2':    safeNum(sheet.getRange('W' + index).getValue()),
    Corretor_Venda_2_Nome:   sheet.getRange('X' + index).getValue(),
    '$_Corretor_Captador_1': safeNum(sheet.getRange('Y' + index).getValue()),
    Corretor_Captador_1_Nome:sheet.getRange('Z' + index).getValue(),
    '$_Corretor_Captador_2': safeNum(sheet.getRange('AA' + index).getValue()),
    Corretor_Captador_2_Nome:sheet.getRange('AB' + index).getValue(),

    // ── Parceria e flags NF ──
    imovelParceiro:            safeBool(sheet.getRange('AC' + index).getValue()),
    removeCalcGerenteVenda:    safeBool(sheet.getRange('EJ' + index).getValue()),
    removeCalcGerenteCaptacao: safeBool(sheet.getRange('EK' + index).getValue()),
    removeCalcDiretor:         safeBool(sheet.getRange('EL' + index).getValue()),

    // ── Calculados ──
    Liquido_61:    safeNum(sheet.getRange('BE' + index).getValue()),
    neg_Gerado_V1: safeNum(sheet.getRange('BF' + index).getValue()),
    neg_Gerado_V2: safeNum(sheet.getRange('BG' + index).getValue()),
    neg_Gerado_C1: safeNum(sheet.getRange('BH' + index).getValue()),
    neg_Gerado_C2: safeNum(sheet.getRange('BI' + index).getValue())
  };
}

// ──────────────────────────────────────────────────────────
//  updateRow
//  Grava os dados editados na planilha.
//  IMPORTANTE: NÃO calcula as colunas de %, NF, Líquido etc.
//  Esses valores são recalculados por calculateCommissions()
//  chamado pelo HTML após o sucesso do save.
// ──────────────────────────────────────────────────────────
function updateRow(formData) {
  var sheet    = SpreadsheetApp.openById(LINK_EDICAO).getSheetByName('Vendas');
  var rowIndex = parseInt(formData.rowIndex);

  if (rowIndex < 2 || rowIndex > sheet.getLastRow()) {
    throw new Error('Índice de linha inválido: ' + rowIndex);
  }

  // ── Validação de percentuais antes de gravar ──
  // Reutiliza a mesma função do lançamento (deve estar em Calculos.gs ou Validacoes.gs).
  // Lança erro se as regras forem violadas, impedindo a gravação.
  var validacao = validarRegrasLancamento({
    valorNegocio:          toNumberSafe(formData.Valor_Negocio),
    valorComissao:         toNumberSafe(formData.Valor_Comissao),
    valorTotal61:          toNumberSafe(formData.Valor_Total_61),
    imovelParceiro:        formData.imovelParceiro,
    gerenteVendaNome:      formData.Gerente_Venda_Nome,
    gerenteCaptacaoNome:   formData.Gerente_Captacao_Nome,
    diretorNome:           formData.Diretor_Nome,
    corretorVenda1Nome:    formData.Corretor_Venda_1_Nome,
    corretorVenda2Nome:    formData.Corretor_Venda_2_Nome,
    corretorCaptacao1Nome: formData.Corretor_Captador_1_Nome,
    corretorCaptacao2Nome: formData.Corretor_Captador_2_Nome,
    comGerenteVenda:       toNumberSafe(formData.$_Gerente_Venda),
    comGerenteCaptacao:    toNumberSafe(formData.$_Gerente_Captacao),
    comDiretor:            toNumberSafe(formData.$_Diretor),
    comCorV1:              toNumberSafe(formData.$_Corretor_Venda_1),
    comCorV2:              toNumberSafe(formData.$_Corretor_Venda_2),
    comCorC1:              toNumberSafe(formData.$_Corretor_Captador_1),
    comCorC2:              toNumberSafe(formData.$_Corretor_Captador_2)
  });

  if (!validacao.valido) {
    throw new Error('EDIÇÃO BLOQUEADA — regras da 61 divergentes:\n\n' + validacao.erros.join('\n'));
  }

  // ── Gravação das colunas editáveis ──
  sheet.getRange('A' + rowIndex).setValue(formData.Id_Contrato);
  sheet.getRange('B' + rowIndex).setValue(formData.Data_Contrato);
  sheet.getRange('C' + rowIndex).setValue(formData.Contrato);
  sheet.getRange('D' + rowIndex).setValue(toNumberSafe(formData.Valor_Negocio));
  sheet.getRange('E' + rowIndex).setValue(toNumberSafe(formData.Valor_Comissao));
  sheet.getRange('F' + rowIndex).setValue(toNumberSafe(formData.Valor_Total_61));

  // Valores monetários da equipe (O-AB)
  sheet.getRange('O' + rowIndex).setValue(toNumberSafe(formData.$_Gerente_Venda));
  sheet.getRange('P' + rowIndex).setValue(formData.Gerente_Venda_Nome  || '');
  sheet.getRange('Q' + rowIndex).setValue(toNumberSafe(formData.$_Gerente_Captacao));
  sheet.getRange('R' + rowIndex).setValue(formData.Gerente_Captacao_Nome || '');
  sheet.getRange('S' + rowIndex).setValue(toNumberSafe(formData.$_Diretor));
  sheet.getRange('T' + rowIndex).setValue(formData.Diretor_Nome          || '');
  sheet.getRange('U' + rowIndex).setValue(toNumberSafe(formData.$_Corretor_Venda_1));
  sheet.getRange('V' + rowIndex).setValue(formData.Corretor_Venda_1_Nome  || '');
  sheet.getRange('W' + rowIndex).setValue(toNumberSafe(formData.$_Corretor_Venda_2));
  sheet.getRange('X' + rowIndex).setValue(formData.Corretor_Venda_2_Nome  || '');
  sheet.getRange('Y' + rowIndex).setValue(toNumberSafe(formData.$_Corretor_Captador_1));
  sheet.getRange('Z' + rowIndex).setValue(formData.Corretor_Captador_1_Nome || '');
  sheet.getRange('AA' + rowIndex).setValue(toNumberSafe(formData.$_Corretor_Captador_2));
  sheet.getRange('AB' + rowIndex).setValue(formData.Corretor_Captador_2_Nome || '');

  // Parceria (AC) e flags NF (EJ-EL)
  var toBool_ = function(v) { return (v === true || String(v).trim().toUpperCase() === 'TRUE'); };
  sheet.getRange('AC' + rowIndex).setValue(toBool_(formData.imovelParceiro));
  sheet.getRange('EJ' + rowIndex).setValue(toBool_(formData.removeCalcGerenteVenda));
  sheet.getRange('EK' + rowIndex).setValue(toBool_(formData.removeCalcGerenteCaptacao));
  sheet.getRange('EL' + rowIndex).setValue(toBool_(formData.removeCalcDiretor));

  // NÃO gravamos G (NF_61_Imoveis), H-N (%), BE (Liquido_61), BF-BI (neg_Gerado) aqui.
  // calculateCommissions() recalcula tudo isso a partir dos valores acima.

  Logger.log('Linha ' + rowIndex + ' atualizada. calculateCommissions() será chamado pelo HTML.');
  return 'Success';
}

// ──────────────────────────────────────────────────────────
//  getContractsEdicao
//  Retorna lista de contratos para o dropdown de seleção.
// ──────────────────────────────────────────────────────────
function getContractsEdicao() {
  var sheet  = SpreadsheetApp.openById(LINK_EDICAO).getSheetByName('Vendas');
  var lastRow = sheet.getLastRow();
  var values  = sheet.getRange('C2:C' + lastRow).getValues();

  return values
    .map(function(row, i) { return { idContrato: row[0], row: i + 2 }; })
    .filter(function(c) { return c.idContrato; })
    .reverse(); // mais recente (maior row) primeiro
}

// ──────────────────────────────────────────────────────────
//  getDropdownDataEdicao
//  Retorna gerentes e corretores para os selects.
// ──────────────────────────────────────────────────────────
function getDropdownDataEdicao() {
  var ss = SpreadsheetApp.openById('1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw');
  var gerentesSheet   = ss.getSheetByName('Dim_Gerente');
  var corretoresSheet = ss.getSheetByName('Dim_Corretor');

  var gerentesData   = gerentesSheet.getRange('A2:B' + gerentesSheet.getLastRow()).getValues();
  var corretoresData  = corretoresSheet.getRange('A2:B' + corretoresSheet.getLastRow()).getValues();

  return {
    gerentes:   gerentesData.map(function(row)  { return { id: row[0], nome: row[1] }; }),
    corretores: corretoresData.map(function(row) { return { id: row[0], nome: row[1] }; })
  };
}