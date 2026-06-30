const TRELLO_API_KEY = 'c0cc166d47e1d4dab61cb97f533ff6a1';
const TRELLO_API_TOKEN = 'ATTA7f45e4929f09ce5ad22d636360c68aeac6824299db522511a30977cb076afcde03E6CE39';

const TRELLO_LIST_ID = '6643c5b2966673d78351a842';

const LABEL_ID_COM_FINANCIAMENTO = '6644c76f5084cf29aa94015a';
const LABEL_ID_SEM_FINANCIAMENTO = '6644beec12fc318554bd1d45';

function submitDataToTrello(selectedRow) {
  const sourceSpreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';
  const sourceSheet = SpreadsheetApp.openById(sourceSpreadsheetId).getSheetByName('Vendas');

  if (!sourceSheet) {
    Logger.log('A aba "Vendas" não foi encontrada.');
    return 'Erro: A aba "Vendas" não foi encontrada.';
  }

  // ── OTIMIZAÇÃO: lê a linha inteira de uma vez ──
  var lastCol = sourceSheet.getLastColumn();
  var rowData = sourceSheet.getRange(selectedRow, 1, 1, lastCol).getValues()[0];

  // Helper: coluna letra → índice 0-based
  function col(letter) {
    var n = 0;
    for (var i = 0; i < letter.length; i++) {
      n = n * 26 + (letter.toUpperCase().charCodeAt(i) - 64);
    }
    return n - 1;
  }

  var financiamento = rowData[col('BB')];
  var labelId = financiamento ? LABEL_ID_COM_FINANCIAMENTO : LABEL_ID_SEM_FINANCIAMENTO;

  var data = {
    Id_Contrato:        rowData[col('A')],
    Data_Contrato:      rowData[col('B')],
    Contrato:           rowData[col('C')],
    Valor_Negocio:      rowData[col('D')],
    Valor_Comissao:     rowData[col('E')],

    Data_Assinatura:    formatDateISO(rowData[col('AC')]),
    Data_Escritura:     formatDateISO(rowData[col('AD')]),
    Data_Quitacao:      formatDateISO(rowData[col('AE')]),
    Data_Sinal:         formatDateISO(rowData[col('EN')]),
    Data_Posse:         formatDateISO(rowData[col('AF')]),

    Financiamento:      financiamento,
    Parcela_Comsissao:  rowData[col('AG')],
    Correspondente:     rowData[col('AI')],
    Envio_Docs:         formatDateISO(rowData[col('AJ')]),
    Data_Vistoria:      formatDateISO(rowData[col('AK')]),

    Numero_Protocolo1:  rowData[col('AL')],
    Numero_Protocolo2:  rowData[col('AM')],
    Numero_Protocolo3:  rowData[col('AN')],
    Numero_Protocolo4:  rowData[col('AO')],

    Anexo_Contrato:     rowData[col('AQ')],

    Nome_Comprador1:    rowData[col('AX')],
    CPF_Comprador1:     rowData[col('AY')],
    Nome_Comprador2:    rowData[col('AZ')],
    CPF_Comprador2:     rowData[col('BA')],

    Vendedor_1:         rowData[col('V')],
    Vendedor_2:         rowData[col('X')],
    Captador_1:         rowData[col('Z')],
    Captador_2:         rowData[col('AB')],

    Cliente_Vendedor1:      rowData[col('BO')],
    CPF_Cliente_Vendedor1:  rowData[col('BP')],
    Cliente_Vendedor2:      rowData[col('BQ')],
    CPF_Cliente_Vendedor2:  rowData[col('BR')],

    Data_Intermediaria: rowData[col('EO')]
  };

  // ── OTIMIZAÇÃO: baixa todos os anexos ANTES de criar o cartão ──
  var attachmentUrls = [
    rowData[col('AQ')],
    rowData[col('EP')],
    rowData[col('AR')],
    rowData[col('AS')],
    rowData[col('AT')],
    rowData[col('AU')],
    rowData[col('AV')],
    rowData[col('AW')]
  ];

  var attachmentNames = [
    'Anexo Contrato.pdf',
    'Anexo Contrato Honorario.pdf',
    'Anexo Docs Pessoais Compradores',
    'Anexo Docs Pessoais Vendedores',
    'Anexo Ônus',
    'Anexo Cert Negativas Vendedores',
    'Anexo Cert Negativa Imóvel',
    'Anexo Ficha Cadastral'
  ];

  Logger.log('Baixando anexos antecipadamente...');
  var blobs = attachmentUrls.map(function(url, index) {
    if (!url) return null;
    return downloadFile(url, attachmentNames[index]);
  });

  // ── Cria o cartão ──
  var createCardUrl = 'https://api.trello.com/1/cards?key=' + TRELLO_API_KEY + '&token=' + TRELLO_API_TOKEN;

  var payload = {
    name: String(data.Contrato),
    desc: 'Detalhes do contrato:\n'
      + '- Id: '                  + data.Id_Contrato + '\n'
      + '- Data do Contrato: '    + formatDateBR(data.Data_Contrato) + '\n'
      + '- Valor do Negócio: '    + data.Valor_Negocio + '\n'
      + '- Valor da Comissão: '   + data.Valor_Comissao + '\n'
      + '- Corretor Vendedor: '   + data.Vendedor_1 + ' ; ' + data.Vendedor_2 + '\n'
      + '- Corretor Captador: '   + data.Captador_1 + ' ; ' + data.Captador_2 + '\n'
      + '- Cliente Comprador 1: ' + data.Nome_Comprador1 + ' ; CPF: ' + data.CPF_Comprador1 + '\n'
      + '- Cliente Comprador 2: ' + data.Nome_Comprador2 + ' ; CPF: ' + data.CPF_Comprador2 + '\n'
      + '- Cliente Vendedor 1: '  + data.Cliente_Vendedor1 + ' ; CPF: ' + data.CPF_Cliente_Vendedor1 + '\n'
      + '- Cliente Vendedor 2: '  + data.Cliente_Vendedor2 + ' ; CPF: ' + data.CPF_Cliente_Vendedor2,
    idList: TRELLO_LIST_ID,
    idLabels: [labelId]
  };

  var createCardResponse = trelloRequest(createCardUrl, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  });

  var cardId = JSON.parse(createCardResponse.getContentText()).id;
  Logger.log('Cartão criado com ID: ' + cardId);

  // ── Custom fields ──
  updateCustomField(cardId, "666af9daf7d322220b7c8d9f", data.Data_Assinatura,   'date');
  updateCustomField(cardId, "664798fe673e24d1c66d171e", data.Data_Escritura,    'date');
  updateCustomField(cardId, "6650ddd53d8eecd90077195a", data.Data_Quitacao,     'date');
  updateCustomField(cardId, "6644c620b1716150c030169b", data.Data_Posse,        'date');
  updateCustomField(cardId, "6644c3e3b29e1c339bd1c013", data.Parcela_Comsissao, 'number');
  updateCustomField(cardId, "6644c7c67b5ba32b40af2b59", data.Correspondente,    'text');
  updateCustomField(cardId, "6644c882abd30fdcb4ed345d", data.Envio_Docs,        'date');
  updateCustomField(cardId, "6644c8b0daea4c7ef8f9c8f0", data.Data_Vistoria,     'date');
  updateCustomField(cardId, "665e2487fdde7d5f17b468b2", data.Numero_Protocolo1, 'text');
  updateCustomField(cardId, "665f666a8a20e5811ae6f85c", data.Numero_Protocolo2, 'text');
  updateCustomField(cardId, "665f655c308a72e7d369d39c", data.Numero_Protocolo3, 'text');
  updateCustomField(cardId, "665f65c7a19bc1ae90146ca1", data.Numero_Protocolo4, 'text');

  addChecklistsToCard(cardId, data.Financiamento, data);

  // ── OTIMIZAÇÃO: faz upload dos blobs já baixados (sem sleep de download no meio) ──
  blobs.forEach(function(blob, index) {
    if (blob && blob.getBytes().length > 0) {
      uploadAttachmentToCard(cardId, blob, attachmentNames[index]);
    } else {
      Logger.log('Arquivo ignorado: ' + attachmentNames[index]);
    }
  });

  return 'Cartão criado, campos personalizados, checklists e anexos processados com sucesso!';
}

function trelloRequest(url, options) {
  options = options || {};
  Utilities.sleep(300); // reduzido de 700ms

  var finalOptions = Object.assign({ muteHttpExceptions: true }, options);

  var response = UrlFetchApp.fetch(url, finalOptions);
  var code = response.getResponseCode();
  var text = response.getContentText();

  Logger.log('Trello Response Code: ' + code);

  if (code === 429 || text.indexOf('rate limit') !== -1 || text.indexOf('exceeded') !== -1) {
    Logger.log('Limite atingido. Aguardando 5 segundos...');
    Utilities.sleep(5000);
    response = UrlFetchApp.fetch(url, finalOptions);
    code = response.getResponseCode();
    Logger.log('Retry Response Code: ' + code);
  }

  return response;
}

function updateCustomField(cardId, fieldId, value, valueType) {
  if (value === null || value === undefined || value === '' || value === 'null') {
    return;
  }

  var cleanValue = value;

  if (valueType === 'date') {
    cleanValue = formatDateISO(value);
    if (!cleanValue) return;
  }

  if (valueType === 'number') {
    cleanValue = cleanNumberForTrello(value);
    if (cleanValue === null) return;
  }

  if (valueType === 'text') {
    cleanValue = String(cleanValue);
  }

  var url = 'https://api.trello.com/1/cards/' + cardId + '/customField/' + fieldId + '/item?key=' + TRELLO_API_KEY + '&token=' + TRELLO_API_TOKEN;

  var payload = { value: {} };
  payload.value[valueType] = String(cleanValue);

  trelloRequest(url, {
    method: 'PUT',
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  });
}

function cleanNumberForTrello(value) {
  if (value === null || value === undefined || value === '') return null;

  var numberValue = value;
  if (typeof value === 'string') {
    numberValue = value.replace('R$', '').replace(/\./g, '').replace(',', '.').trim();
  }

  var parsed = Number(numberValue);
  return isNaN(parsed) ? null : parsed;
}

function formatDateISO(date) {
  if (!date) return null;
  var d = new Date(date);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

function formatDateBR(date) {
  if (!date) return '';
  var d = new Date(date);
  if (isNaN(d.getTime())) return '';
  return String(d.getDate()).padStart(2, '0') + '/'
       + String(d.getMonth() + 1).padStart(2, '0') + '/'
       + d.getFullYear();
}

function calculateDate(baseDate, daysOffset) {
  if (!baseDate) return null;
  var d = new Date(baseDate);
  if (isNaN(d.getTime())) return null;
  d.setDate(d.getDate() + daysOffset);
  return d.toISOString();
}

function addChecklistsToCard(cardId, ehFinanciamento, data) {
  var checklistNames = ehFinanciamento
    ? ["Anexar documentos", "Pagamento", "Emissão de NFs", "Financiamento", "Escrituração", "Pós-Escrituração"]
    : ["Anexar documentos", "Pagamento", "Emissão de NFs", "Escrituração", "Pós-Escrituração"];

  var today = new Date();
  var dataQuitacao  = data.Data_Quitacao  ? new Date(data.Data_Quitacao)  : null;
  var dataEscritura = data.Data_Escritura ? new Date(data.Data_Escritura) : null;
  var dataPosse     = data.Data_Posse     ? new Date(data.Data_Posse)     : null;
  var dataSinal     = data.Data_Sinal     ? new Date(data.Data_Sinal)     : null;

  var pagamentosIntermediarios = [];
  if (data.Data_Intermediaria) {
    var dataString = data.Data_Intermediaria.toString();
    var datasRaw = dataString.indexOf(';') !== -1
      ? dataString.split(';').map(function(d) { return d.trim(); })
      : [dataString];

    datasRaw.forEach(function(dateStr) {
      var date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        pagamentosIntermediarios.push({
          name: 'Lembrar - Pagamento Intermediário (' + dateStr + ')',
          state: 'incomplete',
          due: calculateDate(date, -3)
        });
      }
    });
  }

  var checklistItems = {
    "Anexar documentos": [
      { name: "Contrato", state: "complete" },
      { name: "Documentos Pessoais dos Compradores (Prazo)", state: "complete", due: calculateDate(today, 3) },
      { name: "Documentos Pessoais dos Vendedores (Prazo)",  state: "complete", due: calculateDate(today, 3) },
      { name: "Ônus", state: "complete" },
      { name: "Certidões Negativas - Vendedores", state: "complete" },
      { name: "Certidão Negativa - Imóvel", state: "complete" },
      { name: "Ficha Cadastral - Imóvel", state: "complete" }
    ],
    "Pagamento": [
      { name: "Anexar comprovante de Pagamento do Sinal", state: "incomplete" },
      { name: "Salvar comprovantes de pagamento de comissão", state: "incomplete" },
      { name: "Lembrar - Pagamento Quitação (Prazo)",  state: "incomplete", due: dataQuitacao  ? calculateDate(dataQuitacao,  -5) : null },
      { name: "Lembrar - Pagamento Sinal (Prazo)",     state: "incomplete", due: dataSinal     ? calculateDate(dataSinal,     -5) : null },
      { name: "Lembrar - Pagamento Escritura (Prazo)", state: "incomplete", due: dataEscritura ? calculateDate(dataEscritura, -5) : null },
      { name: "Comprovante de Pagamento 1 (Prazo)", state: "incomplete" },
      { name: "Comprovante de Pagamento 2 (Prazo)", state: "incomplete" },
      { name: "Comprovante de Pagamento 3 (Prazo)", state: "incomplete" }
    ].concat(pagamentosIntermediarios),
    "Emissão de NFs": [
      { name: "Anexar NF 61", state: "incomplete" },
      { name: "Anexar NF Corretor Venda", state: "incomplete" },
      { name: "Anexar NF Corretor Captador", state: "incomplete" },
      { name: "Anexar NF Gerente", state: "incomplete" },
      { name: "Solicitar emissão de NF", state: "incomplete" }
    ],
    "Financiamento": ehFinanciamento ? [
      { name: "Enviar documentação do comprador ao banco", state: "incomplete" },
      { name: "Confirmar vistoria feita (prazo)", state: "incomplete", due: calculateDate(today, 15) },
      { name: "Receber Minuta de Contrato de Financiamento (prazo)", state: "incomplete" },
      { name: "Conferir dados", state: "incomplete" },
      { name: "Enviar para o corretor fazer análise e enviar aos clientes", state: "incomplete" },
      { name: "Verificar se o laudo foi emitido (prazo)", state: "incomplete" }
    ] : [],
    "Escrituração": [
      { name: "Elaborar minuta da escritura (Prazo)",       state: "incomplete", due: dataEscritura ? calculateDate(dataEscritura, -5) : null },
      { name: "Aprovar minuta (Prazo)",                     state: "incomplete" },
      { name: "Emitir Guia de ITBI (Prazo)",                state: "incomplete" },
      { name: "Conferir pagamento da Guia",                 state: "incomplete" },
      { name: "Salvar arquivo Escritura Assinada",          state: "incomplete" },
      { name: "Anexar comprovante de pagamento final (prazo)", state: "incomplete" },
      { name: "Receber Protocolo RI e anexar (Prazo)",      state: "incomplete" },
      { name: "Solicitar ônus real atualizada",             state: "incomplete" },
      { name: "Acompanhar averbação da Compra e Venda (Prazo)", state: "incomplete" },
      { name: "Agendar com clientes a assinatura",          state: "incomplete" },
      { name: "Confirmar recebimento da escritura pelo banco", state: "incomplete" },
      { name: "Preencher Número de Protocolo",              state: "incomplete" }
    ],
    "Pós-Escrituração": [
      { name: "Receber dados para encontro de contas (Prazo)",                            state: "incomplete", due: dataPosse ? calculateDate(dataPosse, -7) : null },
      { name: "Realizar encontro de contas (Prazo)",                                      state: "incomplete", due: dataPosse ? calculateDate(dataPosse, -2) : null },
      { name: "Solicitar alteração de titularidade no GDF",                               state: "incomplete" },
      { name: "Verificar com corretor se o Comprador alterou a conta de luz e água (prazo)", state: "incomplete" }
    ]
  };

  checklistNames.forEach(function(checklistName) {
    Utilities.sleep(300); // reduzido de 1000ms

    var checklistUrl = 'https://api.trello.com/1/checklists?key=' + TRELLO_API_KEY + '&token=' + TRELLO_API_TOKEN;

    var checklistResponse = trelloRequest(checklistUrl, {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify({ idCard: cardId, name: checklistName })
    });

    var newChecklistId = JSON.parse(checklistResponse.getContentText()).id;
    var items = checklistItems[checklistName] || [];

    items.forEach(function(item) {
      Utilities.sleep(150); // reduzido de 600ms

      var itemPayload = { name: item.name, state: item.state };
      if (item.due) itemPayload.due = item.due;

      trelloRequest(
        'https://api.trello.com/1/checklists/' + newChecklistId + '/checkItems?key=' + TRELLO_API_KEY + '&token=' + TRELLO_API_TOKEN,
        { method: 'POST', contentType: 'application/json', payload: JSON.stringify(itemPayload) }
      );
    });
  });
}

function downloadFile(fileUrl, fileName) {
  try {
    var match = fileUrl.match(/\/d\/([a-zA-Z0-9_-]+)\//);
    if (!match || !match[1]) {
      Logger.log('URL inválida: ' + fileUrl);
      return null;
    }

    var downloadUrl = 'https://drive.google.com/uc?export=download&id=' + match[1];
    Utilities.sleep(300); // reduzido de 800ms

    var response = UrlFetchApp.fetch(downloadUrl, { muteHttpExceptions: true });
    var blob = response.getBlob();

    if (blob.getContentType() === 'text/html') {
      Logger.log('URL retornou HTML, não é arquivo válido: ' + downloadUrl);
      return null;
    }

    blob.setName(fileName);
    Logger.log('Baixado: ' + fileName + ' | ' + blob.getBytes().length + ' bytes');
    return blob;

  } catch (e) {
    Logger.log('Erro ao baixar: ' + fileUrl + ' | ' + e.message);
    return null;
  }
}

function uploadAttachmentToCard(cardId, fileBlob, fileName) {
  Utilities.sleep(400); // reduzido de 1200ms

  var boundary = '-------314159265358979323846';
  var body = Utilities.newBlob(
    '\r\n--' + boundary + '\r\n'
    + 'Content-Disposition: form-data; name="file"; filename="' + fileName + '"\r\n'
    + 'Content-Type: ' + fileBlob.getContentType() + '\r\n\r\n'
  ).getBytes()
    .concat(fileBlob.getBytes())
    .concat(Utilities.newBlob('\r\n--' + boundary + '--').getBytes());

  var response = trelloRequest(
    'https://api.trello.com/1/cards/' + cardId + '/attachments?key=' + TRELLO_API_KEY + '&token=' + TRELLO_API_TOKEN,
    { method: 'POST', contentType: 'multipart/form-data; boundary=' + boundary, payload: body }
  );

  Logger.log('Upload concluído: ' + fileName);
}