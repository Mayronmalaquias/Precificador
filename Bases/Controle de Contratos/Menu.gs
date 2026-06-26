function onOpen() {
    var ui = SpreadsheetApp.getUi();
    ui.createMenu('Menu Personalizado')
      .addItem('Abrir Menu', 'showMainMenu')
      .addToUi();
}

function showMainMenu() {
    const html = HtmlService.createHtmlOutputFromFile('Form_Menu')
        .setWidth(1280)
        .setHeight(720); // Define a altura como o tamanho máximo esperado
    SpreadsheetApp.getUi().showModalDialog(html, 'Controle de Contratos 61 Imóveis');
}

function showFormVendas() {
    var html = HtmlService.createHtmlOutputFromFile('Form_Venda')
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Controle de Contratos 61 Imóveis');
}

function showFormBV() {
    var html = HtmlService.createHtmlOutputFromFile('Form_BV') // Certifique-se de que o nome do arquivo está correto
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Controle de Contratos BV'); // Alterei o título para corresponder ao novo nome do formulário
}

function showFormTrello() {
    var html = HtmlService.createHtmlOutputFromFile('Form_Cartao_Trello') // Certifique-se de que o nome do arquivo está correto
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Controle de Contratos Cartão no Trello'); // Alterei o título para corresponder ao novo nome do formulário
}

function showEdicaoVenda() {
    var html = HtmlService.createHtmlOutputFromFile('Form_Edicao_Venda') // Certifique-se de que o nome do arquivo está correto
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Controle de Contratos Edição de Venda'); // Alterei o título para corresponder ao novo nome do formulário
}

function showContratoAntigo() {
    var html = HtmlService.createHtmlOutputFromFile('Form_Contrato/Cliente_Antigos') // Certifique-se de que o nome do arquivo está correto
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Anexar Contratos'); // Alterei o título para corresponder ao novo nome do formulário
}

function showPremiacao() {
    var html = HtmlService.createHtmlOutputFromFile('Form_Premiacao') // Certifique-se de que o nome do arquivo está correto
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Lançar premiações'); // Alterei o título para corresponder ao novo nome do formulário
}

function showPremiacaoDiretor() {
    var html = HtmlService.createHtmlOutputFromFile('Form_Premiacao_Diretor') // Certifique-se de que o nome do arquivo está correto
      .setWidth(1280)
      .setHeight(720);
    SpreadsheetApp.getUi().showModalDialog(html, 'Lançar premiações Diretor'); // Alterei o título para corresponder ao novo nome do formulário
}