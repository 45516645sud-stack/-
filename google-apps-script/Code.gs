function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('박람회 찾기')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
}
