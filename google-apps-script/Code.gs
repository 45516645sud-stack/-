function doGet() {
  return HtmlService.createTemplateFromFile('index')
    .evaluate()
    .setTitle('박람회 찾기')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
}

// index.html 안에서 <?!= include('Stylesheet'); ?> 처럼 다른 HTML 파일을 끼워 넣을 때 씁니다.
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}
