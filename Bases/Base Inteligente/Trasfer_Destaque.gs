function processXLSXFiles(segurosContent, imoveisContent, assinadosContent) {
  const ss = SpreadsheetApp.openById('1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw');

  const imoveisRows = processImoveisXLSX(imoveisContent, ss, segurosContent, assinadosContent);
  const updatedRowsWithIds = replaceNamesWithIds(imoveisRows, ss);

  const sheetEstoque = ss.getSheetByName('Fato_Destaque');
  const lastRow = sheetEstoque.getLastRow();
  const lastCol = sheetEstoque.getLastColumn();
  if (lastRow > 1) {
    sheetEstoque.getRange(2, 1, sheetEstoque.getMaxRows() - 1, lastCol).clearContent();
  }

  if (updatedRowsWithIds.length > 0) {
    sheetEstoque.getRange(2, 1, updatedRowsWithIds.length, updatedRowsWithIds[0].length).setValues(updatedRowsWithIds);
  }

  substituirNomesPorIds(ss);

  return 'Dados XLSX processados e inseridos com sucesso!';
}

function processImoveisXLSX(imoveisContent, ss, segurosContent, assinadosContent) {
  const sheetCorretores = ss.getSheetByName('Dim_Corretor');
  const corretores = sheetCorretores.getRange('A2:C' + sheetCorretores.getLastRow()).getValues();

  const nomeParaId = {};
  const nomeParaGerente = {};

  corretores.forEach(corretor => {
    nomeParaId[corretor[1]] = corretor[0];
    nomeParaGerente[corretor[1]] = corretor[2];
  });

  const headers = imoveisContent[0];
  const data = imoveisContent.slice(1);

  const updatedRows = data.map(row => {
    const codigo = row[headers.indexOf('Codigo')];
    const captadores = row[headers.indexOf('Captadores')] || '';
    const captadorParts = separarCaptadores(captadores);

    const captador1 = nomeParaId[captadorParts[0]] || captadorParts[0];
    const captador2 = nomeParaId[captadorParts[1]] || captadorParts[1];
    const captador3 = nomeParaId[captadorParts[2]] || captadorParts[2];
    const gerente = nomeParaGerente[captadorParts[0]] || '';

    const endereco = row[headers.indexOf('Endereco')];
    const valor = row[headers.indexOf('Valor')];
    const bairro = row[headers.indexOf('Bairro')];
    const publicacaoNaInternet = checarPublicacao(row, headers);
    const portalOlxBrasil = filtraOlx(row[headers.indexOf('PortalOlxBrasil')]);
    const portalImovelWeb = filtraImovelWeb(row[headers.indexOf('PortalImovelWeb')]);
    const imovelSeguro = checarSeguro(codigo, segurosContent);
    const assinado = checarAssinados(codigo, assinadosContent);

    return [codigo, captador1, captador2, captador3, gerente, endereco, bairro, publicacaoNaInternet, portalOlxBrasil, portalImovelWeb, imovelSeguro, assinado, valor];
  });

  return updatedRows;
}

function separarCaptadores(captadores) {
  if (!captadores) return [null, null, null];
  const parts = captadores.split('|');
  return [parts[0] || null, parts[1] || null, parts[2] || null];
}

function replaceNamesWithIds(rows, ss) {
  const sheetCorretores = ss.getSheetByName('Dim_Corretor');
  const corretores = sheetCorretores.getRange('A2:C' + sheetCorretores.getLastRow()).getValues();

  const nomeParaId = {};
  corretores.forEach(corretor => {
    nomeParaId[corretor[1]] = corretor[0];
  });

  const updatedRows = rows.map(row => {
    row[1] = checkAndReplace(row[1], nomeParaId);
    row[2] = checkAndReplace(row[2], nomeParaId);
    row[3] = checkAndReplace(row[3], nomeParaId);
    return row;
  });

  return updatedRows;
}

function checkAndReplace(value, nomeParaId) {
  return nomeParaId[value] || value;
}

function substituirNomesPorIds(ss) {
  var sheetDados = ss.getSheetByName('Fato_Destaque');
  var sheetCorretores = ss.getSheetByName('Dim_Corretor');

  var captadoresRange = sheetDados.getRange(2, 2, sheetDados.getLastRow() - 1, 3).getValues();
  var corretoresRange = sheetCorretores.getRange(2, 1, sheetCorretores.getLastRow() - 1, 2).getValues();

  var nomeParaId = {};
  for (var i = 0; i < corretoresRange.length; i++) {
    var id = corretoresRange[i][0];
    var nome = corretoresRange[i][1];
    nomeParaId[nome.trim().toLowerCase()] = id;
  }

  function isId(value) {
    return typeof value === 'string' && value.startsWith('C') && !isNaN(value.substring(1));
  }

  for (var i = 0; i < captadoresRange.length; i++) {
    var captador1 = captadoresRange[i][0];
    var captador2 = captadoresRange[i][1];
    var captador3 = captadoresRange[i][2];

    if (typeof captador1 === 'string' && !isId(captador1)) {
      var idCaptador1 = nomeParaId[captador1.trim().toLowerCase()];
      if (idCaptador1) sheetDados.getRange(i + 2, 2).setValue(idCaptador1);
    }

    if (typeof captador2 === 'string' && !isId(captador2)) {
      var idCaptador2 = nomeParaId[captador2.trim().toLowerCase()];
      if (idCaptador2) sheetDados.getRange(i + 2, 3).setValue(idCaptador2);
    }

    if (typeof captador3 === 'string' && !isId(captador3)) {
      var idCaptador3 = nomeParaId[captador3.trim().toLowerCase()];
      if (idCaptador3) sheetDados.getRange(i + 2, 4).setValue(idCaptador3);
    }
  }
}

// ─── FUNÇÕES CORRIGIDAS ───────────────────────────────────────────────────────

// CORREÇÃO 1 & 2: filtraOlx e filtraImovelWeb
// Problema original: split por palavra perdia "Super destaque" no OLX (não estava em
// palavrasPermitidas) e era frágil no ImovelWeb. Substituído por includes() direto
// na string, garantindo que qualquer valor retornado é um dos 3 rótulos canônicos.

function filtraOlx(valor) {
  if (!valor) return '';
  const s = String(valor);
  if (s.toLowerCase().includes('desativado')) return 'Simples';
  const sl = s.toLowerCase();
  if (sl.includes('super destaque')) return 'Super destaque';
  if (sl.includes('destaque'))       return 'Destaque';
  if (sl.includes('simples'))        return 'Simples';
  return '';
}

function filtraImovelWeb(valor) {
  if (!valor) return '';
  const s = String(valor);
  if (s.toLowerCase().includes('desativado')) return 'Simples';
  const sl = s.toLowerCase();
  if (sl.includes('super destaque')) return 'Super destaque';
  if (sl.includes('destaque'))       return 'Destaque';
  if (sl.includes('simples'))        return 'Simples';
  return '';
}

// CORREÇÃO 3: checarPublicacao
// Problema original: retornava 'Não Liberada' (L maiúsculo) mas o campo original
// do sistema grava 'Não liberada' (l minúsculo) → filtros do BI não batiam.

function checarPublicacao(row, headers) {
  const portalOlx       = (row[headers.indexOf('PortalOlxBrasil')] || '').toLowerCase();
  const portalImovelWeb = (row[headers.indexOf('PortalImovelWeb')] || '').toLowerCase();
  if (portalOlx.includes('desativado') && portalImovelWeb.includes('desativado')) {
    return 'Não liberada';
  }
  return row[headers.indexOf('PublicacaoNaInternet')];
}

function checarSeguro(codigo, segurosContent) {
  const segurosRows = segurosContent.slice(2);
  const normalizedCodigo = String(codigo).trim();

  return segurosRows.some(row => {
    const codigoSeguro = String(row[2]).trim();
    const situacaoImovel = row[5];
    return (
      codigoSeguro === normalizedCodigo &&
      situacaoImovel !== 'Cadastrado' &&
      situacaoImovel !== 'Com Pendência'
    );
  }) ? 'Sim' : 'Não';
}

function checarAssinados(codigo, assinadosContent) {
  const assinadosRows = assinadosContent.slice(2);
  const normalizedCodigo = String(codigo).trim();
  return assinadosRows.some(row => String(row[2]).trim() === normalizedCodigo) ? 'Sim' : 'Não';
}