function filterFatoLead() {
  // Open the spreadsheet and select the sheet
  var spreadsheet = SpreadsheetApp.openById("1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw");
  var sheet = spreadsheet.getSheetByName("Fato_Lead");

  // Get all data from the sheet
  var data = sheet.getDataRange().getValues();

  // Define the list of codes to filter
  var codesToFilter = [887430, 775240, 861885]; // Replace with your desired codes

  // Find the column index for "Código"
  var headerRow = data[0];
  var codigoIndex = headerRow.indexOf("Código");
  if (codigoIndex === -1) {
    throw new Error("Column 'Código' not found");
  }

  // Filter rows based on codes
  var filteredData = data.filter(function(row, index) {
    // Skip the header row
    if (index === 0) return true;
    // Check if the 'Código' column value is in the codesToFilter list
    return codesToFilter.includes(row[codigoIndex]);
  });

  // Create a new sheet for the filtered data (or overwrite if it exists)
  var filteredSheetName = "Filtered_Fato_Lead";
  var filteredSheet = spreadsheet.getSheetByName(filteredSheetName);
  if (filteredSheet) {
    filteredSheet.clear();
  } else {
    filteredSheet = spreadsheet.insertSheet(filteredSheetName);
  }

  // Set the filtered data into the new sheet
  filteredSheet.getRange(1, 1, filteredData.length, filteredData[0].length).setValues(filteredData);

  Logger.log("Filtered data has been saved to the sheet: " + filteredSheetName);
}
