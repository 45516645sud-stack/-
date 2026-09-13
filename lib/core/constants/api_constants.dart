/// Cloud Functions 백엔드 엔드포인트 상수.
/// 식약처 공공데이터 API 키는 클라이언트가 아닌 Cloud Functions 쪽에만 존재한다.
class ApiConstants {
  ApiConstants._();

  static const String cloudFunctionsBaseUrl =
      'https://asia-northeast3-<YOUR_FIREBASE_PROJECT>.cloudfunctions.net';

  static const String identifyItemEndpoint = '$cloudFunctionsBaseUrl/identifyItem';
}
