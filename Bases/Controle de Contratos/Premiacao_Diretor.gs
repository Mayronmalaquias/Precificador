// Função para preencher os dados dos diretores no dropdown
function getDropdownDiretor() {
    const ss = SpreadsheetApp.openById('1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw'); // Substitua pelo ID da sua planilha
    const diretoresSheet = ss.getSheetByName('Dim_Diretor');
    
    const diretoresData = diretoresSheet.getRange('A2:B' + diretoresSheet.getLastRow()).getValues();
    
    return {
        diretores: diretoresData.map(row => ({ id: row[0], nome: row[1] })),
    };
}

function atualizarPercentualDiretor(percentual, idContrato, percentualColIndex) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();

    const contratoColIndex = data[0].indexOf('Id_Contrato') + 1;

    // Converte o valor do percentual fornecido (ex: "4" será convertido para 0.04)
    const percentualFormatado = parseFloat(percentual) / 100;

    for (let i = 1; i < data.length; i++) {
        if (data[i][contratoColIndex - 1] == idContrato) {
            Logger.log(`Atualizando contrato: ${idContrato}, Percentual: ${percentualFormatado}, Coluna: ${percentualColIndex}`);
            
            // Grava o percentual formatado na planilha
            sheet.getRange(i + 1, percentualColIndex).setValue(percentualFormatado);

            // Aplicar formatação para exibir o valor como percentual na planilha
            sheet.getRange(i + 1, percentualColIndex).setNumberFormat('0.00%'); // Exibir como percentual com duas casas decimais
            break;
        }
    }
}

// Função principal para filtrar as vendas de um diretor em um intervalo de datas
function filtrarVendasDiretor(diretor, startDateStr, endDateStr) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();
  
    const startDate = new Date(startDateStr);
    const endDate = new Date(endDateStr);
  
    const idContratoColIndex = data[0].indexOf('Id_Contrato');
    const dataContratoColIndex = data[0].indexOf('Data_Contrato');
    const contratoColIndex = data[0].indexOf('Contrato');
    const diretorColIndex = data[0].indexOf('Diretor_Nome');  // Coluna "Diretor"
    const gerenteVendaColIndex = data[0].indexOf('Gerente_Venda_Nome'); // Coluna "Gerente de Venda"
    const gerenteCaptacaoColIndex = data[0].indexOf('Gerente_Captacao_Nome'); // Coluna "Gerente de Captação"
    const liquido61ColIndex = data[0].indexOf('Valor_Comissao');
    const percentualPremiacaoColIndex = data[0].indexOf('%_Diretor');
    const valorComissaoColIndex = data[0].indexOf('Valor_Comissao');  // Coluna "Valor_Comissao"
    const valorTotal61ColIndex = data[0].indexOf('Valor_Total_61');   // Coluna "Valor_Total_61"

    let totalPeriodo = 0;
    let totalEmpresaPeriodo = 0;

    // Limpar o array de linhas
    linhasContratos = [];

    // Atualizando a tabela HTML para incluir Gerente de Venda e Gerente de Captação
    let htmlTable = '<table><tr><th>Id_Contrato</th><th>Data_Contrato</th><th>Contrato</th><th>Diretor</th><th>Gerente_Venda</th><th>Gerente_Captacao</th><th>Valor_Comissao</th><th>Valor_Total_61</th><th>Percentual_Premiacao</th></tr>';
    
    // Filtra os dados pelo diretor e intervalo de datas
    data.forEach((row, index) => {
        if (index === 0) return; // Ignora o cabeçalho
        const rowDate = new Date(row[dataContratoColIndex]);
        const isInDateRange = rowDate >= startDate && rowDate <= endDate;

        if (isInDateRange) {
            // Armazenar o índice da linha (index + 1 porque o índice do Google Sheets é baseado em 1)
            linhasContratos.push(index + 1);

            // Somar o "Líquido Empresa no Período"
            totalEmpresaPeriodo += parseFloat(row[liquido61ColIndex]) || 0;

            // Filtrar vendas associadas ao diretor
            const isMatchingDiretor = row[diretorColIndex] === diretor;
            if (isMatchingDiretor) {
                totalPeriodo += parseFloat(row[liquido61ColIndex]) || 0;
                htmlTable += '<tr>';
                htmlTable += `<td>${row[idContratoColIndex]}</td>`;
                htmlTable += `<td>${formatarData(row[dataContratoColIndex])}</td>`;
                htmlTable += `<td>${row[contratoColIndex] || ''}</td>`;
                htmlTable += `<td>${row[diretorColIndex] || ''}</td>`;
                
                // Adicionando Gerente de Venda e Gerente de Captação
                htmlTable += `<td>${row[gerenteVendaColIndex] || ''}</td>`;
                htmlTable += `<td>${row[gerenteCaptacaoColIndex] || ''}</td>`;

                htmlTable += `<td>${formatarValor(row[valorComissaoColIndex])}</td>`;
                htmlTable += `<td>${formatarValor(row[valorTotal61ColIndex])}</td>`;
                htmlTable += `<td><input type="text" value="${row[percentualPremiacaoColIndex] || ''}" data-idcontrato="${row[idContratoColIndex]}" onchange="atualizarPercentualDiretor(this.value, ${row[idContratoColIndex]}, ${percentualPremiacaoColIndex + 1})"></td>`;
                htmlTable += '</tr>';
            }
        }
    });

    htmlTable += '</table>';

    // Cálculo do "Líquido Empresa no Ano" e "Líquido Diretor no Ano"
    const totalEmpresaAno = calcularTotalAnoEmpresa();
    const totalAno = calcularTotalAnoDiretor(diretor, startDateStr);

    // Cálculo da participação do diretor
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

// Função para calcular o total do "Líquido 61" no ano para o diretor
function calcularTotalAnoDiretor(diretor, startDateStr) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();

    const anoFiltrado = startDateStr.substring(0, 4);
    const liquido61ColIndex = data[0].indexOf('Valor_Comissao');
    const diretorColIndex = data[0].indexOf('Diretor_Nome');
    const dataContratoColIndex = data[0].indexOf('Data_Contrato');

    let totalAno = 0;

    data.forEach((row, index) => {
        if (index === 0) return; // Ignora o cabeçalho

        const rowYear = new Date(row[dataContratoColIndex]).getFullYear();
        if (rowYear == anoFiltrado) {
            const isMatchingDiretor = row[diretorColIndex] === diretor;
            if (isMatchingDiretor) {
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

// Função para obter o valor original do percentual da planilha
function obterValorOriginal(idContrato, percentualColIndex) {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    const ss = SpreadsheetApp.openById(spreadsheetId);
    const sheet = ss.getSheetByName('Vendas');
    const dataRange = sheet.getDataRange();
    const data = dataRange.getValues();

    const contratoColIndex = data[0].indexOf('Id_Contrato') + 1;

    for (let i = 1; i < data.length; i++) {
        if (data[i][contratoColIndex - 1] == idContrato) {
            const valorOriginal = data[i][percentualColIndex - 1];  // Valor original do percentual
            return valorOriginal;
        }
    }
    return null;  // Caso não encontre o contrato
}


