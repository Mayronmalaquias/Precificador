function dim_Clientes(specificRow) {
    var sourceSpreadsheetUrl = 'https://docs.google.com/spreadsheets/d/1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y/edit?gid=146035474#gid=146035474';
    var destinationSpreadsheetUrl = 'https://docs.google.com/spreadsheets/d/1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw/edit?gid=380280845#gid=380280845';
    var sourceSheetName = 'Vendas';
    var destinationSheetName = 'Dim_Cliente';

    var sourceSpreadsheet = SpreadsheetApp.openByUrl(sourceSpreadsheetUrl);
    var destinationSpreadsheet = SpreadsheetApp.openByUrl(destinationSpreadsheetUrl);
    var sourceSheet = sourceSpreadsheet.getSheetByName(sourceSheetName);
    var destinationSheet = destinationSpreadsheet.getSheetByName(destinationSheetName);

    // Usa a linha específica, se fornecida
    var lastSourceRow = specificRow || sourceSheet.getLastRow();

    // Linha específica para transferência (descomente a linha abaixo para usar uma linha específica)
    // lastSourceRow = 294 // Defina o número da linha específica aqui

    // Obter os valores da última linha (ou linha específica) da aba de Vendas
    var data = [
        {CPF: sourceSheet.getRange('AY' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('AX' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('BA' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('AZ' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('BP' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('BO' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('BR' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('BQ' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('BW' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('BV' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('BY' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('BX' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CA' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('BZ' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CC' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CB' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CE' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CD' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CG' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CF' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CH' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CI' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CK' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CJ' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CM' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CL' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CX' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CW' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('CZ' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('CY' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DB' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DA' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DD' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DC' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DF' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DE' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DH' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DG' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DJ' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DI' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DL' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DK' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DN' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DM' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DP' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DO' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DR' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DQ' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DT' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DS' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DV' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DU' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DX' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DW' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('DZ' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('DY' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('EB' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('EA' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()},
        {CPF: sourceSheet.getRange('ED' + lastSourceRow).getValue(), Nome: sourceSheet.getRange('EC' + lastSourceRow).getValue(), Id_Contrato: sourceSheet.getRange('A' + lastSourceRow).getValue(), Link_Drive: sourceSheet.getRange('AQ' + lastSourceRow).getValue()}
    ];


    // Filtrar os dados para remover entradas onde o nome está vazio
    data = data.filter(function(entry) {
        return entry.Nome && entry.Nome.trim() !== '';
    });

    // Identificar a última linha da planilha de destino
    var lastDestRow = destinationSheet.getLastRow() + 1;

    // Inserir os dados filtrados na planilha de destino
    for (var i = 0; i < data.length; i++) {
        destinationSheet.getRange('A' + (lastDestRow + i)).setValue(data[i].CPF);
        destinationSheet.getRange('B' + (lastDestRow + i)).setValue(data[i].Nome);
        destinationSheet.getRange('C' + (lastDestRow + i)).setValue(data[i].Id_Contrato);
        destinationSheet.getRange('D' + (lastDestRow + i)).setValue(data[i].Link_Drive);
    }
}