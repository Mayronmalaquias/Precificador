function doGet() {
    return HtmlService.createHtmlOutputFromFile('Form_BV'); // Substitua 'FormularioContrato' pelo nome do seu arquivo HTML
}

function getContracts() {
    var sheet = SpreadsheetApp.openById('1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y').getSheetByName('Vendas');
    var range = sheet.getRange('C2:C' + sheet.getLastRow()); // Ajuste conforme a necessidade
    var values = range.getValues();
    var contracts = values.map(function(row, index) {
        return { contract: row[0], row: index + 2 }; // +2 porque o array começa em 0 e os dados começam na linha 2
    });
    return contracts.filter(contract => contract.contract); // Filtra elementos vazios
}

function submitDataBV(selectedRow) {
    // ID da planilha fonte (onde os dados serão lidos)
    var sourceSpreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y';
    var sourceSheet = SpreadsheetApp.openById(sourceSpreadsheetId).getSheetByName('Vendas');
    
    // ID da planilha destino (onde os dados serão escritos)
    var destinationSpreadsheetId = '1Kbg1WVCaqx9uOAIXgZW47BazUWNJeBRgpeI8NKq87eA';
    var destinationSheet = SpreadsheetApp.openById(destinationSpreadsheetId).getSheetByName('BV');

    // Verifica se as abas foram encontradas
    if (!sourceSheet || !destinationSheet) {
        Logger.log('Uma das abas não foi encontrada. Verifique os nomes das abas.');
        return 'Erro: Uma das abas não foi encontrada. Verifique os nomes das abas.';
    }
    // Supondo que você queira transferir dados das colunas C, D e E da aba 'BV' para colunas específicas na aba 'Destino'
    var dataA = sourceSheet.getRange('A' + selectedRow).getValue(); // Id_Contrato
    var dataB = sourceSheet.getRange('B' + selectedRow).getValue(); // Data_Contrato
    var dataC = sourceSheet.getRange('C' + selectedRow).getValue(); // Contrato
    var dataD = sourceSheet.getRange('D' + selectedRow).getValue(); // Valor_Negocio
    var dataE = sourceSheet.getRange('E' + selectedRow).getValue(); // Valor_Comissao
    var dataF = sourceSheet.getRange('F' + selectedRow).getValue(); // Valor_Total_61
    var dataG = sourceSheet.getRange('G' + selectedRow).getValue(); // NF_61_ Imoveis
    var dataH = sourceSheet.getRange('H' + selectedRow).getValue(); // %_Gerente_Venda
    var dataI = sourceSheet.getRange('I' + selectedRow).getValue(); // %_Gerente_Captacao
    var dataJ = sourceSheet.getRange('J' + selectedRow).getValue(); // %_Diretor
    var dataK = sourceSheet.getRange('K' + selectedRow).getValue(); // %_Corretor_Venda_1
    var dataL = sourceSheet.getRange('L' + selectedRow).getValue(); // %_Corretor_Captação_1
    var dataM = sourceSheet.getRange('M' + selectedRow).getValue(); // %_Corretor_Venda_2
    var dataN = sourceSheet.getRange('N' + selectedRow).getValue(); // %_Corretor_Captação_2
    var dataO = sourceSheet.getRange('O' + selectedRow).getValue(); // $_Gerente_Venda
    var dataP = sourceSheet.getRange('P' + selectedRow).getValue(); // Gerente_Venda_Nome
    var dataQ = sourceSheet.getRange('Q' + selectedRow).getValue(); // $_Gerente_Captacao
    var dataR = sourceSheet.getRange('R' + selectedRow).getValue(); // Gerente_Captacao_Nome
    var dataS = sourceSheet.getRange('S' + selectedRow).getValue(); // $_Diretor
    var dataT = sourceSheet.getRange('T' + selectedRow).getValue(); // Diretor_Nome
    var dataU = sourceSheet.getRange('U' + selectedRow).getValue(); // $_Corretor_Venda_1
    var dataV = sourceSheet.getRange('V' + selectedRow).getValue(); // Corretor_Venda_1_Nome
    var dataW = sourceSheet.getRange('W' + selectedRow).getValue(); // $_Corretor_Venda_2
    var dataX = sourceSheet.getRange('X' + selectedRow).getValue(); // Corretor_Venda_2_Nome
    var dataY = sourceSheet.getRange('Y' + selectedRow).getValue(); // $_Corretor_Captador_1
    var dataZ = sourceSheet.getRange('Z' + selectedRow).getValue(); // Corretor_Captador_1_Nome
    var dataAA = sourceSheet.getRange('AA' + selectedRow).getValue(); // $_Corretor_Captador_2
    var dataAB = sourceSheet.getRange('AB' + selectedRow).getValue(); // Corretor_Captador_2_Nome
    var dataBE = sourceSheet.getRange('BE' + selectedRow).getValue(); //  Liquido_61
    var dataBF = sourceSheet.getRange('BF' + selectedRow).getValue(); //  neg_Gerado_V1
    var dataBG = sourceSheet.getRange('BG' + selectedRow).getValue(); //  neg_Gerado_V2
    var dataBH = sourceSheet.getRange('BH' + selectedRow).getValue(); //  neg_Gerado_C1
    var dataBI = sourceSheet.getRange('BI' + selectedRow).getValue(); //  neg_Gerado_C2
    var dataBC = sourceSheet.getRange('BC' + selectedRow).getValue(); //  Imobiliaria_Venda
    var dataBD = sourceSheet.getRange('BD' + selectedRow).getValue(); //   Imobiliaria_Cap
    var dataBB = sourceSheet.getRange('BB' + selectedRow).getValue(); //   Financiamento
    var dataAH = sourceSheet.getRange('AH' + selectedRow).getValue(); //   data comissao 1 
    var dataBS = sourceSheet.getRange('BS' + selectedRow).getValue(); //   Valor P  1 Comissao
    var dataCN = sourceSheet.getRange('CN' + selectedRow).getValue(); //   Valor P  2 Comissao
    var dataBT = sourceSheet.getRange('BT' + selectedRow).getValue(); //   Data P  2 Comissao
    var dataCO = sourceSheet.getRange('CO' + selectedRow).getValue(); //   Valor P  3 Comissao
    var dataBU = sourceSheet.getRange('BU' + selectedRow).getValue(); //   Data P  3 Comissao
    var dataCQ = sourceSheet.getRange('CQ' + selectedRow).getValue(); //   Valor P  4 Comissao
    var dataCP = sourceSheet.getRange('CP' + selectedRow).getValue(); //   Data P  4 Comissao
    var dataCS = sourceSheet.getRange('CS' + selectedRow).getValue(); //   Valor P  5 Comissao
    var dataCR = sourceSheet.getRange('CR' + selectedRow).getValue(); //   Data P  5 Comissao



    // Supondo que você quer colocar esses dados em células específicas na aba 'Destino'
    // Colocando dados nas células especificadas da aba 'Destino'
    destinationSheet.getRange('E4').setValue(dataA); // Id_Contrato
    destinationSheet.getRange('B5').setValue(dataB); // Data_Contrato
    destinationSheet.getRange('B6').setValue(dataC); // Contrato
    destinationSheet.getRange('B9').setValue(dataD); // Valor_Negocio
    destinationSheet.getRange('B10').setValue(dataE); // Valor_Comissao
    destinationSheet.getRange('B11').setValue(dataF); // Valor_Total_61
    destinationSheet.getRange('B12').setValue(dataG); // NF_61_ Imoveis
    destinationSheet.getRange('C21').setValue(dataH); // %_Gerente_Venda
    destinationSheet.getRange('C18').setValue(dataI); // %_Gerente_Captacao
    destinationSheet.getRange('C19').setValue(dataK); // %_Corretor_Venda_1
    destinationSheet.getRange('C16').setValue(dataL); // %_Corretor_Captação_1
    destinationSheet.getRange('C20').setValue(dataM); // %_Corretor_Venda_2
    destinationSheet.getRange('C17').setValue(dataN); // %_Corretor_Captação_2
    destinationSheet.getRange('D21').setValue(dataO); // $_Gerente_Venda
    destinationSheet.getRange('B21').setValue(dataP); // Gerente_Venda_Nome
    destinationSheet.getRange('D18').setValue(dataQ); // $_Gerente_Captacao
    destinationSheet.getRange('B18').setValue(dataR); // Gerente_Captacao_Nome
    destinationSheet.getRange('D19').setValue(dataU); // $_Corretor_Venda_1
    destinationSheet.getRange('B19').setValue(dataV); // Corretor_Venda_1_Nome
    destinationSheet.getRange('D20').setValue(dataW); // $_Corretor_Venda_2
    destinationSheet.getRange('B20').setValue(dataX); // Corretor_Venda_2_Nome
    destinationSheet.getRange('D16').setValue(dataY); // $_Corretor_Captador_1
    destinationSheet.getRange('B16').setValue(dataZ); // Corretor_Captador_1_Nome
    destinationSheet.getRange('D17').setValue(dataAA); // $_Corretor_Captador_2
    destinationSheet.getRange('B17').setValue(dataAB); // Corretor_Captador_2_Nome
    destinationSheet.getRange('B13').setValue(dataBE); // Liquido_61
    destinationSheet.getRange('D11').setValue(dataBF); // neg_Gerado_V1
    destinationSheet.getRange('D12').setValue(dataBG); // neg_Gerado_V2
    destinationSheet.getRange('D9').setValue(dataBH); // neg_Gerado_C1
    destinationSheet.getRange('D10').setValue(dataBI); // neg_Gerado_C2
    destinationSheet.getRange('B7').setValue(dataBC); // Imobiliaria_Venda
    destinationSheet.getRange('B8').setValue(dataBD); // Imobiliaria_Cap
    destinationSheet.getRange('B30').setValue(dataBB); // Financiamento
    destinationSheet.getRange('C24').setValue(dataAH); // data comissao 1 
    destinationSheet.getRange('B24').setValue(dataBS); // Valor P  1 Comissao
    destinationSheet.getRange('B25').setValue(dataCN); // Valor P  2 Comissao
    destinationSheet.getRange('C25').setValue(dataBT); // Data P  2 Comissao
    destinationSheet.getRange('B26').setValue(dataCO); // Valor P  3 Comissao
    destinationSheet.getRange('C26').setValue(dataBU); // Data P  3 Comissao
    destinationSheet.getRange('B27').setValue(dataCQ); // Valor P  4 Comissao
    destinationSheet.getRange('C27').setValue(dataCP); // Data P  4 Comissao
    destinationSheet.getRange('B28').setValue(dataCS); // Valor P  5 Comissao
    destinationSheet.getRange('C28').setValue(dataCR); // Data P  5 Comissaoo
    // Limpa as células de destino
    destinationSheet.getRange('D24').clearContent(); // Limpa a célula D24
    destinationSheet.getRange('D25').clearContent(); // Limpa a célula D25
    destinationSheet.getRange('D26').clearContent(); // Limpa a célula D26
    destinationSheet.getRange('D27').clearContent(); // Limpa a célula D27
    destinationSheet.getRange('D28').clearContent(); // Limpa a célula D28

    

    return 'Dados transferidos com sucesso para a aba Destino!';
}