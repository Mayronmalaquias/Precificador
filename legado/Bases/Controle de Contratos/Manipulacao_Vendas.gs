function criarBlobUpload(upload, nomeArquivoPadrao) {
    if (!upload) return null;

    var mimeType = upload.mimeType || 'application/pdf';
    var fileName = nomeArquivoPadrao || upload.name || 'arquivo.pdf';

    if (upload.base64) {
        var base64Limpo = String(upload.base64).replace(/^data:.*;base64,/, '');
        var bytesBase64 = Utilities.base64Decode(base64Limpo);
        return Utilities.newBlob(bytesBase64, mimeType, fileName);
    }

    // Mantém compatibilidade com o modelo antigo, caso algum envio ainda venha por bytes.
    if (upload.bytes && upload.bytes.length > 0) {
        return Utilities.newBlob(upload.bytes, mimeType, fileName);
    }

    return null;
}

function extractFolderIdFromLink(link) {
    if (!link) return '';

    var match = String(link).match(/[-\w]{25,}/);
    return match ? match[0] : '';
}

function submitData(formData, fileData, honorarioData, numeroInter) {
    var lock = LockService.getScriptLock();
    lock.waitLock(30000);

    try {
        var ss = SpreadsheetApp.openById('1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y');
        var sheet = ss.getSheetByName('Vendas');

        if (!sheet) {
            throw new Error('A aba "Vendas" não foi encontrada.');
        }

        var data = typeof formData === 'string' ? JSON.parse(formData) : formData;
        data = data || {};

        // Compatibilidade entre os nomes do HTML novo e do submitData antigo.
        data.comGerenteVenda = data.comGerenteVenda || data.comissaoGerenteVenda || 0;
        data.comGerenteCaptacao = data.comGerenteCaptacao || data.comGerenteCap || data.comissaoGerenteCaptacao || 0;
        data.comDiretor = data.comDiretor || data.comissaoDiretor || 0;

        data.comCorV1 = data.comCorV1 || data.comissaoCorretorVenda1 || 0;
        data.comCorV2 = data.comCorV2 || data.comissaoCorretorVenda2 || 0;
        data.comCorC1 = data.comCorC1 || data.comissaoCorretorCaptacao1 || 0;
        data.comCorC2 = data.comCorC2 || data.comissaoCorretorCaptacao2 || 0;

        // Validação no servidor antes de criar pasta, subir arquivo ou gravar linha.
        validarLancamentoFormulario(data);

        var nextRow = sheet.getLastRow() + 1;

        // Usa até a coluna EP, índice 145. Por isso o array precisa ter 146 posições.
        var newRow = new Array(146).fill("");

        if (sheet.getMaxColumns() < newRow.length) {
            sheet.insertColumnsAfter(
                sheet.getMaxColumns(),
                newRow.length - sheet.getMaxColumns()
            );
        }

        // Pasta raiz
        var rootFolderId = extractFolderIdFromLink(
            'https://drive.google.com/drive/folders/1ovOVwI1Tn5PtWvNGXy-y9O9-p-IvaHPp'
        );

        var rootFolder = DriveApp.getFolderById(rootFolderId);

        // ID do contrato
        var nextIdContrato = generateNextIdContrato(sheet);

        // Pasta do contrato
        var contractFolderName = nextIdContrato + "_" + (data.contrato || "sem_contrato");
        var contractFolder = rootFolder.createFolder(contractFolderName);

        // PDF principal
        var fileUrl = "";

        try {
            var fileBlob = criarBlobUpload(
                fileData,
                nextIdContrato + "_" + (data.contrato || "contrato") + ".pdf"
            );

            if (fileBlob) {
                var uploadedFile = contractFolder.createFile(fileBlob);
                uploadedFile.setSharing(
                    DriveApp.Access.ANYONE_WITH_LINK,
                    DriveApp.Permission.VIEW
                );
                fileUrl = uploadedFile.getUrl();
            } else {
                Logger.log("Nenhum arquivo PDF principal recebido.");
            }
        } catch (ePdf) {
            Logger.log("Erro ao processar arquivo PDF principal: " + ePdf);
            fileUrl = "Erro ao processar PDF";
        }

        // PDF de honorário
        var honorarioFileUrl = "";

        try {
            var honorarioBlob = criarBlobUpload(
                honorarioData,
                nextIdContrato + "_Contrato_Honorario.pdf"
            );

            if (honorarioBlob) {
                var uploadedHonorarioFile = contractFolder.createFile(honorarioBlob);
                uploadedHonorarioFile.setSharing(
                    DriveApp.Access.ANYONE_WITH_LINK,
                    DriveApp.Permission.VIEW
                );
                honorarioFileUrl = uploadedHonorarioFile.getUrl();
            } else {
                Logger.log("Nenhum arquivo de honorário recebido.");
            }
        } catch (eHon) {
            Logger.log("Erro ao processar arquivo de honorário: " + eHon);
            honorarioFileUrl = "Erro ao processar honorário PDF";
        }

        // A até F
        newRow[0] = nextIdContrato.toString();
        newRow[1] = data.mes || "";
        newRow[2] = data.contrato || "";
        newRow[3] = data.valorNegocio || "";
        newRow[4] = data.valorComissao || "";
        newRow[5] = data.valorTotal61 || "";

        // O até AB — comissões e nomes
        newRow[14] = data.comGerenteVenda || "";
        newRow[15] = data.gerenteVendaNome || "";
        newRow[16] = data.comGerenteCaptacao || "";
        newRow[17] = data.gerenteCaptacaoNome || "";
        newRow[18] = data.comDiretor || "";
        newRow[19] = data.diretorNome || "";
        newRow[20] = data.comCorV1 || "";
        newRow[21] = data.corretorVenda1Nome || "";
        newRow[22] = data.comCorV2 || "";
        newRow[23] = data.corretorVenda2Nome || "";
        newRow[24] = data.comCorC1 || "";
        newRow[25] = data.corretorCaptacao1Nome || "";
        newRow[26] = data.comCorC2 || "";
        newRow[27] = data.corretorCaptacao2Nome || "";

        // AC — imóvel parceiro
        newRow[28] = data.imovelParceiro || "FALSE";

        // AD em diante — datas principais
        newRow[29] = data.dataAssinatura || "";
        newRow[30] = data.dataEscritura || "";
        newRow[31] = data.dataQuitacao || "";
        newRow[32] = data.dataPosse || "";
        newRow[33] = data.dataParcela1Comissao || "";
        newRow[34] = data.correspondenteBancario || "";
        newRow[35] = data.dataEnvioDocsFinanc || "";
        newRow[36] = data.dataVistoria || "";

        // Link do contrato
        newRow[42] = fileUrl;

        // Clientes compradores
        newRow[49] = data.nomeClienteCompradores1 || "";
        newRow[50] = data.cpfClienteCompradores1 || "";
        newRow[51] = data.nomeClienteCompradores2 || "";
        newRow[52] = data.cpfClienteCompradores2 || "";

        // Informações gerais
        newRow[53] = data.financiamento || "";
        newRow[54] = data.imobVenda || "";
        newRow[55] = data.imobCap || "";

        // Clientes vendedores
        newRow[66] = data.nomeClienteVendedores1 || "";
        newRow[67] = data.cpfClienteVendedores1 || "";

        // Parcelas de comissão
        newRow[85] = data.valorPComissao2 || "";
        newRow[86] = data.valorPComissao3 || "";
        newRow[87] = data.valorPComissao4 || "";
        newRow[88] = data.dataParcela4Comissao || "";
        newRow[89] = data.valorPComissao5 || "";
        newRow[90] = data.dataParcela5Comissao || "";

        // Bairro e tipo
        newRow[98] = data.bairro || "";
        newRow[99] = data.tipo || "";

        // Checkboxes de remoção do cálculo da NF
        newRow[139] = data.removeCalcGerenteVenda || "FALSE";
        newRow[140] = data.removeCalcGerenteCaptacao || "FALSE";
        newRow[141] = data.removeCalcDiretor || "FALSE";

        // Dados finais
        newRow[142] = data.codigoImovel || "";
        newRow[143] = data.dataPagamentoSinal || "";

        // Parcelas intermediárias
        var parcelas = [];
        numeroInter = Number(numeroInter || data.parcelaCount || 0);

        for (var i = 1; i <= numeroInter; i++) {
            if (data["dataParcelaIntermediaria" + i]) {
                parcelas.push(data["dataParcelaIntermediaria" + i]);
            }
        }

        newRow[144] = parcelas.join(';');

        // Link do contrato de honorário
        newRow[145] = honorarioFileUrl;

        sheet.getRange(nextRow, 1, 1, newRow.length).setValues([newRow]);

        return {
            ok: true,
            message: "Dados gravados com sucesso!",
            row: nextRow,
            idContrato: nextIdContrato
        };

    } catch (e) {
        Logger.log("Erro em submitData: " + e);
        throw e;
    } finally {
        lock.releaseLock();
    }
}
/**
 * Gera um Id_Contrato aleatório com o formato:
 *  C + 4 caracteres aleatórios (letras minúsculas/dígitos) + últimos 2 dígitos do ano
 *  Ex.: "Ca63125", "Cf8x125"  (ano 2025 → "25")
 *  Garante, na medida do possível, que não repita um ID já existente na coluna A da aba "Vendas".
 */
function generateNextIdContrato(sheet) {
    // Data atual em Brasília
    var now = new Date();
    var brDate = new Date(now.toLocaleString("en-US", { timeZone: "America/Sao_Paulo" }));
    var yearSuffix = brDate.getFullYear().toString().slice(-2); // últimos 2 dígitos do ano

    // Coletar IDs já existentes na coluna A (Id_Contrato), a partir da linha 2
    var lastRow = sheet.getLastRow();
    var existingIds = [];
    if (lastRow > 1) {
        var idValues = sheet.getRange(2, 1, lastRow - 1, 1).getValues(); // Coluna A
        existingIds = idValues
            .map(function(row) { return row[0]; })
            .filter(function(v) { return v !== "" && v !== null; });
    }

    var chars = "abcdefghijklmnopqrstuvwxyz0123456789";

    function gerarIdAleatorio() {
        var meio = "";
        for (var i = 0; i < 4; i++) {
            meio += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return "C" + meio + yearSuffix;
    }

    // Tenta gerar um ID que não exista ainda
    var maxTentativas = 50;
    var novoId;
    for (var tentativa = 0; tentativa < maxTentativas; tentativa++) {
        novoId = gerarIdAleatorio();
        if (existingIds.indexOf(novoId) === -1) {
            return novoId.toString();
        }
    }

    // Em caso extremo (muito improvável), retorna o último gerado mesmo assim
    return novoId.toString();
}



// Função para iniciar cálculos após a gravação dos dados
function startCalculations(rowIndex) {
    Utilities.sleep(1000);

    if (rowIndex) {
        calculateCommissions(rowIndex);
    } else {
        calculateCommissions();
    }
}

// Função para preencher os dados de gerentes, corretores e diretores no dropdown
function getDropdownData() {
    const ss = SpreadsheetApp.openById('1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw');
    
    // Obtém as planilhas necessárias
    const gerentesSheet = ss.getSheetByName('Dim_Gerente');
    const corretoresSheet = ss.getSheetByName('Dim_Corretor');
    const diretoresSheet = ss.getSheetByName('Dim_Diretor');
    
    // Obtém os dados das planilhas
    const gerentesData = gerentesSheet.getRange('A2:B' + gerentesSheet.getLastRow()).getValues();
    const corretoresData = corretoresSheet.getRange('A2:B' + corretoresSheet.getLastRow()).getValues();
    const diretoresData = diretoresSheet.getRange('A2:B' + diretoresSheet.getLastRow()).getValues();
    
    // Retorna um objeto contendo os dados de gerentes, corretores e diretores
    return {
        gerentes: gerentesData.map(row => ({ id: row[0], nome: row[1] })),
        corretores: corretoresData.map(row => ({ id: row[0], nome: row[1] })),
        diretores: diretoresData.map(row => ({ id: row[0], nome: row[1] }))
    };
}

function getDropdownDataBairroTipo() {
    const ss = SpreadsheetApp.openById('1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw');
    const bairroSheet = ss.getSheetByName('Dim_Bairro');
    const tipoSheet = ss.getSheetByName('Dim_Tipo');

    const bairroData = bairroSheet.getRange('A2:B' + bairroSheet.getLastRow()).getValues();
    const tipoData = tipoSheet.getRange('A2:B' + tipoSheet.getLastRow()).getValues();

    return {
        bairro: bairroData.map(row => ({ id: row[0], nome: row[1] })),
        tipo: tipoData.map(row => ({ id: row[0], nome: row[1] })),
    };
}


function startBV() {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    var ss = SpreadsheetApp.openById(spreadsheetId); 
    var sheet = ss.getSheetByName("Vendas"); // Nome da aba correta
    var lastRow = sheet.getLastRow();
    submitDataBV(lastRow); // Chame a função diretamente se ela estiver no mesmo projeto
}


function startTrello() {
    const spreadsheetId = '1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y'; // Substitua pelo ID da sua planilha
    var ss = SpreadsheetApp.openById(spreadsheetId); 
    var sheet = ss.getSheetByName("Vendas"); // Nome da aba correta
    var lastRow = sheet.getLastRow();
    submitDataToTrello(lastRow); // Chame a função diretamente se ela estiver no mesmo projeto
}


// Função para extrair o ID da pasta a partir do link
function extractFolderIdFromLink(folderLink) {
    var folderId = folderLink.match(/[-\w]{25,}/); // Expressão regular para extrair o ID
    if (folderId) {
        return folderId[0]; // Retorna o ID da pasta
    } else {
        throw new Error("Link de pasta inválido.");
    }
}
