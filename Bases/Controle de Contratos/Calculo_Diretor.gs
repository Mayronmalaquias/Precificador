function calculateCommissionsDiretor() {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = spreadsheet.getSheetByName('Vendas'); // Ajuste para o nome correto da sua aba

    // Obter a última linha com dados na planilha
    var lastRow = sheet.getLastRow();

    // Determinar a faixa de linhas a processar (últimas 100 linhas)
    var startRow = Math.max(lastRow - 99, 1); // Garante que não tente acessar linhas negativas

    // Obter todos os valores da coluna EI (Percent_Diretor) de uma só vez
    var percentDiretorRange = sheet.getRange('J' + startRow + ':J' + lastRow).getValues();

    // Iterar apenas sobre as linhas com Percent_Diretor válido
    for (var i = 0; i < percentDiretorRange.length; i++) {
        var rowIndex = startRow + i;
        var percentDiretor = percentDiretorRange[i][0]; // Obter o valor da coluna EI para a linha correspondente

        // Verificar se o Percent_Diretor está preenchido e é maior que 0
        if (percentDiretor && percentDiretor > 0) {
            // Obter os valores da coluna E (Valor_Comissao)
            var valorComissao = sheet.getRange('E' + rowIndex).getValue(); // Coluna E: Valor_Comissao

            // Registrar os valores no log
            Logger.log('Linha: ' + rowIndex);
            Logger.log('Valor Comissão: ' + valorComissao);
            Logger.log('Percent. Diretor: ' + percentDiretor);

            // Calcular os valores
            var comissaoDiretor = valorComissao * percentDiretor; // Calcular comissão do diretor

            // Registrar o valor de comissão no log
            Logger.log('Comissão Diretor (R$): ' + comissaoDiretor);

            // Atualizar a planilha com os valores calculados
            sheet.getRange('S' + rowIndex).setValue(comissaoDiretor); // Coluna S: Atualiza $_Diretor
        } else {
            Logger.log('Linha ' + rowIndex + ' ignorada: Percentual Diretor não preenchido ou zero.');
        }
    }
}
