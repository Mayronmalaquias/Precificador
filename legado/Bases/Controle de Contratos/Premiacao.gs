// Função para preencher os dados dos gerentes no dropdown
function getDropdownGerente() {
  const ss = SpreadsheetApp.openById('1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw');
  const gerentesSheet = ss.getSheetByName('Dim_Gerente');
  
  const gerentesData = gerentesSheet.getRange('A2:B' + gerentesSheet.getLastRow()).getValues();
  
  return {
    gerentes: gerentesData.map(row => ({ id: row[0], nome: row[1] })),
  };
}

// Função para atualizar o percentual de premiação em massa
function atualizarPercentual(percentual, idContrato, percentualColIndex) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();

    const contratoColIndex = data[0].indexOf('Id_Contrato') + 1;

    for (let i = 1; i < data.length; i++) {
        if (data[i][contratoColIndex - 1] == idContrato) {
            Logger.log(`Atualizando contrato: ${idContrato}, Percentual: ${percentual}, Coluna: ${percentualColIndex}`);
            sheet.getRange(i + 1, percentualColIndex).setValue(percentual);
            break;
        }
    }
}


// Função para filtrar as vendas de um gerente em um intervalo de datas
function filtrarVendasGerente(gerente, startDateStr, endDateStr) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();
  
    const startDate = new Date(startDateStr);
    const endDate = new Date(endDateStr);
  
    const idContratoColIndex = data[0].indexOf('Id_Contrato');
    const dataContratoColIndex = data[0].indexOf('Data_Contrato');
    const contratoColIndex = data[0].indexOf('Contrato');  // Coluna "Contrato"
    const gerenteVendaColIndex = data[0].indexOf('Gerente_Venda_Nome');
    const gerenteCaptacaoColIndex = data[0].indexOf('Gerente_Captacao_Nome');
    const liquido61ColIndex = data[0].indexOf('Valor_Comissao'); // Mantendo no código, mas não na visualização
    const percentualPremiacaoColIndex = data[0].indexOf('Percentual_Premiacao');
    const valorComissaoColIndex = data[0].indexOf('Valor_Comissao');  // Coluna "Valor_Comissao"
    const valorTotal61ColIndex = data[0].indexOf('Valor_Total_61');   // Coluna "Valor_Total_61"

    let totalPeriodo = 0;
    let totalEmpresaPeriodo = 0;

    // Atualizando a tabela HTML sem a coluna "Liquido_61" (NF_61_ Imoveis)
    let htmlTable = '<table><tr><th>Id_Contrato</th><th>Data_Contrato</th><th>Contrato</th><th>Gerente_Venda</th><th>Gerente_Captacao</th><th>Valor_Comissao</th><th>Valor_Total_61</th><th>Percentual_Premiacao</th></tr>';
    
    // Filtra os dados pelo gerente e intervalo de datas
    data.forEach((row, index) => {
        if (index === 0) return; // Ignora o cabeçalho
        const rowDate = new Date(row[dataContratoColIndex]);
        const isInDateRange = rowDate >= startDate && rowDate <= endDate;

        if (isInDateRange) {
            // Somar o "Líquido Empresa no Período" usando "Liquido_61" (NF_61_ Imoveis)
            totalEmpresaPeriodo += parseFloat(row[liquido61ColIndex]) || 0;

            // Filtrar vendas associadas ao gerente
            const isMatchingGerente = (row[gerenteVendaColIndex] === gerente || row[gerenteCaptacaoColIndex] === gerente);
            if (isMatchingGerente) {
                totalPeriodo += parseFloat(row[liquido61ColIndex]) || 0;
                htmlTable += '<tr>';
                htmlTable += `<td>${row[idContratoColIndex]}</td>`;
                htmlTable += `<td>${formatarData(row[dataContratoColIndex])}</td>`;
                htmlTable += `<td>${row[contratoColIndex] || ''}</td>`;
                
                // Adicionando os valores das colunas de "Gerente de Venda" e "Gerente de Captação"
                htmlTable += `<td>${row[gerenteVendaColIndex] || ''}</td>`;
                htmlTable += `<td>${row[gerenteCaptacaoColIndex] || ''}</td>`;
                
                // Adicionando os valores de "Valor_Comissao" e "Valor_Total_61"
                htmlTable += `<td>${formatarValor(row[valorComissaoColIndex])}</td>`;
                htmlTable += `<td>${formatarValor(row[valorTotal61ColIndex])}</td>`;
                
                // Adicionando a coluna de "Percentual_Premiacao"
                htmlTable += `<td><input type="text" value="${row[percentualPremiacaoColIndex] || ''}" data-idcontrato="${row[idContratoColIndex]}" onchange="atualizarPercentual(this.value, ${row[idContratoColIndex]}, ${percentualPremiacaoColIndex + 1})"></td>`;
                htmlTable += '</tr>';
            }
        }
    });

    htmlTable += '</table>';

    // Cálculo do "Líquido Empresa no Ano" e "Líquido Gerente no Ano"
    const totalEmpresaAno = calcularTotalAnoEmpresa();
    const totalAno = calcularTotalAno(gerente, startDateStr);

    // Cálculo da participação do gerente
    const participacaoPeriodo = totalEmpresaPeriodo > 0 ? (totalPeriodo / totalEmpresaPeriodo) * 100 : 0;
    const participacaoAno = totalEmpresaAno > 0 ? (totalAno / totalEmpresaAno) * 100 : 0;

    return {
        htmlTable: htmlTable,
        totalPeriodo: formatarValor(totalPeriodo),
        totalEmpresaPeriodo: formatarValor(totalEmpresaPeriodo),
        totalAno: formatarValor(totalAno),
        totalEmpresaAno: formatarValor(totalEmpresaAno),
        participacaoPeriodo: `${participacaoPeriodo.toFixed(2)}%`,
        participacaoAno: `${participacaoAno.toFixed(2)}%`
    };
}




// Função para calcular o total do "Líquido 61" no ano para o gerente
function calcularTotalAno(gerente, startDateStr) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();

    const anoFiltrado = startDateStr.substring(0, 4);
    const liquido61ColIndex = data[0].indexOf('Valor_Comissao');
    const gerenteVendaColIndex = data[0].indexOf('Gerente_Venda_Nome');
    const gerenteCaptacaoColIndex = data[0].indexOf('Gerente_Captacao_Nome');
    const dataContratoColIndex = data[0].indexOf('Data_Contrato');

    let totalAno = 0;

    data.forEach((row, index) => {
        if (index === 0) return; // Ignora o cabeçalho

        const rowYear = new Date(row[dataContratoColIndex]).getFullYear();
        if (rowYear == anoFiltrado) {
            const isMatchingGerente = (row[gerenteVendaColIndex] === gerente || row[gerenteCaptacaoColIndex] === gerente);
            if (isMatchingGerente) {
                totalAno += parseFloat(row[liquido61ColIndex]) || 0;
            }
        }
    });

    return totalAno;
}


// Função para calcular o total do "Líquido 61" no ano para a empresa
function calcularTotalAnoEmpresa() {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();

    let totalEmpresaAno = 0;
    const liquido61ColIndex = data[0].indexOf('Valor_Comissao');
    const dataContratoColIndex = data[0].indexOf('Data_Contrato');

    const currentYear = new Date().getFullYear();

    data.forEach((row, index) => {
        if (index === 0) return; // Ignora o cabeçalho

        const rowYear = new Date(row[dataContratoColIndex]).getFullYear();
        if (rowYear == currentYear) {
            totalEmpresaAno += parseFloat(row[liquido61ColIndex]) || 0;
        }
    });

    return totalEmpresaAno;
}

// Funções auxiliares para formatação
function formatarValor(valor) {
    if (!valor) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
}

function formatarData(dataStr) {
    const date = new Date(dataStr);
    const dia = String(date.getDate()).padStart(2, '0');
    const mes = String(date.getMonth() + 1).padStart(2, '0');
    const ano = date.getFullYear();
    return `${dia}/${mes}/${ano}`;
}
