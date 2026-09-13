/// Cloud Functions 백엔드 엔드포인트 상수.
/// 식약처 공공데이터 API 키는 클라이언트가 아닌 Cloud Functions 쪽에만 존재한다.
class ApiConstants {
  ApiConstants._();

  static const String cloudFunctionsBaseUrl =
      'https://asia-northeast3-<YOUR_FIREBASE_PROJECT>.cloudfunctions.net';

  static const String identifyItemEndpoint = '$cloudFunctionsBaseUrl/identifyItem';

  /// 카카오 디벨로퍼스에서 발급받은 JavaScript 키.
  /// kakao_map_plugin은 웹뷰 기반 지도이므로 Native 키가 아닌 JS 키를 사용한다.
  static const String kakaoJavaScriptKey = '<YOUR_KAKAO_JAVASCRIPT_KEY>';
}
