/** CONFIGURAÇÃO **/
const APP_ID = 'NewApp-287229161-25-08-26'; // igual ao da documentação
const SPREADSHEET_ID = '1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU'; // sua planilha
// caminho base dentro da pasta do app: /appsheet/data/<APP_ID>/
const REL_PATH_BASE = `Relatorios/Visitas`; // subpasta sob a pasta do app

/**
 * Função chamada pelo AppSheet (Task: Call a script).
 * @param {string} visitaId  Id da visita (Fato_Visitas[Id_Visita])
 * @returns {string} URL pública do PDF (Drive) para mandar no WhatsApp
 */
function generateVisitaPdf(visitaId) {
  if (!visitaId) throw new Error('visitaId vazio.');

  // 1) Ler dados das sheets
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const shVisitas  = ss.getSheetByName('Fato_Visitas');
  const shAvals    = ss.getSheetByName('Fato_Avaliacao');
  const shClientes = ss.getSheetByName('Dim_Cliente_Visita');
  const shCorretores = ss.getSheetByName('Dim_Corretor');

  const visita = getRowByKey(shVisitas, 'Id_Visita', visitaId);
  if (!visita) throw new Error(`Visita ${visitaId} não encontrada.`);

  // montar objetos auxiliares
  const avals = getRowsByEq(shAvals, 'Id_Visita', visitaId);
  const clientes = getRowsByEq(shClientes, 'Id_Visita', visitaId);

  let corretorNome = '';
  if (visita.Id_Corretor) {
    const cor = getRowByKey(shCorretores, 'IdCorretor', visita.Id_Corretor);
    corretorNome = cor ? (cor.Nome || '') : '';
  }

  // 2) Preparar dados para o template
  const ctx = {
    Id_Visita: visita.Id_Visita,
    CreatedAt: visita.CreatedAt || '',
    Data_Visita: visita.Data_Visita || '',
    Proposta: visita.Proposta || '',
    Agrupador_Imovel: visita.Agrupador_Imovel || '',
    CorretorNome: corretorNome,
    Link_Audio: visita.Link_Audio || '',
    Link_Imagem: visita.Link_Imagem || '',
    // listas
    Clientes: clientes.map(c => ({ Nome_Cliente: c.Nome_Cliente || '' })),
    Avaliacoes: avals.map(a => ({
      Nome_Cliente: derefClienteNome(clientes, a.Id_Cliente),
      Localizacao: a.Localizacao || '',
      Tamanho: a.Tamanho || '',
      Planta_Imovel: a.Planta_Imovel || '',
      Qualidade_Acabamento: a.Qualidade_Acabamento || '',
      Estado_Conservacao: a.Estado_Conservacao || '',
      Condominio_AreaComun: a.Condominio_AreaComun || '',
      Preco: a.Preco || '',
      Preco_N10: a.Preco_N10 || '',
      Nota_Geral: a.Nota_Geral || ''
    })),
    TotAval: avals.length
  };

  // 3) Renderizar HTML do relatório
  const html = HtmlService.createTemplateFromFile('template');
  html.data = ctx;
  const htmlContent = html.evaluate().getContent();

  // 4) Converter HTML -> PDF
  const fileName = `Relatorio_Visita_${visitaId}.pdf`;
  const blob = Utilities.newBlob(htmlContent, 'text/html', fileName).getAs('application/pdf');

  // 5) Salvar no Drive do app em caminho determinístico:
  // /appsheet/data/<APP_ID>/Relatorios/Visitas/<Id_Visita>/Relatorio_Visita_<Id_Visita>.pdf
  const appRoot = ensureAppRootFolder_(APP_ID); // /appsheet/data/<APP_ID>
  const targetFolder = ensurePath_(appRoot, `${REL_PATH_BASE}/${visitaId}`); // cria subpastas
  // Remove arquivo antigo se existir (mesmo nome)
  const existing = targetFolder.getFilesByName(fileName);
  while (existing.hasNext()) existing.next().setTrashed(true);

  const pdfFile = targetFolder.createFile(blob).setName(fileName);

  // 6) Tornar acessível por link (ajuste conforme a política da empresa)
  pdfFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  // 7) Retornar URL pública (Drive)
  return pdfFile.getUrl();
}

/** Util: encontra linha por chave e devolve objeto {col: valor} */
function getRowByKey(sheet, keyColName, keyValue) {
  const { headers, rows } = getTable_(sheet);
  const idx = headers.indexOf(keyColName);
  if (idx < 0) throw new Error(`Coluna ${keyColName} não encontrada em ${sheet.getName()}.`);
  for (const r of rows) {
    if (String(r[idx]) === String(keyValue)) return rowToObject_(headers, r);
  }
  return null;
}

/** Util: encontra linhas por igualdade simples */
function getRowsByEq(sheet, colName, value) {
  const { headers, rows } = getTable_(sheet);
  const idx = headers.indexOf(colName);
  if (idx < 0) throw new Error(`Coluna ${colName} não encontrada em ${sheet.getName()}.`);
  const out = [];
  for (const r of rows) if (String(r[idx]) === String(value)) out.push(rowToObject_(headers, r));
  return out;
}

/** Util: deref do nome do cliente a partir de lista já carregada */
function derefClienteNome(clientes, idCliente) {
  const c = clientes.find(x => String(x.Id_Cliente) === String(idCliente));
  return c ? (c.Nome_Cliente || '') : '';
}

/** Util: carrega planilha como tabela */
function getTable_(sheet) {
  const range = sheet.getDataRange();
  const values = range.getValues();
  const headers = values.shift().map(String);
  return { headers, rows: values };
}

/** Util: array linha => objeto nomeado */
function rowToObject_(headers, row) {
  const o = {};
  headers.forEach((h, i) => o[h] = row[i]);
  return o;
}

/** Garante a pasta /appsheet/data/<APP_ID> */
function ensureAppRootFolder_(appId) {
  const appFolderName = `appsheet`;
  const dataFolderName = `data`;
  const root = DriveApp.getRootFolder();

  const appsheetFolder = getOrCreateChild_(root, appFolderName);
  const dataFolder = getOrCreateChild_(appsheetFolder, dataFolderName);
  const appIdFolder = getOrCreateChild_(dataFolder, appId);
  return appIdFolder;
}

/** Cria subpastas recursivamente sob parent a partir de "a/b/c" */
function ensurePath_(parentFolder, path) {
  const parts = path.split('/').filter(Boolean);
  let cur = parentFolder;
  for (const p of parts) cur = getOrCreateChild_(cur, p);
  return cur;
}

/** Retorna (ou cria) child folder de um parent */
function getOrCreateChild_(parent, name) {
  const it = parent.getFoldersByName(name);
  if (it.hasNext()) return it.next();
  return parent.createFolder(name);
}
