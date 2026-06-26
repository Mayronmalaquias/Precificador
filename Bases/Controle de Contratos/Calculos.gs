// ============================================================
//  Calculos.gs — 61 Imóveis
//  Responsabilidades: validação de percentuais + cálculo de comissões
//  + filtro/transferência para Controle
//
//  NÃO contém: submitData, dropdowns, startBV, startTrello,
//  generateNextIdContrato — essas funções ficam em Manipulacao_Vendas.gs
// ============================================================


// ============================================================
//  UTILITÁRIOS
// ============================================================

function toNumberSafe(value) {
  if (value === null || value === '' || typeof value === 'undefined') return 0;
  if (typeof value === 'number') return isNaN(value) ? 0 : value;
  if (typeof value === 'boolean') return value ? 1 : 0;
  var s = String(value).trim().replace(/\s/g, '');
  if (s === '' || s === '-') return 0;
  s = s.replace(/R\$\s*/g, '');
  var hasComma = s.indexOf(',') !== -1, hasDot = s.indexOf('.') !== -1;
  if (hasComma && hasDot) {
    if (s.lastIndexOf(',') > s.lastIndexOf('.')) { s = s.replace(/\./g,'').replace(',','.'); }
    else { s = s.replace(/,/g,''); }
  } else if (hasComma) {
    s = s.replace(/\./g,'').replace(',','.');
  } else {
    s = s.replace(/,/g,'');
  }
  var n = Number(s);
  return isNaN(n) ? 0 : n;
}

function toBool(value) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number')  return value !== 0;
  var s = String(value).trim().toUpperCase();
  return s === 'TRUE' || s === '1' || s === 'SIM' || s === 'YES';
}

function getColumnLetter(columnNumber) {
  var temp, letter = '';
  while (columnNumber > 0) {
    temp = (columnNumber - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    columnNumber = (columnNumber - temp - 1) / 26;
  }
  return letter;
}

function normalizarCamposComissao(dados) {
  var d = dados || {};
  function pick(longo, curto) {
    var vl = toNumberSafe(d[longo]);
    var vc = toNumberSafe(d[curto]);
    return vl > 0 ? vl : vc;
  }
  d.comissaoGerenteVenda      = pick('comissaoGerenteVenda',    'comGerenteVenda');
  d.comissaoGerenteCaptacao   = pick('comissaoGerenteCaptacao', 'comGerenteCaptacao');
  d.comissaoDiretor           = pick('comissaoDiretor',         'comDiretor');
  d.comissaoCorretorVenda1    = pick('comissaoCorretorVenda1',  'comCorV1');
  d.comissaoCorretorVenda2    = pick('comissaoCorretorVenda2',  'comCorV2');
  d.comissaoCorretorCaptacao1 = pick('comissaoCorretorCaptacao1','comCorC1');
  d.comissaoCorretorCaptacao2 = pick('comissaoCorretorCaptacao2','comCorC2');
  d.comGerenteVenda    = d.comissaoGerenteVenda;
  d.comGerenteCaptacao = d.comissaoGerenteCaptacao;
  d.comDiretor         = d.comissaoDiretor;
  d.comCorV1           = d.comissaoCorretorVenda1;
  d.comCorV2           = d.comissaoCorretorVenda2;
  d.comCorC1           = d.comissaoCorretorCaptacao1;
  d.comCorC2           = d.comissaoCorretorCaptacao2;
  return d;
}


// ============================================================
//  REGRAS DE NEGÓCIO
// ============================================================

var PCT_RULES = {
  GERENTE_TOTAL:      0.10,
  CORRETOR_VENDA:     0.22,
  CORRETOR_CAP_VALID: [0.20, 0.22, 0.24],
  PARCERIA_EXTRA:     0.22,
  EMPRESA_VALID:      [0.42, 0.44, 0.46, 0.48],
  TOLERANCIA_VALOR:   0.05
};

function isBlank(value) {
  return value === null || typeof value === 'undefined' || String(value).trim() === '';
}
function roundMoney(value) {
  var n = toNumberSafe(value);
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
function moneyEquals(a, b) {
  return Math.abs(roundMoney(a) - roundMoney(b)) <= PCT_RULES.TOLERANCIA_VALOR;
}
function formatMoneyBR(value) {
  var n = roundMoney(value);
  return 'R$ ' + n.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
function formatPctBR(value) {
  if (!isFinite(value)) return '—';
  var pct = value * 100;
  if (Math.abs(pct - Math.round(pct)) < 0.0001) return Math.round(pct) + '%';
  return pct.toFixed(2).replace('.', ',') + '%';
}
function pctSobreVT61(valor, vt61) {
  vt61 = toNumberSafe(vt61);
  return vt61 > 0 ? toNumberSafe(valor) / vt61 : 0;
}
function allowedMoneyByPercent(valor, vt61, lista) {
  return lista.some(function(pct) { return moneyEquals(valor, vt61 * pct); });
}
function firstAllowedPercentMatched(valor, vt61, lista) {
  for (var i = 0; i < lista.length; i++) {
    if (moneyEquals(valor, vt61 * lista[i])) return lista[i];
  }
  return null;
}
function contarParticipantes(participantes) {
  return participantes.filter(function(p) {
    return !isBlank(p.nome) || toNumberSafe(p.valor) > 0;
  }).length;
}
function validarNomeValor(participantes, erros) {
  participantes.forEach(function(p) {
    var temNome  = !isBlank(p.nome);
    var temValor = toNumberSafe(p.valor) > 0;
    if (temNome && !temValor)  erros.push(p.label + ': nome preenchido, mas comissão zerada.');
    if (!temNome && temValor)  erros.push(p.label + ': comissão preenchida, mas nome não informado.');
    if (toNumberSafe(p.valor) < 0) erros.push(p.label + ': comissão não pode ser negativa.');
  });
}


// ============================================================
//  VALIDAÇÃO PRINCIPAL
// ============================================================

function validarRegrasLancamento(dados) {
  dados = normalizarCamposComissao(dados || {});
  var erros = [];

  var valorNegocio  = toNumberSafe(dados.valorNegocio);
  var valorComissao = toNumberSafe(dados.valorComissao);
  var vt61          = toNumberSafe(dados.valorTotal61);
  var isParceria    = toBool(dados.imovelParceiro);

  var gerenteVenda      = { label:'Gerente de venda',           nome:dados.gerenteVendaNome,      valor:toNumberSafe(dados.comissaoGerenteVenda) };
  var gerenteCaptacao   = { label:'Gerente de captação',        nome:dados.gerenteCaptacaoNome,   valor:toNumberSafe(dados.comissaoGerenteCaptacao) };
  var corretorVenda1    = { label:'Corretor venda/comprador 1', nome:dados.corretorVenda1Nome,    valor:toNumberSafe(dados.comissaoCorretorVenda1) };
  var corretorVenda2    = { label:'Corretor venda/comprador 2', nome:dados.corretorVenda2Nome,    valor:toNumberSafe(dados.comissaoCorretorVenda2) };
  var corretorCaptacao1 = { label:'Corretor captação 1',        nome:dados.corretorCaptacao1Nome, valor:toNumberSafe(dados.comissaoCorretorCaptacao1) };
  var corretorCaptacao2 = { label:'Corretor captação 2',        nome:dados.corretorCaptacao2Nome, valor:toNumberSafe(dados.comissaoCorretorCaptacao2) };
  var diretor           = { label:'Diretor',                    nome:dados.diretorNome,           valor:toNumberSafe(dados.comissaoDiretor) };

  var gerentes   = [gerenteVenda, gerenteCaptacao];
  var vendas     = [corretorVenda1, corretorVenda2];
  var captadores = [corretorCaptacao1, corretorCaptacao2];
  var todos      = gerentes.concat(vendas).concat(captadores).concat([diretor]);

  if (valorNegocio  <= 0) erros.push('Valor do negócio deve ser maior que zero.');
  if (valorComissao <= 0) erros.push('Valor Comissão deve ser maior que zero.');
  if (vt61          <= 0) erros.push('Valor Total 61 deve ser maior que zero.');
  if (valorComissao > 0 && vt61 > valorComissao + PCT_RULES.TOLERANCIA_VALOR)
    erros.push('Valor Total 61 (' + formatMoneyBR(vt61) + ') não pode ser maior que Valor Comissão (' + formatMoneyBR(valorComissao) + ').');

  validarNomeValor(todos, erros);
  if (vt61 <= 0) return { valido: false, erros: erros, resumo: {} };

  var numGerentes  = contarParticipantes(gerentes);
  var numVenda     = contarParticipantes(vendas);
  var numCaptacao  = contarParticipantes(captadores);
  var somaGerentes = gerenteVenda.valor + gerenteCaptacao.valor;
  var somaVenda    = corretorVenda1.valor + corretorVenda2.valor;
  var somaCaptacao = corretorCaptacao1.valor + corretorCaptacao2.valor;
  var totalAtribuido = somaGerentes + somaVenda + somaCaptacao + diretor.valor;
  var empresa = vt61 - totalAtribuido;

  // 1) Gerência: 10%
  var esperadoGerencia = vt61 * PCT_RULES.GERENTE_TOTAL;
  if (numGerentes === 0) {
    erros.push('Gerência é obrigatória e deve somar 10% do Valor Total 61.');
  } else if (!moneyEquals(somaGerentes, esperadoGerencia)) {
    erros.push('Gerência deve somar exatamente 10%: esperado ' + formatMoneyBR(esperadoGerencia) + ', lançado ' + formatMoneyBR(somaGerentes) + ' (' + formatPctBR(pctSobreVT61(somaGerentes, vt61)) + ').');
  } else {
    var espPorGer = esperadoGerencia / numGerentes;
    gerentes.forEach(function(g) {
      if ((!isBlank(g.nome) || g.valor > 0) && !moneyEquals(g.valor, espPorGer))
        erros.push(g.label + ': esperado ' + formatMoneyBR(espPorGer) + ', lançado ' + formatMoneyBR(g.valor) + '.');
    });
  }

  // 2) Venda/comprador: 22% (ou 44% em parceria)
  var pctVendaEsp   = PCT_RULES.CORRETOR_VENDA + (isParceria ? PCT_RULES.PARCERIA_EXTRA : 0);
  var esperadoVenda = vt61 * pctVendaEsp;
  if (numVenda === 0) {
    erros.push('Corretor de venda/comprador é obrigatório e deve somar ' + formatPctBR(pctVendaEsp) + '.');
  } else if (!moneyEquals(somaVenda, esperadoVenda)) {
    erros.push('Corretores de venda devem somar ' + formatPctBR(pctVendaEsp) + ': esperado ' + formatMoneyBR(esperadoVenda) + ', lançado ' + formatMoneyBR(somaVenda) + ' (' + formatPctBR(pctSobreVT61(somaVenda, vt61)) + ').');
  } else {
    var espPorVenda = esperadoVenda / numVenda;
    vendas.forEach(function(v) {
      if ((!isBlank(v.nome) || v.valor > 0) && !moneyEquals(v.valor, espPorVenda))
        erros.push(v.label + ': esperado ' + formatMoneyBR(espPorVenda) + ', lançado ' + formatMoneyBR(v.valor) + '.');
    });
  }

  // 3) Captação: 20/22/24% (ou 0 em parceria)
  if (isParceria) {
    if (!moneyEquals(somaCaptacao, 0) || numCaptacao > 0)
      erros.push('Em imóvel de parceria, não lance captador interno.');
  } else {
    if (numCaptacao === 0) {
      erros.push('Captação é obrigatória e deve somar 20%, 22% ou 24%.');
    } else if (!allowedMoneyByPercent(somaCaptacao, vt61, PCT_RULES.CORRETOR_CAP_VALID)) {
      erros.push('Captação deve somar 20%, 22% ou 24%: lançado ' + formatMoneyBR(somaCaptacao) + ' (' + formatPctBR(pctSobreVT61(somaCaptacao, vt61)) + ').');
    } else {
      var espPorCap = somaCaptacao / numCaptacao;
      captadores.forEach(function(c) {
        if ((!isBlank(c.nome) || c.valor > 0) && !moneyEquals(c.valor, espPorCap))
          erros.push(c.label + ': esperado ' + formatMoneyBR(espPorCap) + ', lançado ' + formatMoneyBR(c.valor) + '.');
      });
    }
  }

  // 4) Empresa: 42/44/46/48%
  if (empresa < -PCT_RULES.TOLERANCIA_VALOR)
    erros.push('Total atribuído ultrapassou o Valor Total 61 em ' + formatMoneyBR(Math.abs(empresa)) + '.');
  if (!allowedMoneyByPercent(empresa, vt61, PCT_RULES.EMPRESA_VALID))
    erros.push('Empresa 61 deve ficar com 42%, 44%, 46% ou 48%: atual ' + formatMoneyBR(empresa) + ' (' + formatPctBR(pctSobreVT61(empresa, vt61)) + ').');

  return {
    valido: erros.length === 0,
    erros:  erros,
    resumo: { valorNegocio:valorNegocio, valorComissao:valorComissao, valorTotal61:vt61,
              isParceria:isParceria, somaGerentes:somaGerentes, somaVenda:somaVenda,
              somaCaptacao:somaCaptacao, diretor:diretor.valor, empresa:empresa, totalAtribuido:totalAtribuido }
  };
}

function validarLancamentoFormulario(dados) {
  if (typeof dados === 'string') dados = JSON.parse(dados);
  var validacao = validarRegrasLancamento(dados);
  if (!validacao.valido)
    throw new Error('LANÇAMENTO BLOQUEADO — regras da 61 divergentes:\n\n' + validacao.erros.join('\n'));
  return validacao;
}

function validatePercentuais(vt61, comGV, comGC, comCV1, comCV2, comCC1, comCC2, hasGV, hasGC, isParceria) {
  return validarRegrasLancamento({
    valorNegocio:1, valorComissao:vt61, valorTotal61:vt61, imovelParceiro:isParceria,
    gerenteVendaNome:hasGV?'GV':'', gerenteCaptacaoNome:hasGC?'GC':'',
    corretorVenda1Nome:comCV1>0?'CV1':'', corretorVenda2Nome:comCV2>0?'CV2':'',
    corretorCaptacao1Nome:comCC1>0?'CC1':'', corretorCaptacao2Nome:comCC2>0?'CC2':'',
    comissaoGerenteVenda:comGV, comissaoGerenteCaptacao:comGC, comissaoDiretor:0,
    comissaoCorretorVenda1:comCV1, comissaoCorretorVenda2:comCV2,
    comissaoCorretorCaptacao1:comCC1, comissaoCorretorCaptacao2:comCC2
  }).erros;
}


// ============================================================
//  CÁLCULO DE COMISSÕES
// ============================================================

function calculateCommissions(rowIndex) {
  var sheet   = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Vendas');
  var lastRow = rowIndex || sheet.getLastRow();

  var valorComissao         = toNumberSafe(sheet.getRange('E'  + lastRow).getValue());
  var valorTotal61          = toNumberSafe(sheet.getRange('F'  + lastRow).getValue());
  var valorNegocio          = toNumberSafe(sheet.getRange('D'  + lastRow).getValue());
  var $_Gerente_Venda       = toNumberSafe(sheet.getRange('O'  + lastRow).getValue());
  var $_Gerente_Captacao    = toNumberSafe(sheet.getRange('Q'  + lastRow).getValue());
  var $_Corretor_Venda_1    = toNumberSafe(sheet.getRange('U'  + lastRow).getValue());
  var $_Corretor_Venda_2    = toNumberSafe(sheet.getRange('W'  + lastRow).getValue());
  var $_Corretor_Captador_1 = toNumberSafe(sheet.getRange('Y'  + lastRow).getValue());
  var $_Corretor_Captador_2 = toNumberSafe(sheet.getRange('AA' + lastRow).getValue());
  var $_Diretor             = toNumberSafe(sheet.getRange('S'  + lastRow).getValue());

  var gerenteVendaNome      = sheet.getRange('P'  + lastRow).getValue();
  var gerenteCapNome        = sheet.getRange('R'  + lastRow).getValue();
  var diretorNome           = sheet.getRange('T'  + lastRow).getValue();
  var corretorVenda1Nome    = sheet.getRange('V'  + lastRow).getValue();
  var corretorVenda2Nome    = sheet.getRange('X'  + lastRow).getValue();
  var corretorCaptacao1Nome = sheet.getRange('Z'  + lastRow).getValue();
  var corretorCaptacao2Nome = sheet.getRange('AB' + lastRow).getValue();
  var imovelParceiro        = toBool(sheet.getRange('AC' + lastRow).getValue());

  var removeGerenteVenda    = toBool(sheet.getRange('EJ' + lastRow).getValue());
  var removeGerenteCaptacao = toBool(sheet.getRange('EK' + lastRow).getValue());
  var removeDiretor         = toBool(sheet.getRange('EL' + lastRow).getValue());

  var validacao = validarRegrasLancamento({
    valorNegocio:valorNegocio, valorComissao:valorComissao, valorTotal61:valorTotal61,
    imovelParceiro:imovelParceiro,
    gerenteVendaNome:gerenteVendaNome,   gerenteCaptacaoNome:gerenteCapNome,
    diretorNome:diretorNome,
    corretorVenda1Nome:corretorVenda1Nome, corretorVenda2Nome:corretorVenda2Nome,
    corretorCaptacao1Nome:corretorCaptacao1Nome, corretorCaptacao2Nome:corretorCaptacao2Nome,
    comissaoGerenteVenda:$_Gerente_Venda, comissaoGerenteCaptacao:$_Gerente_Captacao,
    comissaoDiretor:$_Diretor,
    comissaoCorretorVenda1:$_Corretor_Venda_1, comissaoCorretorVenda2:$_Corretor_Venda_2,
    comissaoCorretorCaptacao1:$_Corretor_Captador_1, comissaoCorretorCaptacao2:$_Corretor_Captador_2
  });

  if (!validacao.valido)
    throw new Error('LINHA ' + lastRow + ' BLOQUEADA:\n\n' + validacao.erros.join('\n'));

  var notaFiscal = valorTotal61;
  if (!removeGerenteVenda)    notaFiscal -= $_Gerente_Venda;
  if (!removeGerenteCaptacao) notaFiscal -= $_Gerente_Captacao;
  if (!removeDiretor)         notaFiscal -= $_Diretor;
  notaFiscal -= ($_Corretor_Venda_1 + $_Corretor_Venda_2 + $_Corretor_Captador_1 + $_Corretor_Captador_2);

  var totalAtribuido = $_Gerente_Venda + $_Gerente_Captacao + $_Diretor +
                       $_Corretor_Venda_1 + $_Corretor_Venda_2 + $_Corretor_Captador_1 + $_Corretor_Captador_2;
  var percentEmpresa61 = valorTotal61 > 0 ? (valorTotal61 - totalAtribuido) / valorTotal61 : 0;
  var liquido61 = notaFiscal - (notaFiscal * 0.1633);

  var correcaoTemp  = valorComissao !== 0 ? valorTotal61 / valorComissao : 0;
  var correcaoNG_61 = correcaoTemp === 1 ? 1 : (correcaoTemp < 1 ? correcaoTemp * 2 : correcaoTemp);
  var vgvCorrigido  = correcaoNG_61 * valorNegocio;

  var somaV = $_Corretor_Venda_1 + $_Corretor_Venda_2;
  var somaC = $_Corretor_Captador_1 + $_Corretor_Captador_2;
  var cNG_V1 = somaV !== 0 ? $_Corretor_Venda_1    / somaV : 0;
  var cNG_V2 = somaV !== 0 ? $_Corretor_Venda_2    / somaV : 0;
  var cNG_C1 = somaC !== 0 ? $_Corretor_Captador_1 / somaC : 0;
  var cNG_C2 = somaC !== 0 ? $_Corretor_Captador_2 / somaC : 0;

  var pGV  = valorTotal61 !== 0 ? $_Gerente_Venda       / valorTotal61 : 0;
  var pGC  = valorTotal61 !== 0 ? $_Gerente_Captacao    / valorTotal61 : 0;
  var pDir = valorTotal61 !== 0 ? $_Diretor             / valorTotal61 : 0;
  var pCV1 = valorTotal61 !== 0 ? $_Corretor_Venda_1    / valorTotal61 : 0;
  var pCV2 = valorTotal61 !== 0 ? $_Corretor_Venda_2    / valorTotal61 : 0;
  var pCC1 = valorTotal61 !== 0 ? $_Corretor_Captador_1 / valorTotal61 : 0;
  var pCC2 = valorTotal61 !== 0 ? $_Corretor_Captador_2 / valorTotal61 : 0;

  sheet.getRange('G'  + lastRow).setValue(notaFiscal);
  sheet.getRange('H'  + lastRow).setValue(pGV);
  sheet.getRange('I'  + lastRow).setValue(pGC);
  sheet.getRange('J'  + lastRow).setValue(pDir);
  sheet.getRange('K'  + lastRow).setValue(pCV1);
  sheet.getRange('L'  + lastRow).setValue(pCC1);
  sheet.getRange('M'  + lastRow).setValue(pCV2);
  sheet.getRange('N'  + lastRow).setValue(pCC2);
  sheet.getRange('BE' + lastRow).setValue(liquido61);
  sheet.getRange('BF' + lastRow).setValue(cNG_V1 * vgvCorrigido);
  sheet.getRange('BG' + lastRow).setValue(cNG_V2 * vgvCorrigido);
  sheet.getRange('BH' + lastRow).setValue(cNG_C1 * vgvCorrigido);
  sheet.getRange('BI' + lastRow).setValue(cNG_C2 * vgvCorrigido);
  sheet.getRange('BJ' + lastRow).setValue(cNG_V1 * valorNegocio);
  sheet.getRange('BK' + lastRow).setValue(cNG_V2 * valorNegocio);
  sheet.getRange('BL' + lastRow).setValue(cNG_C1 * valorNegocio);
  sheet.getRange('BM' + lastRow).setValue(cNG_C2 * valorNegocio);
  sheet.getRange('BN' + lastRow).setValue(valorNegocio !== 0 ? valorComissao / valorNegocio : 0);
  sheet.getRange('BP' + lastRow).setValue(percentEmpresa61).setNumberFormat('0.00%');
  sheet.getRange('H'  + lastRow + ':N' + lastRow).setNumberFormat('0.00%');

  Logger.log('calculateCommissions: linha ' + lastRow + ' OK. % empresa = ' + (percentEmpresa61*100).toFixed(2) + '%');
}

function chamarCalculo() {
  var linhaDesejada = 637;
  calculateCommissions(linhaDesejada);
}

function runCalculations() {
  var sheet   = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Vendas');
  var lastRow = sheet.getLastRow();
  if (!sheet.getRange('BP1').getValue()) {
    sheet.getRange('BP1').setValue('%_empresa_61').setFontWeight('bold');
  }
  for (var row = 2; row <= lastRow; row++) {
    var c = sheet.getRange('C' + row).getValue();
    if (c && toNumberSafe(sheet.getRange('D'+row).getValue()) > 0
          && toNumberSafe(sheet.getRange('E'+row).getValue()) > 0
          && toNumberSafe(sheet.getRange('F'+row).getValue()) > 0) {
      try { calculateCommissions(row); }
      catch (e) { Logger.log('AVISO linha ' + row + ': ' + e.message); }
    }
  }
}

function startCalculations(rowIndex) {
  Utilities.sleep(1000);
  if (rowIndex) { calculateCommissions(rowIndex); }
  else { calculateCommissions(); }
}

function inicializarColunaBP() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Vendas');
  if (!sheet.getRange('BP1').getValue()) {
    sheet.getRange('BP1').setValue('%_empresa_61').setFontWeight('bold');
    sheet.getRange('BP2:BP' + sheet.getLastRow()).setNumberFormat('0.00%');
  }
}


// ============================================================
//  VERIFICAÇÃO DE DUPLICATA
// ============================================================

function getExistingSalesForDupCheck() {
  var sheet   = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Vendas');
  var lastRow = sheet.getLastRow();
  var result  = [];
  for (var row = 2; row <= lastRow; row++) {
    // coluna EF (índice 99, 0-based) = bairro conforme newRow[98]
    var bairro   = String(sheet.getRange(row, 99).getValue() || '').trim();
    var valor    = toNumberSafe(sheet.getRange('D' + row).getValue());
    var contrato = String(sheet.getRange('C' + row).getValue() || '').trim();
    if (bairro && valor > 0) result.push({ bairro: bairro, valor: valor, contrato: contrato });
  }
  return result;
}


// ============================================================
//  FILTRAR E TRANSFERIR PARA "CONTROLE"
// ============================================================

function runFilterAndTransfer1() {
  var SPREADSHEET_ID   = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';
  var ss           = SpreadsheetApp.openById(SPREADSHEET_ID);
  var controlSheet = ss.getSheetByName('Controle');
  var sourceSheet  = ss.getSheetByName('Vendas');

  limparFormatacao();

  var startDate = new Date(controlSheet.getRange('A2').getValue());
  var endDate   = new Date(controlSheet.getRange('B2').getValue());

  var columnsToCopy = [
    'Id_Contrato','Data_Contrato','Contrato','Valor_Negocio','Valor_Comissao',
    'Valor_Total_61','NF_61_ Imoveis','Liquido_61','%_empresa_61',
    '%_Gerente_Venda','%_Gerente_Captacao','%_Diretor',
    '%_Corretor_Venda_1','%_Corretor_Venda_2','%_Corretor_Captação_1','%_Corretor_Captação_2',
    '$_Gerente_Venda','Gerente_Venda_Nome','$_Gerente_Captacao','Gerente_Captacao_Nome',
    '$_Diretor','Diretor_Nome','$_Corretor_Venda_1','Corretor_Venda_1_Nome',
    '$_Corretor_Venda_2','Corretor_Venda_2_Nome',
    '$_Corretor_Captador_1','Corretor_Captador_1_Nome',
    '$_Corretor_Captador_2','Corretor_Captador_2_Nome'
  ];

  var headers       = sourceSheet.getRange(1,1,1,sourceSheet.getLastColumn()).getValues()[0];
  var columnIndexes = columnsToCopy.map(function(col){return headers.indexOf(col)+1;});
  var dateColIndex  = headers.indexOf('Data_Contrato');
  if (dateColIndex === -1) throw new Error('Coluna Data_Contrato não encontrada.');

  var lastRow = controlSheet.getLastRow();
  if (lastRow > 4) controlSheet.getRange(5,1,lastRow-4,controlSheet.getLastColumn()).clearContent();

  var data         = sourceSheet.getDataRange().getValues();
  var filteredData = data.filter(function(row, index){
    if(index===0) return true;
    var d = new Date(row[dateColIndex]);
    return d >= startDate && d <= endDate;
  });

  var groupedData = {};
  filteredData.slice(1).forEach(function(row){
    var d = new Date(row[dateColIndex]);
    var my = (d.getMonth()+1)+'/'+d.getFullYear();
    if(!groupedData[my]) groupedData[my]=[];
    groupedData[my].push(row);
  });

  var managerNames = ['José Marques','Marcelo Souza','Luana Salvinski','Thais Tannús','Marcelo Pincinato','Helio Junio','Paolla Gardenia'];
  var currentRow   = 5;

  controlSheet.getRange(currentRow,1,1,columnsToCopy.length+managerNames.length)
    .setValues([columnIndexes.map(function(i){return headers[i-1];}).concat(managerNames)]);
  currentRow++;

  for (var my in groupedData) {
    var monthData = groupedData[my].map(function(row){
      var rd  = columnIndexes.map(function(i){return row[i-1];});
      var gvn = rd[columnsToCopy.indexOf('Gerente_Venda_Nome')];
      var gcn = rd[columnsToCopy.indexOf('Gerente_Captacao_Nome')];
      var liq = toNumberSafe(rd[columnsToCopy.indexOf('Liquido_61')]);
      var vg  = new Array(managerNames.length).fill(0);
      var gi  = [];
      managerNames.forEach(function(n,i){ if(gvn===n||gcn===n) gi.push(i); });
      if(gi.length>0){ var vd=liq/gi.length; gi.forEach(function(i){vg[i]=vd;}); }
      return rd.concat(vg);
    });
    controlSheet.getRange(currentRow,1,monthData.length,columnsToCopy.length+managerNames.length).setValues(monthData);
    currentRow += monthData.length + 7;
  }

  controlSheet.getRange(5,1,currentRow-5,columnsToCopy.length+managerNames.length)
    .setBorder(true,true,true,true,true,true);
  aplicarFormatacaoColunas(controlSheet, columnsToCopy, currentRow, managerNames);
  Utilities.sleep(3000);
  calculateAndInsertTotalsWithManagers();
}

function aplicarFormatacaoColunas(sheet, columnsToCopy, lastDataRow, managerNames) {
  var currCols = ['Valor_Negocio','Valor_Comissao','Valor_Total_61','NF_61_ Imoveis','Liquido_61',
    '$_Gerente_Venda','$_Gerente_Captacao','$_Diretor','$_Corretor_Venda_1','$_Corretor_Venda_2',
    '$_Corretor_Captador_1','$_Corretor_Captador_2'].concat(managerNames);
  var pctCols  = ['%_empresa_61','%_Gerente_Venda','%_Gerente_Captacao','%_Diretor',
    '%_Corretor_Venda_1','%_Corretor_Venda_2','%_Corretor_Captação_1','%_Corretor_Captação_2'];
  var hds = sheet.getRange(5,1,1,sheet.getLastColumn()).getValues()[0];
  hds.forEach(function(h,i){
    var cl = getColumnLetter(i+1);
    var r  = sheet.getRange(cl+'6:'+cl+(lastDataRow-8));
    if(currCols.indexOf(h)!==-1) r.setNumberFormat('R$ #,##0.00');
    else if(pctCols.indexOf(h)!==-1) r.setNumberFormat('0.00%');
  });
}

function limparFormatacao() {
  var ss  = SpreadsheetApp.openById('1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y');
  var cs  = ss.getSheetByName('Controle');
  var lr  = cs.getLastRow(), lc = cs.getLastColumn();
  if(lr>=5){ var r=cs.getRange(5,1,lr-4,lc); r.setFontWeight('normal').setFontStyle('normal').clearContent(); }
}

function calculateAndInsertTotalsWithManagers() {
  var ss = SpreadsheetApp.openById('1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y');
  var cs = ss.getSheetByName('Controle');
  var headers = cs.getRange(5,1,1,cs.getLastColumn()).getValues()[0];
  var managerNames = ['José Marques','Marcelo Souza','Luana Salvinski','Thais Tannús','Marcelo Pincinato','Helio Junio','Paolla Gardenia'];
  var numCols = ['Valor_Negocio','Valor_Comissao','Valor_Total_61','NF_61_ Imoveis','Liquido_61','%_empresa_61'].concat(managerNames);
  var cr = 6, lr = cs.getLastRow();
  var overall = headers.map(function(){return 0;}), ppAcc = headers.map(function(){return 0;}), acAcc = headers.map(function(){return 0;});
  var empresaIdx = headers.indexOf('%_empresa_61');

  while(cr<=lr){
    var md=[];
    while(cr<=lr && cs.getRange(cr,1).getValue()!==''){md.push(cs.getRange(cr,1,1,headers.length).getValues()[0]);cr++;}
    if(md.length>0){
      var totals=headers.map(function(h,i){
        if(numCols.indexOf(h)!==-1){var s=md.reduce(function(a,r){return a+toNumberSafe(r[i]);},0);overall[i]+=s;return s;}return '';
      });
      cs.getRange(cr+1,1,1,headers.length).setValues([['Total'].concat(totals.slice(1))]).setFontWeight('bold').setFontStyle('italic');
      cs.getRange(cr+1,2,1,headers.length-1).setNumberFormat('R$ #,##0.00');
      if(empresaIdx!==-1 && md.length>0) cs.getRange(cr+1,empresaIdx+1).setValue(totals[empresaIdx]/md.length).setNumberFormat('0.00%');
      var ni=headers.indexOf('Valor_Negocio');
      var rp=headers.map(function(h,i){return (numCols.indexOf(h)!==-1&&i!==ni)?(totals[ni]!==0?totals[i]/totals[ni]:''):'';});
      cs.getRange(cr+2,1,1,headers.length).setValues([['Rel. Percent.'].concat(rp.slice(1))]).setFontWeight('bold').setFontStyle('italic');
      cs.getRange(cr+2,2,1,headers.length-1).setNumberFormat('0.00%');
      function calcDirRow(filterFn){
        return headers.map(function(h,ci){
          if(numCols.indexOf(h)!==-1&&managerNames.indexOf(h)===-1)
            return md.filter(filterFn).reduce(function(a,r){return a+toNumberSafe(r[ci]);},0);
          return '';
        });
      }
      var gvIdx=headers.indexOf('Gerente_Venda_Nome'), gcIdx=headers.indexOf('Gerente_Captacao_Nome'), dIdx=headers.indexOf('Diretor_Nome');
      var pp=calcDirRow(function(r){return r[dIdx]&&(r[gvIdx]==='Marcelo Souza'||r[gcIdx]==='Thais Tannús'||r[gvIdx]===''||r[gcIdx]==='');});
      var ac=calcDirRow(function(r){return r[gvIdx]==='Luana Salvinski'||r[gcIdx]==='Luana Salvinski';});
      cs.getRange(cr+3,1,1,headers.length).setValues([['Total Diretor PP'].concat(pp.slice(1))]).setFontWeight('bold');
      cs.getRange(cr+3,2,1,headers.length-1).setNumberFormat('R$ #,##0.00');
      cs.getRange(cr+4,1,1,headers.length).setValues([['Total Diretor AC'].concat(ac.slice(1))]).setFontWeight('bold');
      cs.getRange(cr+4,2,1,headers.length-1).setNumberFormat('R$ #,##0.00');
      ppAcc=ppAcc.map(function(v,i){return v+toNumberSafe(pp[i]);});
      acAcc=acAcc.map(function(v,i){return v+toNumberSafe(ac[i]);});
      cr+=7;
    } else {cr++;}
  }
  var ni=headers.indexOf('Valor_Negocio');
  var gt=overall.map(function(t,i){return numCols.indexOf(headers[i])!==-1?t:'';});
  cs.getRange(cr+1,1,1,headers.length).setValues([['Total Anual'].concat(gt.slice(1))]).setFontWeight('bold').setFontStyle('italic');
  cs.getRange(cr+1,2,1,headers.length-1).setNumberFormat('R$ #,##0.00');
  if(empresaIdx!==-1) cs.getRange(cr+1,empresaIdx+1).setNumberFormat('0.00%');
  var grp=headers.map(function(h,i){return (numCols.indexOf(h)!==-1&&i!==ni)?(gt[ni]!==0?gt[i]/gt[ni]:''):'';});
  cs.getRange(cr+2,1,1,headers.length).setValues([['Rel. Percent. Anual'].concat(grp.slice(1))]).setFontWeight('bold').setFontStyle('italic');
  cs.getRange(cr+2,2,1,headers.length-1).setNumberFormat('0.00%');
  var pp2=ppAcc.map(function(v,i){return numCols.indexOf(headers[i])!==-1&&managerNames.indexOf(headers[i])===-1?v:'';});
  var ac2=acAcc.map(function(v,i){return numCols.indexOf(headers[i])!==-1&&managerNames.indexOf(headers[i])===-1?v:'';});
  cs.getRange(cr+3,1,1,headers.length).setValues([['Total Anual Diretor PP'].concat(pp2.slice(1))]).setFontWeight('bold');
  cs.getRange(cr+3,2,1,headers.length-1).setNumberFormat('R$ #,##0.00');
  cs.getRange(cr+4,1,1,headers.length).setValues([['Total Anual Diretor AC'].concat(ac2.slice(1))]).setFontWeight('bold');
  cs.getRange(cr+4,2,1,headers.length-1).setNumberFormat('R$ #,##0.00');
}