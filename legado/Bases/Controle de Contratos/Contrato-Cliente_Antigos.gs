function submitDataAntigo(formData, fileData, row, idContrato) {
    var ss = SpreadsheetApp.openById('1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'); // ID da planilha
    var sheet = ss.getSheetByName('Vendas');
    
    // Assegura que 'row' é um número.
    var rowNum = parseInt(row, 10);
    if (isNaN(rowNum)) {
        throw new Error("Número da linha inválido: " + row);
    }

    // Pega os dados da linha correspondente ao contrato selecionado
    var newRow = sheet.getRange(rowNum, 1, 1, 138).getValues()[0]; // Ajuste para o número correto de colunas
    var data = JSON.parse(formData); // Converte os dados do formulário para JSON

    // Obtém o nome do contrato (coluna C)
    var contratoNome = newRow[2]; // Pega o nome do contrato da coluna C

    // Verifica se existe um arquivo PDF e processa a criação da pasta e upload do arquivo
    if (fileData) {
        var rootFolderId = extractFolderIdFromLink('https://drive.google.com/drive/folders/1ovOVwI1Tn5PtWvNGXy-y9O9-p-IvaHPp');
        var rootFolder = DriveApp.getFolderById(rootFolderId);

        // Cria uma nova subpasta com o ID do contrato e o nome do contrato
        var contractFolderName = idContrato + "_" + contratoNome; // Nome da subpasta no formato correto
        var contractFolder = rootFolder.createFolder(contractFolderName);

        // Define o nome do arquivo PDF para incluir o IdContrato e o nome do contrato
        var newFileName = idContrato + "_" + contratoNome + ".pdf"; // Nome do arquivo no formato correto

        // Cria o arquivo PDF na nova subpasta
        var file = Utilities.newBlob(fileData.bytes, fileData.mimeType, newFileName);
        var uploadedFile = contractFolder.createFile(file);
        
        // Define permissões de compartilhamento do arquivo
        uploadedFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

        // Obtém o link do arquivo PDF para salvar na planilha
        var fileUrl = uploadedFile.getUrl();
        newRow[42] = fileUrl; // Coloque o link do arquivo PDF na célula apropriada
    }

    // Preencher os dados na planilha
    newRow[49] = data.nomeClienteComprador1; // Nome Comprador 1
    newRow[50] = data.cpfClienteComprador1; // CPF Comprador 1
    newRow[51] = data.nomeClienteComprador2; // Nome Comprador 2
    newRow[52] = data.cpfClienteComprador2; // CPF Comprador 2
    newRow[66] = data.nomeClienteVendedor1; // Nome Cliente Vendedor 1
    newRow[67] = data.cpfClienteVendedor1; // CPF Cliente Vendedor 1
    newRow[68] = data.nomeClienteVendedor2; // Nome Cliente Vendedor 2
    newRow[69] = data.cpfClienteVendedor2; // CPF Cliente Vendedor 2
    newRow[73] = data.nomeClienteVendedor3; // Nome Cliente Vendedor 3
    newRow[74] = data.cpfClienteVendedor3; // CPF Cliente Vendedor 3
    newRow[75] = data.nomeClienteVendedor4; // Nome Cliente Vendedor 4
    newRow[76] = data.cpfClienteVendedor4; // CPF Cliente Vendedor 4
    newRow[77] = data.nomeClienteVendedor5; // Nome Cliente Vendedor 5
    newRow[78] = data.cpfClienteVendedor5; // CPF Cliente Vendedor 5
    newRow[114] = data.nomeClienteVendedor6; // Nome Cliente Vendedor 6
    newRow[115] = data.cpfClienteVendedor6; // CPF Cliente Vendedor 6
    newRow[116] = data.nomeClienteVendedor7; // Nome Cliente Vendedor 7
    newRow[117] = data.cpfClienteVendedor7; // CPF Cliente Vendedor 7
    newRow[118] = data.nomeClienteVendedor8; // Nome Cliente Vendedor 8
    newRow[119] = data.cpfClienteVendedor8; // CPF Cliente Vendedor 8
    newRow[120] = data.nomeClienteVendedor9; // Nome Cliente Vendedor 9
    newRow[121] = data.cpfClienteVendedor9; // CPF Cliente Vendedor 9
    newRow[122] = data.nomeClienteVendedor10; // Nome Cliente Vendedor 10
    newRow[123] = data.cpfClienteVendedor10; // CPF Cliente Vendedor 10
    newRow[124] = data.nomeClienteVendedor11; // Nome Cliente Vendedor 11
    newRow[125] = data.cpfClienteVendedor11; // CPF Cliente Vendedor 11
    newRow[126] = data.nomeClienteVendedor12; // Nome Cliente Vendedor 12
    newRow[127] = data.cpfClienteVendedor12; // CPF Cliente Vendedor 12
    newRow[128] = data.nomeClienteVendedor13; // Nome Cliente Vendedor 13
    newRow[129] = data.cpfClienteVendedor13; // CPF Cliente Vendedor 13
    newRow[130] = data.nomeClienteVendedor14; // Nome Cliente Vendedor 14
    newRow[131] = data.cpfClienteVendedor14; // CPF Cliente Vendedor 14
    newRow[132] = data.nomeClienteVendedor15; // Nome Cliente Vendedor 15
    newRow[133] = data.cpfClienteVendedor15; // CPF Cliente Vendedor 15
    newRow[79] = data.nomeClienteComprador3; // Nome Cliente Comprador 3
    newRow[80] = data.cpfClienteComprador3; // CPF Cliente Comprador 3
    newRow[81] = data.nomeClienteComprador4; // Nome Cliente Comprador 4
    newRow[82] = data.cpfClienteComprador4; // CPF Cliente Comprador 4
    newRow[83] = data.nomeClienteComprador5; // Nome Cliente Comprador 5
    newRow[84] = data.cpfClienteComprador5; // CPF Cliente Comprador 5
    newRow[85] = data.nomeClienteComprador6; // Nome Cliente Comprador 6
    newRow[86] = data.cpfClienteComprador6; // CPF Cliente Comprador 6
    newRow[87] = data.nomeClienteComprador7; // Nome Cliente Comprador 7
    newRow[88] = data.cpfClienteComprador7; // CPF Cliente Comprador 7
    newRow[89] = data.nomeClienteComprador8; // Nome Cliente Comprador 8
    newRow[90] = data.cpfClienteComprador8; // CPF Cliente Comprador 8
    newRow[100] = data.nomeClienteComprador9; // Nome Cliente Comprador 9
    newRow[101] = data.cpfClienteComprador9; // CPF Cliente Comprador 9
    newRow[102] = data.nomeClienteComprador10; // Nome Cliente Comprador 10
    newRow[103] = data.cpfClienteComprador10; // CPF Cliente Comprador 10
    newRow[104] = data.nomeClienteComprador11; // Nome Cliente Comprador 11
    newRow[105] = data.cpfClienteComprador11; // CPF Cliente Comprador 11
    newRow[106] = data.nomeClienteComprador12; // Nome Cliente Comprador 12
    newRow[107] = data.cpfClienteComprador12; // CPF Cliente Comprador 12
    newRow[108] = data.nomeClienteComprador13; // Nome Cliente Comprador 13
    newRow[109] = data.cpfClienteComprador13; // CPF Cliente Comprador 13
    newRow[110] = data.nomeClienteComprador14; // Nome Cliente Comprador 14
    newRow[111] = data.cpfClienteComprador14; // CPF Cliente Comprador 14
    newRow[112] = data.nomeClienteComprador15; // Nome Cliente Comprador 15
    newRow[113] = data.cpfClienteComprador15; // CPF Cliente Comprador 15

    sheet.getRange(row, 1, 1, newRow.length).setValues([newRow]);

    return "Dados gravados com sucesso!";
}


function getContractsAntigosAntigo() {
    var sheet = SpreadsheetApp.openById('1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y').getSheetByName('Vendas');
    var range = sheet.getRange('A2:C' + sheet.getLastRow()); // Coluna A para IdContrato e C para o nome do contrato
    var values = range.getValues();
    var contracts = values.map(function(row, index) {
        return { idContrato: row[0], contract: row[2], row: index + 2 }; // Captura IdContrato (A), nome (C), e a linha
    });
    return contracts.filter(contract => contract.contract); // Filtra elementos onde o contrato está vazio
}


function extractFolderIdFromLinkAntigo(link) {
    var match = link.match(/[-\w]{25,}/);
    return match ? match[0] : null;
}


